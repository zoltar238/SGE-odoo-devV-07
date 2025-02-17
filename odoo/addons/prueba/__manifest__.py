# -*- coding: utf-8 -*-


{
    'name': "NER",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # views and security
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
    ],
    # demo data
    'demo': [
        'demo/demo_model_data.xml',
        'demo/demo_entity_data.xml',
        'demo/demo_dataset_data.xml',
        'demo/demo_annotation_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
}
