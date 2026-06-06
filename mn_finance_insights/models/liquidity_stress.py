# -*- coding: utf-8 -*-
"""Liquidity Stress Test — what-if scenarios."""
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class LiquidityStress(models.AbstractModel):
    _name = "finance.liquidity.stress"
    _description = "Liquidity Stress Test"

    @api.model
    def get_stress_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        horizon_weeks = int(options.get("horizon") or 13)
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # opening cash
        cash_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "asset_cash"),
            ("date", "<=", fields.Date.to_string(as_of))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        d, c = (cash_rows[0] if cash_rows else (0, 0))
        opening = (d or 0) - (c or 0)

        # Open AR / AP lines by maturity bucket
        ar_lines = AML.search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False), ("amount_residual", "!=", 0)],
            fields=["amount_residual", "date_maturity"])
        ap_lines = AML.search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False), ("amount_residual", "!=", 0)],
            fields=["amount_residual", "date_maturity"])

        # Build scenarios
        scenarios = {
            "base":          {"ar_delay_days": 0,  "ap_accel_days": 0,  "ar_default_pct": 0},
            "mild_stress":   {"ar_delay_days": 15, "ap_accel_days": 0,  "ar_default_pct": 2},
            "severe_stress": {"ar_delay_days": 45, "ap_accel_days": 15, "ar_default_pct": 8},
        }
        out_scenarios = {}
        for name, p in scenarios.items():
            buckets = [0.0] * horizon_weeks
            for ln in ar_lines:
                due = ln["date_maturity"] or as_of
                due_shifted = due + timedelta(days=p["ar_delay_days"])
                week = (due_shifted - as_of).days // 7
                if week < 0 or week >= horizon_weeks:
                    continue
                buckets[week] += ln["amount_residual"] * (1 - p["ar_default_pct"] / 100.0)
            for ln in ap_lines:
                due = ln["date_maturity"] or as_of
                due_shifted = due - timedelta(days=p["ap_accel_days"])
                week = (due_shifted - as_of).days // 7
                if week < 0 or week >= horizon_weeks:
                    continue
                buckets[week] -= -ln["amount_residual"]  # AP residual is negative
            running = opening
            weeks = []
            min_cash = opening
            for w in range(horizon_weeks):
                running += buckets[w]
                min_cash = min(min_cash, running)
                weeks.append({"week": w + 1,
                              "net": float_round(buckets[w], 2),
                              "cumulative": float_round(running, 2)})
            out_scenarios[name] = {"weeks": weeks, "min_cash": float_round(min_cash, 2)}

        currency = self.env.company.currency_id
        return {
            "options": options,
            "horizon": horizon_weeks,
            "opening": float_round(opening, 2),
            "scenarios": out_scenarios,
            "labels": [f"W{i+1}" for i in range(horizon_weeks)],
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "horizon": int(options.get("horizon") or 13),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
