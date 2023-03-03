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
# This project is based on connector-magneto, developed by Camptocamp SA

import logging
from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class EbayResPartner(models.Model):
    _name = 'ebay.res.partner'
    _inherit = 'ebay.binding'
    _inherits = {'res.partner':'odoo_id'}
    _description = 'eBay Partner'

    odoo_id = fields.Many2one(comodel_name='res.partner',
                              string='Customer',
                              required=True,
                              ondelete='restrict')

    id_partner = fields.Char()

    alias = fields.Char()

    @api.model
    def import_record(self, backend, external_id):
        _super = super(EbayResPartner, self)
        return _super.import_record(backend, external_id)


class EbayPartnerAdapter(Component):
    _name = 'ebay.res.partner.adapter'
    _inherit = 'ebay.adapter'
    _apply_on = 'ebay.res.partner'


class ResPartner(models.Model):
    _inherit = 'res.partner'

    ebay_bind_ids = fields.One2many(
        comodel_name='ebay.res.partner',
        inverse_name='odoo_id',
        string='eBay Bindings',
    )
