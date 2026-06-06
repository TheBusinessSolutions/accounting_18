# -*- coding: utf-8 -*-
"""Customer Acquisition Velocity — new customers per month."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class AcquisitionVelocity(models.AbstractModel):
    _name = "finance.acquisition.velocity"
    _description = "Customer Acquisition Velocity"

    @api.model
    def get_acquisition_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        moves = Move.search([("state", "=", "posted"),
                             ("move_type", "=", "out_invoice"),
                             ("company_id", "in", company_ids),
                             ("partner_id", "!=", False)],
                            order="invoice_date asc")
        first_seen = {}
        for m in moves:
            pid = m.partner_id.id
            if pid not in first_seen:
                first_seen[pid] = (m.invoice_date, m.partner_id.display_name, m.amount_untaxed_signed)

        # bucket by acquisition month
        labels, counts, first_revenue = [], [], []
        cursor = df
        for _i in range(12):
            end = cursor + relativedelta(months=1) - timedelta(days=1)
            new_pids = [pid for pid, (dt_, _name, _rev) in first_seen.items()
                        if dt_ and cursor <= dt_ <= end]
            rev = sum(first_seen[pid][2] for pid in new_pids)
            labels.append(cursor.strftime("%b %Y"))
            counts.append(len(new_pids))
            first_revenue.append(float_round(rev, 2))
            cursor += relativedelta(months=1)

        total_new = sum(counts)
        avg_monthly = total_new / 12 if counts else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels, "counts": counts, "first_revenue": first_revenue,
                "total_new": total_new,
                "avg_monthly": round(avg_monthly, 1),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
