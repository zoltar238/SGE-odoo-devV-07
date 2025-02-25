from odoo import api, fields, models
from odoo.exceptions import ValidationError


class NerEntity(models.Model):
    _name = "adb_ner.entity"
    _description = "NER Entity"

    name = fields.Char(
        string="Entity Name",
        required=True,
        help='Entity name which will be used by the ner model')

    entity_type = fields.Selection([
        ('person', 'Person'),
        ('location', 'Location'),
        ('organization', 'Organization'),
        ('date', 'Date'),
        ('misc', 'Miscellaneous'),
    ],
        string="Entity Type",
        required=True,
        help='Category of your entity')

    model_id = fields.Many2many(
        "adb_ner.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help='''Models that will use this entity.
        Once the model is created, you can not add more entities''')

    # Check if the model has already been created before adding new entities to it
    @api.constrains('model_id')
    def _check_model_creation(self):
        for model in self.model_id:
            if model.created:
                raise ValidationError(f'Model \"{model.name}\" has been already created and it\'s entities can\'t be modified')