# -*- coding: utf-8 -*-
"""Top Discount Recipients — invoices with highest discount %."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class TopDiscounts(models.AbstractModel):
    _name = "finance.top.discounts"
    _description = "Top Discount Recipients"

    @api.model
    def get_discount_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        invoices = Move.search([("state", "=", "posted"),
                                ("move_type", "=", "out_invoice"),
                                ("invoice_date", ">=", fields.Date.to_string(df)),
                                ("invoice_date", "<=", fields.Date.to_string(dt)),
                                ("company_id", "in", company_ids),
                                ("partner_id", "!=", False)])
        rows = []
        for m in invoices:
            gross = sum(ln.price_unit * ln.quantity for ln in m.invoice_line_ids
                        if (not ln.display_type) or ln.display_type == "product")
            net = sum(ln.price_subtotal for ln in m.invoice_line_ids
                      if (not ln.display_type) or ln.display_type == "product")
            disc = gross - net
            if disc <= 0: continue
            disc_pct = (disc / gross * 100) if gross else 0
            rows.append({"id": m.id, "name": m.name,
                         "date": m.invoice_date.isoformat() if m.invoice_date else None,
                         "partner": m.partner_id.display_name,
                         "gross": float_round(gross, 2),
                         "net": float_round(net, 2),
                         "discount": float_round(disc, 2),
                         "discount_pct": float_round(disc_pct, 1)})
        rows.sort(key=lambda r: -r["discount_pct"])
        rows = rows[:50]

        total_disc = sum(r["discount"] for r in rows)
        currency = self.env.company.currency_id
        return {"options": options, "rows": rows,
                "total_discount": float_round(total_disc, 2),
                "count": len(rows),
                "avg_disc_pct": float_round((sum(r["discount_pct"] for r in rows) / len(rows)) if rows else 0, 1),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
