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

import time
from odoo import models, fields, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class EbayProductCategory(models.Model):
    _name = 'ebay.config.product.category'
    _inherit = 'ebay.binding'
    _description = 'eBay category'

    id_category = fields.Integer('Product category ID')
    parent_category_id = fields.Many2one('ebay.config.product.category')
    children_category_ids = fields.One2many(comodel_name='ebay.config.product.category',
                                            inverse_name='parent_category_id')
    is_leaf_category = fields.Boolean()
    level = fields.Integer()
    name_ids = fields.One2many(comodel_name='ebay.config.product.category.name',
                               inverse_name='category_id')


class EbayProductCategoryName(models.Model):
    _name = 'ebay.config.product.category.name'

    category_id = fields.Many2one('ebay.config.product.category')
    name = fields.Char()
    language_id = fields.Many2one('res.lang')


class EbayCategoryProductAdapter(Component):
    _name = 'ebay.product.category.adapter'
    _inherit = 'ebay.adapter'
    _apply_on = 'ebay.config.product.category'

    def get_all_categories(self, filters):
        '''
        Method to call at Aliexpress API and return all categories
        :param filters:
        :return: categories
        '''
        return self._call(method='list_all_categories', arguments=filters)
