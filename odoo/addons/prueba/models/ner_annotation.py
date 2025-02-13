from odoo import api, fields, models
from pathlib import Path
import os
import json
from itertools import groupby

#from odoo.addons.prueba.controllers.ner_controller import NerController


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
                index = 1
                for annotation in sorted_annotations:

                    # If there anre no elements in the model list, create a new one and append it
                    if not model_info_list:
                        ner_model = {
                            "model": annotation.model_id.name,
                            "entities": [annotation.entity_id.name]
                        }
                        model_info_list.append(ner_model)
                    else:
                        for model in model_info_list:
                            if model['model'] != annotation.model_id.name:
                                ner_model = {
                                    "model": annotation.model_id.name,
                                    "entities": [annotation.entity_id.name]
                                }
                                model_info_list.append(ner_model)
                            elif model['model'] == annotation.model_id.name and not model['entities'].__contains__(annotation.entity_id.name):
                                model['entities'].append(annotation.entity_id.name)

                    # If there are no elements in the annotation list, create a new one and append it
                    if not annotation_list:
                        data = {
                            #"index": annotation.text_index,
                            "model": annotation.model_id.name,
                            "text": text_list[annotation.text_index - 1],
                            "entities": [[annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content]]
                        }
                        annotation_list.append(data)
                    elif index == annotation.text_index:
                        if annotation_list[len(annotation_list) - 1]["model"] == annotation.model_id.name:
                            annotation_list[len(annotation_list) - 1]["entities"].append([annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content])
                        else :
                            data = {
                                #"index": annotation.text_index,
                                "model": annotation.model_id.name,
                                "text": text_list[annotation.text_index - 1],
                                "entities": [[annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content]]
                            }
                            annotation_list.append(data)
                    elif index != annotation.text_index:
                        data = {
                            #"index": annotation.text_index,
                            "model": annotation.model_id.name,
                            "text": text_list[annotation.text_index - 1],
                            "entities": [[annotation.start_char, annotation.end_char, annotation.entity_id.name, annotation.text_content]]
                        }
                        annotation_list.append(data)
                        index += 1

                print(model_info_list)

                # Sort data by model name
                annotation_list.sort(key=lambda x: x["model"])
                splitted_annotation_list = {key: list(group) for key, group in groupby(annotation_list, key=lambda x: x["model"])}
                # Transform dictionary to list
                splitted_annotation_list = list(splitted_annotation_list.values())

                for annotation in splitted_annotation_list:
                    print(annotation)
                    # Obtain labels
                    # Todo : implement language, learn_rate, iterations and batch_size modification
                    language = 'en'
                    #model_path = 'odoo/addons/prueba/NER/' + annotation['model']
                    learn_rate = 0.001
                    iterations = 50
                    batch_size = 10
                    # ner = NerController(args.labels, language, model_path, None, learn_rate, iterations, batch_size)

            return True