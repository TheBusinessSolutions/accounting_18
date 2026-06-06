/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class SalesAnalytics extends Component {
    static template = "mn_finance_insights.SalesAnalytics";
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
            this.state.data = await this.orm.call("finance.sales.analytics", "get_sales_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load sales analytics."), { type: "danger" });
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
        const trendCanvas = this.rootRef.el.querySelector("canvas[data-chart='trend']");
        if (trendCanvas && d.monthly_trend) {
            this.charts.trend = new window.Chart(trendCanvas, {
                type: "line",
                data: { labels: d.monthly_trend.labels,
                        datasets: [{ data: d.monthly_trend.values, borderColor: "#10b981",
                                     backgroundColor: "rgba(16,185,129,0.12)", fill: true,
                                     tension: 0.35, pointRadius: 3 }] },
                options: { responsive: true, maintainAspectRatio: false,
                           plugins: { legend: { display: false } },
                           scales: { x: { grid: { display: false } }, y: { beginAtZero: true } } },
            });
        }
        const prodCanvas = this.rootRef.el.querySelector("canvas[data-chart='products']");
        if (prodCanvas && d.top_products) {
            this.charts.products = new window.Chart(prodCanvas, {
                type: "bar",
                data: { labels: d.top_products.map((p) => p.name),
                        datasets: [{ data: d.top_products.map((p) => p.amount), backgroundColor: "#6366f1", borderRadius: 6 }] },
                options: { indexAxis: "y", responsive: true, maintainAspectRatio: false,
                           plugins: { legend: { display: false } },
                           scales: { y: { grid: { display: false } } } },
            });
        }
    }
}

registry.category("actions").add("mn_finance_insights.sales_analytics", SalesAnalytics);
