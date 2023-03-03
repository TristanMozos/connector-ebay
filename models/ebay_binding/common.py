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

from odoo import api, models, fields


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

    @api.model
    def import_record(self, backend, external_id, force=False):
        """ Import a eBay record """
        try:
            with backend.work_on(self._name) as work:
                importer = work.component(usage='record.importer')
                return importer.run(external_id, force=False)
        except Exception as e:
            return e

    def export_record(self, fields=None):
        """ Export a record on eBay """
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            try:
                return exporter.run(self, fields)
            except Exception as e:
                return e
