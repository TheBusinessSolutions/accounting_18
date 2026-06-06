/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class CreditNotesAudit extends Component {
    static template = "mn_finance_insights.CreditNotesAudit";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({ loading: true, data: null,
            options: { date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.credit.notes.audit", "get_credit_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    openMove(id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "account.move", res_id: id, views: [[false, "form"]] });
    }
}
registry.category("actions").add("mn_finance_insights.credit_notes_audit", CreditNotesAudit);
