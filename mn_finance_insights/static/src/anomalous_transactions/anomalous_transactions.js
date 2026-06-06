/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class AnomalousTransactions extends Component {
    static template = "mn_finance_insights.AnomalousTransactions";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null,
            options: { date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toISOString().slice(0,10), z_threshold: 2.5 } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.anomalous.transactions", "get_anomaly_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) {
        let v = ev.target.value;
        if (f === "z_threshold") v = parseFloat(v);
        this.state.options[f] = v;
        this.load();
    }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
}
registry.category("actions").add("mn_finance_insights.anomalous_transactions", AnomalousTransactions);
