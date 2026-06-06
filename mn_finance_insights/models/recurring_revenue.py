# -*- coding: utf-8 -*-
"""Recurring Revenue Tracker — repeat-customer revenue share over time."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class RecurringRevenue(models.AbstractModel):
    _name = "finance.recurring.revenue"
    _description = "Recurring Revenue Tracker"

    @api.model
    def get_recurring_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        moves = Move.search([("state", "=", "posted"),
                             ("move_type", "=", "out_invoice"),
                             ("company_id", "in", company_ids),
                             ("invoice_date", ">=", fields.Date.to_string(df)),
                             ("invoice_date", "<=", fields.Date.to_string(as_of)),
                             ("partner_id", "!=", False)])
        # bucket by month
        per_month_partners = defaultdict(set)
        per_month_revenue = defaultdict(float)
        for m in moves:
            key = (m.invoice_date.year, m.invoice_date.month)
            per_month_partners[key].add(m.partner_id.id)
            per_month_revenue[key] += m.amount_untaxed_signed

        # repeat customers = appeared in prior months
        seen_partners = set()
        labels, total_rev, repeat_rev, repeat_pct = [], [], [], []
        cursor = df
        for _ in range(12):
            key = (cursor.year, cursor.month)
            month_partners = per_month_partners.get(key, set())
            month_rev = per_month_revenue.get(key, 0.0)
            repeat_partners = month_partners & seen_partners
            # repeat revenue: invoices from repeat partners only
            r_rev = sum(m.amount_untaxed_signed for m in moves
                        if m.invoice_date.year == cursor.year and m.invoice_date.month == cursor.month
                        and m.partner_id.id in repeat_partners)
            labels.append(cursor.strftime("%b %Y"))
            total_rev.append(float_round(month_rev, 2))
            repeat_rev.append(float_round(r_rev, 2))
            repeat_pct.append(float_round((r_rev / month_rev * 100) if month_rev else 0, 1))
            seen_partners |= month_partners
            cursor += relativedelta(months=1)

        # KPI: last 3 months repeat %
        last3_total = sum(total_rev[-3:])
        last3_repeat = sum(repeat_rev[-3:])
        last3_pct = (last3_repeat / last3_total * 100) if last3_total else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels, "total": total_rev, "repeat": repeat_rev, "pct": repeat_pct,
                "last3_total": float_round(last3_total, 2),
                "last3_repeat": float_round(last3_repeat, 2),
                "last3_pct": float_round(last3_pct, 1),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
