# -*- coding: utf-8 -*-
"""Daily Sales Snapshot — today / WTD / MTD / YTD revenue."""
from datetime import date, timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class DailySales(models.AbstractModel):
    _name = "finance.daily.sales"
    _description = "Daily Sales Snapshot"

    @api.model
    def get_snapshot_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def revenue(df, dt):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return (c or 0) - (d or 0)

        wstart = as_of - timedelta(days=as_of.weekday())
        mstart = date(as_of.year, as_of.month, 1)
        ystart = date(as_of.year, 1, 1)
        prev_year_today = date(as_of.year - 1, as_of.month, min(as_of.day, 28))

        today = revenue(as_of, as_of)
        wtd = revenue(wstart, as_of)
        mtd = revenue(mstart, as_of)
        ytd = revenue(ystart, as_of)
        last_year_ytd = revenue(date(as_of.year - 1, 1, 1), prev_year_today)

        # Daily breakdown last 30 days
        labels, values = [], []
        for i in range(29, -1, -1):
            d_ = as_of - timedelta(days=i)
            labels.append(d_.isoformat())
            values.append(float_round(revenue(d_, d_), 2))

        currency = self.env.company.currency_id

        return {
            "options": options,
            "today": float_round(today, 2),
            "wtd": float_round(wtd, 2),
            "mtd": float_round(mtd, 2),
            "ytd": float_round(ytd, 2),
            "last_year_ytd": float_round(last_year_ytd, 2),
            "ytd_delta_pct": float_round(((ytd - last_year_ytd) / abs(last_year_ytd) * 100) if last_year_ytd else 0, 1),
            "labels": labels, "values": values,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
