# -*- coding: utf-8 -*-
"""CFO Command Center — single-screen exec overview."""
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class CFOCommand(models.AbstractModel):
    _name = "finance.cfo.command"
    _description = "CFO Command Center"

    @api.model
    def get_command_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        ytd_start = date(as_of.year, 1, 1)

        AML = self.env["account.move.line"]

        def _flow(types, df, dt, is_income):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return (c-d) if is_income else (d-c)

        def _bal(types, dt, signed=True):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return (d-c) if signed else (c-d)

        revenue = _flow(["income","income_other"], ytd_start, as_of, True)
        expenses = _flow(["expense","expense_depreciation","expense_direct_cost"], ytd_start, as_of, False)
        cogs = _flow(["expense_direct_cost"], ytd_start, as_of, False)
        net = revenue - expenses
        cash = _bal(["asset_cash"], as_of)
        ar = _bal(["asset_receivable"], as_of)
        ap = -_bal(["liability_payable"], as_of)
        gm = ((revenue - cogs) / revenue * 100) if revenue else 0
        nm = (net / revenue * 100) if revenue else 0

        # last-month deltas
        last_eom = date(as_of.year, as_of.month, 1) - relativedelta(days=1)
        last_start = date(last_eom.year, 1, 1)
        prev_rev = _flow(["income","income_other"], last_start, last_eom, True)
        prev_exp = _flow(["expense","expense_depreciation","expense_direct_cost"], last_start, last_eom, False)
        prev_net = prev_rev - prev_exp

        # risk count
        risk_count = self._high_risk_count(as_of, company_ids)
        currency = self.env.company.currency_id

        def pct_delta(cur, prev):
            return None if not prev else round((cur - prev) / abs(prev) * 100, 1)

        return {
            "options": options,
            "kpis": {
                "revenue": float_round(revenue, 2),
                "expenses": float_round(expenses, 2),
                "net_profit": float_round(net, 2),
                "cash": float_round(cash, 2),
                "ar": float_round(ar, 2),
                "ap": float_round(ap, 2),
                "gross_margin_pct": float_round(gm, 1),
                "net_margin_pct": float_round(nm, 1),
                "high_risk_customers": risk_count,
                "revenue_delta": pct_delta(revenue, prev_rev),
                "net_delta": pct_delta(net, prev_net),
            },
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}

    @api.model
    def _high_risk_count(self, as_of, company_ids):
        # Use customer.risk model
        try:
            data = self.env["finance.customer.risk"].get_risk_data({
                "as_of": as_of.isoformat(), "company_ids": company_ids,
            })
            return data["summary"]["high_risk"]
        except Exception:
            return 0
