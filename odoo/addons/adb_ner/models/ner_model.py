from odoo.exceptions import ValidationError

from odoo import fields, models


class NerModel(models.Model):
    _name = 'adb_ner.model'
    _description = 'NER Model'

    name = fields.Char(
        string="Model Name",
        required=True,
        help="This is the unique name of your model",
    )

    description = fields.Text(
        string="Description",
        help="Description of your model")

    language = fields.Selection([
        ('en', 'English'),
        ('es', 'Spanish')
    ],
        string="Language",
        default='en',
        required=True,
        help="Language of your model")

    containing_folder = fields.Char(
        string="Folder containing this model",
        required=True,
        default="var/lib/NER",
        help='The path containing your model will be this_folder + /your_model_name')

    active = fields.Boolean(
        string="Active",
        default=True,
        help='Activate or deactivate this model')

    created = fields.Boolean(
        string="Created",
        default=False,
        readonly=True,
        help='''Mark whether the model has benn created. 
        When deleting a created model make sure to also delete its files''')

    # Ensure model name is unique
    _sql_constraints =[
        ('unique_name', 'unique(name)', 'A NER model with this name already exists, model names must be unique')
    ]

