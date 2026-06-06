# -*- coding: utf-8 -*-
"""Gross Margin Stability — variance per product over 12 months."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class MarginStability(models.AbstractModel):
    _name = "finance.margin.stability"
    _description = "Margin Stability"

    @api.model
    def get_stability_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        moves = Move.search([("state", "=", "posted"),
                             ("move_type", "=", "out_invoice"),
                             ("company_id", "in", company_ids),
                             ("invoice_date", ">=", fields.Date.to_string(df)),
                             ("invoice_date", "<=", fields.Date.to_string(as_of))])
        store = defaultdict(lambda: {"name": "", "rev": [0]*12, "cogs": [0]*12})
        for m in moves:
            mi = (m.invoice_date.year - df.year) * 12 + (m.invoice_date.month - df.month)
            if mi < 0 or mi >= 12: continue
            for ln in m.invoice_line_ids:
                if not ln.product_id: continue
                if ln.display_type and ln.display_type != "product": continue
                store[ln.product_id.id]["name"] = ln.product_id.display_name
                store[ln.product_id.id]["rev"][mi] += ln.price_subtotal
                store[ln.product_id.id]["cogs"][mi] += ln.product_id.standard_price * ln.quantity

        rows = []
        for pid, d in store.items():
            margins = []
            for r, c in zip(d["rev"], d["cogs"]):
                if r > 0:
                    margins.append((r - c) / r * 100)
            if len(margins) < 2: continue
            mean = sum(margins) / len(margins)
            variance = sum((x - mean) ** 2 for x in margins) / len(margins)
            stddev = variance ** 0.5
            total_rev = sum(d["rev"])
            rows.append({"id": pid, "name": d["name"],
                         "avg_margin": float_round(mean, 1),
                         "stddev": float_round(stddev, 1),
                         "total_revenue": float_round(total_rev, 2),
                         "samples": len(margins),
                         "stability": "stable" if stddev < 5 else ("moderate" if stddev < 15 else "volatile")})
        rows.sort(key=lambda r: -r["total_revenue"])

        stable_count = sum(1 for r in rows if r["stability"] == "stable")
        volatile_count = sum(1 for r in rows if r["stability"] == "volatile")
        currency = self.env.company.currency_id
        return {"options": options, "rows": rows[:30],
                "stable_count": stable_count, "volatile_count": volatile_count,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
