# -*- coding: utf-8 -*-
"""Vendor Payment Schedule — open AP outflows by week."""
from odoo import _, api, fields, models
from odoo.tools import float_round


class VendorPaymentSchedule(models.AbstractModel):
    _name = "finance.vendor.payment.schedule"
    _description = "Vendor Payment Schedule"

    @api.model
    def get_schedule_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        horizon = int(options.get("horizon") or 12)
        company_ids = options["company_ids"]

        lines = self.env["account.move.line"].search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "liability_payable"),
            ("reconciled", "=", False), ("amount_residual", "!=", 0)],
            fields=["amount_residual", "date_maturity", "partner_id", "move_id"])

        # Negate AP (stored as negative residual)
        buckets = [0.0] * horizon
        overdue = 0.0
        weekly_details = [[] for _ in range(horizon)]
        for ln in lines:
            due = ln["date_maturity"] or as_of
            week = (due - as_of).days // 7
            amount = -ln["amount_residual"]
            if week < 0:
                overdue += amount
            elif week < horizon:
                buckets[week] += amount
                if ln["partner_id"]:
                    weekly_details[week].append({"partner": ln["partner_id"][1], "amount": amount})
        labels = [f"W{i+1}" for i in range(horizon)]
        currency = self.env.company.currency_id
        return {"options": options, "labels": labels,
                "values": [float_round(v, 2) for v in buckets],
                "overdue": float_round(overdue, 2),
                "total": float_round(sum(buckets) + overdue, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "horizon": int(options.get("horizon") or 12),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
