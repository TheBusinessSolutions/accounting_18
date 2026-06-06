# -*- coding: utf-8 -*-
"""Cash Flow Forecast — forward projection from open AR / AP.

Scenarios:
  * best     — 100% of inflows, 100% of outflows
  * expected — 90% of inflows, 100% of outflows
  * worst    — 70% of inflows, 110% of outflows
"""
from datetime import date, timedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


SCENARIO_FACTORS = {
    "best":     {"in": 1.00, "out": 1.00},
    "expected": {"in": 0.90, "out": 1.00},
    "worst":    {"in": 0.70, "out": 1.10},
}
HORIZON_WEEKS = {"4": 4, "8": 8, "13": 13, "26": 26}


class CashFlowForecast(models.AbstractModel):
    _name = "cash.flow.forecast"
    _description = "Cash Flow Forecast"

    # ------------------------------------------------------------------
    @api.model
    def get_forecast_data(self, options=None):
        options = self._sanitize(options or {})
        horizon = HORIZON_WEEKS.get(str(options["horizon"]), 13)
        start = fields.Date.from_string(options["date_from"])
        company_ids = options["company_ids"]

        # opening cash balance (signed)
        opening = self._cash_balance(start - timedelta(days=1), company_ids)

        inflows = self._open_amounts("out", start, horizon, company_ids)   # AR -> inflow
        outflows = self._open_amounts("in", start, horizon, company_ids)   # AP -> outflow

        scenarios = {}
        for name, f in SCENARIO_FACTORS.items():
            running = opening
            rows = []
            for w in range(horizon):
                week_start = start + timedelta(weeks=w)
                inflow = round(inflows[w] * f["in"], 2)
                outflow = round(outflows[w] * f["out"], 2)
                net = inflow - outflow
                running += net
                rows.append({
                    "week": w + 1,
                    "date_from": week_start.isoformat(),
                    "date_to": (week_start + timedelta(days=6)).isoformat(),
                    "inflow": inflow,
                    "outflow": outflow,
                    "net": float_round(net, precision_digits=2),
                    "cumulative": float_round(running, precision_digits=2),
                })
            scenarios[name] = rows

        currency = self.env.company.currency_id
        return {
            "options": options,
            "opening_balance": float_round(opening, precision_digits=2),
            "scenarios": scenarios,
            "labels": [r["date_from"] for r in scenarios["expected"]],
            "currency": {
                "id": currency.id,
                "symbol": currency.symbol,
                "decimals": currency.decimal_places,
            },
            "company_name": self.env.company.name,
        }

    # ------------------------------------------------------------------
    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "date_from": options.get("date_from") or today.isoformat(),
            "horizon": str(options.get("horizon") or "13"),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _cash_balance(self, as_of, company_ids):
        AML = self.env["account.move.line"]
        rows = AML._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "=", "asset_cash"),
                ("date", "<=", fields.Date.to_string(as_of)),
            ],
            groupby=[],
            aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        debit, credit = rows[0][0] or 0.0, rows[0][1] or 0.0
        return debit - credit

    @api.model
    def _open_amounts(self, move_kind, start, horizon, company_ids):
        """Sum of unreconciled receivable (out) or payable (in) lines by week.

        Returns a list of length `horizon` of weekly amounts (positive).
        Anything overdue rolls into week 0; anything past horizon is dropped.
        """
        AML = self.env["account.move.line"]
        account_type = "asset_receivable" if move_kind == "out" else "liability_payable"
        end = start + timedelta(weeks=horizon)
        lines = AML.search_read(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "=", account_type),
                ("reconciled", "=", False),
                ("amount_residual", "!=", 0),
            ],
            fields=["date_maturity", "amount_residual"],
        )
        buckets = [0.0] * horizon
        for ln in lines:
            due = ln["date_maturity"] or start
            if due >= end:
                continue
            week = max(0, (due - start).days // 7)
            # For AP (in), amount_residual is negative (credit balance); flip sign.
            amount = ln["amount_residual"] if move_kind == "out" else -ln["amount_residual"]
            buckets[week] += amount
        return buckets
