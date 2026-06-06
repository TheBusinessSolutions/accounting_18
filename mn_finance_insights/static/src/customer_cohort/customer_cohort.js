/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CustomerCohort extends Component {
    static template = "mn_finance_insights.CustomerCohort";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, options: { as_of: new Date().toISOString().slice(0,10), months: 12 } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.customer.cohort", "get_cohort_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c || !v) return v === 0 ? "—" : v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    heat(v, max) {
        if (!v || !max) return "";
        const pct = v / max;
        if (pct > 0.66) return "heat-good";
        if (pct > 0.33) return "heat-ok";
        return "heat-bad";
    }
    maxVal() {
        if (!this.state.data) return 0;
        let m = 0;
        for (const row of this.state.data.rows) for (const v of row.values) if (v > m) m = v;
        return m;
    }
}
registry.category("actions").add("mn_finance_insights.customer_cohort", CustomerCohort);
