# -*- coding: utf-8 -*-
"""Account Movement Velocity — line count per account, trending up/down."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models


class AccountVelocity(models.AbstractModel):
    _name = "finance.account.velocity"
    _description = "Account Movement Velocity"

    @api.model
    def get_velocity_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # last 3 months vs prior 3 months
        recent_start = (as_of - relativedelta(months=3))
        prior_start = (as_of - relativedelta(months=6))

        def counts(df, dt):
            rows = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=["account_id"], aggregates=["__count"])
            return {a.id: cnt for (a, cnt) in rows if a}

        recent = counts(recent_start, as_of)
        prior = counts(prior_start, recent_start - timedelta(days=1))

        all_accs = set(recent.keys()) | set(prior.keys())
        rows = []
        for aid in all_accs:
            r = recent.get(aid, 0); p = prior.get(aid, 0)
            if r == 0 and p == 0: continue
            delta_pct = ((r - p) / p * 100) if p else (100 if r > 0 else 0)
            acc = self.env["account.account"].browse(aid)
            rows.append({"id": aid, "code": acc.code, "name": acc.name,
                         "recent": r, "prior": p,
                         "delta_pct": round(delta_pct, 1),
                         "trend": "hot" if delta_pct > 30 else ("cold" if delta_pct < -30 else "stable")})
        rows.sort(key=lambda r: -r["recent"])
        return {"options": options, "rows": rows[:50],
                "hot_count": sum(1 for r in rows if r["trend"] == "hot"),
                "cold_count": sum(1 for r in rows if r["trend"] == "cold"),
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
