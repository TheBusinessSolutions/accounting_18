# -*- coding: utf-8 -*-
"""Late Invoice Tracker — overdue invoices with days late & follow-up actions."""
from odoo import _, api, fields, models
from odoo.tools import float_round


class LateInvoices(models.AbstractModel):
    _name = "finance.late.invoices"
    _description = "Late Invoice Tracker"

    @api.model
    def get_late_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]
        invoices = Move.search([
            ("state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_type", "in", ["out_invoice"]),
            ("payment_state", "in", ["not_paid", "partial"]),
            ("invoice_date_due", "<", fields.Date.to_string(as_of)),
        ], order="invoice_date_due asc", limit=500)

        rows = []
        for m in invoices:
            days_late = (as_of - m.invoice_date_due).days if m.invoice_date_due else 0
            sev = "bad" if days_late > 60 else ("ok" if days_late > 30 else "good")
            rows.append({
                "id": m.id, "name": m.name,
                "partner_id": m.partner_id.id if m.partner_id else False,
                "partner_name": m.partner_id.display_name if m.partner_id else "",
                "date_due": m.invoice_date_due.isoformat() if m.invoice_date_due else None,
                "days_late": days_late,
                "severity": sev,
                "residual": float_round(m.amount_residual, 2),
                "total": float_round(m.amount_total, 2),
            })

        total_overdue = sum(r["residual"] for r in rows)
        over_60 = sum(r["residual"] for r in rows if r["days_late"] > 60)
        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": rows,
            "total_overdue": float_round(total_overdue, 2),
            "over_60_overdue": float_round(over_60, 2),
            "count": len(rows),
            "count_critical": sum(1 for r in rows if r["severity"] == "bad"),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
