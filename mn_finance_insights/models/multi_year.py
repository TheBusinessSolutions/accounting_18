# -*- coding: utf-8 -*-
"""Multi-Year Comparison — 3 years of revenue / expense / net profit side-by-side."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class MultiYear(models.AbstractModel):
    _name = "finance.multi.year"
    _description = "Multi-Year Comparison"

    @api.model
    def get_multi_year_data(self, options=None):
        options = self._sanitize(options or {})
        as_of_year = int(options["year"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def flow(types, year, is_income):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", f"{year}-01-01"),
                ("date", "<=", f"{year}-12-31")],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return ((c or 0) - (d or 0)) if is_income else ((d or 0) - (c or 0))

        years = [as_of_year - 2, as_of_year - 1, as_of_year]
        cols = []
        for y in years:
            rev = flow(["income", "income_other"], y, True)
            exp = flow(["expense", "expense_depreciation", "expense_direct_cost"], y, False)
            cogs = flow(["expense_direct_cost"], y, False)
            net = rev - exp
            gm = ((rev - cogs) / rev * 100) if rev else 0
            nm = (net / rev * 100) if rev else 0
            cols.append({"year": y, "revenue": float_round(rev, 2),
                         "expense": float_round(exp, 2), "net": float_round(net, 2),
                         "gm_pct": float_round(gm, 1), "nm_pct": float_round(nm, 1)})

        # YoY deltas
        for i in range(1, len(cols)):
            prev_r = cols[i - 1]["revenue"]
            cols[i]["rev_delta"] = float_round(((cols[i]["revenue"] - prev_r) / abs(prev_r) * 100) if prev_r else 0, 1)
            prev_n = cols[i - 1]["net"]
            cols[i]["net_delta"] = float_round(((cols[i]["net"] - prev_n) / abs(prev_n) * 100) if prev_n else 0, 1)
        cols[0]["rev_delta"] = None
        cols[0]["net_delta"] = None

        currency = self.env.company.currency_id
        return {"options": options, "years": cols,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"year": int(options.get("year") or today.year),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
