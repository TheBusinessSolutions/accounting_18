# -*- coding: utf-8 -*-
"""Credit Notes / Refunds Audit Log."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class CreditNotesAudit(models.AbstractModel):
    _name = "finance.credit.notes.audit"
    _description = "Credit Notes Audit"

    @api.model
    def get_credit_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        out_refunds = Move.search([("state", "=", "posted"),
                                   ("move_type", "=", "out_refund"),
                                   ("invoice_date", ">=", fields.Date.to_string(df)),
                                   ("invoice_date", "<=", fields.Date.to_string(dt)),
                                   ("company_id", "in", company_ids)])
        in_refunds = Move.search([("state", "=", "posted"),
                                  ("move_type", "=", "in_refund"),
                                  ("invoice_date", ">=", fields.Date.to_string(df)),
                                  ("invoice_date", "<=", fields.Date.to_string(dt)),
                                  ("company_id", "in", company_ids)])

        def serialize(moves, kind):
            return [{"id": m.id, "name": m.name, "date": m.invoice_date.isoformat() if m.invoice_date else None,
                     "partner": m.partner_id.display_name if m.partner_id else "",
                     "user": m.create_uid.name if m.create_uid else "",
                     "amount": float_round(m.amount_total, 2),
                     "reason": m.ref or "",
                     "kind": kind} for m in moves]

        rows = serialize(out_refunds, "Sales") + serialize(in_refunds, "Purchase")
        rows.sort(key=lambda r: r["date"] or "", reverse=True)

        currency = self.env.company.currency_id
        return {"options": options, "rows": rows,
                "out_count": len(out_refunds),
                "in_count": len(in_refunds),
                "out_total": float_round(sum(m.amount_total for m in out_refunds), 2),
                "in_total": float_round(sum(m.amount_total for m in in_refunds), 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
