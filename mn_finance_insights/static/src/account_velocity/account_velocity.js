/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AccountVelocity extends Component {
    static template = "mn_finance_insights.AccountVelocity";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, options: { as_of: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.account.velocity", "get_velocity_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
}
registry.category("actions").add("mn_finance_insights.account_velocity", AccountVelocity);
