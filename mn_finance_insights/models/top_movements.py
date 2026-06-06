# -*- coding: utf-8 -*-
"""Top Account Movements — biggest journal entries in period."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class TopMovements(models.AbstractModel):
    _name = "finance.top.movements"
    _description = "Top Account Movements"

    @api.model
    def get_movements_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # Top 30 lines by absolute amount
        lines = AML.search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            fields=["date", "account_id", "move_id", "partner_id", "name", "debit", "credit"],
            limit=2000)
        for ln in lines:
            ln["abs_amount"] = abs(ln["debit"] - ln["credit"])
        lines.sort(key=lambda l: -l["abs_amount"])
        top = lines[:30]
        out = [{"id": l["id"],
                "date": l["date"],
                "account": (l["account_id"] and l["account_id"][1]) or "",
                "move": (l["move_id"] and l["move_id"][1]) or "",
                "partner": (l["partner_id"] and l["partner_id"][1]) or "",
                "label": l.get("name") or "",
                "debit": float_round(l["debit"], 2),
                "credit": float_round(l["credit"], 2),
                "amount": float_round(l["abs_amount"], 2)} for l in top]
        currency = self.env.company.currency_id
        return {"options": options, "rows": out,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
