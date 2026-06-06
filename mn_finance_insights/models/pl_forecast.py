# -*- coding: utf-8 -*-
"""P&L Forecast — next 3 months projection from 6-month trend (linear regression)."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class PLForecast(models.AbstractModel):
    _name = "finance.pl.forecast"
    _description = "P&L Forecast"

    @api.model
    def get_forecast_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def flow(types, df, dt, is_income):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return ((c or 0) - (d or 0)) if is_income else ((d or 0) - (c or 0))

        # 6 trailing months actual + 3 forecast
        labels, revenue, expense, net = [], [], [], []
        cursor = date(as_of.year, as_of.month, 1) - relativedelta(months=5)
        for _i in range(6):
            end = cursor + relativedelta(months=1) - timedelta(days=1)
            r = flow(["income", "income_other"], cursor, end, True)
            e = flow(["expense", "expense_depreciation", "expense_direct_cost"], cursor, end, False)
            labels.append(cursor.strftime("%b %Y"))
            revenue.append(float_round(r, 2))
            expense.append(float_round(e, 2))
            net.append(float_round(r - e, 2))
            cursor += relativedelta(months=1)

        # simple linear regression slope on last 6 months
        def project(series, n_future=3):
            n = len(series)
            if n < 2: return [series[-1]] * n_future if series else [0] * n_future
            mean_x = (n - 1) / 2
            mean_y = sum(series) / n
            num = sum((i - mean_x) * (series[i] - mean_y) for i in range(n))
            den = sum((i - mean_x) ** 2 for i in range(n)) or 1
            slope = num / den
            intercept = mean_y - slope * mean_x
            return [float_round(intercept + slope * (n + i), 2) for i in range(n_future)]

        f_rev = project(revenue)
        f_exp = project(expense)
        f_net = [float_round(r - e, 2) for r, e in zip(f_rev, f_exp)]

        for i in range(3):
            future = cursor + relativedelta(months=i) - relativedelta(months=0)  # cursor already advanced
            labels.append(future.strftime("%b %Y") + "*")
        # KPIs
        total_actual_net = sum(net)
        total_forecast_net = sum(f_net)
        avg_net = sum(net) / len(net) if net else 0
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels,
                "revenue": revenue + f_rev,
                "expense": expense + f_exp,
                "net": net + f_net,
                "forecast_start": len(revenue),  # index where forecast begins
                "total_forecast_net": float_round(total_forecast_net, 2),
                "avg_net_actual": float_round(avg_net, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
