/** @odoo-module **/
import { Component, onMounted, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { formatMonetary } from "@web/views/fields/formatters";

export class ProductProfitability extends Component {
    static template = "mn_finance_insights.ProductProfitability";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true, data: null, search: "", showAlertsOnly: false,
            options: { as_of: new Date().toISOString().slice(0, 10), erosion_threshold: 5 },
        });
        onMounted(() => this.load());
    }
    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("finance.product.profitability", "get_product_data", [this.state.options]);
        } catch (e) {
            this.notification.add(_t("Failed to load product profitability."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }
    onFilterChange(f, ev) {
        let val = ev.target.value;
        if (f === "erosion_threshold") val = parseFloat(val);
        this.state.options[f] = val;
        this.load();
    }
    onSearch(ev) { this.state.search = (ev.target.value || "").toLowerCase(); }
    onToggleAlerts() { this.state.showAlertsOnly = !this.state.showAlertsOnly; }

    formatAmount(v) {
        const c = this.state.data && this.state.data.currency;
        if (!c) return v;
        try { return formatMonetary(v, { currencyId: c.id }); }
        catch (_e) { return `${c.symbol} ${Number(v).toLocaleString()}`; }
    }
    get rows() {
        if (!this.state.data) return [];
        let r = this.state.data.rows;
        if (this.state.showAlertsOnly) r = r.filter((x) => x.alert);
        const q = this.state.search;
        if (q) r = r.filter((x) => x.name.toLowerCase().includes(q));
        return r;
    }
    marginClass(m) {
        if (m === null || m === undefined) return "";
        return m >= 30 ? "heat-good" : (m >= 10 ? "heat-ok" : "heat-bad");
    }
    sparklinePath(series) {
        // Tiny inline SVG sparkline from values (nulls allowed)
        const valid = series.filter((v) => v !== null && v !== undefined);
        if (valid.length < 2) return "";
        const min = Math.min(...valid), max = Math.max(...valid);
        const range = max - min || 1;
        const w = 110, h = 24;
        const step = w / (series.length - 1);
        const points = series.map((v, i) => {
            if (v === null || v === undefined) return null;
            const x = i * step;
            const y = h - ((v - min) / range) * h;
            return `${x.toFixed(1)},${y.toFixed(1)}`;
        }).filter(Boolean);
        return "M" + points.join(" L");
    }
}

registry.category("actions").add("mn_finance_insights.product_profitability", ProductProfitability);
