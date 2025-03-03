import os
import traceback
from itertools import groupby

from odoo.exceptions import ValidationError, UserError

from odoo import api, fields, models
from odoo.addons.adb_ner.controllers.ner_controller import NerController
from odoo.addons.adb_ner.controllers.notification_controller import create_notification


class NerAnnotation(models.Model):
    _name = "adb_ner.annotation"
    _description = "NER Annotation"

    start_char = fields.Integer(
        string="Start Character",
        required=True,
        help='Start character of the annotation')

    end_char = fields.Integer(
        string="End Character",
        required=True,
        help='End character of the annotation')

    entity_id = fields.Many2one(
        "adb_ner.entity",
        string="Entity",
        required=True,
        ondelete="cascade",
        help='Entity associated to this annotation')

    dataset_id = fields.Many2one(
        "adb_ner.dataset",
        string="Dataset",
        required=True,
        ondelete="cascade",
        readonly=True,
        help='Dataset associated to this annotation')

    model_id = fields.Many2one(
        "adb_ner.model",
        string="Model",
        required=True,
        ondelete="cascade",
        help='NER model that will train with this annotation')

    text_index = fields.Integer(
        string="Text Index",
        required=True,
        default=1,
        help="Text index from the dataset"
    )

    text_content = fields.Text(
        string="Text Content",
        compute='_compute_text_content',
        help='Extracted annotation from the data given')

    trained = fields.Boolean(
        string="Trained",
        default=False,
        help='''Marks whether this annotation has already been used for training.
        Although it can be overridden, is not recommended to retrain annotations''')

    faulty_tokens = fields.Boolean(
        default=False,
        readonly=True,
        help='Marks whether the selected text is a valid token')

    # Compute the text content based on the selected characters
    @api.depends('dataset_id.text_list', 'text_index', 'start_char', 'end_char')
    def _compute_text_content(self):
        for record in self:
            if not record.dataset_id:
                continue

            data_list = record.dataset_id.text_list.split('\n')

            # Validate text index
            if not self._is_valid_text_index(record, data_list):
                record.text_content = "Text index out of bounds"
                record.faulty_tokens = True
                continue

            text = data_list[record.text_index - 1]

            # process text and validate tokens
            self._process_text_content(record, text)

    # Check if the text index is within the dataset limits
    def _is_valid_text_index(self, record, data_list):
        return 0 <= record.text_index - 1 < len(data_list)

    # Process the text content based on the selected characters and validates the tokens
    def _process_text_content(self, record, text):
        # No characters selected
        if record.start_char == 0 and record.end_char == 0:
            record.text_content = text
            record.faulty_tokens = False
            return

        # Validar character limits
        if not (0 <= record.start_char < len(text) and
                0 < record.end_char <= len(text) and
                record.start_char < record.end_char):
            record.text_content = f'\"{text[record.start_char:len(text)]}\" (Out of bounds by {record.end_char - len(text)} characters)'
            record.faulty_tokens = True
            return

        # Validate partial tokens
        if self._has_partial_tokens(text, record.start_char, record.end_char):
            record.text_content = f'\"{text[record.start_char:record.end_char]}\" (No partial tokens allowed)'
            record.faulty_tokens = True
        else:
            record.text_content = text[record.start_char:record.end_char]
            record.faulty_tokens = False

    # Check if the selected characters contain partial tokens
    def _has_partial_tokens(self, text, start, end):
        has_partial_start = start > 0 and text[start - 1] != " "
        has_partial_end = end < len(text) and text[end] != " "
        return has_partial_start or has_partial_end

    # Returns all untrained annotations
    def _get_untrained_annotations(self):
        return self.env['adb_ner.annotation'].search([
            ('dataset_id', '=', self.dataset_id.id),
            ('trained', '=', False)
        ])

    # Prepare and group annotations for training based on the model name
    def _annotation_processing(self, annotations, text_list):
        # Sort annotations by text index and model name
        sorted_annotations = annotations.sorted(key=lambda r: (r.text_index, r.model_id.name))
        annotation_list = []

        # Process each annotation
        for annotation in sorted_annotations:
            # Raise an error if faulty tokens are detected
            if annotation.faulty_tokens:
                raise ValidationError(f"Faulty tokens detected at index: {annotation.text_index}")

            # Check if an existing annotation for the same model and text already exists
            existing_annotation = next((data for data in annotation_list if
                                        data["model"] == annotation.model_id.name and data["text"] == text_list[
                                            annotation.text_index - 1]), None)

            # If an existing annotation is found, append the current annotation's entity to it
            if existing_annotation:
                existing_annotation["entities"].append(
                    [annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content])
            # Otherwise, create a new annotation entry
            else:
                data = {
                    "model": annotation.model_id.name,
                    "text": text_list[annotation.text_index - 1],
                    "entities": [[annotation.start_char, annotation.end_char, annotation.entity_id.name,
                                  annotation.text_content]]
                }
                annotation_list.append(data)

        # Sort the annotation list by model name
        annotation_list.sort(key=lambda x: x["model"])
        # Group annotations by model name
        return list({key: list(group) for key, group in groupby(annotation_list, key=lambda x: x["model"])}.values())

    def _mark_annotations_as_trained(self, annotations):
        for annotation in annotations:
            annotation.trained = True

    def button_train_ner_model(self):
        # Declare global variables to store the current model name and start time
        global current_model_name, start_time

        # Check if the dataset is not set or the text list is empty, return early
        if not self.dataset_id or not self.dataset_id.text_list:
            return

        # Search for annotations that are not yet trained and belong to the current dataset
        annotations = self._get_untrained_annotations()

        # Split the dataset text list into individual lines
        text_list = self.dataset_id.text_list.split('\n')

        # Process the annotations and group them by model name
        annotation_list = self._annotation_processing(annotations, text_list)

        # Set training parameters
        learn_rate, iterations, batch_size, language = 0.001, 50, 10, self.model_id.language

        try:
            # Process each group of annotations
            for annotations_group in annotation_list:
                if not annotations_group:
                    continue

                # Set the start time and current model name
                start_time = fields.Datetime.now()
                current_model_name = annotations_group[0]['model']
                # Search for entity labels and model information
                entity_labels = self.env['adb_ner.entity'].search([('model_id.name', '=', current_model_name)])
                entity_model = self.env['adb_ner.model'].search([('name', '=', current_model_name)], limit=1)
                labels = [entity.name for entity in entity_labels]
                # Construct the model path
                joined_model_path = os.path.join(''.join(entity_model.containing_folder), current_model_name)
                # Initialize the NER controller
                ner = NerController(joined_model_path, language, labels, None, learn_rate, iterations, batch_size,
                                    annotations_group)
                model = self.env['adb_ner.model'].search([('name', '=', entity_model.name)], limit=1)

                # Train or create the NER model based on the existence of the model path
                if os.path.exists(joined_model_path):
                    training_results = ner.train_ner_model()
                    model.created = True
                else:
                    training_results = ner.create_ner_model()
                    model.created = True
                    self._create_report('creation', current_model_name, start_time, 'NER model creation',
                                        'NER model created successfully')

                # Mark all annotations as trained
                self._mark_annotations_as_trained(annotations)

                # Create a training report
                self._create_report('training', current_model_name, start_time, 'NER model training',
                                    'Data trained successfully', iterations, training_results, len(annotations))

            # Return a success notification
            return create_notification(
                "Training Completed Successfully",
                "Model has been trained successfully, check the reports for more information",
                False,
                'success'
            )

        except Exception:
            # Capture the error trace and create a failure report
            error_trace = traceback.format_exc()
            self._create_report('training', current_model_name, start_time, 'NER model training',
                                f'There was an error training the model: {current_model_name}', error=error_trace)
            # Raise a UserError with the error trace
            raise UserError(f'Internal error when training data: {error_trace}')

    def _create_report(self, action_type, model_name, beginning, process, notes, iterations=0, training_results=None,
                       record_count=0, error=None):
        vals = {
            'reference': f'{action_type.upper()} {model_name}|{fields.Datetime.now()}',
            'action_type': action_type,
            'state': 'failed' if error else 'completed',
            'iteration_count': iterations,
            'losses_average': sum(item["losses"] for item in training_results) / len(
                training_results) if training_results else 0,
            'record_count': record_count,
            'start_time': beginning,
            'end_time': fields.Datetime.now(),
            'log': {
                'process': process,
                'model': model_name,
                'success': not bool(error),
                'training_results': training_results if training_results else 'Null',
                'error': error,
            },
            'notes': notes
        }
        self.env['adb_ner.report'].create_new_report(vals)
