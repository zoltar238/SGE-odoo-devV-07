from odoo.exceptions import ValidationError

from odoo import fields, models
from odoo.addons.adb_NER.controllers.ner_controller import NerController
import os
import traceback


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
            # Delete model from database
            self.unlink()
            # Generate report
            self._create_report('deletion', self.name, 'Model successfully deleted')
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Success",
                    'message': "All model data has been deleted successfully",
                    'sticky': False,
                }
            }
        except Exception:
            # Capture the error and generate error report
            error_trace = traceback.format_exc()
            self._create_report('deletion', self.name, 'Internal error deleting model', error_trace)
            raise ValidationError(f"Error deleting model: {error_trace}")


    def _create_report(self, action_type, model_name, notes, error=None):
        vals = {
            'reference': f'{action_type.upper()} {model_name}|{fields.Datetime.now()}',
            'action_type': action_type,
            'state': 'failed' if error else 'completed',
            'start_time': fields.Datetime.now(),
            'end_time': fields.Datetime.now(),
            'log': error if error else notes,
            'notes': notes
        }
        self.env['ner.report'].create(vals)