# -*- coding: utf-8 -*-

from odoo import models, fields


# eBay order status, auxiliar model
class eBayOrderStatus(models.Model):
    _name = 'ebay.order.status'
    name = fields.Char('name', required=True)


# eBay order checkout status, auxiliar model
class eBayOrderCheckoutStatus(models.Model):
    _name = 'ebay.order.checkout.status'
    name = fields.Char('name', required=True)
