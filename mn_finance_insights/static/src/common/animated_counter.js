/** @odoo-module **/
/**
 * AnimatedCounter — counts a number up from 0 (or previous value) over `duration` ms.
 * Use anywhere a static KPI used to live.
 */
import { Component, onMounted, onWillUpdateProps, useState } from "@odoo/owl";

export class AnimatedCounter extends Component {
    static template = "mn_finance_insights.AnimatedCounter";
    static props = {
        value:    { type: Number },
        format:   { type: Function, optional: true },  // (n) => string
        duration: { type: Number, optional: true },
        prefix:   { type: String, optional: true },
        suffix:   { type: String, optional: true },
    };
    static defaultProps = { duration: 700, prefix: "", suffix: "" };

    setup() {
        this.state = useState({ display: this.props.value });
        this._from = 0;
        onMounted(() => this._animate(0, this.props.value));
        onWillUpdateProps((next) => this._animate(this.props.value, next.value));
    }

    _animate(from, to) {
        if (from === to) { this.state.display = to; return; }
        const start = performance.now();
        const dur = this.props.duration;
        const step = (now) => {
            const t = Math.min(1, (now - start) / dur);
            // ease-out cubic
            const eased = 1 - Math.pow(1 - t, 3);
            this.state.display = from + (to - from) * eased;
            if (t < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    }

    get formatted() {
        const fmt = this.props.format || ((n) => Math.round(n).toLocaleString());
        return `${this.props.prefix}${fmt(this.state.display)}${this.props.suffix}`;
    }
}
