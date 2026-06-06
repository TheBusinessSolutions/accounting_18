/** @odoo-module **/
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class FinancialRatios extends Component {
    static template = "mn_finance_insights.FinancialRatios";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("ratiosRoot");
        this.chartInstances = {};

        this.state = useState({
            loading: true,
            data: null,
            options: { as_of: new Date().toISOString().slice(0, 10) },
        });

        onMounted(() => this.load());
        onPatched(() => this.renderSparklines());
        onWillUnmount(() => this.destroyCharts());
    }

    destroyCharts() {
        Object.values(this.chartInstances).forEach((c) => c && c.destroy && c.destroy());
        this.chartInstances = {};
    }

    async load() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call("financial.ratios", "get_ratios_data", [
                this.state.options,
            ]);
        } catch (e) {
            this.notification.add(_t("Failed to load ratios."), { type: "danger" });
            console.error(e);
        } finally {
            this.state.loading = false;
        }
    }

    onFilterChange(field, ev) {
        this.state.options[field] = ev.target.value;
        this.load();
    }

    get ratiosByGroup() {
        if (!this.state.data) return {};
        const groups = { liquidity: [], profitability: [], efficiency: [] };
        for (const [key, r] of Object.entries(this.state.data.ratios)) {
            groups[r.group].push({ key, ...r });
        }
        return groups;
    }

    formatValue(r) {
        if (r.unit === "%") return `${r.value.toFixed(1)}%`;
        if (r.unit === "x") return `${r.value.toFixed(2)}×`;
        return `${r.value.toFixed(1)} ${r.unit}`;
    }

    renderSparklines() {
        if (typeof window.Chart === "undefined" || !this.state.data || !this.rootRef.el) return;
        this.destroyCharts();
        const labels = this.state.data.sparkline_labels;
        for (const [key, points] of Object.entries(this.state.data.sparklines)) {
            const canvas = this.rootRef.el.querySelector(`canvas[data-spark="${key}"]`);
            if (!canvas) continue;
            const health = this.state.data.ratios[key].health;
            const color = { good: "#10b981", ok: "#f59e0b", bad: "#ef4444" }[health];
            this.chartInstances[key] = new window.Chart(canvas, {
                type: "line",
                data: {
                    labels,
                    datasets: [{
                        data: points,
                        borderColor: color,
                        backgroundColor: color + "22",
                        fill: true,
                        tension: 0.35,
                        pointRadius: 0,
                        borderWidth: 2,
                    }],
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false }, tooltip: { enabled: true } },
                    scales: { x: { display: false }, y: { display: false } },
                },
            });
        }
    }
}

registry.category("actions").add("mn_finance_insights.ratios", FinancialRatios);
