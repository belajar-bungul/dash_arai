/** @odoo-module **/
import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class ProgressWidget extends Component {
    static template = "ara_dashboard.ProgressWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get data() {
        return this.props.widget.data || {};
    }

    get accentClass() {
        return `accent-${this.props.widget.color_accent || "red"}`;
    }

    onClick() {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }
}

araWidgetRegistry.add("progress", {
    component: ProgressWidget,
    label: "Target / Progress Bar",
});
