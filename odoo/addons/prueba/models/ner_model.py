from odoo import api, fields, models

class NerModel(models.Model):
     _name = 'ner.model'
     _description = 'NER Model'

     name = fields.Char(string="Model Name", required=True)
     description = fields.Text(string = "Description")
     language = fields.Selection([
         ('en', 'English'),
         ('es', 'Spanish')
     ], string="Language", default='en', required=True)
     containing_folder = fields.Char(string="Folder containing this model", required=True, default="var/lib/NER")
     active = fields.Boolean(string="Active", default=True)
     created = fields.Boolean(string="Created", default=False, readonly=True)