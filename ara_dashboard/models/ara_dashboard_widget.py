# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AraDashboardWidget(models.Model):
    _name = 'ara.dashboard.widget'
    _description = 'Ara Dashboard Widget'
    _order = 'sequence, id asc'

    dashboard_id = fields.Many2one(
        'ara.dashboard',
        string='Dashboard',
        required=True,
        ondelete='cascade'
    )
    name = fields.Char(string='Widget Title', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    widget_type = fields.Selection([
        ('tiles', 'Tiles'),
        ('line', 'Line Chart'),
        ('table', 'List View'),
        ('bar', 'Bar Chart'),
        ('horizontal_bar', 'Horizontal Bar Chart'),
        ('todo', 'To-do Item'),
        ('polar_area', 'Polar Area Chart'),
        ('pie', 'Pie Chart'),
        ('doughnut', 'Doughnut Chart'),
        ('flower', 'Flower Chart'),
        ('funnel', 'Funnel Chart'),
        ('radial', 'Radial Chart'),
        ('bullet', 'Bullet Chart'),
        ('scatter', 'Scatter Chart'),
        ('radar', 'Radar Chart'),
        # Backward compatibility
        ('kpi', 'Tiles (Legacy KPI)'),
        ('chart', 'Graph Chart (Legacy)'),
        ('progress', 'Target / Progress Bar (Legacy)'),
    ], string='Widget Type', default='tiles', required=True)

    col_span = fields.Selection([
        ('3', '1/4 Width (3 cols)'),
        ('4', '1/3 Width (4 cols)'),
        ('6', '1/2 Width (6 cols)'),
        ('8', '2/3 Width (8 cols)'),
        ('12', 'Full Width (12 cols)'),
    ], string='Grid Width', default='4', required=True)

    row_span = fields.Integer(string='Row Height', default=1)

    # Data Source
    model_id = fields.Many2one(
        'ir.model',
        string='Odoo Model',
        required=True,
        ondelete='cascade'
    )
    model_name = fields.Char(related='model_id.model', readonly=True, store=True)

    domain = fields.Text(string='Filter Domain', default='[]')
    
    date_field_id = fields.Many2one(
        'ir.model.fields',
        string='Date Filter Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['date', 'datetime'])]",
        help="Field used to apply the global dashboard date range filter."
    )

    measure_field_id = fields.Many2one(
        'ir.model.fields',
        string='Measure Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['integer', 'float', 'monetary'])]",
        help="Numeric field to aggregate (sum, avg, max, min). Leave empty for record count."
    )

    scatter_x_field_id = fields.Many2one(
        'ir.model.fields',
        string='Scatter X-Axis Field',
        domain="[('model_id', '=', model_id), ('ttype', 'in', ['integer', 'float', 'monetary'])]",
        help="Numeric field for X-Axis in Scatter chart. Measure field is used for Y-Axis."
    )

    aggregation_type = fields.Selection([
        ('count', 'Count Records'),
        ('sum', 'Sum'),
        ('avg', 'Average'),
        ('max', 'Maximum'),
        ('min', 'Minimum'),
    ], string='Aggregation', default='count', required=True)

    groupby_field_id = fields.Many2one(
        'ir.model.fields',
        string='Group By Field',
        domain="[('model_id', '=', model_id), ('store', '=', True)]",
        help="Field used to categorize data for charts and groupings."
    )

    chart_type = fields.Selection([
        ('bar', 'Bar Chart'),
        ('horizontal_bar', 'Horizontal Bar Chart'),
        ('line', 'Line Chart'),
        ('doughnut', 'Doughnut Chart'),
        ('pie', 'Pie Chart'),
        ('polar_area', 'Polar Area Chart'),
        ('radar', 'Radar Chart'),
        ('scatter', 'Scatter Chart'),
    ], string='Chart Type', default='bar')

    table_field_ids = fields.Many2many(
        'ir.model.fields',
        'ara_widget_fields_rel',
        'widget_id',
        'field_id',
        string='Table Columns',
        domain="[('model_id', '=', model_id)]"
    )

    limit = fields.Integer(string='Record Limit', default=10)
    sort_order = fields.Selection([
        ('desc', 'Descending'),
        ('asc', 'Ascending'),
    ], string='Sort Direction', default='desc')

    # Visual & Styling
    kpi_icon = fields.Char(string='Icon Class', default='fa-chart-line', help="FontAwesome class e.g. fa-wallet, fa-shopping-cart, fa-users")
    color_accent = fields.Selection([
        ('red', 'Cinematic Red (Signature)'),
        ('emerald', 'Emerald Green'),
        ('cyan', 'Cyber Cyan'),
        ('amber', 'Warm Amber'),
        ('purple', 'Neon Violet'),
        ('blue', 'Sapphire Blue'),
    ], string='Accent Color', default='red')

    target_value = fields.Float(string='Target Value', default=100.0)
    trend_comparison = fields.Selection([
        ('none', 'No Comparison'),
        ('prev_period', 'vs Previous Period'),
        ('prev_year', 'vs Previous Year'),
    ], string='Trend Comparison', default='prev_period')

    config_json = fields.Text(string='Custom Configuration (JSON)', default='{}')

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.date_field_id = False
        self.measure_field_id = False
        self.groupby_field_id = False
        self.table_field_ids = False
        if self.model_id:
            # Auto-detect common date field like date, create_date
            date_field = self.env['ir.model.fields'].search([
                ('model_id', '=', self.model_id.id),
                ('name', 'in', ['date_order', 'invoice_date', 'date', 'create_date']),
                ('ttype', 'in', ['date', 'datetime'])
            ], limit=1)
            if date_field:
                self.date_field_id = date_field.id

    @api.onchange('widget_type')
    def _onchange_widget_type(self):
        type_to_chart = {
            'bar': 'bar',
            'horizontal_bar': 'horizontal_bar',
            'line': 'line',
            'doughnut': 'doughnut',
            'pie': 'pie',
            'polar_area': 'polar_area',
            'radar': 'radar',
            'scatter': 'scatter',
        }
        if self.widget_type in type_to_chart:
            self.chart_type = type_to_chart[self.widget_type]

        type_to_icon = {
            'tiles': 'fa-tachometer',
            'line': 'fa-line-chart',
            'table': 'fa-table',
            'bar': 'fa-bar-chart',
            'horizontal_bar': 'fa-align-left',
            'todo': 'fa-check-square-o',
            'polar_area': 'fa-pie-chart',
            'pie': 'fa-pie-chart',
            'doughnut': 'fa-circle-o-notch',
            'flower': 'fa-snowflake-o',
            'funnel': 'fa-filter',
            'radial': 'fa-dashboard',
            'bullet': 'fa-sliders',
            'scatter': 'fa-braille',
            'radar': 'fa-bullseye',
        }
        if self.widget_type in type_to_icon:
            self.kpi_icon = type_to_icon[self.widget_type]

        chart_like = [
            'bar', 'horizontal_bar', 'line', 'doughnut', 'pie',
            'polar_area', 'radar', 'scatter', 'flower', 'funnel', 'chart'
        ]
        if self.widget_type in chart_like and self.model_id and not self.groupby_field_id:
            preferred = (
                ['stage_id', 'state', 'partner_id', 'user_id', 'type', 'category_id', 'date_order', 'date', 'create_date']
                if self.widget_type == 'funnel'
                else ['partner_id', 'stage_id', 'user_id', 'state', 'country_id', 'type', 'category_id', 'date_order', 'date', 'create_date']
            )
            for pname in preferred:
                common_group = self.env['ir.model.fields'].search([
                    ('model_id', '=', self.model_id.id),
                    ('name', '=', pname),
                    ('store', '=', True),
                ], limit=1)
                if common_group:
                    self.groupby_field_id = common_group.id
                    break
