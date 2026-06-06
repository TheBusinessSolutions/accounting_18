# -*- coding: utf-8 -*-
"""Average Order Value (AOV) Trend — month-over-month."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class AOVTrend(models.AbstractModel):
    _name = "finance.aov.trend"
    _description = "Average Order Value Trend"

    @api.model
    def get_aov_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        labels, counts, totals, aovs = [], [], [], []
        cursor = df
        for _i in range(12):
            end = cursor + relativedelta(months=1) - timedelta(days=1)
            moves = Move.search([("state", "=", "posted"),
                                 ("move_type", "=", "out_invoice"),
                                 ("company_id", "in", company_ids),
                                 ("invoice_date", ">=", fields.Date.to_string(cursor)),
                                 ("invoice_date", "<=", fields.Date.to_string(end))])
            cnt = len(moves)
            tot = sum(m.amount_untaxed_signed for m in moves)
            aov = (tot / cnt) if cnt else 0
            labels.append(cursor.strftime("%b %Y"))
            counts.append(cnt)
            totals.append(float_round(tot, 2))
            aovs.append(float_round(aov, 2))
            cursor += relativedelta(months=1)

        total_aov = (sum(totals) / sum(counts)) if sum(counts) else 0
        recent = aovs[-1] if aovs else 0
        prev = aovs[-2] if len(aovs) > 1 else 0
        delta_pct = ((recent - prev) / abs(prev) * 100) if prev else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels, "counts": counts, "totals": totals, "aovs": aovs,
                "avg_aov": float_round(total_aov, 2),
                "latest_aov": float_round(recent, 2),
                "delta_pct": float_round(delta_pct, 1),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
