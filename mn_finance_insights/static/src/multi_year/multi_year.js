/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class MultiYear extends Component {
    static template = "mn_finance_insights.MultiYear";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.rootRef = useRef("root"); this.chart = null;
        this.state = useState({ loading: true, data: null, options: { year: new Date().getFullYear() } });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.multi.year", "get_multi_year_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = parseInt(ev.target.value, 10); this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    formatDelta(v) { return v === null || v === undefined ? "—" : (v >= 0 ? "+" : "") + v + "%"; }
    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const c = this.rootRef.el.querySelector("canvas[data-chart='my']");
        if (!c) return;
        const d = this.state.data;
        this.chart = new window.Chart(c, {
            type: "bar",
            data: { labels: d.years.map((y) => y.year),
                datasets: [
                    { label: "Revenue", data: d.years.map((y) => y.revenue), backgroundColor: "#10b981", borderRadius: 6 },
                    { label: "Expense", data: d.years.map((y) => y.expense), backgroundColor: "#ef4444", borderRadius: 6 },
                    { label: "Net", data: d.years.map((y) => y.net), backgroundColor: "#6366f1", borderRadius: 6 },
                ] },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(0,0,0,0.05)" } } } },
        });
    }
}
registry.category("actions").add("mn_finance_insights.multi_year", MultiYear);
