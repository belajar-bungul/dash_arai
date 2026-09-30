/** @odoo-module **/
import { Component, useEffect, useRef } from "@odoo/owl";
import { araWidgetRegistry } from "../widget_registry";

export class FlowerWidget extends Component {
    static template = "ara_dashboard.FlowerWidget";
    static props = {
        widget: Object,
        onDrilldown: { type: Function, optional: true },
    };

    setup() {
        this.canvasRef = useRef("flowerCanvas");

        useEffect(() => {
            this.drawFlower();
        });
    }

    get petals() {
        return (this.props.widget.data && this.props.widget.data.petals) || [];
    }

    drawFlower() {
        const canvas = this.canvasRef.el;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const width = canvas.width;
        const height = canvas.height;
        ctx.clearRect(0, 0, width, height);

        const centerX = width / 2;
        const centerY = height / 2;
        const maxRadius = Math.min(centerX, centerY) - 28;

        const petals = this.petals;
        if (!petals.length) return;

        const numPetals = petals.length;
        const angleStep = (2 * Math.PI) / numPetals;

        // Draw petals
        petals.forEach((p, idx) => {
            const angle = idx * angleStep - Math.PI / 2;
            const r = maxRadius * (p.normalized || 0.5);

            ctx.save();
            ctx.translate(centerX, centerY);
            ctx.rotate(angle);

            // Draw petal path (elliptical curve)
            ctx.beginPath();
            ctx.moveTo(0, 0);
            ctx.quadraticCurveTo(18, r * 0.5, 0, r);
            ctx.quadraticCurveTo(-18, r * 0.5, 0, 0);

            // Radial petal gradient (Executive Pastel-Neon Spectrum)
            const petalGradients = [
                ["rgba(139, 92, 246, 0.90)", "rgba(99, 102, 241, 0.18)", "#A78BFA"],
                ["rgba(99, 102, 241, 0.90)", "rgba(59, 130, 246, 0.18)", "#818CF8"],
                ["rgba(6, 182, 212, 0.90)", "rgba(14, 116, 144, 0.18)", "#67E8F9"],
                ["rgba(16, 185, 129, 0.90)", "rgba(5, 150, 105, 0.18)", "#6EE7B7"],
                ["rgba(14, 165, 233, 0.90)", "rgba(3, 105, 161, 0.18)", "#7DD3FC"],
                ["rgba(168, 85, 247, 0.90)", "rgba(126, 34, 206, 0.18)", "#C084FC"],
                ["rgba(245, 158, 11, 0.90)", "rgba(180, 83, 9, 0.18)", "#FDE68A"],
                ["rgba(20, 184, 166, 0.90)", "rgba(15, 118, 110, 0.18)", "#5EEAD4"],
            ];
            const pTheme = petalGradients[idx % petalGradients.length];
            const grad = ctx.createLinearGradient(0, 0, 0, r);
            grad.addColorStop(0, pTheme[1]);
            grad.addColorStop(0.4, pTheme[0]);
            grad.addColorStop(1, pTheme[0]);

            ctx.fillStyle = grad;
            ctx.fill();
            ctx.strokeStyle = pTheme[2];
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Petal Tip Glow Dot
            ctx.beginPath();
            ctx.arc(0, r, 3.5, 0, 2 * Math.PI);
            ctx.fillStyle = "#FFFFFF";
            ctx.fill();

            ctx.restore();
        });

        // Draw glowing center pistil
        ctx.beginPath();
        ctx.arc(centerX, centerY, 14, 0, 2 * Math.PI);
        const centerGrad = ctx.createRadialGradient(centerX, centerY, 2, centerX, centerY, 14);
        centerGrad.addColorStop(0, "#FFFFFF");
        centerGrad.addColorStop(0.5, "#7B68EE");
        centerGrad.addColorStop(1, "#18181b");
        ctx.fillStyle = centerGrad;
        ctx.fill();
        ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
        ctx.lineWidth = 1;
        ctx.stroke();
    }

    onClick() {
        if (this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }
}

araWidgetRegistry.add("flower", {
    component: FlowerWidget,
    label: "Flower Chart",
});
