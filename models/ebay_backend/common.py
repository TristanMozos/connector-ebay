# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2021 Halltic Tech S.L. (https://www.halltic.com)
#                  Tristán Mozos <tristan.mozos@halltic.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from datetime import datetime, timedelta

from decorator import contextmanager
from odoo import models, fields, api, _

from ...components.backend_adapter import EbayAPI

_logger = logging.getLogger(__name__)

IMPORT_DELTA_BUFFER = 120  # seconds


class EbayBackend(models.Model):
    _name = 'ebay.backend'
    _description = 'Ebay Backend'
    _inherit = 'connector.backend'

    name = fields.Char('name', required=True)

    client_id = fields.Char('clientID')
    dev_id = fields.Char('devId')
    client_secret = fields.Char('clientSecret')
    token = fields.Char('token')
    token_valid_until = fields.Datetime('tokenValidUntil')
    automatically_get_token = fields.Boolean('Automatically get token', default=False)
    client_id_test = fields.Char('Test clientID')
    dev_id_test = fields.Char('Test devId')
    client_secret_test = fields.Char('Test clientSecret')
    token_test = fields.Char('Test token')
    token_valid_until_test = fields.Datetime('tokenValidUntil')
    automatically_get_test_token = fields.Boolean('Automatically get test token', default=False)

    no_sales_order_sync = fields.Boolean(string='Sync sales order', default=False)

    stock_sync = fields.Boolean(string='Sync stock products', default=False)

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        help='Warehouse used to compute the '
             'stock quantities.',
    )

    import_sales_from_date = fields.Datetime(
        string='Import sales from date',
    )

    import_updated_sales_from_date = fields.Datetime(
        string='Import updated sales from date',
    )

    sale_prefix = fields.Char(
        string='Sale Prefix',
        help="A prefix put before the name of imported sales orders.\n"
             "For instance, if the prefix is 'eby-', the sales "
             "order 100000692 in eBay, will be named 'eby-100000692' "
             "in Odoo.",
        default='eby-'
    )

    warehouse_id = fields.Many2one(
        comodel_name='stock.warehouse',
        string='Warehouse',
        required=True,
        help='Warehouse used to compute the '
             'stock quantities.',
    )

    company_id = fields.Many2one(
        comodel_name='res.company',
        related='warehouse_id.company_id',
        string='Company',
        readonly=True,
    )

    team_id = fields.Many2one(comodel_name='crm.team', string='Sales Team')

    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal to invoice the orders', help='Journal to invoice the orders')

    invoice_order_automatically = fields.Boolean('Invoice order automatically', default=False)

    cancel_order_if_cancelled_on_ebay = fields.Boolean('Cancel order if the order is cancelled on eBay')

    days_passed_to_invoice_order = fields.Integer('Days passed to invoice order', default=7)

    prod_environment = fields.Boolean("Environment", help="Set to True if your credentials are certified for production.")

    _sql_constraints = [
        ('sale_prefix_uniq', 'unique(sale_prefix)',
         "A backend with the same sale prefix already exists")
    ]

    def toggle_prod_environment(self):
        for c in self:
            c.prod_environment = not c.prod_environment

    @contextmanager
    def work_on(self, model_name, **kwargs):
        self.ensure_one()
        # We create a eBay Client API here, so we can create the
        # client once (lazily on the first use) and propagate it
        # through all the sync session, instead of recreating a client
        # in each backend adapter usage.
        with EbayAPI(self) as ebay_api:
            _super = super(EbayBackend, self)
            # from the components we'll be able to do: self.work.ebay_api
            with _super.work_on(
                    model_name, ebay_api=ebay_api, **kwargs) as work:
                yield work

    def _import_sale_orders(self,
                            import_start_time=None,
                            import_end_time=None,
                            update_import_date=True):
        for backend in self:
            user = backend.warehouse_id.company_id.user_tech_id
            if not user:
                user = self.env['res.users'].browse(self.env.uid)

            if not backend.import_updated_sales_from_date:
                backend.import_updated_sales_from_date = backend.import_sales_from_date

            if not import_end_time:
                import_end_time = datetime.strptime(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S') - timedelta(minutes=2)

            # If the start date to get sales is empty we put now as date
            if not import_start_time:
                if backend.import_sales_from_date:
                    import_start_time = datetime.strptime(backend.import_sales_from_date, '%Y-%m-%d %H:%M:%S')
                else:
                    import_start_time = import_end_time

                sale_binding_model = self.env['ebay.sale.order']
                if user != self.env.user:
                    sale_binding_model = sale_binding_model.sudo(user)
                filters = {'CreateTimeFrom':import_start_time.isoformat(), 'CreateTimeTo':import_end_time.isoformat()}
                sale_binding_model.import_batch(backend, filters=filters)

            if update_import_date:
                backend.write({'import_sales_from_date':import_end_time})

        return True

    def _import_updated_sales(self,
                              import_start_time=None,
                              import_end_time=None,
                              update_import_date=True):

        for backend in self:
            user = backend.warehouse_id.company_id.user_tech_id
            if not user:
                user = self.env['res.users'].browse(self.env.uid)
            sale_binding_model = self.env['ebay.sale.order']
            if user != self.env.user:
                sale_binding_model = sale_binding_model.sudo(user)

            if not import_end_time:
                # We minus two minutes to now time
                import_end_time = datetime.strptime(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), '%Y-%m-%d %H:%M:%S') - timedelta(minutes=2)
            if not import_start_time:
                if backend.import_sales_from_date:
                    import_start_time = datetime.strptime(backend.import_updated_sales_from_date, '%Y-%m-%d %H:%M:%S')
                else:
                    import_start_time = import_end_time

            sale_binding_model.import_batch(backend, filters={'ModTimeFrom':import_start_time.isoformat(),
                                                              'ModTimeTo':import_end_time.isoformat()})
            if update_import_date:
                backend.write({'import_updated_sales_from_date':import_end_time})

    def _get_token(self):
        
        return

    @api.model
    def _ebay_backend(self, callback, domain=None):
        if domain is None:
            domain = []
        backends = self.search(domain)
        if backends:
            getattr(backends, callback)()

    @api.model
    def _scheduler_import_sale_orders(self, domain=None):
        self._ebay_backend('_import_sale_orders', domain=domain)

    @api.model
    def _scheduler_invoice_orders_automatically(self, domain=None):
        self._ebay_backend('_invoice_orders', domain=domain)
