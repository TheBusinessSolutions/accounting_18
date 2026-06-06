# -*- coding: utf-8 -*-
"""Days to Pay Analytics — per-customer actual vs term days."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class DaysToPay(models.AbstractModel):
    _name = "finance.days.to.pay"
    _description = "Days to Pay Analytics"

    @api.model
    def get_dtp_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        moves = self.env["account.move"].search([
            ("state", "=", "posted"),
            ("move_type", "=", "out_invoice"),
            ("payment_state", "=", "paid"),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("company_id", "in", company_ids),
            ("partner_id", "!=", False),
        ])
        # Per partner aggregation
        agg = {}
        for m in moves:
            if not m.invoice_date or not m.write_date:
                continue
            actual_days = (m.write_date.date() - m.invoice_date).days
            term_days = (m.invoice_date_due - m.invoice_date).days if m.invoice_date_due else 30
            late = max(0, actual_days - term_days)
            pid = m.partner_id.id
            e = agg.setdefault(pid, {"id": pid, "name": m.partner_id.display_name,
                                     "actual": [], "term": [], "late_count": 0, "count": 0})
            e["actual"].append(actual_days)
            e["term"].append(term_days)
            if late > 0: e["late_count"] += 1
            e["count"] += 1
        rows = []
        for e in agg.values():
            avg_actual = sum(e["actual"]) / len(e["actual"]) if e["actual"] else 0
            avg_term = sum(e["term"]) / len(e["term"]) if e["term"] else 0
            late_pct = (e["late_count"] / e["count"] * 100) if e["count"] else 0
            rows.append({"id": e["id"], "name": e["name"],
                         "count": e["count"],
                         "avg_actual": float_round(avg_actual, 1),
                         "avg_term": float_round(avg_term, 1),
                         "delta": float_round(avg_actual - avg_term, 1),
                         "late_pct": float_round(late_pct, 1)})
        rows.sort(key=lambda r: -r["delta"])
        currency = self.env.company.currency_id
        return {"options": options, "rows": rows,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
