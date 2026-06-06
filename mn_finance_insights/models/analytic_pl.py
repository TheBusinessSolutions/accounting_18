# -*- coding: utf-8 -*-
"""Analytic / Cost Center P&L."""
from datetime import date
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class AnalyticPL(models.AbstractModel):
    _name = "finance.analytic.pl"
    _description = "Analytic / Cost Center P&L"

    @api.model
    def get_analytic_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        # Use account.analytic.line if available, else aggregate from account.move.line
        AnalyticLine = self.env.get("account.analytic.line")
        rows = []
        if AnalyticLine is not None:
            grouped = AnalyticLine._read_group(
                domain=[("date", ">=", fields.Date.to_string(df)),
                        ("date", "<=", fields.Date.to_string(dt)),
                        ("company_id", "in", company_ids),
                        ("account_id", "!=", False)],
                groupby=["account_id"], aggregates=["amount:sum"],
                order="amount:sum desc")
            for (acc, amt) in grouped:
                if not acc: continue
                rows.append({"id": acc.id, "name": acc.name,
                             "code": acc.code or "",
                             "amount": float_round(amt or 0, 2)})
        currency = self.env.company.currency_id
        total = sum(r["amount"] for r in rows)
        return {"options": options, "rows": rows,
                "total": float_round(total, 2),
                "count": len(rows),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
