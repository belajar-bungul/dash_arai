import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BaseWidget extends Component {
    static template = "ara_dashboard.BaseWidget";
    static props = {
        widget: Object,
        slots: { type: Object, optional: true },
        isEditMode: { type: Boolean, optional: true },
        onRefresh: { type: Function, optional: true },
        onDrilldown: { type: Function, optional: true },
        onDragStart: { type: Function, optional: true },
        onDragOver: { type: Function, optional: true },
        onDrop: { type: Function, optional: true },
        onEdit: { type: Function, optional: true },
        onDelete: { type: Function, optional: true },
        onDuplicate: { type: Function, optional: true },
    };

    setup() {
        this.actionService = useService("action");
    }

    get hasError() {
        return this.props.widget.data && this.props.widget.data.error;
    }

    get errorMessage() {
        return this.props.widget.data ? this.props.widget.data.error : "";
    }

    get accentClass() {
        return `accent-${this.props.widget.color_accent || "red"}`;
    }

    get colClass() {
        return `ara-col-${this.props.widget.col_span || 4}`;
    }

    onWidgetClick() {
        if (!this.props.isEditMode && this.props.onDrilldown) {
            this.props.onDrilldown(this.props.widget);
        }
    }

    handleEdit(ev) {
        ev.stopPropagation();
        if (this.props.onEdit) {
            this.props.onEdit(this.props.widget);
        }
    }

    handleDuplicate(ev) {
        ev.stopPropagation();
        if (this.props.onDuplicate) {
            this.props.onDuplicate(this.props.widget);
        }
    }

    handleDelete(ev) {
        ev.stopPropagation();
        if (this.props.onDelete) {
            this.props.onDelete(this.props.widget);
        }
    }

    handleDragStart(ev) {
        if (this.props.isEditMode && this.props.onDragStart) {
            this.props.onDragStart(ev, this.props.widget.id);
        }
    }

    handleDragOver(ev) {
        if (this.props.isEditMode && this.props.onDragOver) {
            this.props.onDragOver(ev, this.props.widget.id);
        }
    }

    handleDrop(ev) {
        if (this.props.isEditMode && this.props.onDrop) {
            this.props.onDrop(ev, this.props.widget.id);
        }
    }
}
