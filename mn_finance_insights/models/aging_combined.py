# -*- coding: utf-8 -*-
"""AR + AP combined aging dashboard."""
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


BUCKETS = [
    (_("Not due"), -10**6, -1),
    (_("0-30"),   0,   30),
    (_("31-60"),  31,  60),
    (_("61-90"),  61,  90),
    (_("91-120"), 91, 120),
    (_("121+"),  121, 10**9),
]


class AgingCombined(models.AbstractModel):
    _name = "finance.aging.combined"
    _description = "AR & AP Combined Aging"

    @api.model
    def get_aging_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def aging(account_type):
            lines = AML.search_read(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "=", account_type),
                ("reconciled", "=", False), ("amount_residual", "!=", 0)],
                fields=["amount_residual", "date_maturity"])
            buckets = [0.0] * len(BUCKETS)
            for ln in lines:
                due = ln["date_maturity"] or as_of
                days = (as_of - due).days
                for i, (_lbl, mn, mx) in enumerate(BUCKETS):
                    if mn <= days <= mx:
                        buckets[i] += ln["amount_residual"]; break
            return buckets

        ar_buckets = aging("asset_receivable")
        ap_raw = aging("liability_payable")
        ap_buckets = [-x for x in ap_raw]  # display AP as positive

        ar_total = sum(ar_buckets); ap_total = sum(ap_buckets)
        currency = self.env.company.currency_id
        return {
            "options": options,
            "labels": [b[0] for b in BUCKETS],
            "ar_buckets": [float_round(x, 2) for x in ar_buckets],
            "ap_buckets": [float_round(x, 2) for x in ap_buckets],
            "ar_total": float_round(ar_total, 2),
            "ap_total": float_round(ap_total, 2),
            "net_position": float_round(ar_total - ap_total, 2),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
