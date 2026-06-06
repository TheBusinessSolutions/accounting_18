# -*- coding: utf-8 -*-
"""Invoice Cycle Time — days from invoice posted to paid."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class InvoiceCycleTime(models.AbstractModel):
    _name = "finance.invoice.cycle.time"
    _description = "Invoice Cycle Time"

    @api.model
    def get_cycle_data(self, options=None):
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
        ])
        # Distribution buckets (days)
        buckets = {"0-15": 0, "16-30": 0, "31-60": 0, "61-90": 0, "91+": 0}
        cycles = []
        for m in moves:
            # paid date approximation: latest write_date when payment_state became paid
            if not m.invoice_date or not m.write_date:
                continue
            days = (m.write_date.date() - m.invoice_date).days
            if days < 0:
                continue
            cycles.append(days)
            if days <= 15: buckets["0-15"] += 1
            elif days <= 30: buckets["16-30"] += 1
            elif days <= 60: buckets["31-60"] += 1
            elif days <= 90: buckets["61-90"] += 1
            else: buckets["91+"] += 1

        avg = (sum(cycles) / len(cycles)) if cycles else 0
        median = sorted(cycles)[len(cycles) // 2] if cycles else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": list(buckets.keys()),
                "values": list(buckets.values()),
                "total": len(cycles),
                "avg_days": float_round(avg, 1),
                "median_days": median,
                "fastest": min(cycles) if cycles else 0,
                "slowest": max(cycles) if cycles else 0,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
