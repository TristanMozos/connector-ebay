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
from re import search as re_search

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.queue_job.exception import NothingToDoJob, FailedJobError

from ...components.mapper import normalize_datetime
from ...exception import OrderImportRuleRetry

_logger = logging.getLogger(__name__)


class SaleOrderBatchImporter(Component):
    _name = 'ebay.sale.order.batch.importer'
    _inherit = 'ebay.direct.batch.importer'
    _apply_on = 'ebay.sale.order'

    # TODO change direct batch importer for delayed batch importer

    '''
    def _import_record(self, external_id, job_options=None, **kwargs):
        job_options = {
            'max_retries':0,
            'priority':5,
        }
        
        return super(SaleOrderBatchImporter, self)._import_record(
            external_id, job_options=job_options)
    '''


class SaleOrderImportMapper(Component):
    _name = 'ebay.sale.order.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = 'ebay.sale.order'

    direct = [('order_id', 'external_id'),
              ('order_id', 'id_ebay_order'),
              ('date_order', 'date_purchase'),
              ('total_product_price', 'total_product_amount'),
              ('', 'total_ship_amount'),
              ('earlest_delivery_date', 'date_earliest_delivery'),
              ('earlest_ship_date', 'date_earliest_ship'),
              ('lastest_delivery_date', 'date_latest_delivery'),
              ('lastest_ship_date', 'date_latest_ship'),
              ('FulfillmentChannel', 'fullfillment_channel'),
              ('ship_service_level', 'shipment_service_level_category'),
              ]

    children = [('lines', 'ebay_order_line_ids', 'ebay.sale.order.line'), ]

    def _add_shipping_line(self, map_record, values):
        record = map_record.source
        amount_incl = float(record.get('total_ship_amount') or 0.0)
        line_builder = self.component(usage='order.line.builder.shipping')
        # add even if the price is 0, otherwise odoo will add a shipping
        # line in the order when we ship the picking
        line_builder.price_unit = amount_incl

        if values.get('carrier_id'):
            carrier = self.env['delivery.carrier'].browse(values['carrier_id'])
            line_builder.product = carrier.product_id

        line = (0, 0, line_builder.get_line())
        values['order_line'].append(line)
        return values

    def finalize(self, map_record, values):
        values.setdefault('order_line', [])
        # values = self._add_shipping_line(map_record, values)
        values.update({
            'partner_id':self.partner_id,
            'partner_invoice_id':self.partner_id,
            'partner_shipping_id':self.partner_id,
        })

    @mapping
    def name(self, record):
        name = record['order_id']
        prefix = self.backend_record.sale_prefix
        if prefix:
            name = prefix + name
        return {'name':name}

    @mapping
    def partner_id(self, record):
        binder = self.binder_for('ebay.res.partner')
        partner = binder.to_internal(record['partner']['email'], unwrap=True)
        assert partner, (
                "customer_id %s should have been imported in "
                "SaleOrderImporter._import_dependency" % record['partner']['email'])
        return {'partner_id':partner.id}

    @mapping
    def sales_team(self, record):
        team = self.env['crm.team'].search([('name', '=', 'eBay Sales')])
        if team:
            return {'team_id':team.id}

    @mapping
    def warehouse_id(self, record):
        fullfillment = record.get('FulfillmentChannel')
        if not fullfillment or fullfillment == 'MFN':
            return {'warehouse_id':self.backend_record.warehouse_id.id}
        if fullfillment == 'AFN':
            return {'fba_warehouse_id':self.backend_record.fba_warehouse_id.id}

    @mapping
    def currency_id(self, record):
        if record['currency']:
            currency = self.env['res.currency'].search([('name', '=', record['currency'])])
            if currency:
                return {'currency_id':currency.id}

    @mapping
    def total_product_amount(self, record):
        if record.get('lines'):
            total_product_amount = 0.
            for line in record['lines']:
                total_product_amount += float(line['item_price'] or 0.)

            record['total_pruduct_amount'] = total_product_amount
            return {'total_pruduct_amount':total_product_amount}

        return

    @mapping
    def total_ship_amount(self, record):
        if record.get('lines'):
            total_ship_amount = 0.
            for line in record['lines']:
                total_ship_amount += float(line['ship_price'] or 0.)

            record['total_ship_amount'] = total_ship_amount
            return {'total_ship_amount':total_ship_amount}

        return

    @mapping
    def total_amount(self, record):
        if record.get('lines'):
            total_amount = 0.
            for line in record['lines']:
                total_amount += float(line['item_price'] or 0.) + float(line['ship_price'] or 0.)

            record['total_amount'] = total_amount
            return {'total_amount':total_amount}

        return

    # partner_id, partner_invoice_id, partner_shipping_id
    # are done in the importer

    @mapping
    def backend_id(self, record):
        return {'backend_id':self.backend_record.id}


class SaleOrderImporter(Component):
    _name = 'ebay.sale.order.importer'
    _inherit = 'ebay.importer'
    _apply_on = ['ebay.sale.order']

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        if self.binder.to_internal(self.external_id):
            return _('Already imported')

    def _import_dependencies(self):
        importer = self.component(usage='record.importer', model_name='ebay.res.partner')
        importer.ebay_record = self.ebay_record['partner']
        self._import_dependency(external_id=self.ebay_record['partner']['email'], binding_model='ebay.res.partner', importer=importer)
        self.ebay_record['partner_id'] = self.env['ebay.res.partner'].search([('email', '=', self.ebay_record['partner']['email'])]).id

    def _create(self, data):
        import wdb
        wdb.set_trace()
        binding = super(SaleOrderImporter, self)._create(data)
        if binding.fiscal_position_id:
            binding.odoo_id._compute_tax_id()
        return binding

    def _get_ebay_data(self):
        if self.ebay_record:
            return self.ebay_record
        return self.backend_adapter.read(external_id=self.external_id)

    def _create_data(self, map_record, **kwargs):
        return super(SaleOrderImporter, self)._create_data(
            map_record,
            tax_include=True,
            partner_id=self.ebay_record['partner_id'],
            partner_invoice_id=self.ebay_record['partner_id'],
            partner_shipping_id=self.ebay_record['partner_id'],
            **kwargs)

    def _update_data(self, map_record, **kwargs):
        return super(SaleOrderImporter, self)._update_data(
            map_record,
            tax_include=True,
            **kwargs)

    def _after_import(self, binding):
        """ Hook called at the end of the import """
        return

    def run(self, external_id, force=False):
        """ Run the synchronization

        :param external_id: identifier of the record on eBay
        """
        if external_id and (isinstance(external_id, list) or isinstance(external_id, tuple)):
            self.external_id = external_id[0]
            self.ebay_record = external_id[1]
        else:
            self.external_id = external_id
        _super = super(SaleOrderImporter, self)
        _super.run(self.external_id, force)


class SaleOrderLineImportMapper(Component):
    _name = 'ebay.sale.order.line.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = 'ebay.sale.order.line'

    direct = [('qty_ordered', 'product_uom_qty'),
              ('qty_ordered', 'product_qty'),
              ('name', 'name'),
              ('item_id', 'external_id'),
              ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for('ebay.product.product')
        product = binder.to_internal(record['sku'], unwrap=True)
        assert product, (
                "product_id %s should have been imported in "
                "SaleOrderImporter._import_dependencies" % record['product_id'])
        return {'product_id':product.id}

    @mapping
    def price(self, record):
        return {'price_unit':record['price_unit']}

    def _import_dependencies(self):
        record = self.ebay_record

        # Check if the product is imported
        product = self.env['ebay.product.product'].search([('sku', '=', record.get('sku'))])
        if not product:
            self._import_dependency(record['sku'], 'ebay.product.product')

    def run(self, external_id, force=False):
        """ Run the synchronization

        :param external_id: identifier of the record on eBay
        """
        if external_id and (isinstance(external_id, list) or isinstance(external_id, tuple)):
            self.external_id = external_id[0]
            self.ebay_record = external_id[1]
        else:
            self.external_id = external_id
        _super = super(SaleOrderImporter, self)
        _super.run(external_id[0], force)
