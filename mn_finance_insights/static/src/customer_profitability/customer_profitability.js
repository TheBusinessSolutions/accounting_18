/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CustomerProfitability extends Component {
    static template = "mn_finance_insights.CustomerProfitability";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, data: null, search: "",
            options: {
                date_from: `${new Date().getFullYear()}-01-01`,
                date_to: new Date().toISOString().slice(0, 10),
            },
        });
        onMounted(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.customer.profitability", "get_profit_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load customer profitability."), { type: "danger" });
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
    marginClass(m) { return m >= 20 ? "heat-good" : (m >= 5 ? "heat-ok" : "heat-bad"); }
}

registry.category("actions").add("mn_finance_insights.customer_profitability", CustomerProfitability);
