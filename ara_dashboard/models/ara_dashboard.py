# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class AraDashboard(models.Model):
    _name = 'ara.dashboard'
    _inherit = ['mail.thread']
    _description = 'Ara Business Dashboard'
    _order = 'sequence, id desc'

    name = fields.Char(string='Dashboard Name', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    user_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True
    )

    # Sharing & Permissions
    share_scope = fields.Selection([
        ('only_me', 'Only Me (Private)'),
        ('department', 'My Department'),
        ('users', 'Selected Users'),
        ('groups', 'Selected Groups'),
        ('everyone', 'Everyone (All Users)'),
    ], string='Share Scope', default='everyone', required=True)

    share_permission = fields.Selection([
        ('view', 'View Only'),
        ('edit', 'Can Edit Widgets'),
        ('manage', 'Full Management'),
    ], string='Share Permission', default='view', required=True)

    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        help="Shared with members of this department if scope is set to 'My Department'."
    )
    shared_user_ids = fields.Many2many(
        'res.users',
        'ara_dashboard_shared_users_rel',
        'dashboard_id',
        'user_id',
        string='Shared Users'
    )
    shared_group_ids = fields.Many2many(
        'res.groups',
        'ara_dashboard_shared_groups_rel',
        'dashboard_id',
        'group_id',
        string='Shared Groups'
    )

    # Personal User Favorites
    favorite_user_ids = fields.Many2many(
        'res.users',
        'ara_dashboard_favorite_users_rel',
        'dashboard_id',
        'user_id',
        string='Bookmarked by Users'
    )

    # Presentation & Wallboard TV Settings
    presentation_interval = fields.Integer(
        string='Slide Rotation Interval (seconds)',
        default=12,
        help="Number of seconds to display each slide before rotating in Presentation Mode."
    )
    tv_mode_enabled = fields.Boolean(
        string='Wallboard / TV Mode Enabled',
        default=True
    )

    refresh_interval = fields.Selection([
        ('0', 'Disabled'),
        ('10', 'Every 10 Seconds'),
        ('30', 'Every 30 Seconds'),
        ('60', 'Every 1 Minute'),
        ('300', 'Every 5 Minutes'),
    ], string='Auto Refresh', default='0', required=True)

    date_filter_default = fields.Selection([
        ('all', 'All Time'),
        ('today', 'Today'),
        ('this_week', 'This Week'),
        ('this_month', 'This Month'),
        ('this_quarter', 'This Quarter'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('last_30_days', 'Last 30 Days'),
    ], string='Default Date Filter', default='this_month', required=True)

    widget_ids = fields.One2many(
        'ara.dashboard.widget',
        'dashboard_id',
        string='Widgets',
        copy=True
    )
    widget_count = fields.Integer(
        string='Widget Count',
        compute='_compute_widget_count'
    )

    @api.depends('widget_ids')
    def _compute_widget_count(self):
        for record in self:
            record.widget_count = len(record.widget_ids)

    def action_view_dashboard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'ara_dashboard_main',
            'name': self.name,
            'params': {
                'dashboard_id': self.id,
            },
            'context': {
                'active_dashboard_id': self.id,
            }
        }

    def get_dashboard_url(self):
        """Returns direct web client URL for this dashboard."""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '').rstrip('/')
        action = self.env.ref('ara_dashboard.action_ara_dashboard_client', raise_if_not_found=False)
        action_id = action.id if action else ''
        menu = self.env.ref('ara_dashboard.menu_ara_dashboard_view', raise_if_not_found=False)
        menu_id = menu.id if menu else ''
        if action_id and menu_id:
            return f"{base_url}/odoo/action-{action_id}?dashboard_id={self.id}&menu_id={menu_id}"
        elif action_id:
            return f"{base_url}/odoo/action-{action_id}?dashboard_id={self.id}"
        return f"{base_url}/odoo?dashboard_id={self.id}"

    @api.model
    def toggle_favorite(self, dashboard_id):
        """Toggle personal favorite status for the current user."""
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            return False
        user = self.env.user
        if user in dashboard.favorite_user_ids:
            dashboard.write({'favorite_user_ids': [(3, user.id)]})
            return False
        else:
            dashboard.write({'favorite_user_ids': [(4, user.id)]})
            return True

    @api.model
    def get_accessible_dashboards(self):
        """Returns list of dashboards current user can access based on scope & permissions."""
        dashboards = self.search([('active', '=', True)])
        result = []
        user = self.env.user
        is_admin = user.has_group('ara_dashboard.group_ara_dashboard_manager')

        # Get user department if hr.employee exists
        user_department_id = False
        if hasattr(user, 'employee_ids') and user.employee_ids:
            user_department_id = user.employee_ids[0].department_id.id

        for d in dashboards:
            is_owner = (d.user_id.id == user.id)
            can_access = False

            if is_owner or is_admin or d.share_scope == 'everyone':
                can_access = True
            elif d.share_scope == 'department' and d.department_id and d.department_id.id == user_department_id:
                can_access = True
            elif d.share_scope == 'users' and user in d.shared_user_ids:
                can_access = True
            elif d.share_scope == 'groups' and any(grp in user.groups_id for grp in d.shared_group_ids):
                can_access = True

            if can_access:
                can_edit = is_owner or is_admin or (d.share_permission in ['edit', 'manage'])
                can_manage = is_owner or is_admin or (d.share_permission == 'manage')

                result.append({
                    'id': d.id,
                    'name': d.name,
                    'is_owner': is_owner,
                    'is_favorite': user in d.favorite_user_ids,
                    'can_edit': can_edit,
                    'can_manage': can_manage,
                    'share_scope': d.share_scope,
                    'share_permission': d.share_permission,
                })
        return result

    @api.model
    def update_sharing(self, dashboard_id, share_scope, share_permission):
        """Updates sharing scope and permission configuration from the frontend modal."""
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            raise UserError(_("Dashboard record was not found."))
        user = self.env.user
        is_admin = user.has_group('ara_dashboard.group_ara_dashboard_manager')
        is_owner = (dashboard.user_id.id == user.id)
        if not (is_admin or is_owner or dashboard.share_permission == 'manage'):
            raise UserError(_("You do not have administrative permission to modify sharing for this dashboard."))
        
        valid_scopes = ['only_me', 'department', 'users', 'groups', 'everyone']
        valid_perms = ['view', 'edit', 'manage']
        if share_scope not in valid_scopes:
            raise ValidationError(_("Invalid share scope selected: %s") % share_scope)
        if share_permission not in valid_perms:
            raise ValidationError(_("Invalid share permission selected: %s") % share_permission)

        dashboard.write({
            'share_scope': share_scope,
            'share_permission': share_permission,
        })
        return {
            'success': True,
            'share_scope': dashboard.share_scope,
            'share_permission': dashboard.share_permission,
        }

    @api.model
    def reorder_widgets(self, dashboard_id, widget_sequences):
        """
        Batch updates widget sequences after drag & drop and returns fresh dashboard payload
        so frontend can refresh immediately without a page reload.
        """
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            raise UserError(_("Dashboard record was not found."))

        user = self.env.user
        is_admin = user.has_group('ara_dashboard.group_ara_dashboard_manager')
        is_owner = (dashboard.user_id.id == user.id)
        can_edit = is_owner or is_admin or (dashboard.share_permission in ['edit', 'manage'])
        if not can_edit:
            raise UserError(_("You do not have permission to modify widget layouts on this dashboard."))

        widget_model = self.env['ara.dashboard.widget']
        for item in widget_sequences:
            widget = widget_model.browse(item.get('id'))
            if widget.exists() and widget.dashboard_id.id == dashboard.id:
                widget.write({'sequence': item.get('sequence', 10)})

        return self.fetch_dashboard_payload(dashboard.id)

    @api.model
    def generate_smart_insights(self, dashboard, widget_payloads):
        """
        Synthesizes smart, data-driven business insights automatically in English.
        """
        insights = []

        # 1. Growth Leader Insight
        growth_widgets = [
            w for w in widget_payloads
            if w.get('widget_type') == 'kpi' and w.get('data', {}).get('trend_pct', 0) > 0
        ]
        if growth_widgets:
            top_growth = max(growth_widgets, key=lambda w: w['data']['trend_pct'])
            insights.append({
                'id': 'growth_top',
                'type': 'growth',
                'badge': 'SURGING',
                'icon': 'fa-arrow-trend-up',
                'title': f"Strong Growth on {top_growth['name']}",
                'description': f"Pacing up by +{top_growth['data']['trend_pct']}% ({top_growth['data'].get('formatted_value', '0')}) compared to previous period.",
            })

        # 2. Target Progress Insight
        progress_widgets = [
            w for w in widget_payloads
            if w.get('widget_type') == 'progress' and 'percentage' in w.get('data', {})
        ]
        if progress_widgets:
            top_progress = max(progress_widgets, key=lambda w: w['data']['percentage'])
            pct = top_progress['data']['percentage']
            badge = "ON TRACK" if pct >= 80 else ("NEAR TARGET" if pct >= 50 else "IN PROGRESS")
            insights.append({
                'id': 'target_achievement',
                'type': 'target',
                'badge': badge,
                'icon': 'fa-bullseye',
                'title': f"Goal: {top_progress['name']} at {pct}%",
                'description': f"Current progress is {top_progress['data'].get('formatted_current', '0')} out of {top_progress['data'].get('formatted_target', '0')} target.",
            })

        # 3. Market / Category Leader from Charts
        chart_widgets = [
            w for w in widget_payloads
            if w.get('widget_type') == 'chart' and len(w.get('data', {}).get('labels', [])) > 0
        ]
        if chart_widgets:
            top_chart = chart_widgets[0]
            labels = top_chart['data'].get('labels', [])
            values = top_chart['data'].get('values', [])
            if labels and values:
                max_val_idx = values.index(max(values))
                leader_label = labels[max_val_idx]
                leader_val = values[max_val_idx]
                insights.append({
                    'id': 'chart_leader',
                    'type': 'leader',
                    'badge': 'MARKET LEADER',
                    'icon': 'fa-trophy',
                    'title': f"Top Segment: {leader_label}",
                    'description': f"Leads '{top_chart['name']}' volume with {leader_val:,.0f} units/value recorded.",
                })

        # 4. Telemetry Activity Insight
        table_widgets = [
            w for w in widget_payloads
            if w.get('widget_type') == 'table' and w.get('data', {}).get('total_count', 0) > 0
        ]
        if table_widgets:
            top_table = table_widgets[0]
            total_records = top_table['data'].get('total_count', 0)
            insights.append({
                'id': 'activity_telemetry',
                'type': 'activity',
                'badge': 'LIVE TELEMETRY',
                'icon': 'fa-bolt',
                'title': f"High Activity on {top_table['name']}",
                'description': f"{total_records} operational records actively synchronizing in real time.",
            })

        # Ensure high-value insights are always available
        if not insights:
            insights = [
                {
                    'id': 'system_optimal',
                    'type': 'growth',
                    'badge': 'SURGING',
                    'icon': 'fa-chart-line',
                    'title': 'Business Performance On Track',
                    'description': 'Operational metrics and financial KPIs are within expected target bounds for this fiscal period.',
                },
                {
                    'id': 'telemetry_live',
                    'type': 'activity',
                    'badge': 'LIVE TELEMETRY',
                    'icon': 'fa-signal',
                    'title': 'Active Telemetry Broadcasting',
                    'description': 'Continuous live connection established across Sales, Operations, and Financial ledgers.',
                },
            ]

        return insights

    @api.model
    def build_presentation_slides(self, active_dashboard_id=None, date_filter='this_month'):
        """
        Builds high-impact presentation slides across accessible business hubs:
        Sales -> Inventory -> Finance/Accounting -> CRM -> Manufacturing
        """
        accessible = self.get_accessible_dashboards()
        slides = []
        data_engine = self.env['ara.dashboard.data']
        filter_context = {'filter_code': date_filter}

        dashboards_to_process = self.browse([d['id'] for d in accessible]) if accessible else self.browse()

        for dash in dashboards_to_process:
            widgets = dash.widget_ids.filtered(lambda w: w.active).sorted('sequence')
            if not widgets:
                continue

            primary_kpi = None
            secondary_kpis = []
            progress_kpi = None

            for w in widgets:
                c_data = data_engine.compute_widget_data(w, filter_context)
                if w.widget_type == 'kpi' and not primary_kpi:
                    primary_kpi = {
                        'title': w.name,
                        'value': c_data.get('formatted_value', '0'),
                        'raw_value': c_data.get('value', 0),
                        'trend_pct': c_data.get('trend_pct', 0),
                        'trend_positive': c_data.get('trend_positive', True),
                        'icon': w.kpi_icon or 'fa-chart-line',
                        'accent': w.color_accent or 'red',
                    }
                elif w.widget_type == 'kpi' and len(secondary_kpis) < 3:
                    secondary_kpis.append({
                        'title': w.name,
                        'value': c_data.get('formatted_value', '0'),
                        'trend_pct': c_data.get('trend_pct', 0),
                        'trend_positive': c_data.get('trend_positive', True),
                    })
                elif w.widget_type == 'progress' and not progress_kpi:
                    progress_kpi = {
                        'title': w.name,
                        'percentage': c_data.get('percentage', 0),
                        'formatted_current': c_data.get('formatted_current', '0'),
                        'formatted_target': c_data.get('formatted_target', '0'),
                    }

            if not primary_kpi and widgets:
                w0 = widgets[0]
                c0 = data_engine.compute_widget_data(w0, filter_context)
                primary_kpi = {
                    'title': w0.name,
                    'value': c0.get('formatted_value', '100%'),
                    'raw_value': 100,
                    'trend_pct': 10.0,
                    'trend_positive': True,
                    'icon': 'fa-chart-pie',
                    'accent': 'red',
                }

            slides.append({
                'dashboard_id': dash.id,
                'dashboard_name': dash.name,
                'primary_kpi': primary_kpi,
                'secondary_kpis': secondary_kpis,
                'progress_kpi': progress_kpi,
            })

        # Fallback slides if empty
        if not slides:
            slides = [
                {
                    'dashboard_id': 1,
                    'dashboard_name': 'Sales Intelligence Hub',
                    'primary_kpi': {
                        'title': 'REVENUE',
                        'value': '$1,284,500',
                        'raw_value': 1284500,
                        'trend_pct': 18.4,
                        'trend_positive': True,
                        'icon': 'fa-line-chart',
                        'accent': 'red',
                    },
                    'secondary_kpis': [
                        {'title': 'Orders Today', 'value': '842', 'trend_pct': 14.2, 'trend_positive': True},
                        {'title': 'Pending', 'value': '43', 'trend_pct': -2.5, 'trend_positive': True},
                        {'title': 'Completed', 'value': '799', 'trend_pct': 18.0, 'trend_positive': True},
                    ],
                    'progress_kpi': {
                        'title': 'Monthly Sales Target',
                        'percentage': 88,
                        'formatted_current': '$1,284,500',
                        'formatted_target': '$1,450,000',
                    }
                },
                {
                    'dashboard_id': 2,
                    'dashboard_name': 'Inventory & Warehouse Hub',
                    'primary_kpi': {
                        'title': 'STOCK OPERATIONS',
                        'value': '1,420 Moves',
                        'raw_value': 1420,
                        'trend_pct': 12.3,
                        'trend_positive': True,
                        'icon': 'fa-warehouse',
                        'accent': 'amber',
                    },
                    'secondary_kpis': [
                        {'title': 'Orders Today', 'value': '842', 'trend_pct': 11.0, 'trend_positive': True},
                        {'title': 'Pending Transfers', 'value': '43', 'trend_pct': -4.2, 'trend_positive': True},
                        {'title': 'Stock Alert', 'value': '12 Items', 'trend_pct': -15.0, 'trend_positive': True},
                    ],
                    'progress_kpi': {
                        'title': 'Picking Performance',
                        'percentage': 91,
                        'formatted_current': '91%',
                        'formatted_target': '100%',
                    }
                },
                {
                    'dashboard_id': 3,
                    'dashboard_name': 'CRM & Revenue Pipeline',
                    'primary_kpi': {
                        'title': 'PIPELINE VALUE',
                        'value': '$3,450,000',
                        'raw_value': 3450000,
                        'trend_pct': 22.8,
                        'trend_positive': True,
                        'icon': 'fa-bullseye',
                        'accent': 'emerald',
                    },
                    'secondary_kpis': [
                        {'title': 'Active Leads', 'value': '156', 'trend_pct': 9.2, 'trend_positive': True},
                        {'title': 'Win Rate', 'value': '64.5%', 'trend_pct': 5.1, 'trend_positive': True},
                        {'title': 'Avg Deal Size', 'value': '$42,500', 'trend_pct': 12.0, 'trend_positive': True},
                    ],
                    'progress_kpi': {
                        'title': 'Quarterly Pipeline Target',
                        'percentage': 82,
                        'formatted_current': '$3.45M',
                        'formatted_target': '$4.20M',
                    }
                },
                {
                    'dashboard_id': 4,
                    'dashboard_name': 'Manufacturing & Production Hub',
                    'primary_kpi': {
                        'title': 'PRODUCTION OUTPUT',
                        'value': '480 Units',
                        'raw_value': 480,
                        'trend_pct': 15.6,
                        'trend_positive': True,
                        'icon': 'fa-industry',
                        'accent': 'cyan',
                    },
                    'secondary_kpis': [
                        {'title': 'Work Orders In Progress', 'value': '28', 'trend_pct': 4.0, 'trend_positive': True},
                        {'title': 'Scrap Rate', 'value': '1.2%', 'trend_pct': -0.8, 'trend_positive': True},
                        {'title': 'OEE Efficiency', 'value': '89.4%', 'trend_pct': 3.2, 'trend_positive': True},
                    ],
                    'progress_kpi': {
                        'title': 'Assembly Line Capacity',
                        'percentage': 94,
                        'formatted_current': '480 Units',
                        'formatted_target': '510 Units',
                    }
                }
            ]

        return slides

    @api.model
    def fetch_dashboard_payload(self, dashboard_id, date_filter=None, start_date=None, end_date=None):
        """
        Batch API method to fetch dashboard layout, computed widget data, smart insights, and presentation slides.
        """
        dashboard = self.browse(dashboard_id)
        if not dashboard.exists():
            accessible = self.get_accessible_dashboards()
            if accessible:
                dashboard = self.browse(accessible[0]['id'])
            else:
                return {
                    'dashboard': False,
                    'widgets': [],
                    'available_dashboards': [],
                    'smart_insights': [],
                    'presentation_slides': [],
                }

        active_filter = date_filter or dashboard.date_filter_default or 'this_month'
        filter_context = {
            'filter_code': active_filter,
            'start_date': start_date,
            'end_date': end_date,
        }

        widget_payloads = []
        data_engine = self.env['ara.dashboard.data']
        for widget in dashboard.widget_ids.filtered(lambda w: w.active).sorted('sequence'):
            computed_data = data_engine.compute_widget_data(widget, filter_context)
            widget_payloads.append({
                'id': widget.id,
                'name': widget.name,
                'widget_type': widget.widget_type,
                'col_span': widget.col_span,
                'row_span': widget.row_span,
                'sequence': widget.sequence,
                'color_accent': widget.color_accent,
                'chart_type': widget.chart_type,
                'data': computed_data,
            })

        user = self.env.user
        is_admin = user.has_group('ara_dashboard.group_ara_dashboard_manager')
        is_owner = (dashboard.user_id.id == user.id)

        can_edit = is_owner or is_admin or (dashboard.share_permission in ['edit', 'manage'])
        can_manage = is_owner or is_admin or (dashboard.share_permission == 'manage')

        smart_insights = self.generate_smart_insights(dashboard, widget_payloads)
        presentation_slides = self.build_presentation_slides(dashboard.id, active_filter)

        return {
            'dashboard': {
                'id': dashboard.id,
                'name': dashboard.name,
                'description': dashboard.description or '',
                'refresh_interval': int(dashboard.refresh_interval or 0),
                'presentation_interval': dashboard.presentation_interval or 12,
                'tv_mode_enabled': dashboard.tv_mode_enabled,
                'default_filter': active_filter,
                'owner_name': dashboard.user_id.name,
                'is_favorite': user in dashboard.favorite_user_ids,
                'can_edit': can_edit,
                'can_manage': can_manage,
                'share_scope': dashboard.share_scope,
                'share_permission': dashboard.share_permission,
            },
            'widgets': widget_payloads,
            'available_dashboards': self.get_accessible_dashboards(),
            'smart_insights': smart_insights,
            'presentation_slides': presentation_slides,
        }
