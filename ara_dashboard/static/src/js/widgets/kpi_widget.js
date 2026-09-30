/** @odoo-module **/
import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class KPIWidget extends Component {
    static template = "ara_dashboard.KPIWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get data() {
        return this.props.widget.data || {};
    }

    get trendClass() {
        const dir = this.data.trend_direction || "neutral";
        return `trend-${dir}`;
    }

    get trendIcon() {
        const dir = this.data.trend_direction;
        if (dir === "up") return "fa-arrow-up";
        if (dir === "down") return "fa-arrow-down";
        return "fa-minus";
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

araWidgetRegistry.add("kpi", {
    component: KPIWidget,
    label: "KPI Metric Card",
});
araWidgetRegistry.add("tiles", {
    component: KPIWidget,
    label: "Tiles",
});
