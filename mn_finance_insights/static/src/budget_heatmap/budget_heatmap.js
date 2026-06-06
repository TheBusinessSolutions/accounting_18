/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class BudgetHeatmap extends Component {
    static template = "mn_finance_insights.BudgetHeatmap";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, data: null,
            options: { year: new Date().getFullYear() },
        });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.budget.heatmap", "get_budget_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load budget heatmap."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(f, ev) { this.state.options[f] = parseInt(ev.target.value, 10); this.load(); }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    cellClass(v, isIncome) {
        if (v === null || v === undefined) return "";
        // For income: positive variance is good. For expense: negative variance is good.
        const ok = isIncome ? v >= 0 : v <= 0;
        const mag = Math.abs(v);
        if (mag < 5)  return "heat-good";
        if (mag < 15) return ok ? "heat-good" : "heat-ok";
        return ok ? "heat-ok" : "heat-bad";
    }
    cellFmt(v) {
        if (v === null || v === undefined) return "—";
        const sign = v >= 0 ? "+" : "";
        return `${sign}${v.toFixed(1)}%`;
    }
}

registry.category("actions").add("mn_finance_insights.budget_heatmap", BudgetHeatmap);
