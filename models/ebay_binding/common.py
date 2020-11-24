# -*- coding: utf-8 -*-
# Copyright 2019 Halltic eSolutions S.L.
# © 2019 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models, fields
from odoo.addons.queue_job.exception import FailedJobError, RetryableJobError
from odoo.addons.queue_job.job import job, related_action


class EbayBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.

    All the models used as bindings between Ebay and Odoo
    (``ebay.res.partner``, ``ebay.product.product``, ...) should
    ``_inherit`` it.
    """
    _name = 'ebay.binding'
    _inherit = 'external.binding'
    _description = 'Ebay Binding (abstract)'

    # odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name='ebay.backend',
        string='eBay Backend',
        required=True,
        ondelete='restrict',
    )
    # fields.Char because 0 is a valid eBay ID
    external_id = fields.Char(string='ID on eBay')

    _sql_constraints = [
        ('ebay_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same eBay ID.'),
    ]

    @job(default_channel='root.ebay')
    @api.model
    def import_batch(self, backend, filters=None):
        """ Prepare the import of records modified on eBay """
        if filters is None:
            filters = {}

        try:
            with backend.work_on(self._name) as work:
                importer = work.component(usage='batch.importer')
                return importer.run(filters=filters)
        except Exception as e:
            return e

    @job(default_channel='root.ebay')
    @api.model
    def export_batch(self, backend, filters=None):
        """ Prepare the export of records on eBay """
        if filters is None:
            filters = {}
        try:
            with backend.work_on(self._name) as work:
                exporter = work.component(usage='batch.exporter')
                return exporter.run(filters=filters)
        except Exception as e:
            return e

    @job(default_channel='root.ebay')
    @api.model
    def import_record(self, backend, external_id, force=False):
        """ Import a eBay record """
        try:
            with backend.work_on(self._name) as work:
                importer = work.component(usage='record.importer')
                return importer.run(external_id, force=False)
        except Exception as e:
            return e

    @job(default_channel='root.ebay')
    @api.multi
    def export_record(self, fields=None):
        """ Export a record on eBay """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            try:
                return exporter.run(self, fields)
            except Exception as e:
                return e
