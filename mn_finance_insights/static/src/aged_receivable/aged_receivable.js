/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { download } from "@web/core/network/download";
import { formatMonetary } from "@web/views/fields/formatters";

export class AgedReceivable extends Component {
    static template = "mn_finance_insights.AgedReceivable";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            data: null,
            search: "",
            options: { as_of: new Date().toISOString().slice(0, 10) },
        });
        onMounted(() => this.load());
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.aged.receivable", "get_aged_data", [
                this.state.options,
            ]);
        } catch (e) {
            this.notification.add(_t("Failed to load aged receivable."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    onFilterChange(field, ev) {
        this.state.options[field] = ev.target.value;
        this.load();
    }

    onSearch(ev) { this.state.search = (ev.target.value || "").toLowerCase(); }

    get filteredRows() {
        if (!this.state.data) return [];
        const q = this.state.search;
        if (!q) return this.state.data.rows;
        return this.state.data.rows.filter((r) => r.partner_name.toLowerCase().includes(q));
    }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }

    async onDrillDown(partnerId) {
        const a = await this.orm.call("finance.aged.receivable", "action_partner_drilldown", [partnerId]);
        if (a) this.action.doAction(a);
    }
    async onSendStatement(partnerId) {
        const a = await this.orm.call("finance.aged.receivable", "action_send_statement", [partnerId]);
        if (a) this.action.doAction(a);
    }
    async onExport() {
        await download({
            url: "/mn_finance_insights/aged_receivable/xlsx",
            data: { options: JSON.stringify(this.state.options) },
        });
    }
}

registry.category("actions").add("mn_finance_insights.aged_receivable", AgedReceivable);
