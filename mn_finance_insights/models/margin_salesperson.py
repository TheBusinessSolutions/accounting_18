# -*- coding: utf-8 -*-
"""Margin by Salesperson."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class MarginSalesperson(models.AbstractModel):
    _name = "finance.margin.salesperson"
    _description = "Margin by Salesperson"

    @api.model
    def get_margin_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        invoices = Move.search([
            ("state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("invoice_user_id", "!=", False),
        ])
        agg = {}
        for m in invoices:
            uid = m.invoice_user_id.id
            entry = agg.setdefault(uid, {"id": uid, "name": m.invoice_user_id.name,
                                         "revenue": 0.0, "cogs": 0.0, "count": 0})
            sign = -1.0 if m.move_type == "out_refund" else 1.0
            for ln in m.invoice_line_ids:
                if ln.display_type and ln.display_type != "product":
                    continue
                entry["revenue"] += sign * ln.price_subtotal
                if ln.product_id:
                    entry["cogs"] += sign * ln.product_id.standard_price * ln.quantity
            entry["count"] += 1 if m.move_type == "out_invoice" else 0

        rows = []
        for d in agg.values():
            revenue = d["revenue"]; cogs = d["cogs"]
            margin = revenue - cogs
            margin_pct = (margin / revenue * 100) if revenue else 0
            rows.append({"id": d["id"], "name": d["name"],
                         "revenue": float_round(revenue, 2),
                         "cogs": float_round(cogs, 2),
                         "margin": float_round(margin, 2),
                         "margin_pct": float_round(margin_pct, 1),
                         "count": d["count"]})
        rows.sort(key=lambda r: -r["margin"])

        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": rows,
            "totals": {
                "revenue": float_round(sum(r["revenue"] for r in rows), 2),
                "cogs": float_round(sum(r["cogs"] for r in rows), 2),
                "margin": float_round(sum(r["margin"] for r in rows), 2),
            },
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
