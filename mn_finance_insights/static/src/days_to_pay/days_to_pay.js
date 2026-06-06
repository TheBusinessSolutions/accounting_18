/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class DaysToPay extends Component {
    static template = "mn_finance_insights.DaysToPay";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, search: "",
            options: { date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.days.to.pay", "get_dtp_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    onSearch(ev) { this.state.search = (ev.target.value || "").toLowerCase(); }
    get rows() {
        if (!this.state.data) return [];
        const q = this.state.search;
        return q ? this.state.data.rows.filter((r) => r.name.toLowerCase().includes(q)) : this.state.data.rows;
    }
    deltaClass(d) { return d <= 0 ? "heat-good" : (d <= 15 ? "heat-ok" : "heat-bad"); }
}
registry.category("actions").add("mn_finance_insights.days_to_pay", DaysToPay);
