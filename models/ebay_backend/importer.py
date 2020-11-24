# -*- coding: utf-8 -*-
# Copyright 2019 Halltic eSolutions S.L.
# © 2019 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component


class MetadataBatchImporter(Component):
    """ Import the records directly, without delaying the jobs.

    Import the eBay Orders, Products
    """

    _name = 'ebay.metadata.batch.importer'
    _inherit = 'ebay.direct.batch.importer'
    _apply_on = [
        'ebay.product.product',
        'ebay.res.partner',
    ]
