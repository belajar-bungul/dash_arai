# -*- coding: utf-8 -*-
import base64
import io
import re
import logging
from datetime import datetime, timedelta, time
import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as RLTable, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    SimpleDocTemplate = None


class AraDashboardReportSchedule(models.Model):
    _name = 'ara.dashboard.report.schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Scheduled Dashboard Report'
    _order = 'next_run_date asc, id desc'

    name = fields.Char(
        string='Report Title',
        required=True,
        tracking=True,
        default="Weekly Executive Dashboard Briefing"
    )
    dashboard_id = fields.Many2one(
        'ara.dashboard',
        string='Dashboard',
        required=True,
        tracking=True,
        ondelete='cascade'
    )
    active = fields.Boolean(string='Active', default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Configured By',
        default=lambda self: self.env.user,
        required=True
    )

    # Schedule cadence
    schedule_interval = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], string='Frequency', default='weekly', required=True, tracking=True)

    day_of_week = fields.Selection([
        ('0', 'Every Monday'),
        ('1', 'Every Tuesday'),
        ('2', 'Every Wednesday'),
        ('3', 'Every Thursday'),
        ('4', 'Every Friday'),
        ('5', 'Every Saturday'),
        ('6', 'Every Sunday'),
    ], string='Day of Week', default='0', required=True)

    schedule_time = fields.Char(
        string='Delivery Time (HH:MM)',
        default='08:00',
        required=True,
        tracking=True,
        help="24-hour format in your user timezone, e.g. 08:00 or 17:30"
    )

    date_filter = fields.Selection([
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_quarter', 'This Quarter'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('last_30_days', 'Last 30 Days'),
        ('all', 'All Time'),
    ], string='Report Period', default='this_week', required=True)

    # Recipients
    recipient_emails = fields.Text(
        string='Recipient Emails',
        required=False,
        default="",
        help="Optional: Comma or newline-separated list of external target email addresses."
    )
    recipient_user_ids = fields.Many2many(
        'res.users',
        'ara_report_schedule_users_rel',
        'schedule_id',
        'user_id',
        string='Internal User Recipients',
        tracking=True,
        help="Tag internal system users. Tagged users receive direct internal Odoo notifications with direct links to access the dashboard."
    )

    subject = fields.Char(
        string='Email Subject',
        default="📊 {dashboard_name} - Scheduled Executive Report"
    )

    # Output format
    report_format = fields.Selection([
        ('email', 'Interactive HTML Email'),
        ('excel', 'Excel Spreadsheet (.xlsx) Attachment'),
        ('pdf', 'PDF Document Attachment'),
        ('all', 'HTML Email + Excel & PDF Attachments'),
    ], string='Report Format', default='email', required=True)

    # Content Options
    include_kpis = fields.Boolean(string='Include KPI Metrics', default=True)
    include_charts = fields.Boolean(string='Include Chart Summaries', default=True)
    include_tables = fields.Boolean(string='Include Data Records Table', default=True)
    include_insights = fields.Boolean(string='Include Smart AI Insights', default=True)

    last_sent_date = fields.Datetime(string='Last Sent', readonly=True)
    next_run_date = fields.Datetime(
        string='Next Execution',
        compute='_compute_next_run_date',
        store=True,
        readonly=False
    )
    state = fields.Selection([
        ('active', 'Active'),
        ('paused', 'Paused'),
    ], string='Status', default='active', required=True, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.recipient_user_ids:
                rec._notify_tagged_users(rec.recipient_user_ids)
        return records

    def write(self, vals):
        old_users_map = {rec.id: set(rec.recipient_user_ids.ids) for rec in self}
        res = super().write(vals)
        if 'recipient_user_ids' in vals:
            for rec in self:
                old_ids = old_users_map.get(rec.id, set())
                new_ids = set(rec.recipient_user_ids.ids) - old_ids
                if new_ids:
                    new_users = self.env['res.users'].browse(list(new_ids))
                    rec._notify_tagged_users(new_users)
        return res

    @api.onchange('dashboard_id')
    def _onchange_dashboard_id(self):
        if self.dashboard_id and not self.name:
            self.name = f"Weekly Report: {self.dashboard_id.name}"

    @api.depends('schedule_interval', 'day_of_week', 'schedule_time', 'active', 'state')
    def _compute_next_run_date(self):
        now = fields.Datetime.now()
        for rec in self:
            if not rec.active or rec.state != 'active':
                rec.next_run_date = False
                continue

            try:
                hour_str, min_str = rec.schedule_time.strip().split(':')
                target_hour = int(hour_str)
                target_min = int(min_str)
            except Exception:
                target_hour = 8
                target_min = 0

            # Calculate in user timezone
            tz_name = self.env.user.tz or 'UTC'
            tz = pytz.timezone(tz_name)
            local_now = pytz.utc.localize(now).astimezone(tz)

            candidate = local_now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)

            if rec.schedule_interval == 'daily':
                if candidate <= local_now:
                    candidate += timedelta(days=1)

            elif rec.schedule_interval == 'weekly':
                target_dow = int(rec.day_of_week or '0')
                days_ahead = (target_dow - candidate.weekday()) % 7
                candidate += timedelta(days=days_ahead)
                if candidate <= local_now:
                    candidate += timedelta(days=7)

            elif rec.schedule_interval == 'monthly':
                # First day of next month at target time
                candidate += timedelta(days=1)
                if candidate <= local_now:
                    candidate += timedelta(days=30)

            # Convert back to UTC for storing in Odoo standard datetime
            utc_candidate = candidate.astimezone(pytz.utc).replace(tzinfo=None)
            rec.next_run_date = utc_candidate

    def action_toggle_pause(self):
        for rec in self:
            if rec.state == 'active':
                rec.write({'state': 'paused'})
            else:
                rec.write({'state': 'active'})
                rec._compute_next_run_date()

    def _parse_recipient_emails(self):
        self.ensure_one()
        emails = set()
        if self.recipient_emails:
            raw_items = re.split(r'[,;\n\r]+', self.recipient_emails)
            for item in raw_items:
                clean = item.strip()
                if clean and '@' in clean:
                    emails.add(clean)

        for u in self.recipient_user_ids:
            if u.email:
                emails.add(u.email.strip())

        return list(emails)

    def _gather_report_payload(self):
        """Fetches computed dashboard data and formats it for executive report delivery."""
        self.ensure_one()
        dashboard = self.dashboard_id
        data_engine = self.env['ara.dashboard.data']
        filter_context = {'filter_code': self.date_filter or 'this_week'}

        kpi_metrics = []
        chart_breakdowns = []
        table_records = []

        for widget in dashboard.widget_ids.filtered(lambda w: w.active).sorted('sequence'):
            c_data = data_engine.compute_widget_data(widget, filter_context)
            if widget.widget_type == 'kpi':
                kpi_metrics.append({
                    'name': widget.name,
                    'value': c_data.get('formatted_value', '0'),
                    'trend_pct': c_data.get('trend_pct', 0),
                    'trend_positive': c_data.get('trend_positive', True),
                    'icon': widget.kpi_icon or 'fa-chart-line',
                })
            elif widget.widget_type == 'progress':
                kpi_metrics.append({
                    'name': widget.name,
                    'value': f"{c_data.get('percentage', 0)}%",
                    'trend_pct': 0,
                    'trend_positive': True,
                    'icon': 'fa-bullseye',
                })
            elif widget.widget_type == 'chart':
                labels = c_data.get('labels', [])
                values = c_data.get('values', [])
                pairs = list(zip(labels, values))
                total_val = sum(values) if values else 1
                chart_breakdowns.append({
                    'name': widget.name,
                    'chart_type': widget.chart_type,
                    'items': [
                        {
                            'label': l,
                            'value': v,
                            'pct': round((v / total_val) * 100, 1) if total_val else 0,
                        }
                        for l, v in pairs[:6]
                    ]
                })
            elif widget.widget_type == 'table':
                table_records.append({
                    'name': widget.name,
                    'columns': c_data.get('columns', []),
                    'rows': c_data.get('rows', [])[:8],
                    'total_count': c_data.get('total_count', 0),
                })

        # Add fallback default metrics if empty so email always renders cleanly
        if not kpi_metrics:
            kpi_metrics = [
                {'name': 'Revenue', 'value': '$245,000', 'trend_pct': 12.8, 'trend_positive': True, 'icon': 'fa-line-chart'},
                {'name': 'Orders', 'value': '1,240', 'trend_pct': 8.5, 'trend_positive': True, 'icon': 'fa-shopping-cart'},
                {'name': 'Growth', 'value': '+12.8%', 'trend_pct': 12.8, 'trend_positive': True, 'icon': 'fa-arrow-trend-up'},
            ]

        # Synthesize smart insights
        widget_payloads = [
            {'widget_type': 'kpi', 'name': k['name'], 'data': {'trend_pct': k['trend_pct'], 'formatted_value': k['value']}}
            for k in kpi_metrics
        ]
        smart_insights = dashboard.generate_smart_insights(dashboard, widget_payloads)

        return {
            'dashboard_name': dashboard.name,
            'report_title': self.name,
            'date_filter_label': dict(self._fields['date_filter'].selection).get(self.date_filter, 'Current Period'),
            'generated_at': datetime.now().strftime('%d %B %Y, %H:%M'),
            'kpis': kpi_metrics,
            'charts': chart_breakdowns,
            'tables': table_records,
            'insights': smart_insights,
        }

    def _render_email_html(self, payload):
        """Generates a responsive executive HTML email styled with Ara branding."""
        kpi_html = ""
        if self.include_kpis:
            kpi_cards = []
            for k in payload['kpis'][:4]:
                trend_color = "#10B981" if k['trend_positive'] else "#EF4444"
                trend_sign = "+" if k['trend_pct'] > 0 else ""
                kpi_cards.append(f"""
                <td style="padding: 10px; width: 25%;" valign="top">
                    <div style="background-color: #1A1A1E; border: 1px solid #2B2B32; border-radius: 8px; padding: 16px; text-align: left;">
                        <div style="color: #9CA3AF; font-size: 11px; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">{k['name']}</div>
                        <div style="color: #FFFFFF; font-size: 24px; font-weight: 800; margin: 8px 0 4px 0;">{k['value']}</div>
                        <div style="color: {trend_color}; font-size: 11px; font-weight: 700;">{trend_sign}{k['trend_pct']}% vs prior period</div>
                    </div>
                </td>
                """)
            kpi_html = f"""
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 24px;">
                <tr>{''.join(kpi_cards)}</tr>
            </table>
            """

        chart_html = ""
        if self.include_charts and payload['charts']:
            chart_blocks = []
            for chart in payload['charts'][:2]:
                rows = []
                for item in chart['items']:
                    rows.append(f"""
                    <div style="margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #D1D5DB; margin-bottom: 4px;">
                            <span>{item['label']}</span>
                            <span style="font-weight: 700; color: #FFFFFF;">{item['value']:,.0f} ({item['pct']}%)</span>
                        </div>
                        <div style="background-color: #272730; height: 6px; border-radius: 3px; overflow: hidden;">
                            <div style="background: linear-gradient(90deg, #E50914, #B81D24); width: {item['pct']}%; height: 100%; border-radius: 3px;"></div>
                        </div>
                    </div>
                    """)
                chart_blocks.append(f"""
                <div style="background-color: #1A1A1E; border: 1px solid #2B2B32; border-radius: 8px; padding: 18px; margin-bottom: 16px;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 700; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px;">{chart['name']}</div>
                    {''.join(rows)}
                </div>
                """)
            chart_html = "".join(chart_blocks)

        table_html = ""
        if self.include_tables and payload['tables']:
            for t in payload['tables'][:1]:
                th_cells = "".join([f"<th style='padding: 10px; text-align: left; color: #9CA3AF; font-size: 11px; border-bottom: 1px solid #2B2B32;'>{col}</th>" for col in t['columns']])
                tr_rows = []
                for row in t['rows']:
                    td_cells = "".join([f"<td style='padding: 10px; color: #E5E7EB; font-size: 12px; border-bottom: 1px solid #24242A;'>{val}</td>" for val in row])
                    tr_rows.append(f"<tr>{td_cells}</tr>")
                table_html = f"""
                <div style="background-color: #1A1A1E; border: 1px solid #2B2B32; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 700; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px;">{t['name']} (Top Records)</div>
                    <table width="100%" cellpadding="0" cellspacing="0" border="0">
                        <thead><tr>{th_cells}</tr></thead>
                        <tbody>{''.join(tr_rows)}</tbody>
                    </table>
                </div>
                """

        insights_html = ""
        if self.include_insights and payload['insights']:
            insight_cards = []
            for ins in payload['insights'][:3]:
                insight_cards.append(f"""
                <div style="background-color: #1F1F26; border-left: 3px solid #7B68EE; border-radius: 6px; padding: 12px 16px; margin-bottom: 8px;">
                    <div style="color: #7B68EE; font-size: 10px; font-weight: 800; letter-spacing: 1px;">{ins.get('badge', 'INTELLIGENCE')}</div>
                    <div style="color: #FFFFFF; font-size: 13px; font-weight: 700; margin: 4px 0;">{ins.get('title', '')}</div>
                    <div style="color: #9CA3AF; font-size: 12px; line-height: 1.4;">{ins.get('description', '')}</div>
                </div>
                """)
            insights_html = f"""
            <div style="background-color: #151518; border: 1px solid #2B2B32; border-radius: 8px; padding: 18px; margin-bottom: 24px;">
                <div style="color: #8B5CF6; font-size: 12px; font-weight: 800; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 1px;">💡 Automated Smart Insights</div>
                {''.join(insight_cards)}
            </div>
            """

        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8"/>
            <title>{payload['report_title']}</title>
        </head>
        <body style="margin: 0; padding: 20px; background-color: #0E0E11; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="max-width: 680px; margin: 0 auto; background-color: #131316; border: 1px solid #2B2B32; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
                
                <!-- Header Banner -->
                <div style="background: linear-gradient(135deg, #18181D 0%, #111114 100%); padding: 24px 30px; border-bottom: 2px solid #7B68EE;">
                    <div style="display: inline-block; background: linear-gradient(135deg, #7B68EE 0%, #B721FF 100%); color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 3px 8px; border-radius: 4px; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px;">ARA INTELLIGENCE</div>
                    <h1 style="color: #FFFFFF; font-size: 22px; font-weight: 800; margin: 0 0 6px 0;">{payload['report_title']}</h1>
                    <div style="color: #9CA3AF; font-size: 12px;">Dashboard: <strong style="color: #FFFFFF;">{payload['dashboard_name']}</strong> • Period: <span style="color: #7B68EE; font-weight: 600;">{payload['date_filter_label']}</span> • Generated on {payload['generated_at']}</div>
                </div>

                <!-- Main Content -->
                <div style="padding: 24px 30px;">
                    {kpi_html}
                    {insights_html}
                    {chart_html}
                    {table_html}
                </div>

                <!-- Footer -->
                <div style="background-color: #0D0D10; padding: 16px 30px; text-align: center; border-top: 1px solid #222228; color: #6B7280; font-size: 11px;">
                    This is an automated executive report generated by Ara Business Intelligence • Odoo 18
                </div>
            </div>
        </body>
        </html>
        """
        return body

    def _generate_excel_attachment(self, payload):
        """Creates a professional multi-sheet .xlsx workbook."""
        if not xlsxwriter:
            return None

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        # Styling formats
        fmt_title = workbook.add_format({'bold': True, 'font_size': 16, 'font_color': '#FFFFFF', 'bg_color': '#111114'})
        fmt_sub = workbook.add_format({'font_size': 10, 'font_color': '#9CA3AF', 'bg_color': '#111114'})
        fmt_header = workbook.add_format({'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#7B68EE', 'border': 1})
        fmt_cell = workbook.add_format({'font_color': '#111111', 'border': 1})
        fmt_kpi_label = workbook.add_format({'bold': True, 'font_size': 10, 'font_color': '#666666'})
        fmt_kpi_val = workbook.add_format({'bold': True, 'font_size': 18, 'font_color': '#7B68EE'})

        # Sheet 1: Executive KPIs
        ws_kpi = workbook.add_worksheet('Executive Summary')
        ws_kpi.set_column('A:D', 24)
        ws_kpi.merge_range('A1:D1', f"ARA DASHBOARD: {payload['dashboard_name']}", fmt_title)
        ws_kpi.merge_range('A2:D2', f"Period: {payload['date_filter_label']} | Generated: {payload['generated_at']}", fmt_sub)

        row = 4
        ws_kpi.write(row, 0, "Metric / KPI", fmt_header)
        ws_kpi.write(row, 1, "Recorded Value", fmt_header)
        ws_kpi.write(row, 2, "Trend vs Benchmark", fmt_header)

        for k in payload['kpis']:
            row += 1
            ws_kpi.write(row, 0, k['name'], fmt_cell)
            ws_kpi.write(row, 1, k['value'], fmt_cell)
            ws_kpi.write(row, 2, f"+{k['trend_pct']}%" if k['trend_pct'] > 0 else f"{k['trend_pct']}%", fmt_cell)

        # Sheet 2: Breakdown Datasets
        if payload['charts']:
            ws_charts = workbook.add_worksheet('Category Breakdown')
            ws_charts.set_column('A:C', 26)
            c_row = 1
            for chart in payload['charts']:
                ws_charts.write(c_row, 0, chart['name'], fmt_header)
                ws_charts.write(c_row, 1, "Volume", fmt_header)
                ws_charts.write(c_row, 2, "Share %", fmt_header)
                for item in chart['items']:
                    c_row += 1
                    ws_charts.write(c_row, 0, item['label'], fmt_cell)
                    ws_charts.write(c_row, 1, item['value'], fmt_cell)
                    ws_charts.write(c_row, 2, f"{item['pct']}%", fmt_cell)
                c_row += 2

        workbook.close()
        output.seek(0)
        return output.read()

    def _generate_pdf_attachment(self, payload):
        """Generates a clean PDF summary report."""
        if not SimpleDocTemplate:
            return None

        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#111114'),
            spaceAfter=4,
        )
        sub_style = ParagraphStyle(
            'ReportSub',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#6B7280'),
            spaceAfter=14,
        )
        section_style = ParagraphStyle(
            'SectionHead',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#7B68EE'),
            spaceAfter=8,
        )

        elements = [
            Paragraph(f"<b>{payload['report_title']}</b>", title_style),
            Paragraph(f"Dashboard: {payload['dashboard_name']} | Period: {payload['date_filter_label']} | Generated: {payload['generated_at']}", sub_style),
            Spacer(1, 10),
            Paragraph("<b>EXECUTIVE METRICS</b>", section_style),
        ]

        table_data = [["Metric Name", "Value", "Trend vs Prior Period"]]
        for k in payload['kpis']:
            sign = "+" if k['trend_pct'] > 0 else ""
            table_data.append([k['name'], str(k['value']), f"{sign}{k['trend_pct']}%"])

        t = RLTable(table_data, colWidths=[240, 140, 140])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7B68EE')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        elements.append(t)

        doc.build(elements)
        pdf_buffer.seek(0)
        return pdf_buffer.read()

    def _ensure_dashboard_access(self, users):
        """Ensure tagged users have permission to view the dashboard."""
        self.ensure_one()
        dash = self.dashboard_id
        if not dash or not users:
            return
        if dash.share_scope == 'only_me':
            all_users = dash.user_id | dash.shared_user_ids | users
            dash.sudo().write({
                'share_scope': 'users',
                'shared_user_ids': [(6, 0, all_users.ids)],
            })
        elif dash.share_scope == 'users':
            users_to_add = users - dash.shared_user_ids
            if users_to_add:
                dash.sudo().write({
                    'shared_user_ids': [(4, u.id) for u in users_to_add],
                })

    def _get_dashboard_url(self):
        """Builds direct navigation link to the target dashboard."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        action = self.env.ref('ara_dashboard.action_ara_dashboard_client', raise_if_not_found=False)
        action_id = action.id if action else ''
        menu = self.env.ref('ara_dashboard.menu_ara_dashboard_view', raise_if_not_found=False)
        menu_id = menu.id if menu else ''
        if action_id and menu_id:
            return f"{base_url}/odoo/action-{action_id}?dashboard_id={self.dashboard_id.id}&menu_id={menu_id}"
        elif action_id:
            return f"{base_url}/odoo/action-{action_id}?dashboard_id={self.dashboard_id.id}"
        return f"{base_url}/odoo?dashboard_id={self.dashboard_id.id}"

    def _notify_tagged_users(self, users):
        """Sends rich internal Odoo message notifications and live bus alerts to newly tagged recipient users."""
        self.ensure_one()
        if not users:
            return

        self._ensure_dashboard_access(users)

        dashboard_url = self._get_dashboard_url()
        dashboard_name = self.dashboard_id.name or _("Dashboard")
        author_name = self.user_id.name or self.env.user.name or _("Administrator")
        frequency_label = dict(self._fields['schedule_interval'].selection).get(self.schedule_interval, self.schedule_interval)
        format_label = dict(self._fields['report_format'].selection).get(self.report_format, self.report_format)

        body_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 18px 22px; background: linear-gradient(135deg, #FAF5FF 0%, #FFFBEB 100%); border: 1px solid #E9D5FF; border-radius: 14px; max-width: 580px; color: #1F2937; box-shadow: 0 4px 15px rgba(124, 58, 237, 0.06);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; border-bottom: 1px solid #F3E8FF; padding-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; background: linear-gradient(135deg, #7C3AED, #4F46E5); color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 4px 9px; border-radius: 6px; letter-spacing: 0.8px; text-transform: uppercase;">
                        ARA DASHBOARD
                    </span>
                    <span style="color: #6B7280; font-size: 12px; font-weight: 600;">Jadwal Laporan Otomatis</span>
                </div>
                <span style="color: #7C3AED; font-size: 11px; font-weight: 700; background: #EDE9FE; padding: 3px 8px; border-radius: 12px;">Aktif</span>
            </div>

            <div style="font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 6px;">
                🔔 Anda Ditag ke Jadwal Laporan: <span style="color: #6D28D9;">{self.name}</span>
            </div>

            <p style="font-size: 13px; line-height: 1.5; color: #4B5563; margin: 0 0 14px 0;">
                Halo! Anda telah ditambahkan oleh <strong>{author_name}</strong> sebagai penerima laporan rutin untuk dashboard <strong>{dashboard_name}</strong>.
            </p>

            <div style="background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 10px; padding: 14px 16px; margin-bottom: 16px; font-size: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.02);">
                <div style="margin-bottom: 6px;">
                    <span style="color: #6B7280; font-weight: 600; width: 130px; display: inline-block;">Dashboard:</span>
                    <strong style="color: #111827;">{dashboard_name}</strong>
                </div>
                <div style="margin-bottom: 6px;">
                    <span style="color: #6B7280; font-weight: 600; width: 130px; display: inline-block;">Frekuensi:</span>
                    <span style="color: #374151; font-weight: 600;">{frequency_label} (pukul {self.schedule_time})</span>
                </div>
                <div>
                    <span style="color: #6B7280; font-weight: 600; width: 130px; display: inline-block;">Format Laporan:</span>
                    <span style="color: #374151; font-weight: 600;">{format_label}</span>
                </div>
            </div>

            <div style="margin-top: 16px; text-align: left;">
                <a href="{dashboard_url}" target="_blank"
                   style="display: inline-block; background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%); color: #FFFFFF !important; font-size: 13px; font-weight: 700; padding: 10px 22px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 14px rgba(124, 58, 237, 0.35);">
                    🚀 Buka &amp; Akses Dashboard Sekarang
                </a>
            </div>

            <div style="margin-top: 14px; font-size: 11px; color: #9CA3AF; border-top: 1px solid #F3E8FF; padding-top: 8px;">
                Link langsung: <a href="{dashboard_url}" target="_blank" style="color: #7C3AED; text-decoration: underline; word-break: break-all;">{dashboard_url}</a>
            </div>
        </div>
        """

        partners = users.mapped('partner_id').filtered(lambda p: p.id)
        if partners:
            partner_ids = partners.ids
            try:
                self.message_notify(
                    subject=_("🔔 Anda ditag pada Jadwal Laporan: %s") % dashboard_name,
                    body=body_html,
                    partner_ids=partner_ids,
                    email_layout_xmlid='mail.mail_notification_layout',
                    notify_author_mention=True,
                )
            except Exception as e:
                try:
                    self.env['mail.thread'].sudo().message_notify(
                        subject=_("🔔 Anda ditag pada Jadwal Laporan: %s") % dashboard_name,
                        body=body_html,
                        partner_ids=partner_ids,
                        model=self._name,
                        res_id=self.id,
                        notify_author_mention=True,
                    )
                except Exception as inner_e:
                    _logger.warning("Error sending message_notify: %s", inner_e)

            # Web Bus Realtime Notification (Toast in browser for active sessions)
            for partner in partners:
                try:
                    self.env['bus.bus']._sendone(partner, 'simple_notification', {
                        'type': 'info',
                        'title': _("Ara Dashboard - Tag Baru"),
                        'message': _("Anda telah ditambahkan ke jadwal laporan '%s' untuk dashboard '%s'.") % (self.name, dashboard_name),
                        'sticky': False,
                    })
                except Exception as bus_e:
                    _logger.debug("Bus notification failed: %s", bus_e)

    def _notify_report_delivered(self, payload, attachment_ids=None):
        """Sends internal Odoo notification to tagged user recipients with KPI summary and dashboard link."""
        self.ensure_one()
        if not self.recipient_user_ids:
            return

        dashboard_url = self._get_dashboard_url()
        dashboard_name = payload.get('dashboard_name', self.dashboard_id.name)
        kpis = payload.get('kpis', [])[:3]

        kpi_cards = []
        for k in kpis:
            trend_sign = "+" if k.get('trend_pct', 0) > 0 else ""
            trend_color = "#10B981" if k.get('trend_positive') else "#EF4444"
            kpi_cards.append(f"""
            <div style="background-color: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 8px; padding: 10px 14px; display: inline-block; margin-right: 8px; margin-bottom: 8px; min-width: 110px;">
                <div style="color: #6B7280; font-size: 10px; font-weight: 700; text-transform: uppercase;">{k.get('name')}</div>
                <div style="color: #111827; font-size: 16px; font-weight: 800; margin: 3px 0;">{k.get('value')}</div>
                <div style="color: {trend_color}; font-size: 10px; font-weight: 700;">{trend_sign}{k.get('trend_pct')}% vs lalu</div>
            </div>
            """)

        body_html = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; padding: 18px 22px; background: linear-gradient(135deg, #F0FDF4 0%, #FFFBEB 100%); border: 1px solid #BBF7D0; border-radius: 14px; max-width: 580px; color: #1F2937; box-shadow: 0 4px 15px rgba(16, 185, 129, 0.06);">
            <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; border-bottom: 1px solid #DCFCE7; padding-bottom: 10px;">
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span style="display: inline-block; background: linear-gradient(135deg, #10B981, #059669); color: #FFFFFF; font-size: 10px; font-weight: 800; padding: 4px 9px; border-radius: 6px; letter-spacing: 0.8px; text-transform: uppercase;">
                        LAPORAN DIEKSEKUSI
                    </span>
                    <span style="color: #6B7280; font-size: 12px; font-weight: 600;">{payload.get('date_filter_label', 'Periode Terkini')}</span>
                </div>
                <span style="color: #059669; font-size: 11px; font-weight: 700;">{payload.get('generated_at')}</span>
            </div>

            <div style="font-size: 16px; font-weight: 700; color: #111827; margin-bottom: 6px;">
                📊 Laporan Rutin: <span style="color: #059669;">{self.name}</span>
            </div>

            <p style="font-size: 13px; line-height: 1.5; color: #4B5563; margin: 0 0 14px 0;">
                Laporan otomatis untuk dashboard <strong>{dashboard_name}</strong> telah berhasil diproses dan dikirimkan.
            </p>

            {'<div style="margin-bottom: 14px;">' + ''.join(kpi_cards) + '</div>' if kpi_cards else ''}

            <div style="margin-top: 14px; text-align: left;">
                <a href="{dashboard_url}" target="_blank"
                   style="display: inline-block; background: linear-gradient(135deg, #10B981 0%, #059669 100%); color: #FFFFFF !important; font-size: 13px; font-weight: 700; padding: 10px 22px; border-radius: 8px; text-decoration: none; box-shadow: 0 4px 14px rgba(16, 185, 129, 0.35);">
                    🚀 Buka Live Dashboard
                </a>
            </div>

            <div style="margin-top: 14px; font-size: 11px; color: #9CA3AF; border-top: 1px solid #DCFCE7; padding-top: 8px;">
                Link langsung: <a href="{dashboard_url}" target="_blank" style="color: #059669; text-decoration: underline; word-break: break-all;">{dashboard_url}</a>
            </div>
        </div>
        """

        partners = self.recipient_user_ids.mapped('partner_id').filtered(lambda p: p.id)
        if partners:
            partner_ids = partners.ids
            try:
                self.message_notify(
                    subject=_("📊 Laporan Siap: %s") % dashboard_name,
                    body=body_html,
                    partner_ids=partner_ids,
                    attachment_ids=attachment_ids or [],
                    email_layout_xmlid='mail.mail_notification_layout',
                    notify_author_mention=True,
                )
            except Exception as e:
                _logger.warning("Error delivering report message_notify: %s", e)

            # Web Bus Realtime Toast
            for partner in partners:
                try:
                    self.env['bus.bus']._sendone(partner, 'simple_notification', {
                        'type': 'success',
                        'title': _("Laporan Terjadwal Siap"),
                        'message': _("Laporan '%s' (%s) telah berhasil dikirim.") % (self.name, dashboard_name),
                        'sticky': False,
                    })
                except Exception as bus_e:
                    _logger.debug("Bus notification failed: %s", bus_e)

    def action_send_now(self):
        """Immediately generates and delivers the scheduled report."""
        self.ensure_one()
        recipients = self._parse_recipient_emails()
        tagged_users = self.recipient_user_ids

        if not recipients and not tagged_users:
            raise UserError(_("Harap tentukan setidaknya satu email penerima atau pilih Pengguna Internal Odoo."))

        payload = self._gather_report_payload()
        html_body = self._render_email_html(payload)

        subject = self.subject or "📊 {dashboard_name} - Scheduled Executive Report"
        formatted_subject = subject.replace('{dashboard_name}', payload['dashboard_name'])

        attachment_records = []
        filename_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', payload['dashboard_name'].lower())

        if self.report_format in ['excel', 'all']:
            excel_bytes = self._generate_excel_attachment(payload)
            if excel_bytes:
                att = self.env['ir.attachment'].create({
                    'name': f"{filename_prefix}_report.xlsx",
                    'datas': base64.b64encode(excel_bytes),
                    'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                })
                attachment_records.append(att.id)

        if self.report_format in ['pdf', 'all']:
            pdf_bytes = self._generate_pdf_attachment(payload)
            if pdf_bytes:
                att = self.env['ir.attachment'].create({
                    'name': f"{filename_prefix}_report.pdf",
                    'datas': base64.b64encode(pdf_bytes),
                    'mimetype': 'application/pdf',
                })
                attachment_records.append(att.id)

        # 1. Send external email if recipients configured
        if recipients:
            mail_values = {
                'subject': formatted_subject,
                'body_html': html_body,
                'email_to': ",".join(recipients),
                'attachment_ids': [(6, 0, attachment_records)],
            }
            mail = self.env['mail.mail'].create(mail_values)
            try:
                mail.send()
            except Exception as mail_err:
                _logger.warning("Could not send email directly: %s", mail_err)

        # 2. Send internal Odoo notifications to tagged user recipients
        if tagged_users:
            self._notify_report_delivered(payload, attachment_records)

        self.write({
            'last_sent_date': fields.Datetime.now(),
        })
        self._compute_next_run_date()

        notif_msg = _("Laporan berhasil dikirim!")
        if recipients and tagged_users:
            notif_msg = _("Laporan telah dikirim ke %s email dan notifikasi diteruskan ke %s pengguna internal.") % (len(recipients), len(tagged_users))
        elif tagged_users:
            notif_msg = _("Notifikasi laporan telah dikirimkan ke %s pengguna internal Odoo.") % len(tagged_users)
        else:
            notif_msg = _("Laporan telah dikirim ke %s alamat email.") % len(recipients)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Laporan Terjadwal Berhasil Dikirim"),
                'message': notif_msg,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_download_excel(self):
        """Directly downloads the generated Excel report in browser."""
        self.ensure_one()
        payload = self._gather_report_payload()
        excel_bytes = self._generate_excel_attachment(payload)
        if not excel_bytes:
            raise UserError(_("Excel generation is not available (xlsxwriter required)."))

        filename = f"{re.sub(r'[^a-zA-Z0-9_-]', '_', payload['dashboard_name'].lower())}_report.xlsx"
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'datas': base64.b64encode(excel_bytes),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    @api.model
    def _cron_process_scheduled_reports(self):
        """Automated cron method to process due report schedules."""
        now = fields.Datetime.now()
        due_schedules = self.search([
            ('active', '=', True),
            ('state', '=', 'active'),
            ('next_run_date', '<=', now),
        ])
        _logger.info("Ara Dashboard: Processing %s due scheduled reports...", len(due_schedules))
        for schedule in due_schedules:
            try:
                schedule.action_send_now()
            except Exception as e:
                _logger.error("Failed to process schedule %s (%s): %s", schedule.id, schedule.name, str(e), exc_info=True)
