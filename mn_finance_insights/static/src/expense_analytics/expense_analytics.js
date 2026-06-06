/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class ExpenseAnalytics extends Component {
    static template = "mn_finance_insights.ExpenseAnalytics";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.charts = {};
        this.state = useState({
            loading: true, data: null,
            options: {
                date_from: `${new Date().getFullYear()}-01-01`,
                date_to: new Date().toISOString().slice(0, 10),
            },
        });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderCharts(); });
        onWillUnmount(() => Object.values(this.charts).forEach((c) => c && c.destroy()));
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.expense.analytics", "get_expense_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load expense analytics."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(field, ev) { this.state.options[field] = ev.target.value; this.load(); }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }

    renderCharts() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        Object.values(this.charts).forEach((c) => c && c.destroy());
        this.charts = {};
        const d = this.state.data;
        const trend = this.rootRef.el.querySelector("canvas[data-chart='trend']");
        if (trend && d.monthly_trend) {
            this.charts.trend = new window.Chart(trend, {
                type: "bar",
                data: { labels: d.monthly_trend.labels,
                        datasets: [{ data: d.monthly_trend.values, backgroundColor: "#ef4444", borderRadius: 6 }] },
                options: { responsive: true, maintainAspectRatio: false,
                           plugins: { legend: { display: false } },
                           scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
            });
        }
        const cats = this.rootRef.el.querySelector("canvas[data-chart='accounts']");
        if (cats && d.by_account) {
            this.charts.cats = new window.Chart(cats, {
                type: "doughnut",
                data: { labels: d.by_account.map((a) => a.name),
                        datasets: [{ data: d.by_account.map((a) => a.amount),
                                     backgroundColor: ["#ef4444","#f97316","#f59e0b","#eab308","#84cc16","#10b981","#14b8a6","#06b6d4","#3b82f6","#8b5cf6"],
                                     borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: "60%",
                           plugins: { legend: { position: "right" } } },
            });
        }
    }
}

registry.category("actions").add("mn_finance_insights.expense_analytics", ExpenseAnalytics);
