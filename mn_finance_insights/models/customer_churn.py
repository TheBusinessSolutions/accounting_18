# -*- coding: utf-8 -*-
"""Customer Churn Risk — inactive-since detection."""
from datetime import date, timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerChurn(models.AbstractModel):
    _name = "finance.customer.churn"
    _description = "Customer Churn Risk"

    @api.model
    def get_churn_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        inactive_days = int(options.get("inactive_days") or 90)
        Move = self.env["account.move"]

        # For every partner with a historical invoice — find last invoice date
        moves = Move.search([("state", "=", "posted"),
                             ("move_type", "=", "out_invoice"),
                             ("company_id", "in", company_ids),
                             ("partner_id", "!=", False)],
                            order="invoice_date desc")
        last_seen = {}
        ltv = {}
        for m in moves:
            pid = m.partner_id.id
            if pid not in last_seen:
                last_seen[pid] = (m.invoice_date, m.partner_id.display_name)
            ltv[pid] = ltv.get(pid, 0.0) + m.amount_untaxed_signed

        rows = []
        for pid, (last_date, name) in last_seen.items():
            if not last_date:
                continue
            days = (as_of - last_date).days
            if days < inactive_days:
                continue
            sev = "bad" if days > inactive_days * 2 else "ok"
            rows.append({"id": pid, "name": name,
                         "last_invoice": last_date.isoformat(),
                         "days_inactive": days,
                         "ltv": float_round(ltv[pid], 2),
                         "severity": sev})
        rows.sort(key=lambda r: -r["ltv"])

        total_ltv_at_risk = sum(r["ltv"] for r in rows)
        critical = sum(1 for r in rows if r["severity"] == "bad")
        currency = self.env.company.currency_id
        return {"options": options, "rows": rows[:100],
                "count": len(rows),
                "critical_count": critical,
                "ltv_at_risk": float_round(total_ltv_at_risk, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "inactive_days": int(options.get("inactive_days") or 90),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
