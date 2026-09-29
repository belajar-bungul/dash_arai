# -*- coding: utf-8 -*-
{
    'name': 'Ara Dashboard - Modern Executive Business Intelligence',
    'version': '19.0.1.0.0',
    'category': 'Productivity/Dashboard',
    'summary': 'Next-Gen Executive Business Intelligence Dashboard with 15+ Interactive Widgets, Dynamic Year Filter, TV Wallboard, Scheduled Reports & Odoo Discuss Notifications',
    'description': """
Ara Dashboard - Modern Executive Business Intelligence for Odoo 19
==================================================================

Transform your enterprise data into actionable, visual business intelligence with Ara Dashboard.
Featuring a world-class ClickUp-inspired porcelain pastel aesthetic designed for maximum visual comfort during prolonged work sessions, Ara Dashboard bridges executive high-level oversight with operational precision.

Key Features & Highlights:
--------------------------
* **Modern Porcelain Pastel Aesthetic:** Ergonomic, elegant design with gentle blush pink and warm butter yellow gradients that look stunning and keep eyes relaxed.
* **15+ Interactive Visualization Widgets:**
  - Executive Revenue Tiles (KPI Card with trend direction and shortcuts)
  - Target Achievement Radial Dial (Modern percentage gauge)
  - Margin Performance Bullet Chart (Threshold zones: 0%, 50%, target 80%, 100%)
  - Revenue Trajectory Line Chart (Smooth spline curve trends)
  - Sales Performance Bar Chart (Warm amber comparison)
  - Top Accounts Horizontal Bar Chart (Corporate account ranking)
  - Sales Pipeline Funnel Chart (CRM conversion stages & drop-off rate)
  - Market Segmentation Pie Chart (Industry breakdown)
  - Order Status Doughnut Chart (Transaction status distribution)
  - Territory Yield Polar Area Chart (Geographical performance distribution)
  - Operational Excellence Radar Chart (Multi-axis operational metrics)
  - Deal Size vs Win Probability Scatter Plot (Predictive closing analysis)
  - Multi-Division Flower Chart (Multi-petal divisional contribution)
  - Executive Priority Checklist (To-Do list with interactive checkboxes)
  - Top Enterprise Orders Registry (Interactive document list view)
* **Smart Filter Toolbar & Dynamic Year Capsule:**
  - Quick date pills: Today, This Week, This Month, This Quarter, All Time
  - Dynamic Fiscal Year Capsule: This Year, Last Year, historical years (2024, 2023, 2022...) with automatic Year-over-Year comparison and instant 1-click reset.
* **TV Mode (Operations Wallboard):** Full-screen telemetry view with digital live clock and telemetry beacons, ideal for office TV monitors and warehouse command centers.
* **Automated Scheduled Reports & Account Notifications:**
  - Cadence: Daily, Weekly, or Monthly delivery in Interactive HTML Email and Excel (.xlsx) formats.
  - Native Odoo User Tagging: Automatically sends Discuss inbox messages and notification bell alerts with direct access links.
* **Pre-Configured Out-of-the-Box Hubs:** Ready-to-use business hubs for Sales, CRM, Inventory/Stock, Accounting, Manufacturing (MRP), and Purchase/Procurement with 44+ metric templates.
* **Real-Time ORM & Performance First:** Sub-second server-side aggregation calculations without redundant data synchronization.
* **Native Odoo 19 OWL Architecture:** 100% OWL component structure, fully responsive on desktop, tablet, and mobile devices.
    """,
    'author': 'ARA SOFT',
    'website': 'https://www.arasoft.id',
    'license': 'OPL-1',
    'price': 69.99,
    'currency': 'USD',
    'images': [
        'static/description/banner.gif',
        # 'static/description/dashboard_main.png',
        # 'static/description/dashboard_config.png',
        # 'static/description/dashboard_widgets_list.png',
        # 'static/description/scheduled_reports.png',
    ],
    'depends': [
        'base',
        'web',
        'sale_management',
        'crm',
        'stock',
        'account',
        'mrp',
        'purchase',
        'hr',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/ara_dashboard_views.xml',
        'views/ara_dashboard_report_schedule_views.xml',
        'views/menus.xml',
        'data/default_dashboard_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ara_dashboard/static/src/scss/dashboard.scss',
            'ara_dashboard/static/src/js/widget_registry.js',
            'ara_dashboard/static/src/js/widgets/base_widget.js',
            'ara_dashboard/static/src/js/widgets/kpi_widget.js',
            'ara_dashboard/static/src/js/widgets/chart_widget.js',
            'ara_dashboard/static/src/js/widgets/table_widget.js',
            'ara_dashboard/static/src/js/widgets/progress_widget.js',
            'ara_dashboard/static/src/js/widgets/radial_widget.js',
            'ara_dashboard/static/src/js/widgets/bullet_widget.js',
            'ara_dashboard/static/src/js/widgets/funnel_widget.js',
            'ara_dashboard/static/src/js/widgets/flower_widget.js',
            'ara_dashboard/static/src/js/widgets/todo_widget.js',
            'ara_dashboard/static/src/js/dashboard.js',
            'ara_dashboard/static/src/xml/widgets/base_widget.xml',
            'ara_dashboard/static/src/xml/widgets/kpi_widget.xml',
            'ara_dashboard/static/src/xml/widgets/chart_widget.xml',
            'ara_dashboard/static/src/xml/widgets/table_widget.xml',
            'ara_dashboard/static/src/xml/widgets/progress_widget.xml',
            'ara_dashboard/static/src/xml/widgets/radial_widget.xml',
            'ara_dashboard/static/src/xml/widgets/bullet_widget.xml',
            'ara_dashboard/static/src/xml/widgets/funnel_widget.xml',
            'ara_dashboard/static/src/xml/widgets/flower_widget.xml',
            'ara_dashboard/static/src/xml/widgets/todo_widget.xml',
            'ara_dashboard/static/src/xml/dashboard.xml',
        ],
    },
    'application': True,
    'installable': True,
    'auto_install': False,
}
