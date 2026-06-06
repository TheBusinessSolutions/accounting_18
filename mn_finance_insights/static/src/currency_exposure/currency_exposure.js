/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class CurrencyExposure extends Component {
    static template = "mn_finance_insights.CurrencyExposure";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, options: {} });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.currency.exposure", "get_exposure_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    fmt(v, sym) { return `${sym || ""} ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`; }
}
registry.category("actions").add("mn_finance_insights.currency_exposure", CurrencyExposure);
