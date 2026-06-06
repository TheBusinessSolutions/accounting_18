/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";
export class CrossSell extends Component {
    static template = "mn_finance_insights.CrossSell";
    static props = { "*": true };
    setup() {
        this.orm = useService("orm"); this.notification = useService("notification");
        this.state = useState({ loading: true, data: null,
            options: { date_from: `${new Date().getFullYear()}-01-01`, date_to: new Date().toISOString().slice(0,10) } });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try { this.state.data = await this.orm.call("finance.cross.sell", "get_matrix_data", [this.state.options]); }
        catch (e) { this.notification.add(_t("Failed."), { type: "danger" }); }
        finally { this.state.loading = false; }
    }
    onFilterChange(f, ev) { this.state.options[f] = ev.target.value; this.load(); }
    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c || !v) return v === 0 ? "" : v;
        try { return formatMonetary(v, { currencyId: c.id }); } catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    maxVal() {
        if (!this.state.data) return 0;
        let m = 0;
        for (const r of this.state.data.rows) for (const v of r.cells) if (v > m) m = v;
        return m;
    }
    heat(v, max) {
        if (!v || !max) return "";
        const p = v / max;
        if (p > 0.66) return "heat-good";
        if (p > 0.33) return "heat-ok";
        return "heat-bad";
    }
}
registry.category("actions").add("mn_finance_insights.cross_sell", CrossSell);
