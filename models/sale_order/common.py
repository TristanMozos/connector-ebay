# -*- coding: utf-8 -*-
# Copyright 2019 Halltic eSolutions S.L.
# © 2019 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import xmlrpclib

import odoo.addons.decimal_precision as dp
from odoo import models, fields, api, _
from odoo.addons.component.core import Component
from odoo.addons.connector.exception import IDMissingInBackend
from odoo.addons.queue_job.job import job

_logger = logging.getLogger(__name__)


class EbaySaleOrder(models.Model):
    _name = 'ebay.sale.order'
    _inherit = 'ebay.binding'
    _description = 'eBay Sale Order'
    _inherits = {'sale.order':'odoo_id'}

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    odoo_id = fields.Many2one(comodel_name='sale.order',
                              string='Sale Order',
                              required=True,
                              ondelete='cascade')

    ebay_order_line_ids = fields.One2many(
        comodel_name='ebay.sale.order.line',
        inverse_name='ebay_order_id',
        string='eBay Order Lines'
    )
    partner_id = fields.Many2one('ebay.res.partner', "Id of partner", required=False)
    id_ebay_order = fields.Char(string='eBay Order Id', help='An eBay-defined order identifier', required=True)
    date_purchase = fields.Datetime('The date of purchase', required=False)
    order_status_id = fields.Many2one('ebay.config.order.status', "order_status_id", required=False)
    total_product_amount = fields.Float('The total charge for the products into the order.', required=True, default=0.0)
    total_ship_amount = fields.Float('The total charge for the ship into the order.', required=True, default=0.0)
    total_amount = fields.Float('The total charge for the order.', required=True, default=0.0)
    currency_total_amount = fields.Many2one('res.currency', 'Currency of total amount',
                                            default=_get_default_currency_id,
                                            required=False)
    number_items_shipped = fields.Integer('The number of items shipped.', required=False)
    number_items_unshipped = fields.Integer('The number of items unshipped.', required=False)
    buyer_email = fields.Char('buyer_email', required=False)
    # The name of the buyer.
    buyer_name = fields.Char('buyer_name', required=False)
    # The start of the time period that you have committed to ship the order.
    # In ISO 8601 date time format.
    date_earliest_ship = fields.Datetime('date_earliest_ship', required=False)
    # The end of the time period that you have committed to ship the order. In
    # ISO 8601 date time format.
    date_latest_ship = fields.Datetime('date_latest_ship', required=False)
    # The start of the time period that you have commited to fulfill the
    # order. In ISO 8601 date time format.
    date_earliest_delivery = fields.Datetime('date_earliest_delivery', required=False)
    # The end of the time period that you have commited to fulfill the order.
    # In ISO 8601 date time format.
    date_latest_delivery = fields.Datetime('date_latest_delivery', required=False)

    @job(default_channel='root.ebay')
    @api.model
    def import_record(self, backend, external_id):
        _super = super(EbaySaleOrder, self)
        return _super.import_record(backend, external_id)

    @api.model
    def create(self, vals):
        ebay_order_id = vals['id_ebay_order']
        binding = self.env['ebay.sale.order'].browse(ebay_order_id)
        vals['ebay_order_id'] = binding.odoo_id.id
        binding = super(EbaySaleOrderLine, self).create(vals)
        return binding


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    ebay_bind_ids = fields.One2many(
        comodel_name='ebay.sale.order',
        inverse_name='odoo_id',
        string="eBay Bindings",
    )

    def _ebay_cancel(self):
        """ Cancel sales order on eBay

        Do not export the other state changes, eBay handles them itself
        when it receives shipments and invoices.
        """
        for order in self:
            old_state = order.state
            if old_state == 'cancel':
                continue  # skip if already canceled
            for binding in order.ebay_bind_ids:
                job_descr = _("Cancel sales order %s") % (binding.external_id,)
                binding.with_delay(
                    description=job_descr
                ).export_state_change(allowed_states=['cancel'])

    @api.multi
    def write(self, vals):
        if vals.get('state') == 'cancel':
            self._ebay_cancel()
        return super(SaleOrder, self).write(vals)

    def _ebay_link_binding_of_copy(self, new):
        # link binding of the canceled order to the new order, so the
        # operations done on the new order will be sync'ed with eBay
        if self.state != 'cancel':
            return
        binding_model = self.env['ebay.sale.order']
        bindings = binding_model.search([('odoo_id', '=', self.id)])
        bindings.write({'odoo_id':new.id})

        for binding in bindings:
            # the sales' status on eBay is likely 'canceled'
            # so we will export the new status (pending, processing, ...)
            job_descr = _("Reopen sales order %s") % (binding.external_id,)
            binding.with_delay(
                description=job_descr
            ).export_state_change()

    @api.multi
    def copy(self, default=None):
        self_copy = self.with_context(__copy_from_quotation=True)
        new = super(SaleOrder, self_copy).copy(default=default)
        self_copy._ebay_link_binding_of_copy(new)
        return new


class EbaySaleOrderLine(models.Model):
    _name = 'ebay.sale.order.line'
    _inherit = 'ebay.binding'
    _description = 'eBay Sale Order Line'
    _inherits = {'sale.order.line':'odoo_id'}

    ebay_order_id = fields.Many2one(comodel_name='ebay.sale.order',
                                    string='eBay Sale Order',
                                    required=True,
                                    ondelete='cascade',
                                    index=True)
    odoo_id = fields.Many2one(comodel_name='sale.order.line',
                              string='Sale Order Line',
                              required=True,
                              ondelete='cascade')
    backend_id = fields.Many2one(
        related='ebay_order_id.backend_id',
        string='eBay Backend',
        readonly=True,
        store=True,
        # override 'ebay.binding', can't be INSERTed if True:
        required=False,
    )

    product_id = fields.Many2one('ebay.product.product')
    qty_shipped = fields.Integer()
    qty_ordered = fields.Integer()
    item_price = fields.Float()
    fee = fields.Float('Item fee',
                       compute='_compute_item_fee',
                       digits=dp.get_precision('Product Price'),
                       store=True,
                       readonly=True)

    def _compute_item_fee(self):
        return 0.0

    @api.model
    def create(self, vals):
        ebay_order_id = vals['ebay_order_id']
        binding = self.env['ebay.sale.order'].browse(ebay_order_id)
        vals['order_id'] = binding.odoo_id.id
        binding = super(EbaySaleOrderLine, self).create(vals)
        # FIXME triggers function field
        # The amounts (amount_total, ...) computed fields on 'sale.order' are
        # not triggered when ebay.sale.order.line are created.
        # It might be a v8 regression, because they were triggered in
        # v7. Before getting a better correction, force the computation
        # by writing again on the line.
        # line = binding.odoo_id
        # line.write({'price_unit': line.price_unit})
        return binding


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    ebay_bind_ids = fields.One2many(
        comodel_name='ebay.sale.order.line',
        inverse_name='odoo_id',
        string="eBay Bindings",
    )

    @api.model
    def create(self, vals):
        old_line_id = None
        if self.env.context.get('__copy_from_quotation'):
            # when we are copying a sale.order from a canceled one,
            # the id of the copied line is inserted in the vals
            # in `copy_data`.
            old_line_id = vals.pop('__copy_from_line_id', None)
        new_line = super(SaleOrderLine, self).create(vals)
        if old_line_id:
            # link binding of the canceled order lines to the new order
            # lines, happens when we are using the 'New Copy of
            # Quotation' button on a canceled sales order
            binding_model = self.env['ebay.sale.order.line']
            bindings = binding_model.search([('odoo_id', '=', old_line_id)])
            if bindings:
                bindings.write({'odoo_id':new_line.id})
        return new_line

    @api.multi
    def copy_data(self, default=None):
        data = super(SaleOrderLine, self).copy_data(default=default)[0]
        if self.env.context.get('__copy_from_quotation'):
            # copy_data is called by `copy` of the sale.order which
            # builds a dict for the full new sale order, so we lose the
            # association between the old and the new line.
            # Keep a trace of the old id in the vals that will be passed
            # to `create`, from there, we'll be able to update the
            # eBay bindings, modifying the relation from the old to
            # the new line.
            data['__copy_from_line_id'] = self.id
        return [data]


class SaleOrderAdapter(Component):
    _name = 'ebay.sale.order.adapter'
    _inherit = 'ebay.adapter'
    _apply_on = 'ebay.sale.order'

    def _call(self, method, arguments):
        try:
            return super(SaleOrderAdapter, self)._call(method, arguments)
        except:
            raise
