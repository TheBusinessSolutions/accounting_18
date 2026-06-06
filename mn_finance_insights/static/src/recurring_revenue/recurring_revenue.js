/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class RecurringRevenue extends Component {
    static template = "mn_finance_insights.RecurringRevenue";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.rootRef = useRef("root"); this.chart = null;
        this.state = useState({ loading: true, data: null,
            options: { as_of: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.recurring.revenue", "get_recurring_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const c = this.rootRef.el.querySelector("canvas[data-chart='rr']");
        if (!c) return;
        const d = this.state.data;
        this.chart = new window.Chart(c, {
            data: { labels: d.labels,
                datasets: [
                    { type: "bar", label: "New revenue", data: d.total.map((t, i) => t - d.repeat[i]),
                      backgroundColor: "#3b82f6", borderRadius: 6, stack: "rev" },
                    { type: "bar", label: "Repeat revenue", data: d.repeat, backgroundColor: "#10b981", borderRadius: 6, stack: "rev" },
                    { type: "line", label: "Repeat %", data: d.pct, borderColor: "#f59e0b",
                      backgroundColor: "rgba(245,158,11,0.12)", fill: true, tension: 0.35, pointRadius: 3, yAxisID: "y1" },
                ] },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                scales: { x: { stacked: true, grid: { display: false } },
                    y: { stacked: true, grid: { color: "rgba(0,0,0,0.05)" } },
                    y1: { position: "right", grid: { display: false }, max: 100 } } },
        });
    }
}
registry.category("actions").add("mn_finance_insights.recurring_revenue", RecurringRevenue);
