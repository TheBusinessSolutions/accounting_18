# -*- coding: utf-8 -*-
"""Cash Conversion Efficiency — operating cash flow / net income ratio."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class CashEfficiency(models.AbstractModel):
    _name = "finance.cash.efficiency"
    _description = "Cash Conversion Efficiency"

    @api.model
    def get_efficiency_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def cash_change(df, dt):
            d = self._balance(["asset_cash"], dt, company_ids) - self._balance(["asset_cash"], df - timedelta(days=1), company_ids)
            return d

        def net_income(df, dt):
            rev = self._flow(["income", "income_other"], df, dt, company_ids, True)
            exp = self._flow(["expense", "expense_depreciation", "expense_direct_cost"], df, dt, company_ids, False)
            return rev - exp

        labels, cash_v, ni_v, ratio_v = [], [], [], []
        cursor = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        for _ in range(12):
            end = cursor + relativedelta(months=1) - timedelta(days=1)
            c = cash_change(cursor, end)
            n = net_income(cursor, end)
            r = (c / n) if n else 0
            cash_v.append(float_round(c, 2))
            ni_v.append(float_round(n, 2))
            ratio_v.append(float_round(r, 2))
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)

        avg_ratio = (sum(ratio_v) / len(ratio_v)) if ratio_v else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels, "cash_change": cash_v, "net_income": ni_v, "ratio": ratio_v,
                "avg_ratio": float_round(avg_ratio, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}

    @api.model
    def _balance(self, types, as_of, company_ids):
        r = self.env["account.move.line"]._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "in", types),
            ("date", "<=", fields.Date.to_string(as_of))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        if not r: return 0.0
        d, c = r[0]; return (d or 0) - (c or 0)

    @api.model
    def _flow(self, types, df, dt, company_ids, is_income):
        r = self.env["account.move.line"]._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "in", types),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        if not r: return 0.0
        d, c = r[0]; return ((c or 0) - (d or 0)) if is_income else ((d or 0) - (c or 0))
