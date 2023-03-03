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

import logging
from datetime import datetime

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class CategoryBatchImporter(Component):
    """ Import the categories.

    """
    _name = 'ebay.category.batch.importer'
    _inherit = 'ebay.delayed.batch.importer'
    _apply_on = 'ebay.config.product.category'

    def run(self, filters=None):
        categories = self.backend_adapter.get_all_categories(filters)
        for category in categories:
            category_binding_model = self.env['ebay.config.product.category']
            delayable = category_binding_model.with_delay()
            delayable.description = '%s.import_record: %s' % (category_binding_model._name, category.json())
            delayable.import_record(self.backend_record, category)
        import wdb
        wdb.set_trace()
        return


class CategoryImporter(Component):
    _name = 'ebay.category.importer'
    _inherit = 'ebay.importer'
    _apply_on = ['ebay.config.product.category']

    def _after_import(self, binding):
        return

    def run(self, external_id, force=False):
        """ Run the synchronization

        :param external_id: identifier of the record on Amazon
        """
        _super = super(CategoryImporter, self)
        self.external_id = external_id
        return _super.run(external_id=self.external_id, force=force)


class ProductImportMapper(Component):
    _name = 'ebay.product.product.import.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = ['ebay.product.product']

    direct = [("id_category", "id_category"),
              ("parent_category_id", "parent_category_id"),
              ("is_leaf_category", "is_leaf_category"),
              ("level", "level"),
              ]
