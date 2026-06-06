/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CashPosition extends Component {
    static template = "mn_finance_insights.CashPosition";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.chart = null;
        const today = new Date();
        const start = new Date(today); start.setMonth(start.getMonth() - 3);
        this.state = useState({
            loading: true, data: null,
            options: {
                date_from: start.toISOString().slice(0, 10),
                date_to: today.toISOString().slice(0, 10),
            },
        });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.cash.position", "get_cash_position_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load cash position."), { type: "danger" });
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

    renderChart() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        if (this.chart) this.chart.destroy();
        const canvas = this.rootRef.el.querySelector("canvas[data-chart='timeline']");
        if (!canvas) return;
        const d = this.state.data;
        const colors = ["#6366f1","#10b981","#f59e0b","#ef4444","#3b82f6","#8b5cf6","#14b8a6","#ec4899"];
        const datasets = d.per_account.map((acc, i) => ({
            label: acc.name,
            data: acc.values,
            backgroundColor: colors[i % colors.length] + "55",
            borderColor: colors[i % colors.length],
            fill: true,
            tension: 0.3,
            pointRadius: 0,
            borderWidth: 2,
        }));
        this.chart = new window.Chart(canvas, {
            type: "line",
            data: { labels: d.labels, datasets },
            options: {
                responsive: true, maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                plugins: { legend: { position: "bottom" } },
                scales: {
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 12 } },
                    y: { stacked: true, grid: { color: "rgba(0,0,0,0.05)" } },
                },
            },
        });
    }
}

registry.category("actions").add("mn_finance_insights.cash_position", CashPosition);
