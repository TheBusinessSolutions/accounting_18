/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class BurnRate extends Component {
    static template = "mn_finance_insights.BurnRate";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.chart = null;
        this.state = useState({
            loading: true, data: null,
            options: { as_of: new Date().toISOString().slice(0, 10), months: 12 },
        });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.burn.rate", "get_burn_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load burn rate."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    formatRunway(r) { return r === null || r === undefined ? "∞" : `${r} mo`; }
    runwayClass(r) {
        if (r === null || r === undefined) return "heat-good";
        if (r >= 18) return "heat-good";
        if (r >= 6)  return "heat-ok";
        return "heat-bad";
    }
    runwayWidth(r) {
        if (r === null || r === undefined) return 100;
        return Math.min(100, (r / 24) * 100);
    }

    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const canvas = this.rootRef.el.querySelector("canvas[data-chart='burn']");
        if (!canvas) return;
        const d = this.state.data;
        this.chart = new window.Chart(canvas, {
            type: "bar",
            data: {
                labels: d.labels,
                datasets: [
                    { type: "bar", label: _t("Net cash change"),
                      data: d.net_changes,
                      backgroundColor: d.net_changes.map((v) => v >= 0 ? "#10b981" : "#ef4444"),
                      borderRadius: 6 },
                    { type: "line", label: _t("Cash balance"),
                      data: d.cash_balances,
                      borderColor: "#6366f1",
                      backgroundColor: "rgba(99,102,241,0.12)",
                      fill: true, tension: 0.35, pointRadius: 3, yAxisID: "y1" },
                ],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { position: "bottom" } },
                scales: {
                    y:  { grid: { color: "rgba(0,0,0,0.05)" }, title: { display: true, text: _t("Monthly net") } },
                    y1: { position: "right", grid: { display: false }, title: { display: true, text: _t("Cash") } },
                    x:  { grid: { display: false } },
                },
            },
        });
    }
}

registry.category("actions").add("mn_finance_insights.burn_rate", BurnRate);
