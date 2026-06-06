/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CustomerLTV extends Component {
    static template = "mn_finance_insights.CustomerLTV";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, search: "", options: {} });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.customer.ltv", "get_ltv_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onSearch(ev) { this.state.search = (ev.target.value || "").toLowerCase(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    get rows() {
        if (!this.state.data) return [];
        const q = this.state.search;
        return q ? this.state.data.rows.filter((r) => r.name.toLowerCase().includes(q)) : this.state.data.rows;
    }
}
registry.category("actions").add("mn_finance_insights.customer_ltv", CustomerLTV);
