/** @odoo-module **/
/**
 * Cash Flow Forecast - forward projection with best/expected/worst scenarios.
 */
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { formatMonetary } from "@web/views/fields/formatters";

export class CashFlowForecast extends Component {
    static template = "mn_finance_insights.CashFlowForecast";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.chartRef = useRef("cfChart");
        this.chart = null;

        this.state = useState({
            loading: true,
            data: null,
            options: {
                date_from: new Date().toISOString().slice(0, 10),
                horizon: "13",
            },
            scenario: "expected",
        });

        onMounted(() => this.load());
        onPatched(() => {
            if (this.state.data && !this.state.loading) this.renderChart();
        });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("cash.flow.forecast", "get_forecast_data", [
                this.state.options,
            ]);
            // Chart rendered from onPatched once canvas is live.
        } catch (e) {
            this.notification.add(_t("Failed to load cash flow forecast."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    onFilterChange(field, ev) {
        this.state.options[field] = ev.target.value;
        this.load();
    }
    onScenario(name) {
        this.state.scenario = name;
        this.renderChart();
    }

    async onExport() {
        await download({
            url: "/mn_finance_insights/cash_flow/xlsx",
            data: { options: JSON.stringify(this.state.options) },
        });
    }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }

    renderChart() {
        if (typeof window.Chart === "undefined" || !this.state.data) return;
        if (this.chart) this.chart.destroy();
        const rows = this.state.data.scenarios[this.state.scenario];
        const labels = rows.map((r) => `W${r.week}`);
        const cumulative = rows.map((r) => r.cumulative);
        const inflow = rows.map((r) => r.inflow);
        const outflow = rows.map((r) => -r.outflow);

        this.chart = new window.Chart(this.chartRef.el, {
            type: "bar",
            data: {
                labels,
                datasets: [
                    { type: "bar", label: _t("Inflow"), data: inflow, backgroundColor: "#10b981", borderRadius: 6, stack: "flow" },
                    { type: "bar", label: _t("Outflow"), data: outflow, backgroundColor: "#ef4444", borderRadius: 6, stack: "flow" },
                    { type: "line", label: _t("Cumulative cash"), data: cumulative, borderColor: "#6366f1", backgroundColor: "rgba(99,102,241,0.12)", fill: true, tension: 0.35, pointRadius: 3, yAxisID: "y1" },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { position: "bottom" } },
                scales: {
                    y: { stacked: true, grid: { color: "rgba(0,0,0,0.05)" }, title: { display: true, text: _t("Weekly flow") } },
                    y1: { position: "right", grid: { display: false }, title: { display: true, text: _t("Cumulative") } },
                    x: { grid: { display: false } },
                },
            },
        });
    }
}

registry.category("actions").add("mn_finance_insights.cash_flow", CashFlowForecast);
