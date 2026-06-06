# -*- coding: utf-8 -*-
"""Journal Audit Trail — recent posts/edits with anomaly flags."""
from datetime import date, timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class JournalAudit(models.AbstractModel):
    _name = "finance.journal.audit"
    _description = "Journal Audit Trail"

    @api.model
    def get_audit_data(self, options=None):
        options = self._sanitize(options or {})
        days = int(options.get("days") or 14)
        company_ids = options["company_ids"]
        since = fields.Date.context_today(self) - timedelta(days=days)
        Move = self.env["account.move"]
        moves = Move.search([
            ("state", "=", "posted"), ("company_id", "in", company_ids),
            ("write_date", ">=", fields.Date.to_string(since)),
        ], order="write_date desc", limit=200)

        amounts = moves.mapped("amount_total")
        avg = (sum(amounts) / len(amounts)) if amounts else 0
        stddev = ((sum((a - avg) ** 2 for a in amounts) / len(amounts)) ** 0.5) if amounts else 0
        threshold = avg + 3 * stddev

        out = []
        for m in moves:
            anomaly = []
            if m.amount_total > threshold:
                anomaly.append("LARGE")
            if m.write_date and m.create_date and (m.write_date - m.create_date).total_seconds() > 3600 * 24 * 7:
                anomaly.append("LATE-EDIT")
            if m.date and m.create_date and (m.create_date.date() - m.date).days > 30:
                anomaly.append("BACKDATED")
            out.append({
                "id": m.id, "name": m.name or "/",
                "date": m.date.isoformat() if m.date else None,
                "create_date": m.create_date.isoformat() if m.create_date else None,
                "write_date": m.write_date.isoformat() if m.write_date else None,
                "user": (m.create_uid.name or "") if m.create_uid else "",
                "journal": m.journal_id.name if m.journal_id else "",
                "amount": float_round(m.amount_total, 2),
                "anomaly": anomaly,
            })
        currency = self.env.company.currency_id
        return {
            "options": {**options, "days": days},
            "rows": out,
            "threshold": float_round(threshold, 2),
            "anomaly_count": sum(1 for r in out if r["anomaly"]),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        return {"days": int(options.get("days") or 14),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
