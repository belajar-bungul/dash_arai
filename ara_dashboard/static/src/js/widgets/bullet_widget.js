/** @odoo-module **/
import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class BulletWidget extends Component {
    static template = "ara_dashboard.BulletWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get data() {
        return this.props.widget.data || {};
    }

    get percentage() {
        return Math.min(100, Math.max(0, this.data.percentage || 0));
    }

    get gradientStyle() {
        const themeGradients = {
            purple: "linear-gradient(90deg, #6366F1 0%, #8B5CF6 50%, #C084FC 100%)",
            emerald: "linear-gradient(90deg, #059669 0%, #10B981 50%, #34D399 100%)",
            cyan: "linear-gradient(90deg, #0891B2 0%, #06B6D4 50%, #67E8F9 100%)",
            amber: "linear-gradient(90deg, #D97706 0%, #F59E0B 50%, #FCD34D 100%)",
            blue: "linear-gradient(90deg, #1D4ED8 0%, #3B82F6 50%, #93C5FD 100%)",
            red: "linear-gradient(90deg, #F43F5E 0%, #FB7185 50%, #FDA4AF 100%)",
        };
        const key = this.props.widget.color_accent || "purple";
        return themeGradients[key] || themeGradients.purple;
    }

    get accentColor() {
        return "#7B68EE";
    }

    onClick() {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }
}

araWidgetRegistry.add("bullet", {
    component: BulletWidget,
    label: "Bullet Chart",
});
