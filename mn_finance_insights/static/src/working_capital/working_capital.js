/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class WorkingCapital extends Component {
    static template = "mn_finance_insights.WorkingCapital";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.chart = null;
        this.state = useState({
            loading: true, data: null,
            options: { as_of: new Date().toISOString().slice(0, 10) },
        });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }
    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.working.capital", "get_ccc_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load working capital."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }

    cccClass(c) { return c <= 60 ? "heat-good" : (c <= 120 ? "heat-ok" : "heat-bad"); }

    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const canvas = this.rootRef.el.querySelector("canvas[data-chart='ccc']");
        if (!canvas) return;
        const d = this.state.data;
        this.chart = new window.Chart(canvas, {
            type: "line",
            data: {
                labels: d.labels,
                datasets: [
                    { label: "DSO", data: d.dso, borderColor: "#f59e0b", backgroundColor: "transparent", tension: 0.35, pointRadius: 3 },
                    { label: "DIO", data: d.dio, borderColor: "#3b82f6", backgroundColor: "transparent", tension: 0.35, pointRadius: 3 },
                    { label: "DPO", data: d.dpo, borderColor: "#10b981", backgroundColor: "transparent", tension: 0.35, pointRadius: 3 },
                    { label: "CCC", data: d.ccc, borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.12)", fill: true, tension: 0.35, pointRadius: 4, borderWidth: 3 },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(0,0,0,0.05)" } } } },
        });
    }
}

registry.category("actions").add("mn_finance_insights.working_capital", WorkingCapital);
