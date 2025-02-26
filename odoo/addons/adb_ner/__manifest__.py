# -*- coding: utf-8 -*-


{
    'name': "NER (Named Entity Recognition)",

    'summary': "A module for managing Named Entity Recognition (NER) models, datasets, and annotations.",

    'description': """
This module provides functionality for training and managing Named Entity Recognition (NER) models,
including dataset handling, entity annotation, and model evaluation.
    """,

    'author': "Andrei Darius Bacanu",
    'website': "https://github.com/zoltar238/SGE-odoo-devV-07",

    'category': 'Artificial Intelligence',
    'version': '1.0',

    # Dependencies
    'depends': ['base', 'mail'],
    'external_dependencies': {
        'python': ['spacy'],
    },

    # Views and security
    'data': [
        'security/ir.model.access.csv',
        'views/action_definitions.xml',
        'views/view_ner_model_tree.xml',
        'views/view_ner_model_form.xml',
        'views/view_ner_entity_tree.xml',
        'views/view_ner_entity_form.xml',
        'views/view_ner_dataset_tree.xml',
        'views/view_ner_dataset_form.xml',
        'views/view_ner_annotation_form.xml',
        'views/view_ner_annotation_kanban.xml',
        'views/view_ner_report_tree.xml',
        'views/view_ner_report_form.xml',
        'views/view_ner_report_search.xml',
        'views/view_ner_report_pivot.xml',
        'views/view_ner_report_calendar.xml',
        'views/view_ner_report_kanban.xml',
        'views/menu_definitions.xml',
    ],

    # Demo data
    'demo': [
        'demo/demo_model.xml',
        'demo/demo_entity.xml',
        'demo/demo_dataset.xml',
        'demo/demo_annotation.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': True,
}
