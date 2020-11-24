# -*- coding: utf-8 -*-
# Copyright 2018 Halltic eSolutions S.L.
# © 2018 Halltic eSolutions S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import urllib2
import base64

from odoo import _
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, follow_m2o_relations
from odoo.addons.connector.exception import InvalidDataError

from ...components.mapper import normalize_datetime

_logger = logging.getLogger(__name__)


class ProductProductBatchImporter(Component):
    """
    Import the eBay Products.
    """
    _name = 'ebay.product.product.batch.importer'
    _inherit = 'ebay.direct.batch.importer'
    _apply_on = 'ebay.product.product'


class ProductImportMapper(Component):
    _name = 'ebay.product.product.import.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = ['ebay.product.product']

    direct = [('Title', 'name'),
              ('ItemID', 'id_item'),
              ('SKU', 'sku'),
              ('Quantity', 'ebay_qty'),
              ]

    children = [('product_product_market_ids', 'product_product_market_ids', 'ebay.product.product.detail'), ]

    @mapping
    def backend_id(self, record):
        return {'backend_id':self.backend_record.id}


class ProductImporter(Component):
    _name = 'ebay.product.product.importer'
    _inherit = 'ebay.importer'
    _apply_on = ['ebay.product.product']

    def _get_ebay_data(self):
        """ Return the raw eBay data for ``self.external_id`` """
        if self.ebay_record:
            return self.ebay_record

    def _get_binary_image(self, image_url):
        url = image_url.encode('utf8')
        try:
            request = urllib2.Request(url)
            binary = urllib2.urlopen(request)
        except urllib2.HTTPError as err:
            if err.code == 404:
                # the image is just missing, we skip it
                return
            else:
                # we don't know why we couldn't download the image
                # so we propagate the error, the import will fail
                # and we have to check why it couldn't be accessed
                raise
        else:
            return binary.read()

    def _write_image_data(self, binding, binary):
        binding = binding.with_context(connector_no_export=True)
        binding.write({'image':base64.b64encode(binary)})

    def _write_product_data(self, binding, marketplace_id):
        self.external_id = binding.external_id
        marketplace = self.env['ebay.config.marketplace'].browse(marketplace_id)
        data_product = self.backend_adapter.read(external_id=self.external_id, attributes=marketplace.id_mws)
        self._write_brand(binding, data_product)
        self._write_dimensions(binding, data_product)
        if data_product.get('url_images'):
            images = data_product['url_images']
            while images:
                image_url = images.pop()
                binary = self._get_binary_image(image_url)
                self._write_image_data(binding, binary)

        return data_product

    def _validate_product_type(self, data):
        """ Check if the product type is in the selection (so we can
        prevent the `except_orm` and display a better error message).
        """
        product_type = data['product_type']
        product_model = self.env['ebay.product.product']
        types = product_model.product_type_get()
        available_types = [typ[0] for typ in types]
        if product_type not in available_types:
            raise InvalidDataError("The product type '%s' is not "
                                   "yet supported in the connector." %
                                   product_type)

    def _must_skip(self):
        """ Hook called right after we read the data from the backend.

        If the method returns a message giving a reason for the
        skipping, the import will be interrupted and the message
        recorded in the job (if the import is called directly by the
        job, not by dependencies).

        If it returns None, the import will continue normally.

        :returns: None | str | unicode
        """
        return None

    def _validate_data(self, data):
        """ Check if the values to import are correct

        Pro-actively check before the ``_create`` or
        ``_update`` if some fields are missing or invalid

        Raise `InvalidDataError`
        """
        if not data or not data.get('name'):
            raise InvalidDataError

    def _create(self, data):
        data['type'] = 'product'
        binding = super(ProductImporter, self)._create(data)
        return binding

    def run(self, external_id, force=False):
        """ Run the synchronization

        :param external_id: identifier of the record on eBay
        """
        self.external_id = external_id
        _super = super(ProductImporter, self)
        _super.run(external_id=external_id[0], force=force)


class ProductProductMarketImportMapper(Component):
    _name = 'ebay.product.product.detail.mapper'
    _inherit = 'ebay.import.mapper'
    _apply_on = 'ebay.product.product.detail'

    direct = [('sku', 'code'),
              ('title', 'title'),
              ('price_unit', 'price'),
              ('price_shipping', 'price_ship'),
              ('status', 'status'),
              ('stock', 'stock'),
              ('is_mine_buy_box', 'has_buybox'),
              ('is_mine_lowest_price', 'has_lowest_price'),
              ('lowest_landed_price', 'lowest_price'),
              ('lowest_listing_price', 'lowest_product_price'),
              ('lowest_shipping_price', 'lowest_shipping_price'),
              ('merchant_shipping_group', 'merchant_shipping_group'), ]

    @mapping
    def names(self, record):
        if record.get('sku') and record.get('marketplace_id'):
            return {'name':record['sku'] + ' || ' + self.env['ebay.config.marketplace'].browse(record['marketplace_id']).name}
        return

    @mapping
    def external_id(self, record):
        if record.get('sku') and record.get('marketplace_id'):
            return {'name':record['sku'] + '||' + self.env['ebay.config.marketplace'].browse(record['marketplace_id']).id}
        return

    @mapping
    def website_id(self, record):
        return {'website_id':None}

    @mapping
    def item_ids(self, record):
        item = {'applied_on':'1_product',
                'compute_price':'fixed',
                'fixed_price':record.get('price_unit'), }
        # TODO we need recover the product

        return {'item_ids':item}

    @mapping
    def marketplace_id(self, record):
        return {'marketplace_id':record.get('marketplace_id')}

    @mapping
    def marketplace_price_id(self, record):
        '''
        Return the marketplace to product_pricelist
        :param record:
        :return:
        '''
        return {'marketplace_price_id':record.get('marketplace_id')}

    @mapping
    def currency_id(self, record):
        return {'currency_id':record.get('currency_price_unit')}

    @mapping
    def currency_price(self, record):
        return {'currency_price':record.get('currency_price_unit')}

    @mapping
    def currency_ship(self, record):
        return {'currency_price':record.get('currency_shipping')}
