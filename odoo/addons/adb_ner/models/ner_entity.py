from odoo import api, fields, models


class NerEntity(models.Model):
    _name = "adb_ner.entity"
    _description = "NER Entity"

    name = fields.Char(string="Entity Name", required=True)
    entity_type = fields.Selection([
        ('person', 'Person'),
        ('location', 'Location'),
        ('organization', 'Organization'),
        ('date', 'Date'),
        ('misc', 'Miscellaneous'),
    ], string="Entity Type", required=True)
    model_id = fields.Many2many("adb_ner.model", string="Model", required=True, ondelete="cascade")
