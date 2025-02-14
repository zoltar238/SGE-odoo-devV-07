from odoo import api, fields, models
from pathlib import Path
import os
import json
from itertools import groupby
from odoo.addons.prueba.controllers.ner_controller import NerController


class NerAnnotation(models.Model):
    _name = "ner.annotation"
    _description = "NER Annotation"

    start_char = fields.Integer(string="Start Character", required=True)
    end_char = fields.Integer(string="End Character", required=True)
    entity_id = fields.Many2one("ner.entity", string="Entity", required=True, ondelete="cascade")
    dataset_id = fields.Many2one("ner.dataset", string="Dataset", required=True, ondelete="cascade")
    model_id = fields.Many2one("ner.model", string="Model", required=True, ondelete="set null")
    text_index = fields.Integer(
        string="Text Index",
        required=True,
        help="Índice del texto en la lista de textos del dataset"
    )
    text_content = fields.Text(string="Text Content", compute='_compute_text_content')

    @api.depends('dataset_id.text_list', 'text_index', 'start_char', 'end_char')
    def _compute_text_content(self):
        for rec in self:
            # Verifica que exista el dataset y que text_index sea válido
            if rec.dataset_id and rec.text_index is not None:
                data_list = rec.dataset_id.text_list.split('\n')

                # Verifica que text_index esté dentro de los límites del dataset
                if 0 <= rec.text_index - 1 <= len(data_list):
                    text = data_list[rec.text_index - 1]
                    if rec.start_char == 0 and rec.end_char == 0:
                        rec.text_content = text
                    elif 0 <= rec.start_char < len(text) and 0 < rec.end_char <= len(text) and rec.end_char > rec.start_char:
                        if rec.end_char < len(text) and text[rec.end_char] != " ":
                            rec.text_content = "No partial tokens allowed"
                        elif rec.start_char > 0 and text[rec.start_char - 1] != " ":
                            rec.text_content = "No partial tokens allowed"
                        else :
                            rec.text_content = text[rec.start_char:rec.end_char]
                    else:
                        rec.text_content = "Text out of bounds"
                else:
                    rec.text_content = "Text index out of bounds"


    @api.depends('model_id.name', 'model_id.containing_folder', 'dataset_id.text_list')
    def action_on_button_click(self):
        self.ensure_one()
        for rec in self:
            if self.dataset_id:
                # Obtener todas las anotaciones del dataset
                annotations = self.env['ner.annotation'].search([
                    ('dataset_id', '=', self.dataset_id.id)
                ])

                # Split text into list
                if rec.dataset_id.text_list:
                    text_list = rec.dataset_id.text_list.split('\n')

                # Sort the list by index order
                sorted_annotations = annotations.sorted(key=lambda r: (r.text_index, r.model_id.name))

                # List to hold all the annotations
                annotation_list = []
                model_info_list = []

                # Obtain all annotations
                for annotation in sorted_annotations:
                    # **Model: add or update the model in model_info_list**
                    # Check if the model already exists in model_info_list
                    existing_model = next((model for model in model_info_list if model['model'] == annotation.model_id.name), None)

                    if existing_model:
                        # If the model exists and the entity is not in the list, we add it
                        if annotation.entity_id.name not in existing_model['entities']:
                            existing_model['entities'].append(annotation.entity_id.name)
                    else:
                        # If the model does not exist, create a new one with the entity
                        ner_model = {
                            "model": annotation.model_id.name,
                            "entities": [annotation.entity_id.name],
                            "path": [annotation.model_id.containing_folder]
                        }
                        model_info_list.append(ner_model)

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
                model_info_list.sort(key=lambda x: x["model"])
                annotation_list.sort(key=lambda x: x["model"])

                split_annotation_list = {key: list(group) for key, group in groupby(annotation_list, key=lambda x: x["model"])}
                # Transform dictionary to list
                split_annotation_list = list(split_annotation_list.values())

                # Fixed loop to match entities with model names
                for index, annotations_group in enumerate(split_annotation_list):
                    if annotations_group:  # Check if the group has annotations
                        model_name = annotations_group[0]['model']
                        # Find the matching model info
                        matching_model = next((model for model in model_info_list if model['model'] == model_name), None)

                        if matching_model:
                            labels = matching_model['entities']
                            language = 'en'
                            joined_model_path = os.path.join(''.join(matching_model['path']), model_name)
                            # Todo: let user change this parameters
                            learn_rate = 0.001
                            iterations = 50
                            batch_size = 10
                            # Train model, if the model doesn't exist in the path, create it
                            ner = NerController(joined_model_path, language, labels,  None, learn_rate, iterations, batch_size, annotations_group)
                            if os.path.exists(joined_model_path):
                                ner.train_ner_model()
                                model = self.env['ner.model'].search([('name', '=', matching_model['model'])], limit=1)
                                model.active = False
                                print(model.active)
                            else:
                                ner.create_ner_model()

            return True