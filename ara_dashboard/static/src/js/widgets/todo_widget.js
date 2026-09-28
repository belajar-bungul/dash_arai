import { Component, useState } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class TodoWidget extends Component {
    static template = "ara_dashboard.TodoWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    setup() {
        const rawItems = (this.props.widget.data && this.props.widget.data.items) || [];
        this.state = useState({
            items: rawItems.map((item) => ({ ...item })),
        });
    }

    get completedCount() {
        return this.state.items.filter((i) => i.done).length;
    }

    get totalCount() {
        return this.state.items.length;
    }

    get percentage() {
        if (!this.totalCount) return 0;
        return Math.round((this.completedCount / this.totalCount) * 100);
    }

    toggleItem(item, ev) {
        ev.stopPropagation();
        item.done = !item.done;
    }

    onItemClick(item) {
        if (this.props.onDrilldown && item.id) {
            this.props.onDrilldown(this.props.widget, item.id);
        }
    }
}

araWidgetRegistry.add("todo", {
    component: TodoWidget,
    label: "To-do Item",
});
