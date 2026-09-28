import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class TableWidget extends Component {
    static template = "ara_dashboard.TableWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get data() {
        return this.props.widget.data || { columns: [], rows: [] };
    }

    get isTableEmpty() {
        return !this.data.rows || this.data.rows.length === 0;
    }

    onRowClick(row) {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget, row.id);
        }
    }
}

araWidgetRegistry.add("table", {
    component: TableWidget,
    label: "Data Table / List",
});
araWidgetRegistry.add("list", {
    component: TableWidget,
    label: "List View",
});
