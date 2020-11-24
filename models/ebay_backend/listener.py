# -*- coding: utf-8 -*-
# Copyright 2018 Halltic eSolutions S.L.
# © 2018 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

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
