/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CustomerRisk extends Component {
    static template = "mn_finance_insights.CustomerRisk";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, data: null, search: "",
            options: { as_of: new Date().toISOString().slice(0, 10) },
        });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.customer.risk", "get_risk_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load customer risk."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    onSearch(ev) { this.state.search = (ev.target.value || "").toLowerCase(); }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    get rows() {
        if (!this.state.data) return [];
        const q = this.state.search;
        return q ? this.state.data.rows.filter((r) => r.name.toLowerCase().includes(q)) : this.state.data.rows;
    }
}

registry.category("actions").add("mn_finance_insights.customer_risk", CustomerRisk);
