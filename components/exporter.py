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
from contextlib import contextmanager
from datetime import datetime

import odoo
import psycopg2
from odoo import _
from odoo.addons.component.core import AbstractComponent
from odoo.addons.connector.exception import (IDMissingInBackend,
                                             RetryableJobError)

from .backend_adapter import EBAY_DATETIME_FORMAT

_logger = logging.getLogger(__name__)

"""

Exporters for eBay.

In addition to its export job, an exporter has to:

* check in eBay if the record has been updated more recently than the
  last sync date and if yes, delay an import
* call the ``bind`` method of the binder to update the last sync date

"""


class BatchExporter(AbstractComponent):
    """ The role of a BatchExporter is to send a list of
    items to export, then it can either export them directly or delay
    the export of each item separately.
    """

    _name = 'ebay.batch.exporter'
    _inherit = ['base.exporter', 'base.ebay.connector']
    _usage = 'batch.exporter'

    def run(self, records=None):
        """ Run the synchronization """
        for record_id in records:
            self._export_record(record_id)

    def _export_record(self, external_id):
        """ Import a record directly or delay the import of the record.

        Method to implement in sub-classes.
        """
        raise NotImplementedError


class EbayExporter(AbstractComponent):
    """ Base exporter for eBay """

    _name = 'ebay.exporter'
    _inherit = ['base.exporter', 'base.ebay.connector']
    _usage = 'record.exporter'

    def __init__(self, working_context):
        super(EbayExporter, self).__init__(working_context)
        self.binding = None
        self.external_id = None

    def _delay_export(self):
        """ Schedule an export of the record.

        Adapt in the sub-classes when the model is not exported
        using ``export_record``.
        """
        # force is True because the sync_date will be more recent
        # so the import would be skipped
        assert self.external_id
        self.binding.with_delay().export_record(self.backend_record,
                                                self.external_id,
                                                force=True)

    def _should_import(self):
        """ Before the export, compare the update date
        in eBay and the last sync date in Odoo,
        if the former is more recent, schedule an import
        to not miss changes done in eBay.
        """
        assert self.binding
        if not self.external_id:
            return False
        sync = self.binding.sync_date
        if not sync:
            return True
        record = self.backend_adapter.read(self.external_id,
                                           attributes=['updated_at'])
        if not record['updated_at']:
            # in rare case it can be empty, in doubt, import it
            return True
        sync_date = odoo.fields.Datetime.from_string(sync)
        ebay_date = datetime.strptime(record['updated_at'],
                                      EBAY_DATETIME_FORMAT)
        return sync_date < ebay_date

    def run(self, binding, *args, **kwargs):
        """ Run the synchronization

        :param binding: binding record to export
        """
        self.binding = binding

        self.external_id = self.binder.to_external(self.binding)
        try:
            should_import = self._should_import()
        except IDMissingInBackend:
            self.external_id = None
            should_import = False
        if should_import:
            self._delay_import()

        result = self._run(*args, **kwargs)

        self.binder.bind(self.external_id, self.binding)
        # Commit so we keep the external ID when there are several
        # exports (due to dependencies) and one of them fails.
        # The commit will also release the lock acquired on the binding
        # record
        if not odoo.tools.config['test_enable']:
            self.env.cr.commit()  # noqa

        self._after_export()
        return result

    def _after_export(self):
        """ Can do several actions after exporting a record on ebay """
        pass

    def _lock(self):
        """ Lock the binding record.

        Lock the binding record so we are sure that only one export
        job is running for this record if concurrent jobs have to export the
        same record.

        When concurrent jobs try to export the same record, the first one
        will lock and proceed, the others will fail to lock and will be
        retried later.

        This behavior works also when the export becomes multilevel
        with :meth:`_export_dependencies`. Each level will set its own lock
        on the binding record it has to export.

        """
        sql = ("SELECT id FROM %s WHERE ID = %%s FOR UPDATE NOWAIT" %
               self.model._table)
        try:
            self.env.cr.execute(sql, (self.binding.id,),
                                log_exceptions=False)
        except psycopg2.OperationalError:
            _logger.info('A concurrent job is already exporting the same '
                         'record (%s with id %s). Job delayed later.',
                         self.model._name, self.binding.id)
            raise RetryableJobError(
                'A concurrent job is already exporting the same record '
                '(%s with id %s). The job will be retried later.' %
                (self.model._name, self.binding.id))

    def _has_to_skip(self):
        """ Return True if the export can be skipped """
        return False

    @contextmanager
    def _retry_unique_violation(self):
        """ Context manager: catch Unique constraint error and retry the
        job later.

        When we execute several jobs workers concurrently, it happens
        that 2 jobs are creating the same record at the same time (binding
        record created by :meth:`_export_dependency`), resulting in:

            IntegrityError: duplicate key value violates unique
            constraint "ebay_product_product_odoo_uniq"
            DETAIL:  Key (backend_id, odoo_id)=(1, 4851) already exists.

        In that case, we'll retry the import just later.

        .. warning:: The unique constraint must be created on the
                     binding record to prevent 2 bindings to be created
                     for the same eBay record.

        """
        try:
            yield
        except psycopg2.IntegrityError as err:
            if err.pgcode == psycopg2.errorcodes.UNIQUE_VIOLATION:
                raise RetryableJobError(
                    'A database error caused the failure of the job:\n'
                    '%s\n\n'
                    'Likely due to 2 concurrent jobs wanting to create '
                    'the same record. The job will be retried later.' % err)
            else:
                raise

    def _export_dependency(self, relation, binding_model,
                           component_usage='record.exporter',
                           binding_field='ebay_bind_ids',
                           binding_extra_vals=None):
        """
        Export a dependency. The exporter class is a subclass of
        ``EbayExporter``. If a more precise class need to be defined,
        it can be passed to the ``exporter_class`` keyword argument.

        .. warning:: a commit is done at the end of the export of each
                     dependency. The reason for that is that we pushed a record
                     on the backend and we absolutely have to keep its ID.

                     So you *must* take care not to modify the Odoo
                     database during an export, excepted when writing
                     back the external ID or eventually to store
                     external data that we have to keep on this side.

                     You should call this method only at the beginning
                     of the exporter synchronization,
                     in :meth:`~._export_dependencies`.

        :param relation: record to export if not already exported
        :type relation: :py:class:`odoo.models.BaseModel`
        :param binding_model: name of the binding model for the relation
        :type binding_model: str | unicode
        :param component_usage: 'usage' to look for to find the Component to
                                for the export, by default 'record.exporter'
        :type exporter: str | unicode
        :param binding_field: name of the one2many field on a normal
                              record that points to the binding record
                              (default: ebay_bind_ids).
                              It is used only when the relation is not
                              a binding but is a normal record.
        :type binding_field: str | unicode
        :binding_extra_vals:  In case we want to create a new binding
                              pass extra values for this binding
        :type binding_extra_vals: dict
        """
        if not relation:
            return
        rel_binder = self.binder_for(binding_model)
        # wrap is typically True if the relation is for instance a
        # 'product.product' record but the binding model is
        # 'ebay.product.product'
        wrap = relation._name != binding_model

        if wrap and hasattr(relation, binding_field):
            domain = [('odoo_id', '=', relation.id),
                      ('backend_id', '=', self.backend_record.id)]
            binding = self.env[binding_model].search(domain)
            if binding:
                assert len(binding) == 1, (
                    'only 1 binding for a backend is '
                    'supported in _export_dependency')
            # we are working with a unwrapped record (e.g.
            # product.category) and the binding does not exist yet.
            # Example: I created a product.product and its binding
            # ebay.product.product and we are exporting it, but we need to
            # create the binding for the product.category on which it
            # depends.
            else:
                bind_values = {'backend_id':self.backend_record.id,
                               'odoo_id':relation.id}
                if binding_extra_vals:
                    bind_values.update(binding_extra_vals)
                # If 2 jobs create it at the same time, retry
                # one later. A unique constraint (backend_id,
                # odoo_id) should exist on the binding model
                with self._retry_unique_violation():
                    binding = (self.env[binding_model]
                               .with_context(connector_no_export=True)
                               .sudo()
                               .create(bind_values))
                    # Eager commit to avoid having 2 jobs
                    # exporting at the same time. The constraint
                    # will pop if an other job already created
                    # the same binding. It will be caught and
                    # raise a RetryableJobError.
                    if not odoo.tools.config['test_enable']:
                        self.env.cr.commit()  # noqa
        else:
            # If ebay_bind_ids does not exist we are typically in a
            # "direct" binding (the binding record is the same record).
            # If wrap is True, relation is already a binding record.
            binding = relation

        if not rel_binder.to_external(binding):
            exporter = self.component(usage=component_usage,
                                      model_name=binding_model)
            exporter.run(binding)

    def _export_dependencies(self):
        """ Export the dependencies for the record"""
        return

    def _map_data(self):
        """ Returns an instance of
        :py:class:`~odoo.addons.connector.components.mapper.MapRecord`

        """
        return self.mapper.map_record(self.binding)

    def _validate_create_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.create`` if some fields
        are missing or invalid

        Raise `InvalidDataError`
        """
        return

    def _validate_update_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``Model.update`` if some fields
        are missing or invalid

        Raise `InvalidDataError`
        """
        return

    def _create_data(self, map_record, fields=None, **kwargs):
        """ Get the data to pass to :py:meth:`_create` """
        return map_record.values(for_create=True, fields=fields, **kwargs)

    def _create(self, data):
        """ Create the eBay record """
        # special check on data before export
        self._validate_create_data(data)
        return self.backend_adapter.create(data)

    def _update_data(self, map_record, fields=None, **kwargs):
        """ Get the data to pass to :py:meth:`_update` """
        return map_record.values(fields=fields, **kwargs)

    def _update(self, data):
        """ Update an eBay record """
        assert self.external_id
        # special check on data before export
        self._validate_update_data(data)
        self.backend_adapter.write(self.external_id, data)

    def _run(self, fields=None):
        """ Flow of the synchronization, implemented in inherited classes"""
        assert self.binding

        if not self.external_id:
            fields = None  # should be created with all the fields

        if self._has_to_skip():
            return

        # export the missing linked resources
        self._export_dependencies()

        # prevent other jobs to export the same record
        # will be released on commit (or rollback)
        self._lock()

        map_record = self._map_data()

        if self.external_id:
            record = self._update_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            self._update(record)
        else:
            record = self._create_data(map_record, fields=fields)
            if not record:
                return _('Nothing to export.')
            self.external_id = self._create(record)
        return _('Record exported with ID %s on eBay.') % self.external_id
