/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class PaymentMethodMix extends Component {
    static template = "mn_finance_insights.PaymentMethodMix";
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
        try { this.state.data = await this.orm.call("finance.payment.method.mix", "get_mix_data", [this.state.options]); }
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
        const palette = ["#10b981","#3b82f6","#6366f1","#8b5cf6","#ec4899","#f59e0b","#f97316","#ef4444","#14b8a6","#06b6d4"];
        for (const key of ["inbound", "outbound"]) {
            const c = this.rootRef.el.querySelector(`canvas[data-chart='${key}']`);
            const rows = this.state.data[key];
            if (!c || !rows.length) continue;
            this.charts[key] = new window.Chart(c, {
                type: "doughnut",
                data: { labels: rows.map((r) => r.name),
                    datasets: [{ data: rows.map((r) => r.amount), backgroundColor: palette, borderWidth: 0 }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: "60%",
                    plugins: { legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } } } },
            });
        }
    }
}
registry.category("actions").add("mn_finance_insights.payment_method_mix", PaymentMethodMix);
