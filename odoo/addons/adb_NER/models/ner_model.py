from odoo.exceptions import ValidationError

from odoo import fields, models
from odoo.addons.adb_NER.controllers.ner_controller import NerController
import os


class NerModel(models.Model):
    _name = 'ner.model'
    _description = 'NER Model'

    name = fields.Char(string="Model Name", required=True)
    description = fields.Text(string="Description")
    language = fields.Selection([
        ('en', 'English'),
        ('es', 'Spanish')
    ], string="Language", default='en', required=True)
    containing_folder = fields.Char(string="Folder containing this model", required=True, default="var/lib/NER")
    active = fields.Boolean(string="Active", default=True)
    created = fields.Boolean(string="Created", default=False, readonly=True)


    def action_delete_model(self):
        ner = NerController(self.containing_folder)
        try:
            model_path = os.path.join(self.containing_folder, self.name)
            if os.path.exists(model_path):
                ner.delete_ner_model()
            self.unlink()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Success",
                    'message': "All model data has been deleted successfully",
                    'sticky': False,
                }
            }
        except Exception as e:
            raise ValidationError(f"Error deleting model: {str(e)}")
