# -*- coding: utf-8 -*-
"""Customer Cohort Analysis — monthly cohort × month-since-acquisition."""
from datetime import date
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerCohort(models.AbstractModel):
    _name = "finance.customer.cohort"
    _description = "Customer Cohort Analysis"

    @api.model
    def get_cohort_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        months_back = int(options.get("months") or 12)

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=months_back - 1)
        moves = self.env["account.move"].search([
            ("state", "=", "posted"),
            ("move_type", "=", "out_invoice"),
            ("company_id", "in", company_ids),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(as_of)),
            ("partner_id", "!=", False),
        ])
        first_invoice = {}
        for m in moves:
            pid = m.partner_id.id
            if pid not in first_invoice or m.invoice_date < first_invoice[pid]:
                first_invoice[pid] = m.invoice_date

        cohort_revenue = defaultdict(lambda: defaultdict(float))
        cohort_size = defaultdict(set)
        for m in moves:
            pid = m.partner_id.id
            cohort_month = first_invoice[pid].replace(day=1)
            inv_month = m.invoice_date.replace(day=1)
            offset = (inv_month.year - cohort_month.year) * 12 + (inv_month.month - cohort_month.month)
            if offset < 0 or offset >= months_back:
                continue
            cohort_revenue[cohort_month][offset] += m.amount_untaxed_signed
            cohort_size[cohort_month].add(pid)

        cohort_months = sorted(cohort_revenue.keys())
        rows = []
        for cm in cohort_months:
            row = {"cohort": cm.strftime("%b %Y"), "customers": len(cohort_size[cm]), "values": []}
            for off in range(months_back):
                row["values"].append(float_round(cohort_revenue[cm][off], 2))
            rows.append(row)
        currency = self.env.company.currency_id
        return {"options": options,
                "month_labels": [f"M{i}" for i in range(months_back)],
                "rows": rows,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "months": int(options.get("months") or 12),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
