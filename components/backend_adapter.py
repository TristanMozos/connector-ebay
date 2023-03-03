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
import dateutil.parser
import re
from lxml import etree

import unicodecsv
from odoo.fields import Datetime
from odoo.addons.component.core import AbstractComponent
from odoo.addons.queue_job.exception import FailedJobError, RetryableJobError

from ebaysdk.exception import ConnectionError
from ebaysdk.trading import Connection as Trading

_logger = logging.getLogger(__name__)

_logger.debug("Cannot import 'ebay' API")

EBAY_DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

EBAY_ORDER_ID_PATTERN = '^([\d]{12}-'

_EBAY_TRADING_METHOD_LIST = {
    'ebay_sale_order_search':'GetOrders',
    'ebay_sale_order_read':'GetOrders'
}


class EbayAPI(object):

    def __init__(self, backend):
        """
        :param backend: eBay Backend
        :type location: :class:`MagentoLocation`
        """
        self._backend = backend
        self._api = None
        self._method = None

    @property
    def api(self):
        api = None
        if self.method in _EBAY_TRADING_METHOD_LIST.keys():
            api = Trading(config_file=None,
                          appid=self._backend.client_id,
                          devid=self._backend.dev_id,
                          certid=self._backend.client_secret,
                          token=self._backend.token)
            self.method = _EBAY_TRADING_METHOD_LIST[self.method]
        self._api = api
        return self._api

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, type, value, traceback):
        if self._api is not None:
            self._api.__exit__(type, value, traceback)

    def call(self, method, arguments):
        try:
            self.method = method
            result = self.api.execute(self.method, arguments)
        except ConnectionError as e:
            _logger.error(e.response.dict())
            raise e
        except:
            _logger.error("api.call('%s', %s) failed", method, arguments)
            raise
        return result


class EbayCRUDAdapter(AbstractComponent):
    """ External Records Adapter for Ebay """

    _name = 'ebay.crud.adapter'
    _inherit = ['base.backend.adapter', 'base.ebay.connector']
    _usage = 'backend.adapter'

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids """
        raise NotImplementedError

    def read(self, id, attributes=None):
        """ Returns the information of a record """
        raise NotImplementedError

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    def create(self, data):
        """ Create a record on the external system """
        raise NotImplementedError

    def write(self, id, data):
        """ Update records on the external system """
        raise NotImplementedError

    def delete(self, id):
        """ Delete a record on the external system """
        raise NotImplementedError

    def _call(self, method, arguments):
        try:
            ebay_api = getattr(self.work, 'ebay_api')
        except AttributeError:
            raise AttributeError(
                'You must provide a ebay_api attribute with a '
                'EbayAPI instance to be able to use the '
                'Backend Adapter.'
            )
        return ebay_api.call(method, arguments)


class GenericAdapter(AbstractComponent):
    _name = 'ebay.adapter'
    _inherit = 'ebay.crud.adapter'

    _ebay_model = None
    _admin_path = None

    def _get_model(self):
        if self._ebay_model:
            return self._ebay_model
        elif self.model:
            return self.model._name
        elif self._apply_on:
            return self._apply_on
        return ''

    def search(self, filters=None):
        """ Search records according to some criterias
        and returns a list of ids

        :rtype: list
        """
        return self._call('%s_search' % self._get_model().replace('.', '_'), filters if filters else {})

    def read(self, external_id, attributes=None):
        """ Returns the information of a record

        :rtype: dict
        """
        if external_id and isinstance(external_id, (list, tuple)):
            arguments = external_id
        else:
            arguments = [external_id]
        if attributes:
            arguments.append(attributes)
        return self._call('%s_read' % self._get_model().replace('.', '_'), [arguments])

    def search_read(self, filters=None):
        """ Search records according to some criterias
        and returns their information"""
        return self._call('%s_list' % self._get_model(), [filters])

    def create(self, data):
        """ Create a record on the external system """
        return self._call('%s_create' % self._get_model(), [data])

    def write(self, id, data):
        """ Update records on the external system """
        return self._call('%s_update' % self._get_model(),
                          [int(id), data])

    def delete(self, id):
        """ Delete a record on the external system """
        return self._call('%s.delete' % self._get_model(), [int(id)])
