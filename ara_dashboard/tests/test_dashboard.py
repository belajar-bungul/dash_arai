# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import AccessError


class TestAraDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Dashboard = cls.env['ara.dashboard']
        cls.Widget = cls.env['ara.dashboard.widget']
        cls.PartnerModel = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        cls.test_dashboard = cls.Dashboard.create({
            'name': 'Sales Executive Hub',
            'refresh_interval': '30',
            'date_filter_default': 'this_month',
            'share_scope': 'everyone',
        })

    def test_dashboard_creation(self):
        """Test creating a dashboard and adding widgets."""
        self.assertEqual(self.test_dashboard.name, 'Sales Executive Hub')
        self.assertEqual(self.test_dashboard.widget_count, 0)

        # Add a KPI widget
        widget = self.Widget.create({
            'dashboard_id': self.test_dashboard.id,
            'name': 'Total Contacts',
            'widget_type': 'kpi',
            'model_id': self.PartnerModel.id,
            'aggregation_type': 'count',
        })

        self.assertEqual(self.test_dashboard.widget_count, 1)
        self.assertEqual(widget.dashboard_id.id, self.test_dashboard.id)

    def test_accessible_dashboards(self):
        """Test user access control on dashboards."""
        accessible = self.Dashboard.get_accessible_dashboards()
        ids = [d['id'] for d in accessible]
        self.assertIn(self.test_dashboard.id, ids)

    def test_fetch_dashboard_payload(self):
        """Test batch fetching payload for frontend rendering."""
        # Create partner widget
        self.Widget.create({
            'dashboard_id': self.test_dashboard.id,
            'name': 'Total Contacts',
            'widget_type': 'kpi',
            'model_id': self.PartnerModel.id,
            'aggregation_type': 'count',
        })

        payload = self.Dashboard.fetch_dashboard_payload(self.test_dashboard.id, 'this_month')
        self.assertTrue(payload['dashboard'])
        self.assertEqual(payload['dashboard']['id'], self.test_dashboard.id)
        self.assertEqual(len(payload['widgets']), 1)
        self.assertEqual(payload['widgets'][0]['widget_type'], 'kpi')

    def test_reorder_widgets_instant_refresh(self):
        """Test instant sequence updating and payload refresh without full reload."""
        w1 = self.Widget.create({
            'dashboard_id': self.test_dashboard.id,
            'name': 'Widget 1',
            'widget_type': 'kpi',
            'model_id': self.PartnerModel.id,
            'sequence': 10,
        })
        w2 = self.Widget.create({
            'dashboard_id': self.test_dashboard.id,
            'name': 'Widget 2',
            'widget_type': 'kpi',
            'model_id': self.PartnerModel.id,
            'sequence': 20,
        })

        # Reorder them
        reorder_data = [
            {'id': w1.id, 'sequence': 20},
            {'id': w2.id, 'sequence': 10},
        ]
        res = self.Dashboard.reorder_widgets(self.test_dashboard.id, reorder_data)
        self.assertTrue(res['widgets'])
        w1.invalidate_recordset(['sequence'])
        w2.invalidate_recordset(['sequence'])
        self.assertEqual(w1.sequence, 20)
        self.assertEqual(w2.sequence, 10)

    def test_scheduled_dashboard_report(self):
        """Test creating, computing next run, and generating scheduled dashboard report."""
        Schedule = self.env['ara.dashboard.report.schedule']
        schedule = Schedule.create({
            'name': 'Weekly Executive Briefing',
            'dashboard_id': self.test_dashboard.id,
            'schedule_interval': 'weekly',
            'day_of_week': '0',
            'schedule_time': '08:00',
            'recipient_emails': 'sales@company.com, manager@company.com',
            'report_format': 'all',
        })
        self.assertTrue(schedule.next_run_date)
        emails = schedule._parse_recipient_emails()
        self.assertIn('sales@company.com', emails)
        self.assertIn('manager@company.com', emails)

        # Test gathering payload
        payload = schedule._gather_report_payload()
        self.assertEqual(payload['dashboard_name'], self.test_dashboard.name)
        self.assertTrue(len(payload['kpis']) > 0)

        # Test rendering HTML
        html = schedule._render_email_html(payload)
        self.assertIn('Weekly Executive Briefing', html)

        # Test Excel & PDF generation
        excel_bytes = schedule._generate_excel_attachment(payload)
        self.assertTrue(excel_bytes is not None and len(excel_bytes) > 0)

        pdf_bytes = schedule._generate_pdf_attachment(payload)
        self.assertTrue(pdf_bytes is not None and len(pdf_bytes) > 0)

        # Test send now action
        action_res = schedule.action_send_now()
        self.assertEqual(action_res['params']['type'], 'success')
        self.assertTrue(schedule.last_sent_date)

    def test_all_15_widget_types_computation(self):
        """Test data engine computation for all 15 commercial chart and widget types."""
        data_engine = self.env['ara.dashboard.data']
        filter_context = {'filter_code': 'all'}
        sale_model = self.env['ir.model'].search([('model', '=', 'sale.order')], limit=1) or self.PartnerModel
        measure_field = self.env['ir.model.fields'].search([
            ('model_id', '=', sale_model.id),
            ('name', '=', 'amount_total'),
            ('store', '=', True),
        ], limit=1) or self.env['ir.model.fields'].search([
            ('model_id', '=', sale_model.id),
            ('ttype', 'in', ['integer', 'float', 'monetary']),
            ('store', '=', True),
        ], limit=1)
        groupby_field = self.env['ir.model.fields'].search([
            ('model_id', '=', sale_model.id),
            ('name', 'in', ['state', 'partner_id', 'stage_id']),
            ('store', '=', True),
        ], limit=1) or self.env['ir.model.fields'].search([
            ('model_id', '=', sale_model.id),
            ('store', '=', True),
        ], limit=1)
        
        types_to_test = [
            'tiles', 'line', 'table', 'bar', 'horizontal_bar',
            'todo', 'polar_area', 'pie', 'doughnut', 'flower',
            'funnel', 'radial', 'bullet', 'scatter', 'radar'
        ]
        
        for wtype in types_to_test:
            widget = self.Widget.create({
                'dashboard_id': self.test_dashboard.id,
                'name': f"Test {wtype.title()}",
                'widget_type': wtype,
                'model_id': sale_model.id,
                'measure_field_id': measure_field.id if measure_field else False,
                'groupby_field_id': groupby_field.id if groupby_field else False,
                'aggregation_type': 'sum' if measure_field else 'count',
                'target_value': 1000.0,
            })
            res = data_engine.compute_widget_data(widget, filter_context)
            self.assertNotIn('error', res, f"Widget type {wtype} returned calculation error: {res.get('error')}")

