import json

from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models
import os
from itertools import groupby
from odoo.addons.adb_NER.controllers.ner_controller import NerController


class NerAnnotation(models.Model):
    _name = "ner.annotation"
    _description = "NER Annotation"

    start_char = fields.Integer(string="Start Character", required=True)
    end_char = fields.Integer(string="End Character", required=True)
    entity_id = fields.Many2one("ner.entity", string="Entity", required=True, ondelete="cascade")
    dataset_id = fields.Many2one("ner.dataset", string="Dataset", required=True, ondelete="cascade")
    model_id = fields.Many2one("ner.model", string="Model", required=True, ondelete="cascade")
    text_index = fields.Integer(
        string="Text Index",
        required=True,
        help="Índice del texto en la lista de textos del dataset"
    )
    text_content = fields.Text(string="Text Content", compute='_compute_text_content')
    trained = fields.Boolean(string="Trained", default = False)
    faulty_tokens = fields.Boolean(default=False, readonly=True)

    @api.depends('dataset_id.text_list', 'text_index', 'start_char', 'end_char')
    def _compute_text_content(self):
        for rec in self:
            # Verify that the dataset exists and the text index is different from none
            if rec.dataset_id and rec.text_index is not None:
                data_list = rec.dataset_id.text_list.split('\n')

                # Verify text_index is within the limits of the dataset
                if 0 <= rec.text_index - 1 <= len(data_list):
                    text = data_list[rec.text_index - 1]
                    # If no end and start char selected, set full line as selected text
                    if rec.start_char == 0 and rec.end_char == 0:
                        rec.text_content = text
                    # When given and start and end character
                    elif 0 <= rec.start_char < len(text) and 0 < rec.end_char <= len(text) and rec.end_char > rec.start_char:
                        # End char surpasses token length
                        if rec.end_char < len(text) and text[rec.end_char] != " ":
                            rec.text_content = f'\"{text[rec.start_char:rec.end_char]}\" (No partial tokens allowed)'
                            rec.faulty_tokens = True
                        # Start char is lower than token length
                        elif rec.start_char > 0 and text[rec.start_char - 1] != " ":
                            rec.text_content = f'\"{text[rec.start_char:rec.end_char]}\" (No partial tokens allowed)'
                            rec.faulty_tokens = True
                        else :
                            rec.text_content = text[rec.start_char:rec.end_char]
                            rec.faulty_tokens = False
                    # End char surpasses text length
                    else:
                        rec.text_content = f'\"{text[rec.start_char:len(text)]}\" (Out of bounds by {rec.end_char - len(text)} characters)'
                        rec.faulty_tokens = True
                # Text index is out of bounds
                else:
                    rec.text_content = "Text index out of bounds"
                    rec.faulty_tokens = True


    def action_on_button_click(self):
        global current_model_name, start_time
        if self.dataset_id:
            # Obtain all annotations from dataset that haven`t been trained
            annotations = self.env['ner.annotation'].search([
                ('dataset_id', '=', self.dataset_id.id),
                ('trained', '=', False)
            ])

            # Split text into list
            if self.dataset_id.text_list:
                text_list = self.dataset_id.text_list.split('\n')

            # Sort the list by index order
            sorted_annotations = annotations.sorted(key=lambda r: (r.text_index, r.model_id.name))

            # List to hold all the annotations
            annotation_list = []

            # Obtain all annotations
            for annotation in sorted_annotations:
                # Check for invalid tokens
                if annotation.faulty_tokens:
                    raise ValidationError(f"Faulty tokens detected at index: {annotation.text_index}")

                # **Annotations: add or update the annotations in annotation_list**
                # Check if there's already an annotation with the same text index and model
                existing_annotation = next((data for data in annotation_list if data["model"] == annotation.model_id.name and data["text"] == text_list[annotation.text_index - 1]), None)

                if existing_annotation:
                    # If the annotation exists, add the new entity to it
                    existing_annotation["entities"].append([annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content])
                else:
                    # If the annotation does not exist, create a new one
                    data = {
                        "model": annotation.model_id.name,
                        "text": text_list[annotation.text_index - 1],
                        "entities": [[annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content]]
                    }
                    annotation_list.append(data)

            # Sort data by model name
            annotation_list.sort(key=lambda x: x["model"])

            split_annotation_list = {key: list(group) for key, group in groupby(annotation_list, key=lambda x: x["model"])}
            # Transform dictionary to list
            split_annotation_list = list(split_annotation_list.values())

            # Result object for the report
            results = {
                'process':'NER model training',
            'training_results':[]
            }

            # Todo: let user change this parameters
            learn_rate = 0.001
            iterations = 50
            batch_size = 10
            language = 'en'

            # Fixed loop to match entities with model names
            try:
                for index, annotations_group in enumerate(split_annotation_list):
                    # Check if the group has annotations
                    if annotations_group:
                        start_time = fields.Datetime.now()
                        current_model_name = annotations_group[0]['model']

                        # Load the entities from database that match the NER model
                        entity_labels = self.env['ner.entity'].search([('model_id.name', '=', current_model_name)])
                        entity_model = self.env['ner.model'].search([('name', '=', current_model_name)], limit=1)
                        labels = [entity.name for entity in entity_labels]

                        joined_model_path = os.path.join(''.join(entity_model.containing_folder), current_model_name)
                        # Train model, if the model doesn't exist in the path, create it
                        ner = NerController(joined_model_path, language, labels,  None, learn_rate, iterations, batch_size, annotations_group)
                        model = self.env['ner.model'].search([('name', '=', entity_model.name)], limit=1)
                        if os.path.exists(joined_model_path):
                            # Train model and obtain trained results
                            training_results = ner.train_ner_model()

                            # Set Model created to true just in case
                            model.created = True

                            new_model_created = False


                            # Append result
                            results['training_results'].append({
                                'ner_model':current_model_name,
                                'created':False,
                                'success':True,
                                'result_list':training_results
                            })
                        else:
                            # Create the new model mark it as created
                            training_results=ner.create_ner_model()
                            model.created = True
                            new_model_created = True
                            # Append result
                            results['training_results'].append({
                                'ner_model':current_model_name,
                                'created':True,
                                'success':True,
                                'result_list':training_results
                            })

                        # Mark all annotations used as trained
                        for annotation in annotations:
                            annotation.trained = True

                        # Generate new report if a new model has been created
                        if new_model_created:
                            results = {
                                'process': 'NER model created',
                                'model': current_model_name,
                            }
                            new_report = {
                                'reference': f'CREATED: {current_model_name}|{fields.Datetime.now()}',
                                'action_type': 'creation',
                                'state': 'completed',
                                'iteration_count': 0,
                                'losses_average': 0,
                                'record_count': 0,
                                'start_time': start_time,
                                'end_time': fields.Datetime.now(),
                                'log': json.dumps(results, indent=4),
                                'notes': 'NER model created successfully'
                            }
                            self.env['ner.report'].create(new_report)

                        # Create result summary and report
                        results = {
                            'process': 'NER model training',
                            'model': current_model_name,
                            'training_results': training_results
                        }
                        new_report = {
                            'reference':f'TRAINED {current_model_name}|{fields.Datetime.now()}',
                            'action_type': 'training',
                            'state': 'completed',
                            'iteration_count': iterations,
                            'losses_average': sum(item["losses"] for item in training_results) / len(training_results),
                            'record_count': len(sorted_annotations),
                            'start_time': start_time,
                            'end_time': fields.Datetime.now(),
                            'log':json.dumps(results, indent=4),
                            'notes': 'Data trained successfully'
                        }
                        # Create the new model
                        self.env['ner.report'].create(new_report)

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': "Success",
                        'message': "Data trained successfully",
                        'sticky': False,
                    }
                }
            # If an error occurs notify the user
            except Exception as e:
                results = {
                    'ner_model':current_model_name,
                    'created':False,
                    'error':str(e),
                    'success':False,
                    'result_list':'Null'
                }

                #Create new error report
                new_report = {
                    'reference': f'TRAINED {current_model_name}|{fields.Datetime.now()}',
                    'action_type': 'training',
                    'state': 'failed',
                    'log':json.dumps(results, indent=4),
                    'start_time': start_time,
                    'end_time': fields.Datetime.now(),
                    'notes': f'There was an error training the model: {current_model_name}'
                }
                self.env['ner.report'].create(new_report)

                raise UserError(f'Internal error when training data: {e}')