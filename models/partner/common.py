# -*- coding: utf-8 -*-
# Copyright 2019 Halltic eSolutions S.L.
# © 2019 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
# This project is based on connector-magneto, developed by Camptocamp SA

import logging
from collections import defaultdict

from odoo import models, fields, api
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action

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

    @job(default_channel='root.ebay')
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
