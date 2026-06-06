/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class IncomeExpenseDonut extends Component {
    static template = "mn_finance_insights.IncomeExpenseDonut";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.rootRef = useRef("root"); this.charts = {};
        this.state = useState({ loading: true, data: null,
            options: { date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderCharts(); });
        onWillUnmount(() => Object.values(this.charts).forEach((c) => c && c.destroy()));
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.income.expense.donut", "get_donut_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    renderCharts() {
        if (typeof window.Chart === "undefined" || !this.rootRef.el) return;
        Object.values(this.charts).forEach((c) => c && c.destroy());
        this.charts = {};
        const greens = ["#10b981","#14b8a6","#06b6d4","#3b82f6","#6366f1","#8b5cf6","#a855f7","#d946ef","#84cc16","#22c55e"];
        const reds   = ["#ef4444","#f97316","#f59e0b","#eab308","#ec4899","#f43f5e","#dc2626","#ea580c","#d97706","#ca8a04"];
        for (const [key, color] of [["income", greens], ["expense", reds]]) {
            const c = this.rootRef.el.querySelector(`canvas[data-chart='${key}']`);
            const rows = this.state.data[key];
            if (!c || !rows.length) continue;
            this.charts[key] = new window.Chart(c, {
                type: "doughnut",
                data: { labels: rows.map((r) => r.name),
                    datasets: [{ data: rows.map((r) => r.amount), backgroundColor: color, borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: "60%",
                    plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } } },
            });
        }
    }
}
registry.category("actions").add("mn_finance_insights.income_expense_donut", IncomeExpenseDonut);
