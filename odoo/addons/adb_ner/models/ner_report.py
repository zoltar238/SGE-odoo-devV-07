from odoo import api, fields, models

from odoo import models, fields, api

class NerReport(models.Model):
    _name = "adb_ner.report"
    _description = "NER Report"
    _rec_name = 'reference'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Campos de identificación y referencia
    reference = fields.Char(
        string='Reference',
        required=True,
        readonly=True,
        default='New'
    )

    # Campos de información general
    action_type = fields.Selection([
        ('training', 'Model Training'),
        ('creation', 'Model Created'),
        ('detection', 'Entities detected'),
    ], string='Action Type', required=True)

    state = fields.Selection([
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], string='Status', default='completed')

    # Métricas y estadísticas
    iteration_count = fields.Integer(
        string="Number of iterations",
        help='Times the model has iterated over the same data'
    )

    losses_average = fields.Float(
        string="Average losses",
        help="Average difference between predicted entities and expected entities (lower is better)",
        store=True
    )

    record_count = fields.Integer(
        string='Number of Records',
        help='Total number of records processed'
    )

    success_count = fields.Integer(
        string='Successful Records',
        help='Number of successfully processed records'
    )

    entities_count = fields.Integer(
        string='Entities Found',
        help='Number of entities found in the processed data'
    )

    annotations_created = fields.Integer(
        string='New Annotations Created',
        help='Number of new annotations created during the process'
    )

    success_rate = fields.Float(
        string='Success Rate (%)',
        compute='_compute_success_rate',
        store=True,
        group_operator='avg'
    )

    # Campos de tiempo
    start_time = fields.Datetime(
        string='Start Time',
        default=fields.Datetime.now
    )

    end_time = fields.Datetime(
        string='End Time'
    )

    duration = fields.Float(
        string='Duration (minutes)',
        compute='_compute_duration',
        store=True,
        group_operator='avg'
    )

    # Campos relacionales
    user_id = fields.Many2one(
        'res.users',
        string='User',
        default=lambda self: self.env.user
    )

    # Log
    log = fields.Html(
        string='Log',
        help='Detailed log',
        readonly=True,
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes or observations',
        readonly=True
    )

    @api.depends('success_count', 'record_count')
    def _compute_success_rate(self):
        for record in self:
            if record.record_count and record.action_type == 'detection':
                record.success_rate = (record.success_count / record.record_count) * 100
            elif record.record_count and record.action_type == 'training':
                record.success_rate = 100.0
            elif record.state != 'completed':
                record.success_rate = 0.0
            else:
                record.success_rate = 100.0

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for record in self:
            if record.start_time and record.end_time:
                duration = (record.end_time - record.start_time).total_seconds() / 60
                record.duration = round(duration, 2)
            else:
                record.duration = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('reference', 'New') == 'New':
                vals['reference'] = self.env['ir.sequence'].next_by_code('ner.report') or 'New'
        return super(NerReport, self).create(vals_list)

    def action_complete(self):
        self.write({
            'state': 'completed',
            'end_time': fields.Datetime.now()
        })

    def action_fail(self):
        self.write({
            'state': 'failed',
            'end_time': fields.Datetime.now()
        })

    # Method to create a new report
    def create_new_report(self, vals):
        vals.setdefault('reference', f'REPORT {fields.Datetime.now()}')
        vals.setdefault('action_type', 'creation')
        vals.setdefault('state', 'completed')
        vals.setdefault('start_time', fields.Datetime.now())
        vals.setdefault('end_time', fields.Datetime.now())
        vals.setdefault('iteration_count', 0)
        vals.setdefault('losses_average', 0.0)
        vals.setdefault('record_count', 0)
        vals.setdefault('success_count', 0)
        vals.setdefault('entities_count', 0)
        vals.setdefault('annotations_created', 0)
        vals.setdefault('success_rate', 0.0)
        vals.setdefault('log', 'Report created successfully')
        vals.setdefault('notes', 'Initial report creation')
        vals.setdefault('user_id', self.env.user.id)
        return self.create(vals)
