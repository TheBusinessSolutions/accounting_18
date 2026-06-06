/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class JournalAudit extends Component {
    static template = "mn_finance_insights.JournalAudit";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null, anomaliesOnly: false, options: { days: 14 } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.journal.audit", "get_audit_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = parseInt(ev.target.value, 10); this.load(); }
    onToggle() { this.state.anomaliesOnly = !this.state.anomaliesOnly; }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    get rows() {
        if (!this.state.data) return [];
        return this.state.anomaliesOnly ? this.state.data.rows.filter((r) => r.anomaly.length) : this.state.data.rows;
    }
}
registry.category("actions").add("mn_finance_insights.journal_audit", JournalAudit);
