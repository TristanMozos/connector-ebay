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
from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


def chunks(items, length):
    for index in xrange(0, len(items), length):
        yield items[index:index + length]


class EbayProductProduct(models.Model):
    _name = 'ebay.product.product'
    _inherit = 'ebay.binding'
    _inherits = {'product.product':'odoo_id'}
    _description = 'eBay Product'

    odoo_id = fields.Many2one(comodel_name='product.product',
                              string='Product',
                              required=True,
                              ondelete='restrict')

    id_item = fields.Char('ItemID', readonly=True)
    id_type_product = fields.Selection(selection=[('UPC', 'UPC'),
                                                  ('EAN', 'EAN'), ],
                                       string='Type product Id')

    id_product = fields.Char()
    status = fields.Char('status', required=False)
    sku = fields.Char('SKU', required=True, readonly=True)
    brand = fields.Char('Brand')
    created_at = fields.Date('Created At (on eBay)')
    updated_at = fields.Date('Updated At (on eBay)')
    ebay_qty = fields.Float(string='Computed Quantity',
                            help="Last computed quantity to send "
                                 "on eBay.")

    product_product_ad_ids = fields.One2many('ebay.product.product.ad', 'product_id',
                                             string='Product data on marketplaces', copy=True)

    RECOMPUTE_QTY_STEP = 1000  # products at a time

    @api.model
    def import_record(self, backend, external_id):
        _super = super(EbayProductProduct, self)
        return _super.import_record(backend, external_id)


class ProductMarketplaceData(models.Model):
    _name = 'ebay.product.product.ad'
    _inherits = {'product.template':'odoo_id'}
    _description = 'eBay Product Ad'

    odoo_id = fields.Many2one(comodel_name='product.template',
                              string='PriceList',
                              required=True,
                              ondelete='restrict')

    product_id = fields.Many2one('ebay.product.product', 'product_product_ad_ids', ondelete='cascade', required=True,
                                 readonly=True)
    title = fields.Char('Product_name', required=False)
    price = fields.Float('Price', required=False)  # This price have the tax included
    currency_price = fields.Many2one('res.currency', 'Currency price', required=False)
    price_ship = fields.Float('Price of ship', required=False)  # This price have the tax included
    currency_ship_price = fields.Many2one('res.currency', 'Currency price ship', required=False)
    status = fields.Selection(selection=[('Active', 'Active'),
                                         ('Inactive', 'Inactive'),
                                         ('Unpublished', 'Unpublished'),
                                         ('Submmited', 'Submmited')],
                              string='Status', default='Active')
    stock = fields.Integer('Stock')
    date_created = fields.Datetime('Date created', required=False)
    date_end_ad = fields.Datetime('Date to finish Ad', required=False)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    ebay_bind_ids = fields.One2many(
        comodel_name='ebay.product.product',
        inverse_name='odoo_id',
        string='eBay Bindings',
    )


class ProductProductAdapter(Component):
    _name = 'ebay.product.product.adapter'
    _inherit = 'ebay.adapter'
    _apply_on = 'ebay.product.product'

    def _call(self, method, arguments):
        try:
            return super(ProductProductAdapter, self)._call(method, arguments)
        except Exception:
            raise
