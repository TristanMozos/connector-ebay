# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2020 Halltic eSolutions (https://www.halltic.com)
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

{
    'name':"eBay Connector",

    'summary':"""
        eBay module for integration of your eBay account on odoo""",

    'description':"""
        eBay module for integration of your eBay account on odoo
    """,

    'author':"Halltic eSolutions S.L.",
    'website':"https://www.halltic.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/TristanMozos/connector-ebay
    # for the full list
    'category':'Sales',
    'version':'0.1.0',

    # any module necessary for this one to work correctly
    'depends':['base', 'sale', 'product_margin'],

    # always loaded
    'data':[
        'security/connector_security.xml',
        #'security/ir.model.access.csv',
        'views/ebay_backend_views.xml',
        'views/connector_ebay_menu.xml',
        'data/ebay_scheduler.xml',
        'data/ebay_data.xml',
    ],
    # only loaded in demonstration mode
    'demo':[
        'demo/demo.xml',
    ],
    'installable':True,
    'application':True,
    'auto_install':False,
}
