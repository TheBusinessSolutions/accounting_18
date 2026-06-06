/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class PricingPower extends Component {
    static template = "mn_finance_insights.PricingPower";
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
        try { this.state.data = await this.orm.call("finance.pricing.power", "get_pricing_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    powerClass(p) { return p >= 90 ? "heat-good" : (p >= 70 ? "heat-ok" : "heat-bad"); }
    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const c = this.rootRef.el.querySelector("canvas[data-chart='pp']");
        if (!c) return;
        const d = this.state.data;
        this.chart = new window.Chart(c, {
            type: "line",
            data: { labels: d.labels,
                datasets: [{ label: "Discount %", data: d.disc_pct, borderColor: "#f59e0b",
                    backgroundColor: "rgba(245,158,11,0.15)", fill: true, tension: 0.35, pointRadius: 4, borderWidth: 3 }] },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(0,0,0,0.05)" }, beginAtZero: true } } },
        });
    }
}
registry.category("actions").add("mn_finance_insights.pricing_power", PricingPower);
