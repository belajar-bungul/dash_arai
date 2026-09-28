import { Component } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class FunnelWidget extends Component {
    static template = "ara_dashboard.FunnelWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    get stages() {
        return (this.props.widget.data && this.props.widget.data.stages) || [];
    }

    get accentColor() {
        const colors = {
            red: "#FF577F",
            emerald: "#00D084",
            cyan: "#00C0F3",
            amber: "#FFA726",
            purple: "#7B68EE",
            blue: "#3E7BFA",
        };
        return colors[this.props.widget.color_accent] || "#7B68EE";
    }

    getStageColor(index, total) {
        const opacities = [1.0, 0.85, 0.70, 0.55, 0.40, 0.30];
        const opacity = opacities[index % opacities.length];
        const hex = this.accentColor;
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }

    getStageGradient(index, total) {
        const themeGradients = {
            purple: [
                ["#8B5CF6", "#6366F1"],
                ["#6366F1", "#3B82F6"],
                ["#06B6D4", "#0EA5E9"],
                ["#10B981", "#059669"],
                ["#A855F7", "#7C3AED"],
            ],
            emerald: [
                ["#10B981", "#059669"],
                ["#059669", "#047857"],
                ["#14B8A6", "#0F766E"],
                ["#06B6D4", "#0891B2"],
            ],
            cyan: [
                ["#06B6D4", "#0EA5E9"],
                ["#0EA5E9", "#3B82F6"],
                ["#3B82F6", "#6366F1"],
                ["#6366F1", "#8B5CF6"],
            ],
            amber: [
                ["#F59E0B", "#D97706"],
                ["#FB923C", "#EA580C"],
                ["#FBBF24", "#F59E0B"],
                ["#FCD34D", "#FBBF24"],
            ],
            blue: [
                ["#3B82F6", "#2563EB"],
                ["#2563EB", "#1D4ED8"],
                ["#60A5FA", "#3B82F6"],
                ["#6366F1", "#4F46E5"],
            ],
            red: [
                ["#FB7185", "#E11D48"],
                ["#F43F5E", "#BE123C"],
                ["#FB923C", "#EA580C"],
                ["#F472B6", "#DB2777"],
            ],
        };
        const key = this.props.widget.color_accent || "purple";
        const palette = themeGradients[key] || themeGradients.purple;
        const pair = palette[index % palette.length];
        return `linear-gradient(90deg, ${pair[0]} 0%, ${pair[1]} 100%)`;
    }

    getStageGlow(index) {
        if (index === 0) {
            return "0 0 10px rgba(123, 104, 238, 0.4)";
        }
        return "none";
    }

    getTopBadgeStyle() {
        const hex = this.accentColor;
        const r = parseInt(hex.slice(1, 3), 16);
        const g = parseInt(hex.slice(3, 5), 16);
        const b = parseInt(hex.slice(5, 7), 16);
        return `background: rgba(${r}, ${g}, ${b}, 0.18); color: ${hex}; border: 1px solid rgba(${r}, ${g}, ${b}, 0.35);`;
    }

    onClick() {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }
}

araWidgetRegistry.add("funnel", {
    component: FunnelWidget,
    label: "Funnel Chart",
});
