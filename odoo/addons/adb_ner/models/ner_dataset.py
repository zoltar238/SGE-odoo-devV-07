import json
import os.path

from odoo.exceptions import ValidationError, UserError

from odoo import api, fields, models
from odoo.addons.adb_ner.controllers.data_controller import english_data_sanitizer
from odoo.addons.adb_ner.controllers.ner_controller import NerController


class NerDataset(models.Model):
    _name = "adb_ner.dataset"
    _description = "NER Training Dataset"

    name = fields.Char(
        string="Dataset Name",
        required=True,
        help='Name that identifies this dataset')

    text_list = fields.Json(
        string="Lista de textos",
        required=True,
        help='Data to be analyzed line by line')

    annotations = fields.One2many(
        "adb_ner.annotation",
        "dataset_id",
        string="Annotations",
        help='Annotations found in this dataset')

    model_ids = fields.Many2many(
        "adb_ner.model",
        "ner_model_dataset_rel",
        "dataset_id",
        "model_id",
        string="Models",
        required=True,
        help='Models that will analyze this data')

    wipe_punctuation = fields.Boolean(
        string="Wipe punctuation signs",
        default=False,
        help='If checked, punctuation signs will be removed when sanitizing data')

    wipe_numbers = fields.Boolean(
        string="Wipe numbers",
        default=False,
        help='If checked, numeric values will be removed when sanitizing data')

    image = fields.Image(
        string="Dataset image",
        help='Image that represents this dataset')

    # Function that sanitices data on this dataset
    def button_data_sanitizer(self):
        if self.text_list:
            # Split the text into a list
            data_list = self.text_list.split('\n')

            # Sanitize the list
            if self.wipe_punctuation or self.wipe_numbers:
                sanitized_data = english_data_sanitizer(data_list, self.wipe_punctuation, self.wipe_numbers)

                # Save the sanitized list
                result_data = ''
                for data in sanitized_data:
                    result_data += data + '\n'

                self.text_list = result_data.strip()

    # Function to extract entities from data
    def button_detect_entities(self):
        global start_time

        # Split text into list
        data_list = []
        text_list = self.text_list.split('\n')
        for text in text_list:
            data_list.append({"text": text})

        # Initialize counters
        total_lines = len(data_list)

        # Detect entities for each model
        for model in self.model_ids:
            total_entities = 0
            new_annotations = 0
            analyzed_lines = 0
            
            start_time = fields.Datetime.now()
            path = os.path.join(model.containing_folder, model.name)
            # Check if NER model exits before using it
            if os.path.exists(path):
                ner = NerController(model_path=path, data_list=data_list)
                results = ner.analyze_data()
                model_entities = 0

                # Process results
                for result in results:
                    # If the model has detected any results update number of analyzed lines
                    if result['entities']:
                        analyzed_lines += 1
                    # skip this iteration if no entities were found
                    else:
                        continue

                    for entity in result['entities']:
                        total_entities += 1
                        model_entities += 1
                        # Get all necessary elements
                        start_char, end_char, entity_label, entity_text = entity
                        entity_record = self.env['adb_ner.entity'].search([('name', '=', entity_label)], limit=1)

                        # Check if a model with the same data already exist
                        existing_annotation = self.env['adb_ner.annotation'].search([
                            ('text_index', '=', result['index'] + 1),
                            ('model_id', '=', model.id),
                            ('start_char', '=', start_char),
                            ('end_char', '=', end_char),
                            ('entity_id', '=', entity_record.id),
                            ('dataset_id', '=', self.id)
                        ], limit=1)

                        # If it does not exist, create a new model with the data
                        if not existing_annotation:
                            new_annotations += 1
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
                            self.env['adb_ner.annotation'].create(annotation_vals)

                # Create report with detection statistics
                report_data = {
                    'results': results,
                    'stats': {
                        'total_lines': total_lines,
                        'total_entities': model_entities,
                        'new_annotations': new_annotations,
                        'analyzed_lines': analyzed_lines
                    }
                }
                self._create_report(model.name, start_time, report_data)


            # If model could not be found
            else:
                self._create_report(model.name, start_time, 'Null', error=True)
                raise ValidationError(f'NER model {model.name} not found')
                # If everything was ok, return a success message
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': "Detection Completed Successfully",
                'message': "Data has been detected successfully",
                'sticky': True,
                'type': 'success'
            }
        }



    def _create_report(self, model_name, start_time, results, error=False):
        # Create result summary and report
        new_report = {
            'reference': f'DETECTION {model_name}|{fields.Datetime.now()}',
            'action_type': 'detection',
            'state': 'failed' if error else 'completed',
            'record_count': results['stats']['total_lines'],
            'success_count': results['stats']['analyzed_lines'],
            'entities_count': results['stats']['total_entities'],
            'annotations_created': results['stats']['new_annotations'],
            'start_time': start_time,
            'end_time': fields.Datetime.now(),
            'log': json.dumps(results, indent=4),
            'notes': 'Error detecting data' if error else 'Data detected successfully'
        }
        self.env['adb_ner.report'].create(new_report)
