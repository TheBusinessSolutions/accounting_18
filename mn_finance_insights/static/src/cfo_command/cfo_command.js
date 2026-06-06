/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CFOCommand extends Component {
    static template = "mn_finance_insights.CFOCommand";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, options: { as_of: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.cfo.command", "get_command_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); console.error(e); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    formatPct(v) { return v === null || v === undefined ? "—" : `${v.toFixed(1)}%`; }
}
registry.category("actions").add("mn_finance_insights.cfo_command", CFOCommand);
