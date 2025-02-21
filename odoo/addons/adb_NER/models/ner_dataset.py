import os.path
import json
from odoo.exceptions import ValidationError, UserError

from odoo import api, fields, models
from odoo.addons.adb_NER.controllers.data_controller import english_data_sanitizer
from odoo.addons.adb_NER.controllers.ner_controller import NerController


class NerDataset(models.Model):
    _name = "ner.dataset"
    _description = "NER Training Dataset"

    name = fields.Char(string="Dataset Name", required=True)
    text_list = fields.Json(string="Lista de textos", required=True)
    annotations = fields.One2many("ner.annotation", "dataset_id", string="Annotations")
    model_ids = fields.Many2many("ner.model", "ner_model_dataset_rel", "dataset_id", "model_id", string="Models",
                                 required=True)
    wipe_punctuation = fields.Boolean(string="Wipe punctuation signs", default=True)
    wipe_numbers = fields.Boolean(string="Wipe numbers", default=True)
    image = fields.Image(string="Dataset image")


    def button_data_sanitizer(self):
        for rec in self:
            if rec.text_list:
                # Split the text into a list
                data_list = rec.text_list.split('\n')

                # Sanitize the list
                if rec.wipe_punctuation or rec.wipe_numbers:
                    sanitized_data = english_data_sanitizer(data_list, rec.wipe_punctuation, rec.wipe_numbers)

                    # Save the sanitized list
                    result_data = ''
                    for data in sanitized_data:
                        result_data += data + '\n'

                    rec.text_list = result_data.strip()


    def button_detect_entities(self):
        global start_time, model
        # Split text into list
        data_list = []
        text_list = self.text_list.split('\n')
        for text in text_list:
            data_list.append({"text": text})

        # Detect entities for each model
        try:
            for model in self.model_ids:
                start_time = fields.Datetime.now()
                path = os.path.join(model.containing_folder, model.name)
                # Check if NER model exits before using it
                if os.path.exists(path):
                    ner = NerController(model_path=path, data_list=data_list)
                    results = ner.analyze_data()
                    for result in results:
                        for entity in result['entities']:
                            # Get all necessary elements
                            start_char, end_char, entity_label, entity_text = entity
                            entity_record = self.env['ner.entity'].search([('name', '=', entity_label)], limit=1)

                            # Check if a model with the same data already exist
                            existing_annotation = self.env['ner.annotation'].search([
                                ('text_index', '=', result['index'] + 1),
                                ('model_id', '=', model.id),
                                ('start_char', '=', start_char),
                                ('end_char', '=', end_char),
                                ('entity_id', '=', entity_record.id),
                                ('dataset_id', '=', self.id)
                            ], limit=1)

                            # If it does not exist, create a new model with the data
                            if not existing_annotation:
                                annotation_vals = {
                                    'text_index': result['index'] + 1,
                                    'model_id': model.id,
                                    'end_char': end_char,
                                    'start_char': start_char,
                                    'entity_id': entity_record.id,
                                    'text_content': entity_text,
                                    'dataset_id': self.id
                                }
                                # Create the new model
                                self.env['ner.annotation'].create(annotation_vals)

                    # Create result summary and report
                    results = {
                        'process': 'NER model data detection',
                        'model': model.name,
                        'detection_results': results
                    }
                    new_report = {
                        'reference': f'DETECTED {model.name}|{fields.Datetime.now()}',
                        'action_type': 'detection',
                        'state': 'completed',
                        'record_count': len(data_list),
                        'success_count': len(results),
                        'start_time': start_time,
                        'end_time': fields.Datetime.now(),
                        'log': json.dumps(results, indent=4),
                        'notes': 'Data detected successfully'
                    }
                    self.env['ner.report'].create(new_report)

                # If model could not be found
                else:
                    # Create result summary and report
                    results = {
                        'process': 'NER model data detection',
                        'model': model.name,
                        'detection_results': 'Null'
                    }
                    new_report = {
                        'reference': f'DETECTED {model.name}|{fields.Datetime.now()}',
                        'action_type': 'detection',
                        'state': 'failed',
                        'record_count': len(data_list),
                        'start_time': start_time,
                        'end_time': fields.Datetime.now(),
                        'log': json.dumps(results, indent=4),
                        'notes': 'Error detecting data'
                    }
                    self.env['ner.report'].create(new_report)
                    raise ValidationError(f'NER model {model.name} not found')

            # Show message of success if nothing fails
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': "Success",
                    'message': "Data detected successfully",
                    'sticky': False,
                }
            }
        # Throw an exception if data analysis fails
        except Exception as e:
            # Create result summary and report
            new_report = {
                'reference': f'DETECTED {model.name}|{fields.Datetime.now()}',
                'action_type': 'detection',
                'state': 'failed',
                'start_time': start_time,
                'end_time': fields.Datetime.now(),
                'log': str(e),
                'notes': 'Internal error detecting data'
            }
            self.env['ner.report'].create(new_report)

            raise UserError(f'Internal error while analyzing data: {e}')
