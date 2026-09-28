# -*- coding: utf-8 -*-
import ast
import json
import pytz
from datetime import datetime, time, timedelta, date
from dateutil.relativedelta import relativedelta

from odoo import models, api, fields, _
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class AraDashboardDataEngine(models.AbstractModel):
    _name = 'ara.dashboard.data'
    _description = 'Ara Dashboard Data Aggregation Engine'

    @api.model
    def resolve_date_filter(self, filter_code, start_date_str=None, end_date_str=None):
        """
        Calculates UTC start and end datetimes for current and comparison periods.
        Returns: {
            'current': (start_dt, end_dt),
            'previous': (prev_start_dt, prev_end_dt),
            'label': str
        }
        """
        user_tz_name = self.env.user.tz or 'UTC'
        try:
            tz = pytz.timezone(user_tz_name)
        except Exception:
            tz = pytz.UTC

        now_local = datetime.now(tz)
        today = now_local.date()

        if filter_code == 'today':
            start = datetime.combine(today, time.min)
            end = datetime.combine(today, time.max)
            prev_start = start - timedelta(days=1)
            prev_end = end - timedelta(days=1)
            label = "vs Yesterday"

        elif filter_code == 'this_week':
            start_week = today - timedelta(days=today.weekday())
            start = datetime.combine(start_week, time.min)
            end = datetime.combine(start_week + timedelta(days=6), time.max)
            prev_start = start - timedelta(days=7)
            prev_end = end - timedelta(days=7)
            label = "vs Last Week"

        elif filter_code == 'this_month':
            start_month = today.replace(day=1)
            # Last day of current month
            next_month = start_month + relativedelta(months=1)
            end_month = next_month - timedelta(days=1)
            start = datetime.combine(start_month, time.min)
            end = datetime.combine(end_month, time.max)
            prev_start = start - relativedelta(months=1)
            prev_end = end - relativedelta(months=1)
            label = "vs Last Month"

        elif filter_code == 'this_quarter':
            quarter = (today.month - 1) // 3 + 1
            first_month_of_q = 3 * quarter - 2
            start_q = today.replace(month=first_month_of_q, day=1)
            next_q = start_q + relativedelta(months=3)
            end_q = next_q - timedelta(days=1)
            start = datetime.combine(start_q, time.min)
            end = datetime.combine(end_q, time.max)
            prev_start = start - relativedelta(months=3)
            prev_end = end - relativedelta(months=3)
            label = "vs Last Quarter"

        elif filter_code == 'this_year':
            start_year = today.replace(month=1, day=1)
            end_year = today.replace(month=12, day=31)
            start = datetime.combine(start_year, time.min)
            end = datetime.combine(end_year, time.max)
            prev_start = start - relativedelta(years=1)
            prev_end = end - relativedelta(years=1)
            label = "vs Last Year"

        elif filter_code == 'last_year':
            last_y = today.year - 1
            start_year = date(last_y, 1, 1)
            end_year = date(last_y, 12, 31)
            start = datetime.combine(start_year, time.min)
            end = datetime.combine(end_year, time.max)
            prev_start = datetime.combine(date(last_y - 1, 1, 1), time.min)
            prev_end = datetime.combine(date(last_y - 1, 12, 31), time.max)
            label = f"vs {last_y - 1}"

        elif filter_code and (str(filter_code).startswith('year_') or (isinstance(filter_code, str) and filter_code.isdigit() and len(filter_code) == 4)):
            try:
                raw_year = str(filter_code).replace('year_', '')
                target_year = int(raw_year)
                start_year = date(target_year, 1, 1)
                end_year = date(target_year, 12, 31)
                start = datetime.combine(start_year, time.min)
                end = datetime.combine(end_year, time.max)
                prev_start = datetime.combine(date(target_year - 1, 1, 1), time.min)
                prev_end = datetime.combine(date(target_year - 1, 12, 31), time.max)
                label = f"vs {target_year - 1}"
            except Exception:
                return {'current': (None, None), 'previous': (None, None), 'label': ''}

        elif filter_code == 'last_30_days':
            end = datetime.combine(today, time.max)
            start = datetime.combine(today - timedelta(days=29), time.min)
            prev_end = start - timedelta(seconds=1)
            prev_start = prev_end - timedelta(days=29)
            label = "vs Prior 30 Days"

        elif filter_code == 'custom' and start_date_str and end_date_str:
            try:
                s_date = fields.Date.from_string(start_date_str)
                e_date = fields.Date.from_string(end_date_str)
                start = datetime.combine(s_date, time.min)
                end = datetime.combine(e_date, time.max)
                delta = end - start
                prev_end = start - timedelta(seconds=1)
                prev_start = prev_end - delta
                label = "vs Prior Period"
            except Exception:
                return {'current': (None, None), 'previous': (None, None), 'label': ''}
        else:
            # All time or fallback
            return {'current': (None, None), 'previous': (None, None), 'label': ''}

        # Convert timezone-aware datetimes to UTC naive for Odoo DB queries
        def to_utc_naive(dt):
            if dt is None:
                return None
            localized = tz.localize(dt) if dt.tzinfo is None else dt
            utc_dt = localized.astimezone(pytz.UTC)
            return utc_dt.replace(tzinfo=None)

        return {
            'current': (to_utc_naive(start), to_utc_naive(end)),
            'previous': (to_utc_naive(prev_start), to_utc_naive(prev_end)),
            'label': label
        }

    @api.model
    def safe_parse_domain(self, domain_str):
        """Safely parses domain string into Python list without using dangerous eval."""
        if not domain_str or not domain_str.strip():
            return []
        try:
            parsed = ast.literal_eval(domain_str.strip())
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        return []

    @api.model
    def compute_widget_data(self, widget, filter_context):
        """
        Dispatches calculation according to widget type with full error isolation.
        """
        if not widget.model_id:
            return {'error': _('Model not specified')}

        model_name = widget.model_id.model
        if model_name not in self.env:
            return {'error': _('Model "%s" is not installed') % model_name}

        try:
            wtype = widget.widget_type
            if wtype in ['tiles', 'kpi']:
                return self._compute_kpi(widget, filter_context)
            elif wtype in ['table', 'list']:
                return self._compute_table(widget, filter_context)
            elif wtype in ['radial', 'progress']:
                return self._compute_radial(widget, filter_context)
            elif wtype == 'bullet':
                return self._compute_bullet(widget, filter_context)
            elif wtype == 'funnel':
                return self._compute_funnel(widget, filter_context)
            elif wtype == 'flower':
                return self._compute_flower(widget, filter_context)
            elif wtype == 'scatter':
                return self._compute_scatter(widget, filter_context)
            elif wtype == 'todo':
                return self._compute_todo(widget, filter_context)
            elif wtype in ['chart', 'bar', 'horizontal_bar', 'line', 'pie', 'doughnut', 'polar_area', 'radar']:
                return self._compute_chart(widget, filter_context)
            else:
                return {'error': _('Unknown widget type: %s') % widget.widget_type}
        except Exception as e:
            return {'error': str(e)}

    @api.model
    def _build_domain(self, widget, start_dt, end_dt):
        domain = self.safe_parse_domain(widget.domain)
        if widget.date_field_id and start_dt and end_dt:
            date_col = widget.date_field_id.name
            domain += [
                (date_col, '>=', start_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                (date_col, '<=', end_dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
            ]
        return domain

    @api.model
    def _compute_kpi(self, widget, filter_context):
        model = self.env[widget.model_id.model]
        dates = self.resolve_date_filter(
            filter_context.get('filter_code'),
            filter_context.get('start_date'),
            filter_context.get('end_date')
        )

        curr_start, curr_end = dates['current']
        prev_start, prev_end = dates['previous']

        curr_domain = self._build_domain(widget, curr_start, curr_end)
        prev_domain = self._build_domain(widget, prev_start, prev_end)

        measure = widget.measure_field_id.name if widget.measure_field_id else None
        agg = widget.aggregation_type or 'count'

        current_val = self._aggregate_value(model, curr_domain, measure, agg)
        previous_val = self._aggregate_value(model, prev_domain, measure, agg) if prev_start else None

        trend_pct = 0.0
        trend_direction = 'neutral'
        if previous_val is not None and previous_val > 0:
            diff = current_val - previous_val
            trend_pct = round((diff / previous_val) * 100.0, 1)
            trend_direction = 'up' if trend_pct > 0 else ('down' if trend_pct < 0 else 'neutral')
        elif previous_val == 0 and current_val > 0:
            trend_pct = 100.0
            trend_direction = 'up'

        # Determine currency formatting if applicable
        currency_symbol = ""
        if widget.measure_field_id and widget.measure_field_id.ttype == 'monetary':
            currency = self.env.company.currency_id
            currency_symbol = currency.symbol or "$"

        return {
            'value': current_val,
            'formatted_value': self._format_number(current_val, currency_symbol),
            'previous_value': previous_val,
            'trend_pct': trend_pct,
            'trend_direction': trend_direction,
            'comparison_label': dates['label'] if widget.trend_comparison != 'none' else '',
            'icon': widget.kpi_icon or 'fa-chart-line',
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': curr_domain,
            'model': widget.model_id.model,
        }

    @api.model
    def _compute_chart(self, widget, filter_context):
        model = self.env[widget.model_id.model]
        dates = self.resolve_date_filter(
            filter_context.get('filter_code'),
            filter_context.get('start_date'),
            filter_context.get('end_date')
        )
        curr_start, curr_end = dates['current']
        domain = self._build_domain(widget, curr_start, curr_end)

        # 1. Determine groupby column safely
        if widget.groupby_field_id:
            if widget.groupby_field_id.ttype in ['date', 'datetime']:
                groupby_col = f"{widget.groupby_field_id.name}:month"
            else:
                groupby_col = widget.groupby_field_id.name
        else:
            # Auto-detect best field on model if not configured
            if widget.widget_type == 'funnel':
                preferred = ['stage_id', 'state', 'type', 'category_id', 'user_id', 'partner_id']
            else:
                preferred = ['partner_id', 'stage_id', 'user_id', 'state', 'country_id', 'type', 'category_id']
            found = None
            for p in preferred:
                if p in model._fields:
                    found = p
                    break
            if not found:
                for df in ['date_order', 'invoice_date', 'date', 'create_date']:
                    if df in model._fields:
                        found = f"{df}:month"
                        break
            groupby_col = found or 'create_date:month'

        # 2. Determine measure column safely (must be a stored numeric field)
        measure_col = None
        if widget.measure_field_id and widget.measure_field_id.name in model._fields:
            m_field = model._fields[widget.measure_field_id.name]
            if getattr(m_field, 'store', False):
                measure_col = widget.measure_field_id.name
        agg = widget.aggregation_type or 'sum'

        # 3. Only pass aggregation fields to read_group (NEVER put groupby_col in fields!)
        fields_to_read = []
        if measure_col:
            fields_to_read.append(f"{measure_col}:{agg}")

        # 4. Execute read_group with resilient fallback
        try:
            order_col = measure_col or '__count'
            order_dir = 'desc' if widget.sort_order == 'desc' else 'asc'
            groups = model.read_group(
                domain=domain,
                fields=fields_to_read,
                groupby=[groupby_col],
                limit=widget.limit or 10,
                orderby=f"{order_col} {order_dir}"
            )
        except Exception:
            try:
                groups = model.read_group(
                    domain=domain,
                    fields=[],
                    groupby=[groupby_col],
                    limit=widget.limit or 10,
                )
            except Exception:
                # Ultimate fallback
                fallback_grp = 'id' if 'id' in model._fields else []
                groups = model.read_group(
                    domain=domain,
                    fields=[],
                    groupby=[fallback_grp] if fallback_grp else [],
                    limit=widget.limit or 10,
                )

        labels = []
        data_values = []
        for g in groups:
            # Format label
            raw_label = g.get(groupby_col)
            if raw_label is None:
                raw_label = g.get(groupby_col.split(':')[0])

            if isinstance(raw_label, (list, tuple)):
                label_str = str(raw_label[1]) if len(raw_label) > 1 else str(raw_label[0])
            elif raw_label:
                label_str = str(raw_label)
            else:
                label_str = _("Undefined")

            # Extract metric value
            val = 0.0
            if measure_col:
                if measure_col in g and g[measure_col] is not None:
                    val = g[measure_col]
                elif f"{measure_col}:{agg}" in g and g[f"{measure_col}:{agg}"] is not None:
                    val = g[f"{measure_col}:{agg}"]
            if not val:
                val = g.get('__count') or g.get(f"{groupby_col.split(':')[0]}_count") or 0.0

            labels.append(label_str)
            data_values.append(round(val, 2) if isinstance(val, float) else val)

        resolved_chart_type = (
            widget.widget_type
            if widget.widget_type in ['bar', 'horizontal_bar', 'line', 'pie', 'doughnut', 'polar_area', 'radar']
            else (widget.chart_type or 'bar')
        )

        return {
            'labels': labels,
            'values': data_values,
            'chart_type': resolved_chart_type,
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': domain,
            'model': widget.model_id.model,
        }

    @api.model
    def _compute_radial(self, widget, filter_context):
        res = self._compute_progress(widget, filter_context)
        res['widget_type'] = 'radial'
        target = res.get('target_value', 100.0) or 100.0
        current = res.get('current_value', 0.0) or 0.0
        pct = round((current / target) * 100.0, 1) if target > 0 else 0.0
        res['percentage'] = pct
        res['min_value'] = 0.0
        res['max_value'] = max(target, current)
        return res

    @api.model
    def _compute_bullet(self, widget, filter_context):
        res = self._compute_progress(widget, filter_context)
        res['widget_type'] = 'bullet'
        target = res.get('target_value', 100.0) or 100.0
        current = res.get('current_value', 0.0) or 0.0
        pct = round((current / target) * 100.0, 1) if target > 0 else 0.0
        res['percentage'] = pct
        res['bands'] = {
            'poor': round(target * 0.5, 2),
            'satisfactory': round(target * 0.8, 2),
            'good': round(target * 1.2, 2),
        }
        return res

    @api.model
    def _compute_funnel(self, widget, filter_context):
        chart_res = self._compute_chart(widget, filter_context)
        labels = chart_res.get('labels', [])
        values = chart_res.get('values', [])

        # Determine currency formatting if applicable
        currency_symbol = ""
        if widget.measure_field_id and widget.measure_field_id.ttype == 'monetary':
            currency = self.env.company.currency_id
            currency_symbol = currency.symbol or "$"

        stages = []
        max_val = max(values) if values and max(values) > 0 else 1.0
        first_val = values[0] if values and values[0] > 0 else max_val

        for i, (lbl, val) in enumerate(zip(labels, values)):
            pct_of_first = round((val / first_val) * 100.0, 1) if first_val else 0.0
            prev_val = values[i - 1] if i > 0 and values[i - 1] > 0 else val
            drop_off = round(((val - prev_val) / prev_val) * 100.0, 1) if (i > 0 and prev_val) else 0.0
            stages.append({
                'name': lbl,
                'value': val,
                'formatted_value': self._format_number(val, currency_symbol),
                'percentage': min(100.0, max(5.0, round((val / max_val) * 100.0, 1))),
                'conversion_pct': pct_of_first,
                'drop_off': drop_off,
            })

        return {
            'stages': stages,
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': chart_res.get('drilldown_domain', []),
            'model': widget.model_id.model,
            'total_stages': len(stages),
        }

    @api.model
    def _compute_flower(self, widget, filter_context):
        chart_res = self._compute_chart(widget, filter_context)
        labels = chart_res.get('labels', [])
        values = chart_res.get('values', [])

        max_val = max(values) if values and max(values) > 0 else 1.0
        total_count = len(labels)
        petals = []
        for i, (lbl, val) in enumerate(zip(labels, values)):
            normalized = max(0.25, min(1.0, (val / max_val) if max_val else 0.5))
            angle = (360.0 / total_count * i) if total_count > 0 else 0
            petals.append({
                'index': i,
                'label': lbl,
                'value': val,
                'formatted_value': self._format_number(val),
                'normalized': round(normalized, 3),
                'angle': round(angle, 1),
                'percentage': round((val / max_val * 100.0) if max_val else 0.0, 1),
            })

        return {
            'petals': petals,
            'labels': labels,
            'values': values,
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': chart_res.get('drilldown_domain', []),
            'model': widget.model_id.model,
        }

    @api.model
    def _compute_scatter(self, widget, filter_context):
        model = self.env[widget.model_id.model]
        dates = self.resolve_date_filter(
            filter_context.get('filter_code'),
            filter_context.get('start_date'),
            filter_context.get('end_date')
        )
        curr_start, curr_end = dates['current']
        domain = self._build_domain(widget, curr_start, curr_end)

        x_field = widget.scatter_x_field_id.name if widget.scatter_x_field_id else None
        y_field = widget.measure_field_id.name if widget.measure_field_id else None

        if not y_field:
            num_fields = [f.name for f in widget.model_id.field_id if f.ttype in ['integer', 'float', 'monetary'] and f.name != 'id']
            y_field = num_fields[0] if num_fields else 'id'
        if not x_field:
            num_fields = [f.name for f in widget.model_id.field_id if f.ttype in ['integer', 'float', 'monetary'] and f.name not in ['id', y_field]]
            x_field = num_fields[0] if num_fields else 'id'

        fields_to_read = list(set(['display_name', x_field, y_field, 'id']))
        records = model.search_read(
            domain=domain,
            fields=fields_to_read,
            limit=widget.limit or 25,
            order='id desc'
        )

        points = []
        for r in records:
            x_val = r.get(x_field) or 0.0
            y_val = r.get(y_field) or 0.0
            points.append({
                'x': round(float(x_val), 2),
                'y': round(float(y_val), 2),
                'label': r.get('display_name') or f"Record #{r.get('id')}",
                'id': r.get('id'),
            })

        x_label = widget.scatter_x_field_id.field_description if widget.scatter_x_field_id else x_field.replace('_', ' ').title()
        y_label = widget.measure_field_id.field_description if widget.measure_field_id else y_field.replace('_', ' ').title()

        return {
            'points': points,
            'x_label': x_label,
            'y_label': y_label,
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': domain,
            'model': widget.model_id.model,
        }

    @api.model
    def _compute_todo(self, widget, filter_context):
        model_name = widget.model_id.model
        model = self.env[model_name]
        dates = self.resolve_date_filter(
            filter_context.get('filter_code'),
            filter_context.get('start_date'),
            filter_context.get('end_date')
        )
        curr_start, curr_end = dates['current']
        domain = self._build_domain(widget, curr_start, curr_end)

        items = []
        if model_name == 'mail.activity':
            acts = model.search_read(
                domain=domain,
                fields=['summary', 'date_deadline', 'res_name', 'user_id', 'activity_type_id'],
                limit=widget.limit or 8,
                order='date_deadline asc'
            )
            for a in acts:
                items.append({
                    'id': a['id'],
                    'title': a.get('summary') or a.get('res_name') or _('Action Item'),
                    'subtitle': f"Deadline: {a.get('date_deadline') or 'None'}",
                    'done': False,
                    'badge': a.get('activity_type_id')[1] if a.get('activity_type_id') else 'Activity',
                })
        else:
            custom_tasks = []
            if widget.config_json:
                try:
                    loaded = json.loads(widget.config_json)
                    if isinstance(loaded, list):
                        custom_tasks = loaded
                    elif isinstance(loaded, dict) and 'tasks' in loaded:
                        custom_tasks = loaded['tasks']
                except Exception:
                    pass

            if custom_tasks:
                for idx, t in enumerate(custom_tasks):
                    items.append({
                        'id': t.get('id', idx + 1),
                        'title': t.get('title', f"Task #{idx + 1}"),
                        'subtitle': t.get('subtitle', ''),
                        'done': bool(t.get('done', False)),
                        'badge': t.get('badge', 'Action'),
                    })
            else:
                records = model.search_read(domain=domain, fields=['display_name', 'write_date'], limit=widget.limit or 6, order='id desc')
                for r in records:
                    items.append({
                        'id': r['id'],
                        'title': r.get('display_name') or f"Review #{r['id']}",
                        'subtitle': str(r.get('write_date') or '')[:10],
                        'done': False,
                        'badge': 'Pending',
                    })

        completed_count = sum(1 for item in items if item.get('done'))
        return {
            'items': items,
            'total_count': len(items),
            'completed_count': completed_count,
            'pending_count': len(items) - completed_count,
            'color_accent': widget.color_accent or 'red',
            'drilldown_domain': domain,
            'model': model_name,
        }

    @api.model
    def _compute_table(self, widget, filter_context):
        model = self.env[widget.model_id.model]
        dates = self.resolve_date_filter(
            filter_context.get('filter_code'),
            filter_context.get('start_date'),
            filter_context.get('end_date')
        )
        curr_start, curr_end = dates['current']
        domain = self._build_domain(widget, curr_start, curr_end)

        field_names = [f.name for f in widget.table_field_ids] if widget.table_field_ids else ['display_name']
        if 'id' not in field_names:
            field_names.append('id')

        # Read column string headers
        columns = []
        for fname in field_names:
            if fname == 'id':
                continue
            field_obj = model._fields.get(fname)
            label = field_obj.string if field_obj else fname.title()
            columns.append({'name': fname, 'label': label})

        order_clause = f"id {'desc' if widget.sort_order == 'desc' else 'asc'}"
        records = model.search_read(
            domain=domain,
            fields=field_names,
            limit=widget.limit or 10,
            order=order_clause
        )

        formatted_rows = []
        for r in records:
            row_dict = {'id': r['id'], 'cells': {}}
            for col in columns:
                val = r.get(col['name'])
                if isinstance(val, (list, tuple)):
                    formatted_val = val[1] if len(val) > 1 else str(val[0])
                elif isinstance(val, (datetime, fields.Date)):
                    formatted_val = str(val)
                elif val is False:
                    formatted_val = '-'
                else:
                    formatted_val = str(val)
                row_dict['cells'][col['name']] = formatted_val
            formatted_rows.append(row_dict)

        return {
            'columns': columns,
            'rows': formatted_rows,
            'total_count': model.search_count(domain),
            'model': widget.model_id.model,
            'drilldown_domain': domain,
        }

    @api.model
    def _compute_progress(self, widget, filter_context):
        kpi_data = self._compute_kpi(widget, filter_context)
        current_val = kpi_data.get('value', 0.0)
        target_val = widget.target_value or 100.0
        percentage = min(round((current_val / target_val) * 100.0, 1), 100.0) if target_val > 0 else 0.0

        return {
            'current_value': current_val,
            'formatted_current': kpi_data.get('formatted_value', str(current_val)),
            'target_value': target_val,
            'formatted_target': self._format_number(target_val),
            'percentage': percentage,
            'color_accent': widget.color_accent or 'red',
            'icon': widget.kpi_icon or 'fa-bullseye',
            'drilldown_domain': kpi_data.get('drilldown_domain', []),
            'model': widget.model_id.model,
        }

    @api.model
    def _aggregate_value(self, model, domain, measure_field=None, agg_type='count'):
        if not measure_field or agg_type == 'count':
            return model.search_count(domain)

        try:
            res = model.read_group(domain, [f"{measure_field}:{agg_type}"], [])
            if res and len(res) > 0:
                key = f"{measure_field}:{agg_type}"
                val = res[0].get(key) or res[0].get(measure_field) or 0.0
                return round(val, 2) if isinstance(val, float) else val
        except Exception:
            # Fallback
            records = model.search(domain)
            vals = [getattr(r, measure_field, 0.0) for r in records if getattr(r, measure_field, None)]
            if not vals:
                return 0.0
            if agg_type == 'sum':
                return round(sum(vals), 2)
            elif agg_type == 'avg':
                return round(sum(vals) / len(vals), 2)
            elif agg_type == 'max':
                return max(vals)
            elif agg_type == 'min':
                return min(vals)
        return 0.0

    @api.model
    def _format_number(self, value, currency_symbol=""):
        if value is None:
            return "0"
        if isinstance(value, float):
            formatted = f"{value:,.2f}"
        elif isinstance(value, int):
            formatted = f"{value:,}"
        else:
            formatted = str(value)

        if currency_symbol:
            return f"{currency_symbol} {formatted}"
        return formatted

    @api.model
    def get_widget_action(self, widget_id, extra_domain=None):
        """Generates standard Odoo Window Action for drilldown navigation."""
        widget = self.env['ara.dashboard.widget'].browse(widget_id)
        if not widget.exists() or not widget.model_id:
            return False

        model_name = widget.model_id.model
        domain = self.safe_parse_domain(widget.domain)
        if extra_domain:
            domain += extra_domain

        return {
            'type': 'ir.actions.act_window',
            'name': widget.name,
            'res_model': model_name,
            'view_mode': 'list,form',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
            'target': 'current',
        }
