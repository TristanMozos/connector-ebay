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
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class PartnerImportMapper(Component):
    _name = 'ebay.partner.import.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = 'ebay.res.partner'

    direct = [
        ('name', 'name'),
        ('alias', 'alias'),
        ('email', 'email'),
        ('phone', 'phone'),
        ('street', 'street'),
        ('street2', 'street2'),
        ('street3', 'street3'),
        ('city', 'city'),
        ('zip', 'zip'),
        ('type', 'type'),
    ]

    @mapping
    def country_id(self, record):
        if record.get('country'):
            country = self.env['res.country'].search([('code', '=', record['country'])])
            if country:
                return {'country_id':country.id}
        return

    @mapping
    def state_id(self, record):
        if record.get('country') and record.get('state'):
            state = self.env['res.country.state'].search([('country_id.code', '=', record['country']), ('name', '=', record['state'])])
            if state:
                return {'state_id':state.id}
        return {'state_id':None}

    @only_create
    @mapping
    def is_company(self, record):
        # partners are companies so we can bind
        # addresses on them
        return {'is_company':False}

    @only_create
    @mapping
    def customer(self, record):
        return {'customer':True}

    @mapping
    def type(self, record):
        return {'type':'delivery'}

    @only_create
    @mapping
    def odoo_id(self, record):
        """ Will bind the customer on a existing partner
        with the same email """
        partner = self.env['res.partner'].search(
            [('email', '=', record['email']),
             ('customer', '=', True),
             '|',
             ('is_company', '=', True),
             ('parent_id', '=', False)],
            limit=1,
        )
        if partner:
            return {'odoo_id':partner.id}

    @mapping
    def backend_id(self, record):
        return {'backend_id':self.backend_record.id}


class PartnerImporter(Component):
    _name = 'ebay.res.partner.importer'
    _inherit = 'ebay.importer'
    _apply_on = ['ebay.res.partner']

    def _get_ebay_data(self):
        return self.ebay_record
