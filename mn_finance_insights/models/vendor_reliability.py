# -*- coding: utf-8 -*-
"""Vendor Reliability Score — payment compliance + refund/return rate."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class VendorReliability(models.AbstractModel):
    _name = "finance.vendor.reliability"
    _description = "Vendor Reliability Score"

    @api.model
    def get_reliability_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        bills = Move.search([("state", "=", "posted"),
                             ("move_type", "in", ["in_invoice", "in_refund"]),
                             ("invoice_date", ">=", fields.Date.to_string(df)),
                             ("invoice_date", "<=", fields.Date.to_string(dt)),
                             ("company_id", "in", company_ids),
                             ("partner_id", "!=", False)])
        agg = {}
        for b in bills:
            pid = b.partner_id.id
            e = agg.setdefault(pid, {"id": pid, "name": b.partner_id.display_name,
                                     "bill_count": 0, "refund_count": 0,
                                     "total_spend": 0.0, "refund_amount": 0.0,
                                     "paid_count": 0, "paid_late_count": 0})
            if b.move_type == "in_invoice":
                e["bill_count"] += 1
                e["total_spend"] += b.amount_untaxed_signed
                if b.payment_state == "paid":
                    e["paid_count"] += 1
                    if b.invoice_date_due and b.write_date and b.write_date.date() > b.invoice_date_due:
                        e["paid_late_count"] += 1
            else:
                e["refund_count"] += 1
                e["refund_amount"] += b.amount_untaxed_signed
        rows = []
        for e in agg.values():
            refund_rate = (e["refund_amount"] / e["total_spend"] * 100) if e["total_spend"] else 0
            late_rate = (e["paid_late_count"] / e["paid_count"] * 100) if e["paid_count"] else 0
            # 100 = perfect, deductions
            score = 100 - min(40, refund_rate * 2) - min(40, late_rate * 1.5)
            score = max(0, round(score))
            sev = "good" if score >= 80 else ("ok" if score >= 50 else "bad")
            rows.append({"id": e["id"], "name": e["name"],
                         "bill_count": e["bill_count"], "refund_count": e["refund_count"],
                         "total_spend": float_round(e["total_spend"], 2),
                         "refund_rate": float_round(refund_rate, 1),
                         "late_rate": float_round(late_rate, 1),
                         "score": score, "severity": sev})
        rows.sort(key=lambda r: r["score"])
        currency = self.env.company.currency_id
        return {"options": options, "rows": rows,
                "good_count": sum(1 for r in rows if r["severity"] == "good"),
                "ok_count": sum(1 for r in rows if r["severity"] == "ok"),
                "bad_count": sum(1 for r in rows if r["severity"] == "bad"),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
