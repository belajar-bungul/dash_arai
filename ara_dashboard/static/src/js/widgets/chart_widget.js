/** @odoo-module **/
import { Component, useRef, onWillStart, onWillUnmount, useEffect } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { araWidgetRegistry } from "../widget_registry";

// Modern Glassmorphic Gradients & Borders (ClickUp / Stripe / Linear Aesthetic)
const GLASS_THEMES = {
    purple: {
        gradients: [
            ["rgba(139, 92, 246, 0.92)", "rgba(99, 102, 241, 0.25)"], // Electric Violet -> Indigo
            ["rgba(99, 102, 241, 0.92)", "rgba(59, 130, 246, 0.25)"], // Royal Indigo -> Blue
            ["rgba(6, 182, 212, 0.92)", "rgba(14, 116, 144, 0.25)"],  // Cyan Horizon
            ["rgba(16, 185, 129, 0.92)", "rgba(5, 150, 105, 0.25)"],  // Mint Emerald
            ["rgba(14, 165, 233, 0.92)", "rgba(3, 105, 161, 0.25)"],  // Sky Blue
            ["rgba(168, 85, 247, 0.92)", "rgba(126, 34, 206, 0.25)"], // Lilac Purple
            ["rgba(56, 189, 248, 0.92)", "rgba(30, 64, 175, 0.25)"],  // Azure
            ["rgba(20, 184, 166, 0.92)", "rgba(15, 118, 110, 0.25)"], // Teal Lagoon
        ],
        borders: [
            "rgba(196, 181, 253, 0.95)",
            "rgba(165, 180, 252, 0.95)",
            "rgba(103, 232, 249, 0.95)",
            "rgba(110, 231, 183, 0.95)",
            "rgba(125, 211, 252, 0.95)",
            "rgba(216, 180, 254, 0.95)",
            "rgba(147, 197, 253, 0.95)",
            "rgba(94, 234, 212, 0.95)",
        ],
    },
    emerald: {
        gradients: [
            ["rgba(16, 185, 129, 0.92)", "rgba(5, 150, 105, 0.25)"],
            ["rgba(5, 150, 105, 0.92)", "rgba(6, 95, 70, 0.25)"],
            ["rgba(20, 184, 166, 0.92)", "rgba(15, 118, 110, 0.25)"],
            ["rgba(14, 165, 233, 0.92)", "rgba(3, 105, 161, 0.25)"],
            ["rgba(52, 211, 153, 0.92)", "rgba(5, 150, 105, 0.25)"],
            ["rgba(45, 212, 191, 0.92)", "rgba(13, 148, 136, 0.25)"],
        ],
        borders: [
            "rgba(110, 231, 183, 0.95)",
            "rgba(52, 211, 153, 0.95)",
            "rgba(94, 234, 212, 0.95)",
            "rgba(125, 211, 252, 0.95)",
            "rgba(167, 243, 208, 0.95)",
            "rgba(153, 246, 228, 0.95)",
        ],
    },
    cyan: {
        gradients: [
            ["rgba(6, 182, 212, 0.92)", "rgba(14, 116, 144, 0.25)"],
            ["rgba(14, 165, 233, 0.92)", "rgba(3, 105, 161, 0.25)"],
            ["rgba(59, 130, 246, 0.92)", "rgba(29, 78, 216, 0.25)"],
            ["rgba(99, 102, 241, 0.92)", "rgba(67, 56, 202, 0.25)"],
            ["rgba(34, 211, 238, 0.92)", "rgba(8, 145, 178, 0.25)"],
            ["rgba(56, 189, 248, 0.92)", "rgba(2, 132, 199, 0.25)"],
        ],
        borders: [
            "rgba(103, 232, 249, 0.95)",
            "rgba(125, 211, 252, 0.95)",
            "rgba(147, 197, 253, 0.95)",
            "rgba(165, 180, 252, 0.95)",
            "rgba(165, 243, 252, 0.95)",
            "rgba(186, 230, 253, 0.95)",
        ],
    },
    amber: {
        gradients: [
            ["rgba(245, 158, 11, 0.92)", "rgba(180, 83, 9, 0.25)"],
            ["rgba(251, 146, 60, 0.92)", "rgba(194, 65, 12, 0.25)"],
            ["rgba(234, 88, 12, 0.92)", "rgba(154, 52, 18, 0.25)"],
            ["rgba(251, 191, 36, 0.92)", "rgba(217, 119, 6, 0.25)"],
            ["rgba(252, 211, 77, 0.92)", "rgba(180, 83, 9, 0.25)"],
        ],
        borders: [
            "rgba(253, 230, 138, 0.95)",
            "rgba(254, 215, 170, 0.95)",
            "rgba(253, 186, 116, 0.95)",
            "rgba(252, 211, 77, 0.95)",
            "rgba(254, 240, 138, 0.95)",
        ],
    },
    blue: {
        gradients: [
            ["rgba(59, 130, 246, 0.92)", "rgba(29, 78, 216, 0.25)"],
            ["rgba(99, 102, 241, 0.92)", "rgba(67, 56, 202, 0.25)"],
            ["rgba(14, 165, 233, 0.92)", "rgba(3, 105, 161, 0.25)"],
            ["rgba(139, 92, 246, 0.92)", "rgba(109, 40, 217, 0.25)"],
            ["rgba(37, 99, 235, 0.92)", "rgba(30, 64, 175, 0.25)"],
        ],
        borders: [
            "rgba(147, 197, 253, 0.95)",
            "rgba(165, 180, 252, 0.95)",
            "rgba(125, 211, 252, 0.95)",
            "rgba(196, 181, 253, 0.95)",
            "rgba(191, 219, 254, 0.95)",
        ],
    },
    red: {
        // Calming Sunset Coral & Lilac Glass (never alarming or panicked red)
        gradients: [
            ["rgba(139, 92, 246, 0.92)", "rgba(99, 102, 241, 0.25)"],
            ["rgba(244, 63, 94, 0.85)", "rgba(159, 18, 57, 0.22)"],
            ["rgba(251, 113, 133, 0.85)", "rgba(190, 18, 60, 0.22)"],
            ["rgba(168, 85, 247, 0.85)", "rgba(107, 33, 168, 0.22)"],
            ["rgba(251, 146, 60, 0.85)", "rgba(194, 65, 12, 0.22)"],
            ["rgba(99, 102, 241, 0.85)", "rgba(67, 56, 202, 0.22)"],
        ],
        borders: [
            "rgba(196, 181, 253, 0.90)",
            "rgba(254, 205, 211, 0.90)",
            "rgba(253, 164, 175, 0.90)",
            "rgba(233, 213, 255, 0.90)",
            "rgba(254, 215, 170, 0.90)",
            "rgba(165, 180, 252, 0.90)",
        ],
    },
};

function createBarGlassGradient(ctx, canvas, chartArea, element, pair, isHorizontal = false) {
    if (!ctx) return pair[0];
    try {
        if (isHorizontal) {
            let xLeft = chartArea ? chartArea.left : 40;
            let xRight = chartArea ? chartArea.right : ((canvas && canvas.clientWidth) || 400) - 20;
            if (element && typeof element.x === "number" && typeof element.base === "number") {
                const bLeft = Math.min(element.x, element.base);
                const bRight = Math.max(element.x, element.base);
                if (bRight - bLeft > 4) {
                    xLeft = bLeft;
                    xRight = bRight;
                }
            }
            const grad = ctx.createLinearGradient(xLeft, 0, xRight, 0);
            grad.addColorStop(0, pair[1]);
            grad.addColorStop(0.5, pair[0]);
            grad.addColorStop(1, pair[0]);
            return grad;
        } else {
            const clientH = (canvas && (canvas.clientHeight || (canvas.parentElement && canvas.parentElement.clientHeight))) || 220;
            let yTop = chartArea ? chartArea.top : 15;
            let yBottom = chartArea ? chartArea.bottom : Math.max(clientH - 35, 120);

            if (element && typeof element.y === "number" && typeof element.base === "number") {
                const bTop = Math.min(element.y, element.base);
                const bBottom = Math.max(element.y, element.base);
                if (bBottom - bTop > 6) {
                    yTop = bTop;
                    yBottom = bBottom;
                }
            }
            const grad = ctx.createLinearGradient(0, yTop, 0, yBottom);
            grad.addColorStop(0, pair[0]);
            grad.addColorStop(0.35, pair[0]);
            grad.addColorStop(1, pair[1]);
            return grad;
        }
    } catch (e) {
        return pair[0];
    }
}


export class ChartWidget extends Component {
    static template = "ara_dashboard.ChartWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    setup() {
        this.canvasRef = useRef("chartCanvas");
        this.chartInstance = null;
        this.renderFrame = null;
        this.isMounted = true;

        onWillStart(async () => {
            await this.ensureChartJsLoaded();
        });

        onWillUnmount(() => {
            this.isMounted = false;
            if (this.renderFrame) {
                cancelAnimationFrame(this.renderFrame);
                this.renderFrame = null;
            }
            this.destroyChart();
        });

        useEffect(() => {
            this.scheduleRender();
        });
    }

    async ensureChartJsLoaded() {
        if (typeof Chart === "undefined") {
            try {
                await loadBundle("web.chartjs_lib");
            } catch (err) {
                console.warn("[AraDashboard] Failed to load web.chartjs_lib:", err);
            }
        }
    }

    get data() {
        return this.props.widget.data || { labels: [], values: [] };
    }

    get effectiveChartType() {
        const chartTypes = ["bar", "horizontal_bar", "line", "doughnut", "pie", "polar_area", "radar", "scatter"];
        const wType = this.props.widget && this.props.widget.widget_type;
        if (chartTypes.includes(wType)) {
            return wType;
        }
        const cType = this.props.widget && this.props.widget.chart_type;
        if (chartTypes.includes(cType)) {
            return cType;
        }
        return "bar";
    }

    get isChartEmpty() {
        if (this.effectiveChartType === "scatter") {
            return !this.data.points || this.data.points.length === 0;
        }
        return !this.data.labels || this.data.labels.length === 0;
    }

    getColorPalette() {
        const accent = (this.props.widget && this.props.widget.color_accent) || "purple";
        const themePalettes = {
            purple: {
                primary: "#7B68EE",
                gradientStart: "rgba(123, 104, 238, 0.7)",
                gradientEnd: "rgba(123, 104, 238, 0.05)",
                borders: ["#7B68EE", "#B721FF", "#49CCF9", "#00D084", "#FFA726", "#FF577F", "#8F55FF", "#3E7BFA"],
                backgrounds: [
                    "rgba(123, 104, 238, 0.85)",
                    "rgba(183, 33, 255, 0.85)",
                    "rgba(73, 204, 249, 0.85)",
                    "rgba(0, 208, 132, 0.85)",
                    "rgba(255, 167, 38, 0.85)",
                    "rgba(255, 87, 127, 0.85)",
                    "rgba(143, 85, 255, 0.85)",
                    "rgba(62, 123, 250, 0.85)",
                ],
            },
            red: {
                primary: "#7B68EE",
                gradientStart: "rgba(123, 104, 238, 0.7)",
                gradientEnd: "rgba(123, 104, 238, 0.05)",
                borders: ["#7B68EE", "#B721FF", "#49CCF9", "#00D084", "#FFA726", "#8F55FF", "#3E7BFA", "#FF577F"],
                backgrounds: [
                    "rgba(123, 104, 238, 0.85)",
                    "rgba(183, 33, 255, 0.85)",
                    "rgba(73, 204, 249, 0.85)",
                    "rgba(0, 208, 132, 0.85)",
                    "rgba(255, 167, 38, 0.85)",
                    "rgba(143, 85, 255, 0.85)",
                    "rgba(62, 123, 250, 0.85)",
                    "rgba(255, 87, 127, 0.85)",
                ],
            },
            emerald: {
                primary: "#00D084",
                gradientStart: "rgba(0, 208, 132, 0.7)",
                gradientEnd: "rgba(0, 208, 132, 0.05)",
                borders: ["#00D084", "#34D399", "#059669", "#6EE7B7", "#047857", "#A7F3D0", "#065F46", "#047857"],
                backgrounds: [
                    "rgba(0, 208, 132, 0.85)",
                    "rgba(52, 211, 153, 0.85)",
                    "rgba(5, 150, 105, 0.85)",
                    "rgba(110, 231, 183, 0.85)",
                    "rgba(4, 120, 87, 0.85)",
                    "rgba(167, 243, 208, 0.85)",
                    "rgba(6, 95, 70, 0.85)",
                    "rgba(4, 120, 87, 0.85)",
                ],
            },
            cyan: {
                primary: "#00C0F3",
                gradientStart: "rgba(0, 192, 243, 0.7)",
                gradientEnd: "rgba(0, 192, 243, 0.05)",
                borders: ["#00C0F3", "#22D3EE", "#0891B2", "#67E8F9", "#0E7490", "#A5F3FC", "#155E75", "#0891B2"],
                backgrounds: [
                    "rgba(0, 192, 243, 0.85)",
                    "rgba(34, 211, 238, 0.85)",
                    "rgba(8, 145, 178, 0.85)",
                    "rgba(103, 232, 249, 0.85)",
                    "rgba(14, 116, 144, 0.85)",
                    "rgba(165, 243, 252, 0.85)",
                    "rgba(21, 94, 117, 0.85)",
                    "rgba(8, 145, 178, 0.85)",
                ],
            },
            amber: {
                primary: "#FFA726",
                gradientStart: "rgba(255, 167, 38, 0.7)",
                gradientEnd: "rgba(255, 167, 38, 0.05)",
                borders: ["#FFA726", "#FBBF24", "#D97706", "#FCD34D", "#B45309", "#FDE68A", "#92400E", "#78350F"],
                backgrounds: [
                    "rgba(255, 167, 38, 0.85)",
                    "rgba(251, 191, 36, 0.85)",
                    "rgba(217, 119, 6, 0.85)",
                    "rgba(252, 211, 77, 0.85)",
                    "rgba(180, 83, 9, 0.85)",
                    "rgba(253, 230, 138, 0.85)",
                    "rgba(146, 64, 14, 0.85)",
                    "rgba(120, 53, 15, 0.85)",
                ],
            },
            blue: {
                primary: "#3E7BFA",
                gradientStart: "rgba(62, 123, 250, 0.7)",
                gradientEnd: "rgba(62, 123, 250, 0.05)",
                borders: ["#3E7BFA", "#60A5FA", "#2563EB", "#93C5FD", "#1D4ED8", "#BFDBFE", "#1E40AF", "#172554"],
                backgrounds: [
                    "rgba(62, 123, 250, 0.85)",
                    "rgba(96, 165, 250, 0.85)",
                    "rgba(37, 99, 235, 0.85)",
                    "rgba(147, 197, 253, 0.85)",
                    "rgba(29, 78, 216, 0.85)",
                    "rgba(191, 219, 254, 0.85)",
                    "rgba(30, 64, 175, 0.85)",
                    "rgba(23, 37, 84, 0.85)",
                ],
            },
        };
        return themePalettes[accent] || themePalettes.purple || themePalettes.red;
    }

    destroyChart() {
        if (this.chartInstance) {
            try {
                this.chartInstance.destroy();
            } catch (e) {
                // Ignore destruction error
            }
            this.chartInstance = null;
        }
        if (this.canvasRef && this.canvasRef.el && typeof Chart !== "undefined") {
            try {
                const existing = Chart.getChart(this.canvasRef.el);
                if (existing) {
                    existing.destroy();
                }
            } catch (e) {
                // Ignore
            }
        }
    }

    scheduleRender() {
        if (this.renderFrame) {
            cancelAnimationFrame(this.renderFrame);
        }
        this.renderFrame = requestAnimationFrame(() => {
            this.renderFrame = null;
            if (this.isMounted) {
                this.renderChart();
            }
        });
    }

    renderChart() {
        const canvas = this.canvasRef && this.canvasRef.el;
        if (!canvas || this.isChartEmpty) {
            this.destroyChart();
            return;
        }

        if (typeof Chart === "undefined") {
            this.ensureChartJsLoaded().then(() => {
                if (this.isMounted) {
                    this.scheduleRender();
                }
            });
            return;
        }

        try {
            const chartType = this.effectiveChartType;
            const palette = this.getColorPalette();

            let chartJsType = "bar";
            let datasetConfig = {};
            let optionsConfig = {
                responsive: true,
                maintainAspectRatio: false,
                resizeDelay: 50,
                animation: {
                    duration: 350,
                },
                plugins: {
                    legend: {
                        display: ["doughnut", "pie", "polar_area", "radar"].includes(chartType),
                        position: "right",
                        labels: {
                            color: "#9CA3AF",
                            font: { size: 11, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto" },
                            boxWidth: 12,
                            padding: 10,
                        },
                    },
                    tooltip: {
                        backgroundColor: "rgba(255, 255, 255, 0.96)",
                        titleColor: "#0F172A",
                        bodyColor: "#334155",
                        borderColor: "rgba(244, 114, 182, 0.35)",
                        borderWidth: 1,
                        padding: 10,
                        cornerRadius: 8,
                    },
                },
            };

            const ctx = canvas.getContext("2d");

            if (chartType === "line") {
                chartJsType = "line";
                let themeKey = (this.props.widget && this.props.widget.color_accent) || "purple";
                const widgetName = (this.props.widget && this.props.widget.name || "").toLowerCase();
                if (themeKey === "red" && (widgetName.includes("revenue") || widgetName.includes("sales") || widgetName.includes("income") || widgetName.includes("customer"))) {
                    themeKey = "purple";
                }
                const glassTheme = GLASS_THEMES[themeKey] || GLASS_THEMES.purple;
                const primaryColor = glassTheme.borders[0] || palette.primary;
                const topFill = glassTheme.gradients[0][0];
                const bottomFill = glassTheme.gradients[0][1];

                datasetConfig = {
                    label: this.props.widget.name,
                    data: this.data.values,
                    borderColor: primaryColor,
                    backgroundColor: (context) => {
                        const chart = context && context.chart;
                        const { ctx: cCtx, chartArea } = chart || {};
                        const usedCtx = cCtx || ctx;
                        if (!usedCtx) return topFill;
                        const top = chartArea ? chartArea.top : 10;
                        const bottom = chartArea ? chartArea.bottom : 220;
                        const g = usedCtx.createLinearGradient(0, top, 0, bottom);
                        g.addColorStop(0, topFill);
                        g.addColorStop(0.6, bottomFill);
                        g.addColorStop(1, "rgba(255, 255, 255, 0.0)");
                        return g;
                    },
                    borderWidth: 3,
                    fill: true,
                    tension: 0.38,
                    pointBackgroundColor: primaryColor,
                    pointBorderColor: "#FFFFFF",
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 7,
                };
                optionsConfig.scales = {
                    x: {
                        grid: { display: false, color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 } },
                    },
                    y: {
                        grid: { color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 } },
                    },
                };
            } else if (chartType === "horizontal_bar") {
                chartJsType = "bar";
                optionsConfig.indexAxis = "y";
                let themeKey = (this.props.widget && this.props.widget.color_accent) || "purple";
                const widgetName = (this.props.widget && this.props.widget.name || "").toLowerCase();
                if (themeKey === "red" && (widgetName.includes("revenue") || widgetName.includes("sales") || widgetName.includes("income") || widgetName.includes("customer"))) {
                    themeKey = "purple";
                }
                const glassTheme = GLASS_THEMES[themeKey] || GLASS_THEMES.purple;

                datasetConfig = {
                    label: this.props.widget.name,
                    data: this.data.values,
                    backgroundColor: (context) => {
                        const c = context && context.chart;
                        const { ctx: chartCtx, chartArea } = c || {};
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        const pair = glassTheme.gradients[idx % glassTheme.gradients.length];
                        return createBarGlassGradient(chartCtx || ctx, canvas, chartArea, context && context.element, pair, true);
                    },
                    borderColor: (context) => {
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        return glassTheme.borders[idx % glassTheme.borders.length];
                    },
                    borderWidth: {
                        top: 1,
                        right: 2,
                        bottom: 1,
                        left: 0,
                    },
                    borderRadius: {
                        topLeft: 0,
                        topRight: 8,
                        bottomLeft: 0,
                        bottomRight: 8,
                    },
                    borderSkipped: false,
                    hoverBorderWidth: 2,
                    hoverBorderColor: "#FFFFFF",
                    hoverBackgroundColor: (context) => {
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        const pair = glassTheme.gradients[idx % glassTheme.gradients.length];
                        return pair[0];
                    },
                };
                optionsConfig.scales = {
                    x: {
                        grid: { color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 } },
                    },
                    y: {
                        grid: { display: false, color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 } },
                    },
                };
            } else if (chartType === "doughnut" || chartType === "pie") {
                chartJsType = chartType;
                let themeKey = (this.props.widget && this.props.widget.color_accent) || "purple";
                const glassTheme = GLASS_THEMES[themeKey] || GLASS_THEMES.purple;
                datasetConfig = {
                    data: this.data.values,
                    backgroundColor: glassTheme.gradients.map(p => p[0]),
                    borderColor: "#FFFFFF",
                    borderWidth: 2.5,
                    hoverOffset: 6,
                };
                if (chartType === "doughnut") {
                    optionsConfig.cutout = "65%";
                }
            } else if (chartType === "polar_area") {
                chartJsType = "polarArea";
                let themeKey = (this.props.widget && this.props.widget.color_accent) || "purple";
                const glassTheme = GLASS_THEMES[themeKey] || GLASS_THEMES.purple;
                datasetConfig = {
                    data: this.data.values,
                    backgroundColor: glassTheme.gradients.map(p => p[0]),
                    borderColor: "#FFFFFF",
                    borderWidth: 2,
                };
                optionsConfig.scales = {
                    r: {
                        grid: { color: "rgba(0, 0, 0, 0.06)" },
                        ticks: { display: false },
                    },
                };
            } else if (chartType === "radar") {
                chartJsType = "radar";
                datasetConfig = {
                    label: this.props.widget.name,
                    data: this.data.values,
                    backgroundColor: palette.gradientStart,
                    borderColor: palette.primary,
                    borderWidth: 2,
                    pointBackgroundColor: palette.primary,
                    pointBorderColor: "#FFFFFF",
                    pointHoverRadius: 6,
                };
                optionsConfig.scales = {
                    r: {
                        grid: { color: "rgba(0, 0, 0, 0.06)" },
                        angleLines: { color: "rgba(0, 0, 0, 0.06)" },
                        pointLabels: { color: "#475569", font: { size: 10 } },
                        ticks: { display: false },
                    },
                };
            } else if (chartType === "scatter") {
                chartJsType = "scatter";
                datasetConfig = {
                    label: this.props.widget.name,
                    data: this.data.points || [],
                    backgroundColor: palette.primary,
                    borderColor: "#FFFFFF",
                    pointRadius: 6,
                    pointHoverRadius: 8,
                };
                optionsConfig.plugins.tooltip.callbacks = {
                    label: (context) => {
                        const pt = context.raw || {};
                        return `${pt.label || "Point"}: (${pt.x}, ${pt.y})`;
                    },
                };
                optionsConfig.scales = {
                    x: {
                        title: { display: true, text: this.data.x_label || "X Axis", color: "#64748B" },
                        grid: { color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B" },
                    },
                    y: {
                        title: { display: true, text: this.data.y_label || "Y Axis", color: "#64748B" },
                        grid: { color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B" },
                    },
                };
            } else {
                // Default Vertical Bar chart with modern Glassmorphism & Vertical Gradient
                chartJsType = "bar";
                let themeKey = (this.props.widget && this.props.widget.color_accent) || "purple";
                const widgetName = (this.props.widget && this.props.widget.name || "").toLowerCase();
                if (themeKey === "red" && (widgetName.includes("revenue") || widgetName.includes("sales") || widgetName.includes("income") || widgetName.includes("customer"))) {
                    themeKey = "purple";
                }
                const glassTheme = GLASS_THEMES[themeKey] || GLASS_THEMES.purple;

                datasetConfig = {
                    label: this.props.widget.name,
                    data: this.data.values,
                    backgroundColor: (context) => {
                        const c = context && context.chart;
                        const { ctx: chartCtx, chartArea } = c || {};
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        const pair = glassTheme.gradients[idx % glassTheme.gradients.length];
                        return createBarGlassGradient(chartCtx || ctx, canvas, chartArea, context && context.element, pair, false);
                    },
                    borderColor: (context) => {
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        return glassTheme.borders[idx % glassTheme.borders.length];
                    },
                    borderWidth: {
                        top: 2,
                        right: 1,
                        bottom: 0,
                        left: 1,
                    },
                    borderRadius: {
                        topLeft: 8,
                        topRight: 8,
                        bottomLeft: 0,
                        bottomRight: 0,
                    },
                    borderSkipped: false,
                    hoverBorderWidth: 2,
                    hoverBorderColor: "#FFFFFF",
                    hoverBackgroundColor: (context) => {
                        const idx = (context && typeof context.dataIndex === "number") ? context.dataIndex : 0;
                        const pair = glassTheme.gradients[idx % glassTheme.gradients.length];
                        return pair[0];
                    },
                };
                optionsConfig.scales = {
                    x: {
                        grid: { display: false, color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11, family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto" } },
                    },
                    y: {
                        grid: { color: "rgba(0, 0, 0, 0.05)" },
                        ticks: { color: "#64748B", font: { size: 11 } },
                    },
                };
            }

            optionsConfig.onClick = (evt, elements) => {
                if (elements && elements.length > 0 && this.props.onDrilldown) {
                    this.props.onDrilldown(this.props.widget);
                }
            };

            const chartData =
                chartType === "scatter"
                    ? { datasets: [datasetConfig] }
                    : { labels: this.data.labels, datasets: [datasetConfig] };

            // Check if existing instance can be updated smoothly in-place
            if (this.chartInstance && this.chartInstance.config && this.chartInstance.config.type === chartJsType) {
                this.chartInstance.data = chartData;
                this.chartInstance.options = optionsConfig;
                this.chartInstance.update("none");
                return;
            }

            // Fresh chart mount: safely clean up any prior chart attached to canvas
            this.destroyChart();

            this.chartInstance = new Chart(canvas, {
                type: chartJsType,
                data: chartData,
                options: optionsConfig,
            });
        } catch (err) {
            console.error("[AraDashboard] Failed to render chart:", err);
            this.destroyChart();
        }
    }
}

// Register for all chart-based widget types
const chartWidgetTypes = [
    "chart",
    "bar",
    "horizontal_bar",
    "line",
    "pie",
    "doughnut",
    "polar_area",
    "radar",
    "scatter",
];
for (const t of chartWidgetTypes) {
    araWidgetRegistry.add(t, {
        component: ChartWidget,
        label: t.replace("_", " ").toUpperCase(),
    });
}
