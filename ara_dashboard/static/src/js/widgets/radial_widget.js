/** @odoo-module **/
import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class RadialWidget extends Component {
    static template = "ara_dashboard.RadialWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get data() {
        return this.props.widget.data || {};
    }

    get percentage() {
        const pct = this.data.percentage || 0;
        return Math.min(100, Math.max(0, pct));
    }

    get strokeDashoffset() {
        // Circumference of radius 50 is 2 * PI * 50 = 314.159
        const circumference = 314.16;
        return circumference - (this.percentage / 100) * circumference;
    }

    get gradientColors() {
        const themeGradients = {
            purple: ["#8B5CF6", "#6366F1"],
            emerald: ["#10B981", "#059669"],
            cyan: ["#06B6D4", "#0284C7"],
            amber: ["#F59E0B", "#D97706"],
            blue: ["#3B82F6", "#1D4ED8"],
            red: ["#FB7185", "#E11D48"],
        };
        const key = this.props.widget.color_accent || "purple";
        return themeGradients[key] || themeGradients.purple;
    }

    get gradientId() {
        return `radial-grad-${this.props.widget.id || "gauge"}`;
    }

    get accentColor() {
        return this.gradientColors[0];
    }

    onClick() {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }
}

araWidgetRegistry.add("radial", {
    component: RadialWidget,
    label: "Radial Chart",
});
