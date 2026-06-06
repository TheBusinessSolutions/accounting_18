/** @odoo-module **/
/**
 * Executive Finance Dashboard - OWL client action.
 * Renders KPI cards + 4 Chart.js charts. Data comes from
 * `finance.dashboard.get_dashboard_data` in one round-trip.
 */
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class FinanceDashboard extends Component {
    static template = "mn_finance_insights.FinanceDashboard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.chartRefs = {
            revenue_vs_expenses: useRef("chartRevExp"),
            cash_trend: useRef("chartCash"),
            top_customers: useRef("chartCustomers"),
            ar_aging: useRef("chartAging"),
        };
        this.chartInstances = {};

        this.state = useState({
            loading: true,
            data: null,
            options: {
                date_from: this._defaultDateFrom(),
                date_to: this._today(),
                compare: "previous_year",
            },
        });

        onMounted(() => this.loadData());
        onPatched(() => {
            // Re-render charts after the DOM patch so canvas refs are live.
            if (this.state.data && !this.state.loading) this.renderCharts();
        });
        onWillUnmount(() => this.destroyCharts());
    }

    // ----- helpers ----------------------------------------------------
    _today() {
        return new Date().toISOString().slice(0, 10);
    }
    _defaultDateFrom() {
        const d = new Date();
        return `${d.getFullYear()}-01-01`;
    }
    destroyCharts() {
        Object.values(this.chartInstances).forEach((c) => c && c.destroy && c.destroy());
        this.chartInstances = {};
    }

    formatAmount(value) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return value;
        const opts = { currencyId: c.id };
        try {
            return formatMonetary(value, opts);
        } catch (_e) {
            return `${c.symbol} ${Number(value).toLocaleString()}`;
        }
    }
    formatPct(value, digits = 1) {
        if (value === null || value === undefined) return "—";
        return `${Number(value).toFixed(digits)}%`;
    }

    // ----- data -------------------------------------------------------
    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("finance.dashboard", "get_dashboard_data", [
                this.state.options,
            ]);
            this.state.data = data;
            this.state.options = data.options;
            // Charts are drawn from onPatched once the canvases exist.
        } catch (e) {
            this.notification.add(_t("Failed to load dashboard data."), { type: "danger" });
            // eslint-disable-next-line no-console
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    onFilterChange(field, ev) {
        this.state.options[field] = ev.target.value || null;
        this.loadData();
    }

    async onDrillDown(kpi) {
        const drillable = ["revenue", "expenses", "cash", "accounts_receivable", "accounts_payable"];
        if (!drillable.includes(kpi)) return;
        const action = await this.orm.call("finance.dashboard", "action_drilldown", [
            kpi,
            this.state.options,
        ]);
        if (action) this.action.doAction(action);
    }

    // ----- charts -----------------------------------------------------
    renderCharts() {
        if (typeof window.Chart === "undefined") {
            // eslint-disable-next-line no-console
            console.warn("Chart.js not loaded; KPI cards still render.");
            return;
        }
        this.destroyCharts();
        const c = this.state.data.charts;
        const palette = {
            revenue: "#10b981",
            expenses: "#ef4444",
            cash: "#3b82f6",
            accent: "#8b5cf6",
            aging: ["#10b981", "#f59e0b", "#f97316", "#ef4444"],
        };

        this.chartInstances.revenue_vs_expenses = new window.Chart(
            this.chartRefs.revenue_vs_expenses.el,
            {
                type: "bar",
                data: {
                    labels: c.revenue_vs_expenses.labels,
                    datasets: [
                        {
                            label: _t("Revenue"),
                            data: c.revenue_vs_expenses.revenue,
                            backgroundColor: palette.revenue,
                            borderRadius: 6,
                        },
                        {
                            label: _t("Expenses"),
                            data: c.revenue_vs_expenses.expenses,
                            backgroundColor: palette.expenses,
                            borderRadius: 6,
                        },
                    ],
                },
                options: this._barOpts(),
            }
        );

        this.chartInstances.cash_trend = new window.Chart(this.chartRefs.cash_trend.el, {
            type: "line",
            data: {
                labels: c.cash_trend.labels,
                datasets: [
                    {
                        label: _t("Cash"),
                        data: c.cash_trend.balance,
                        borderColor: palette.cash,
                        backgroundColor: "rgba(59,130,246,0.12)",
                        tension: 0.35,
                        fill: true,
                        pointRadius: 3,
                    },
                ],
            },
            options: this._lineOpts(),
        });

        this.chartInstances.top_customers = new window.Chart(this.chartRefs.top_customers.el, {
            type: "doughnut",
            data: {
                labels: c.top_customers.labels,
                datasets: [
                    {
                        data: c.top_customers.values,
                        backgroundColor: ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899"],
                        borderWidth: 0,
                    },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false, cutout: "65%" },
        });

        this.chartInstances.ar_aging = new window.Chart(this.chartRefs.ar_aging.el, {
            type: "bar",
            data: {
                labels: c.ar_aging.labels,
                datasets: [
                    {
                        label: _t("AR Aging"),
                        data: c.ar_aging.values,
                        backgroundColor: palette.aging,
                        borderRadius: 6,
                    },
                ],
            },
            options: this._barOpts({ legend: false }),
        });
    }

    _barOpts({ legend = true } = {}) {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: legend, position: "bottom" } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "rgba(0,0,0,0.05)" }, beginAtZero: true },
            },
        };
    }
    _lineOpts() {
        return {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { display: false } },
                y: { grid: { color: "rgba(0,0,0,0.05)" } },
            },
        };
    }
}

registry.category("actions").add("mn_finance_insights.dashboard", FinanceDashboard);
