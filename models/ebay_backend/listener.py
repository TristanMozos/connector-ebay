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

from odoo.addons.component.core import Component
from odoo.addons.component_event import skip_if


class EbayBindingBackendListener(Component):
    _name = 'ebay.binding.ebay.backend.listener'
    _inherit = 'base.connector.listener'
    _apply_on = ['ebay.backend']

    @skip_if(lambda self, record, **kwargs:self.no_connector_export(record))
    def on_record_create(self, record, fields=None):
        if record:
            record._ebay_backend('_import_product_product', domain=None)
