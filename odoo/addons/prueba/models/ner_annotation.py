from odoo import api, fields, models
from pathlib import Path
import os

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

    @api.depends('model_id.name', 'model_id.containing_folder')
    def action_on_button_click(self):
        for rec in self:
            if rec.model_id:  # Verificamos que model_id existe
                folder = rec.model_id.containing_folder
                model_name = rec.model_id.name
                print(f"Folder: {folder}")
                print(f"Model name: {model_name}")

                path = os.path.join(folder, model_name)
                if os.path.exists(path):
                    print(f"El archivo {model_name} existe en la carpeta {folder}")
                else:
                    print("Botón presionado!")
            else:
                print("No hay modelo seleccionado.")