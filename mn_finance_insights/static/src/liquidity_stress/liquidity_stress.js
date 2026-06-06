/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class LiquidityStress extends Component {
    static template = "mn_finance_insights.LiquidityStress";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.rootRef = useRef("root"); this.chart = null;
        this.state = useState({ loading: true, data: null, options: { as_of: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.liquidity.stress", "get_stress_data", [this.state.options]); }
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
        const c = this.rootRef.el.querySelector("canvas[data-chart='stress']");
        if (!c) return;
        const d = this.state.data;
        const colors = { base: "#10b981", mild_stress: "#f59e0b", severe_stress: "#ef4444" };
        const labels = { base: "Base", mild_stress: "Mild stress (+15d AR, 2% default)", severe_stress: "Severe (+45d AR, +15d AP accel, 8% default)" };
        const datasets = Object.entries(d.scenarios).map(([k, s]) => ({
            label: labels[k], data: s.weeks.map((w) => w.cumulative),
            borderColor: colors[k], backgroundColor: colors[k] + "22", fill: false,
            tension: 0.3, pointRadius: 3, borderWidth: 2,
        }));
        this.chart = new window.Chart(c, {
            type: "line",
            data: { labels: d.labels, datasets },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(0,0,0,0.05)" } } } },
        });
    }
}
registry.category("actions").add("mn_finance_insights.liquidity_stress", LiquidityStress);
