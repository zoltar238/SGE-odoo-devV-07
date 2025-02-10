from odoo import api, fields, models
from odoo.addons.prueba.controllers.data_controller import english_data_sanitizer


class NerDataset(models.Model):
    _name = "ner.dataset"
    _description = "NER Training Dataset"

    name = fields.Char(string="Dataset Name", required=True)
    text_list = fields.Json(string="Lista de textos", required=True)
    annotations = fields.One2many("ner.annotation", "dataset_id", string="Annotations")
    model_ids = fields.Many2many("ner.model", "ner_model_dataset_rel", "dataset_id", "model_id", string="Models", required=True)

    def button_data_sanitizer(self):
        for rec in self:
            if rec.text_list:
                # text_list is already a list, no need to split
                data_list = rec.text_list.split('\n')

                print(data_list)

                # Sanitize the list
                sanitized_data = english_data_sanitizer(data_list, True, True, True)

                # Save the sanitized list
                result_data = ''
                for data in sanitized_data:
                    result_data += data+'\n'

                rec.text_list = result_data.strip()

