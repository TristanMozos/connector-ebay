# -*- coding: utf-8 -*-
# Copyright 2018 Halltic eSolutions S.L.
# © 2018 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# This project is based on connector-magneto, developed by Camptocamp SA

from odoo.addons.component.core import Component


class EbayModelBinder(Component):
    """ Bind records and give odoo/ebay ids correspondence

    Binding models are models called ``ebay.{normal_model}``,
    like ``ebay.res.partner`` or ``ebay.product.product``.
    They are ``_inherits`` of the normal models and contains
    the eBay ID, the ID of the eBay Backend and the additional
    fields belonging to the eBay instance.
    """
    _name = 'ebay.binder'
    _inherit = ['base.binder', 'base.ebay.connector']
    _apply_on = [
        'ebay.product.product',
        'ebay.product.product.ad',
        'ebay.sale.order',
        'ebay.sale.order.line',
        'ebay.res.partner',
    ]
