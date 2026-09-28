/** @odoo-module **/

import { Component, useState, onWillStart, onWillUnmount, useRef } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { BaseWidget } from "./widgets/base_widget";
import { araWidgetRegistry } from "./widget_registry";
import "./widgets/kpi_widget";
import "./widgets/chart_widget";
import "./widgets/table_widget";
import "./widgets/progress_widget";
import "./widgets/radial_widget";
import "./widgets/bullet_widget";
import "./widgets/funnel_widget";
import "./widgets/flower_widget";
import "./widgets/todo_widget";

export class AraDashboard extends Component {
    static template = "ara_dashboard.MainDashboard";
    static components = { BaseWidget };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.liveClockRef = useRef("liveClock");
        this.isDataFetching = false;
        this.actionUpdateTimer = null;
        this.isDestroyed = false;

        const parseUrlDashboardId = () => {
            try {
                const searchParams = new URLSearchParams(window.location.search);
                if (searchParams.has("dashboard_id")) {
                    const parsed = parseInt(searchParams.get("dashboard_id"), 10);
                    if (!isNaN(parsed) && parsed > 0) return parsed;
                }
                const hash = window.location.hash ? window.location.hash.slice(1) : "";
                if (hash) {
                    const hashSearch = hash.includes("?") ? hash.slice(hash.indexOf("?") + 1) : hash;
                    const hashParams = new URLSearchParams(hashSearch);
                    if (hashParams.has("dashboard_id")) {
                        const parsed = parseInt(hashParams.get("dashboard_id"), 10);
                        if (!isNaN(parsed) && parsed > 0) return parsed;
                    }
                }
            } catch (err) {
                // Ignore URL parsing errors
            }
            return false;
        };

        const initialDashboardId =
            (this.props.action && this.props.action.params && this.props.action.params.dashboard_id) ||
            (this.props.action && this.props.action.context && this.props.action.context.active_dashboard_id) ||
            parseUrlDashboardId() ||
            false;

        this.state = useState({
            isLoading: true,
            isRefreshing: false,
            isEditMode: false,
            isSmartInsightsOpen: false,
            isShareModalOpen: false,
            isPresentationMode: false,
            isTvMode: false,
            presentationIndex: 0,
            presentationPlaying: true,
            presentationSlides: [],
            smartInsights: [],
            shareScope: "everyone",
            sharePermission: "view",
            shareSaving: false,
            activeDashboardId: initialDashboardId,
            activeFilter: "this_month",
            dashboard: {},
            widgets: [],
            availableDashboards: [],
        });

        this.draggedWidgetId = null;
        this.refreshTimer = null;
        this.presentationTimer = null;
        this.tvClockTimer = null;

        // Global Keydown Handler (ESC, Arrow keys, Spacebar for presentation)
        this.onKeyDown = (ev) => {
            if (ev.key === "Escape") {
                if (this.state.isPresentationMode) this.exitPresentationMode();
                if (this.state.isTvMode) this.exitTvMode();
                if (this.state.isShareModalOpen) this.closeShareModal();
                if (this.state.isSmartInsightsOpen) this.closeSmartInsights();
            } else if (this.state.isPresentationMode) {
                if (ev.key === "ArrowRight") {
                    this.nextSlide();
                } else if (ev.key === "ArrowLeft") {
                    this.prevSlide();
                } else if (ev.key === " ") {
                    ev.preventDefault();
                    this.togglePresentationPlay();
                }
            }
        };
        window.addEventListener("keydown", this.onKeyDown);

        // Auto-refresh when returning from breadcrumbs or action views (debounced & guarded)
        this.onActionUpdate = () => {
            if (this.state.isPresentationMode || this.state.isTvMode) return;
            if (this.actionUpdateTimer) {
                clearTimeout(this.actionUpdateTimer);
            }
            this.actionUpdateTimer = setTimeout(() => {
                if (!this.isDestroyed) {
                    this.loadDashboardData(true);
                }
            }, 350);
        };
        this.env.bus.addEventListener("ACTION_MANAGER:UPDATE", this.onActionUpdate);

        // Auto-refresh silently when user focuses back on window
        this.onWindowFocus = () => {
            if (!this.state.isPresentationMode && !this.state.isTvMode) {
                this.loadDashboardData(true);
            }
        };
        window.addEventListener("focus", this.onWindowFocus);

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onWillUnmount(() => {
            this.isDestroyed = true;
            if (this.actionUpdateTimer) {
                clearTimeout(this.actionUpdateTimer);
                this.actionUpdateTimer = null;
            }
            window.removeEventListener("keydown", this.onKeyDown);
            window.removeEventListener("focus", this.onWindowFocus);
            this.env.bus.removeEventListener("ACTION_MANAGER:UPDATE", this.onActionUpdate);
            this.clearAutoRefresh();
            this.clearPresentationTimer();
            this.clearTvClock();
        });
    }

    async loadDashboardData(isSilent = false) {
        if (this.isDataFetching) {
            return;
        }
        this.isDataFetching = true;
        if (!isSilent) {
            this.state.isLoading = true;
        } else {
            this.state.isRefreshing = true;
        }

        try {
            const payload = await this.orm.call(
                "ara.dashboard",
                "fetch_dashboard_payload",
                [this.state.activeDashboardId || 0],
                { date_filter: this.state.activeFilter }
            );

            if (payload && payload.dashboard) {
                this.state.dashboard = payload.dashboard;
                this.state.activeDashboardId = payload.dashboard.id;
                this.state.widgets = payload.widgets || [];
                this.state.availableDashboards = payload.available_dashboards || [];
                if (!this.state.activeFilter && payload.dashboard.default_filter) {
                    this.state.activeFilter = payload.dashboard.default_filter;
                }
                this.state.smartInsights = payload.smart_insights || [];
                this.state.presentationSlides = payload.presentation_slides || [];
                this.state.shareScope = payload.dashboard.share_scope || "everyone";
                this.state.sharePermission = payload.dashboard.share_permission || "view";

                if (!this.state.isTvMode) {
                    this.setupAutoRefresh(payload.dashboard.refresh_interval);
                }
            } else {
                this.state.dashboard = false;
                this.state.widgets = [];
                this.state.availableDashboards = payload.available_dashboards || [];
                this.state.smartInsights = [];
                this.state.presentationSlides = [];
            }
        } catch (err) {
            this.notification.add(`Failed to load dashboard: ${err.message || err}`, {
                type: "danger",
            });
        } finally {
            this.isDataFetching = false;
            this.state.isLoading = false;
            this.state.isRefreshing = false;
        }
    }

    setupAutoRefresh(intervalSeconds) {
        this.clearAutoRefresh();
        if (intervalSeconds && intervalSeconds > 0) {
            this.refreshTimer = setInterval(() => {
                this.loadDashboardData(true);
            }, intervalSeconds * 1000);
        }
    }

    clearAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    getWidgetComponent(widgetType) {
        const typeAliases = {
            kpi: "kpi",
            tiles: "tiles",
            table: "table",
            list: "list",
            progress: "progress",
            radial: "radial",
            bullet: "bullet",
            funnel: "funnel",
            flower: "flower",
            todo: "todo",
            bar: "bar",
            horizontal_bar: "horizontal_bar",
            line: "line",
            pie: "pie",
            doughnut: "doughnut",
            polar_area: "polar_area",
            radar: "radar",
            scatter: "scatter",
            chart: "chart",
        };
        const resolved = typeAliases[widgetType] || widgetType;
        const entry =
            araWidgetRegistry.get(resolved, null) ||
            araWidgetRegistry.get("chart", null) ||
            araWidgetRegistry.get("kpi", null);
        return entry ? entry.component : null;
    }

    async onDashboardChange(ev) {
        const newId = parseInt(ev.target.value, 10);
        if (newId && newId !== this.state.activeDashboardId) {
            this.state.activeDashboardId = newId;
            await this.loadDashboardData();
        }
    }

    async onFilterChange(filterCode) {
        if (this.state.activeFilter !== filterCode) {
            this.state.activeFilter = filterCode;
            await this.loadDashboardData();
        }
    }

    get currentYear() {
        return new Date().getFullYear();
    }

    get availablePastYears() {
        const cur = new Date().getFullYear();
        return [cur - 2, cur - 3, cur - 4, cur - 5];
    }

    get isYearFilterActive() {
        const f = this.state.activeFilter;
        return (
            f === "this_year" ||
            f === "last_year" ||
            (typeof f === "string" && f.startsWith("year_"))
        );
    }

    get activeYearLabel() {
        const f = this.state.activeFilter;
        const cur = new Date().getFullYear();
        if (f === "this_year") return `${cur}`;
        if (f === "last_year") return `${cur - 1}`;
        if (typeof f === "string" && f.startsWith("year_")) {
            return `${f.replace("year_", "")}`;
        }
        return "Year";
    }

    async onYearSelectChange(ev) {
        const val = ev.target.value;
        if (val) {
            await this.onFilterChange(val);
        }
    }

    async clearYearFilter(ev) {
        if (ev) {
            ev.stopPropagation();
            ev.preventDefault();
        }
        await this.onFilterChange("this_month");
    }

    async onManualRefresh() {
        await this.loadDashboardData(false);
    }

    // =========================================================================
    // FAVORITE DASHBOARD FEATURE (Bookmark / ⭐)
    // =========================================================================
    async toggleFavorite() {
        if (!this.state.dashboard || !this.state.dashboard.id) return;
        try {
            const isFav = await this.orm.call("ara.dashboard", "toggle_favorite", [this.state.dashboard.id]);
            this.state.dashboard.is_favorite = isFav;

            const dashItem = this.state.availableDashboards.find((d) => d.id === this.state.dashboard.id);
            if (dashItem) {
                dashItem.is_favorite = isFav;
            }

            if (isFav) {
                this.notification.add(`Dashboard "${this.state.dashboard.name}" added to your favorites ⭐`, {
                    type: "success",
                });
            } else {
                this.notification.add(`Dashboard "${this.state.dashboard.name}" removed from favorites.`, {
                    type: "info",
                });
            }
        } catch (err) {
            this.notification.add(`Could not update favorite status: ${err.message || err}`, {
                type: "danger",
            });
        }
    }

    // =========================================================================
    // SMART INSIGHTS FEATURE
    // =========================================================================
    toggleSmartInsights() {
        this.state.isSmartInsightsOpen = !this.state.isSmartInsightsOpen;
    }

    closeSmartInsights() {
        this.state.isSmartInsightsOpen = false;
    }

    // =========================================================================
    // DASHBOARD SHARING FEATURE (Only Me, Department, Users, Groups, Everyone)
    // =========================================================================
    openShareModal() {
        if (!this.state.dashboard) return;
        this.state.shareScope = this.state.dashboard.share_scope || "everyone";
        this.state.sharePermission = this.state.dashboard.share_permission || "view";
        this.state.isShareModalOpen = true;
    }

    closeShareModal() {
        this.state.isShareModalOpen = false;
    }

    setShareScope(scope) {
        this.state.shareScope = scope;
    }

    setSharePermission(permission) {
        this.state.sharePermission = permission;
    }

    async saveShareSettings() {
        if (!this.state.dashboard || !this.state.dashboard.id) return;
        this.state.shareSaving = true;
        try {
            await this.orm.call("ara.dashboard", "update_sharing", [
                this.state.dashboard.id,
                this.state.shareScope,
                this.state.sharePermission,
            ]);
            this.state.dashboard.share_scope = this.state.shareScope;
            this.state.dashboard.share_permission = this.state.sharePermission;
            this.state.isShareModalOpen = false;
            this.notification.add("Dashboard sharing settings updated successfully.", {
                type: "success",
            });
        } catch (err) {
            this.notification.add(`Failed to update sharing: ${err.message || err}`, {
                type: "danger",
            });
        } finally {
            this.state.shareSaving = false;
        }
    }

    // =========================================================================
    // PRESENTATION MODE (Auto-rotating Fullscreen Slideshow)
    // =========================================================================
    get currentSlide() {
        if (!this.state.presentationSlides || !this.state.presentationSlides.length) {
            return {
                dashboard_id: 1,
                dashboard_name: (this.state.dashboard && this.state.dashboard.name) || "Sales Intelligence Hub",
                primary_kpi: {
                    title: "REVENUE",
                    value: "$1,284,500",
                    raw_value: 1284500,
                    trend_pct: 18.4,
                    trend_positive: true,
                    icon: "fa-line-chart",
                    accent: "red",
                },
                secondary_kpis: [
                    { title: "Orders Today", value: "842", trend_pct: 14.2 },
                    { title: "Pending", value: "43", trend_pct: -2.5 },
                    { title: "Completed", value: "799", trend_pct: 18.0 },
                ],
                progress_kpi: {
                    title: "Monthly Sales Target",
                    percentage: 88,
                    formatted_current: "$1,284,500",
                    formatted_target: "$1,450,000",
                },
            };
        }
        return this.state.presentationSlides[this.state.presentationIndex] || this.state.presentationSlides[0];
    }

    startPresentationMode() {
        this.state.isPresentationMode = true;
        this.state.presentationPlaying = true;
        this.state.presentationIndex = 0;
        this.startPresentationTimer();

        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(() => {});
        }
    }

    exitPresentationMode() {
        this.state.isPresentationMode = false;
        this.clearPresentationTimer();
        if (document.fullscreenElement && document.exitFullscreen) {
            document.exitFullscreen().catch(() => {});
        }
    }

    togglePresentationPlay() {
        this.state.presentationPlaying = !this.state.presentationPlaying;
        if (this.state.presentationPlaying) {
            this.startPresentationTimer();
        } else {
            this.clearPresentationTimer();
        }
    }

    nextSlide() {
        if (!this.state.presentationSlides.length) return;
        this.state.presentationIndex = (this.state.presentationIndex + 1) % this.state.presentationSlides.length;
        if (this.state.presentationPlaying) {
            this.startPresentationTimer();
        }
    }

    prevSlide() {
        if (!this.state.presentationSlides.length) return;
        this.state.presentationIndex =
            (this.state.presentationIndex - 1 + this.state.presentationSlides.length) %
            this.state.presentationSlides.length;
        if (this.state.presentationPlaying) {
            this.startPresentationTimer();
        }
    }

    goToSlide(index) {
        this.state.presentationIndex = index;
        if (this.state.presentationPlaying) {
            this.startPresentationTimer();
        }
    }

    startPresentationTimer() {
        this.clearPresentationTimer();
        const interval = (this.state.dashboard && this.state.dashboard.presentation_interval) || 12;
        this.presentationTimer = setInterval(() => {
            if (this.state.isPresentationMode && this.state.presentationPlaying && this.state.presentationSlides.length) {
                this.state.presentationIndex =
                    (this.state.presentationIndex + 1) % this.state.presentationSlides.length;
            }
        }, interval * 1000);
    }

    clearPresentationTimer() {
        if (this.presentationTimer) {
            clearInterval(this.presentationTimer);
            this.presentationTimer = null;
        }
    }

    // =========================================================================
    // WALLBOARD / TV MODE 📺 (Continuous 24/7 Operations Display)
    // =========================================================================
    startTvMode() {
        this.state.isTvMode = true;
        this.clearTvClock();
        this.tvClockTimer = setInterval(() => {
            this.updateClock();
        }, 1000);
        setTimeout(() => this.updateClock(), 50);

        // Switch to fast 30-second background telemetry polling
        this.setupAutoRefresh(30);

        if (document.documentElement.requestFullscreen) {
            document.documentElement.requestFullscreen().catch(() => {});
        }

        // Broadcast resize event after fullscreen transition so charts and SVG adapt seamlessly
        setTimeout(() => {
            window.dispatchEvent(new Event("resize"));
        }, 300);

        this.notification.add("Wallboard TV Mode Active. Telemetry updating live.", {
            type: "info",
        });
    }

    exitTvMode() {
        this.state.isTvMode = false;
        this.clearTvClock();
        this.setupAutoRefresh(this.state.dashboard && this.state.dashboard.refresh_interval);

        if (document.fullscreenElement && document.exitFullscreen) {
            document.exitFullscreen().catch(() => {});
        }

        setTimeout(() => {
            window.dispatchEvent(new Event("resize"));
        }, 300);
    }

    updateClock() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString("en-US", { hour12: false });
        if (this.liveClockRef && this.liveClockRef.el) {
            this.liveClockRef.el.textContent = timeStr;
        }
    }

    clearTvClock() {
        if (this.tvClockTimer) {
            clearInterval(this.tvClockTimer);
            this.tvClockTimer = null;
        }
    }

    // =========================================================================
    // REORDER MODE & DRAG AND DROP
    // =========================================================================
    toggleEditMode() {
        this.state.isEditMode = !this.state.isEditMode;
        if (this.state.isEditMode) {
            this.notification.add("Reorder Mode Active: Drag and drop cards to rearrange your layout.", {
                type: "warning",
            });
        } else {
            this.notification.add("Reorder Mode Finished: Dashboard layout has been locked.", {
                type: "info",
            });
        }
    }

    onDragStart(ev, widgetId) {
        if (!this.state.isEditMode) return;
        this.draggedWidgetId = widgetId;
        ev.dataTransfer.setData("text/plain", String(widgetId));
        ev.dataTransfer.effectAllowed = "move";
    }

    onDragOver(ev, targetWidgetId) {
        if (!this.state.isEditMode || !this.draggedWidgetId) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "move";
    }

    async onDrop(ev, targetWidgetId) {
        if (!this.state.isEditMode || !this.draggedWidgetId) return;
        ev.preventDefault();
        const draggedId = this.draggedWidgetId;
        this.draggedWidgetId = null;

        if (draggedId === targetWidgetId) return;

        const widgets = [...this.state.widgets];
        const fromIdx = widgets.findIndex((w) => w.id === draggedId);
        const toIdx = widgets.findIndex((w) => w.id === targetWidgetId);

        if (fromIdx === -1 || toIdx === -1) return;

        const [movedItem] = widgets.splice(fromIdx, 1);
        widgets.splice(toIdx, 0, movedItem);

        const seqMapping = widgets.map((w, index) => {
            const seq = (index + 1) * 10;
            w.sequence = seq;
            return { id: w.id, sequence: seq };
        });

        this.state.widgets = widgets;

        try {
            // Batch update sequences and immediately receive fresh data without a page reload
            const payload = await this.orm.call("ara.dashboard", "reorder_widgets", [
                this.state.dashboard.id,
                seqMapping,
            ]);
            if (payload && payload.widgets) {
                this.state.widgets = payload.widgets;
                this.state.smartInsights = payload.smart_insights || [];
                this.state.presentationSlides = payload.presentation_slides || [];
            }
            this.notification.add("Dashboard layout updated and synced in real-time.", {
                type: "success",
            });
        } catch (err) {
            console.error("Failed to save widget sequence:", err);
            this.notification.add(`Failed to update widget order: ${err.message || err}`, {
                type: "danger",
            });
        }
    }

    // =========================================================================
    // SCHEDULED DASHBOARD REPORTS
    // =========================================================================
    onScheduleReport() {
        if (!this.state.dashboard || !this.state.dashboard.id) return;
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: "Schedule Dashboard Report",
                res_model: "ara.dashboard.report.schedule",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_dashboard_id: this.state.dashboard.id,
                    default_name: `Weekly Report: ${this.state.dashboard.name}`,
                    default_subject: `📊 ${this.state.dashboard.name} - Scheduled Executive Report`,
                    default_schedule_interval: "weekly",
                    default_day_of_week: "0",
                    default_schedule_time: "08:00",
                    default_recipient_emails: "sales@company.com, manager@company.com",
                },
            },
            {
                onClose: () => this.loadDashboardData(),
            }
        );
    }

    // =========================================================================
    // STANDARD ACTIONS & DRILLDOWN
    // =========================================================================
    onEditDashboard() {
        if (!this.state.dashboard || !this.state.dashboard.id) return;
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: "Dashboard Settings",
                res_model: "ara.dashboard",
                res_id: this.state.dashboard.id,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: () => this.loadDashboardData(),
            }
        );
    }

    onAddNewWidget() {
        if (!this.state.dashboard || !this.state.dashboard.id) return;
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: "Add New Widget",
                res_model: "ara.dashboard.widget",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_dashboard_id: this.state.dashboard.id,
                },
            },
            {
                onClose: () => this.loadDashboardData(),
            }
        );
    }

    onEditWidget(widget) {
        if (!widget || !widget.id) return;
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                name: `Edit: ${widget.name}`,
                res_model: "ara.dashboard.widget",
                res_id: widget.id,
                views: [[false, "form"]],
                target: "new",
            },
            {
                onClose: () => this.loadDashboardData(),
            }
        );
    }

    async onDuplicateWidget(widget) {
        if (!widget || !widget.id) return;
        try {
            await this.orm.call("ara.dashboard.widget", "copy", [widget.id]);
            this.notification.add(`Widget "${widget.name}" duplicated.`, {
                type: "success",
            });
            await this.loadDashboardData(true);
        } catch (err) {
            this.notification.add(`Failed to duplicate widget: ${err.message || err}`, {
                type: "danger",
            });
        }
    }

    async onDeleteWidget(widget) {
        if (!widget || !widget.id) return;
        try {
            await this.orm.unlink("ara.dashboard.widget", [widget.id]);
            this.state.widgets = this.state.widgets.filter((w) => w.id !== widget.id);
            this.notification.add(`Widget "${widget.name}" removed from dashboard.`, {
                type: "info",
            });
            await this.loadDashboardData(true);
        } catch (err) {
            this.notification.add(`Failed to delete widget: ${err.message || err}`, {
                type: "danger",
            });
        }
    }

    async onDrilldown(widget, recordId = null) {
        if (!widget || !widget.data || !widget.data.model) return;

        if (recordId) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: widget.data.model,
                res_id: recordId,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            const domain = (widget.data && widget.data.drilldown_domain) || [];
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: widget.name,
                res_model: widget.data.model,
                views: [
                    [false, "list"],
                    [false, "form"],
                ],
                domain: domain,
                target: "current",
            });
        }
    }
}

registry.category("actions").add("ara_dashboard_main", AraDashboard);
