/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class AgingCombined extends Component {
    static template = "mn_finance_insights.AgingCombined";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.chart = null;
        this.state = useState({ loading: true, data: null, options: { as_of: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
        onPatched(() => { if (this.state.data && !this.state.loading) this.renderChart(); });
        onWillUnmount(() => this.chart && this.chart.destroy());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.aging.combined", "get_aging_data", [this.state.options]); }
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
        const c = this.rootRef.el.querySelector("canvas[data-chart='aging']");
        if (!c) return;
        const d = this.state.data;
        this.chart = new window.Chart(c, {
            type: "bar",
            data: {
                labels: d.labels,
                datasets: [
                    { label: "AR", data: d.ar_buckets, backgroundColor: "#f59e0b", borderRadius: 6 },
                    { label: "AP", data: d.ap_buckets, backgroundColor: "#f97316", borderRadius: 6 },
                ],
            },
            options: { responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: "bottom" } },
                scales: { x: { grid: { display: false } }, y: { grid: { color: "rgba(0,0,0,0.05)" } } } },
        });
    }
}
registry.category("actions").add("mn_finance_insights.aging_combined", AgingCombined);
