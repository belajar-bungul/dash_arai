# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestAraDashboardData(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.DataEngine = cls.env['ara.dashboard.data']
        cls.Dashboard = cls.env['ara.dashboard']
        cls.Widget = cls.env['ara.dashboard.widget']
        cls.PartnerModel = cls.env['ir.model'].search([('model', '=', 'res.partner')], limit=1)

        # Create dummy partner for testing counts
        cls.env['res.partner'].create({
            'name': 'Ara Test Partner 1',
            'email': 'test1@arasoft.id',
        })

    def test_date_filter_resolution(self):
        """Test date ranges for various filter keywords."""
        res_today = self.DataEngine.resolve_date_filter('today')
        self.assertIsNotNone(res_today['current'][0])
        self.assertIsNotNone(res_today['current'][1])

        res_month = self.DataEngine.resolve_date_filter('this_month')
        self.assertIsNotNone(res_month['current'][0])
        self.assertIsNotNone(res_month['current'][1])
        self.assertEqual(res_month['label'], 'vs Last Month')

        res_all = self.DataEngine.resolve_date_filter('all')
        self.assertIsNone(res_all['current'][0])

    def test_safe_domain_parser(self):
        """Test safe domain parser without eval."""
        self.assertEqual(self.DataEngine.safe_parse_domain(""), [])
        self.assertEqual(self.DataEngine.safe_parse_domain("[('name', '=', 'Test')]"), [('name', '=', 'Test')])
        self.assertEqual(self.DataEngine.safe_parse_domain("malformed __import__"), [])

    def test_kpi_computation(self):
        """Test KPI metric calculation."""
        dash = self.Dashboard.create({'name': 'KPI Test'})
        widget = self.Widget.create({
            'dashboard_id': dash.id,
            'name': 'Contacts Count',
            'widget_type': 'kpi',
            'model_id': self.PartnerModel.id,
            'aggregation_type': 'count',
        })

        data = self.DataEngine.compute_widget_data(widget, {'filter_code': 'all'})
        self.assertNotIn('error', data)
        self.assertGreaterEqual(data['value'], 1)

    def test_progress_computation(self):
        """Test Progress metric calculation."""
        dash = self.Dashboard.create({'name': 'Progress Test'})
        widget = self.Widget.create({
            'dashboard_id': dash.id,
            'name': 'Target Contacts',
            'widget_type': 'progress',
            'model_id': self.PartnerModel.id,
            'aggregation_type': 'count',
            'target_value': 100.0,
        })

        data = self.DataEngine.compute_widget_data(widget, {'filter_code': 'all'})
        self.assertNotIn('error', data)
        self.assertGreaterEqual(data['percentage'], 0.0)
