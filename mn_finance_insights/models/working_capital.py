# -*- coding: utf-8 -*-
"""Working Capital Cycle (CCC = DSO + DIO − DPO).

DSO = AR ÷ Revenue × days
DIO = Inventory ÷ COGS × days  (uses asset_current as inventory proxy)
DPO = AP ÷ COGS × days
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class WorkingCapital(models.AbstractModel):
    _name = "finance.working.capital"
    _description = "Working Capital Cycle (CCC)"

    @api.model
    def get_ccc_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]

        labels, dso_v, dio_v, dpo_v, ccc_v = [], [], [], [], []
        cursor = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        for _i in range(12):
            month_end = cursor + relativedelta(months=1) - timedelta(days=1)
            month_start = date(month_end.year, month_end.month, 1) - relativedelta(months=2)
            # use trailing 3 months for activity averages
            ar  = self._balance(["asset_receivable"], month_end, company_ids, signed=True)
            ap  = -self._balance(["liability_payable"], month_end, company_ids, signed=True)
            inv = self._balance(["asset_current"],   month_end, company_ids, signed=True)
            revenue = self._flow(["income","income_other"], month_start, month_end, company_ids, is_income=True)
            cogs    = self._flow(["expense_direct_cost"],  month_start, month_end, company_ids, is_income=False)
            days = (month_end - month_start).days + 1
            dso = (ar / revenue * days) if revenue else 0
            dio = (inv / cogs * days) if cogs else 0
            dpo = (ap / cogs * days) if cogs else 0
            ccc = dso + dio - dpo
            labels.append(cursor.strftime("%b %Y"))
            dso_v.append(float_round(dso, 0))
            dio_v.append(float_round(dio, 0))
            dpo_v.append(float_round(dpo, 0))
            ccc_v.append(float_round(ccc, 0))
            cursor += relativedelta(months=1)

        currency = self.env.company.currency_id
        return {
            "options": options,
            "labels": labels,
            "dso": dso_v, "dio": dio_v, "dpo": dpo_v, "ccc": ccc_v,
            "current": {"dso": dso_v[-1], "dio": dio_v[-1], "dpo": dpo_v[-1], "ccc": ccc_v[-1]},
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _balance(self, types, as_of, company_ids, signed):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "in", types),
                    ("date", "<=", fields.Date.to_string(as_of))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return (d - c) if signed else (c - d)

    @api.model
    def _flow(self, types, df, dt, company_ids, is_income):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "in", types),
                    ("date", ">=", fields.Date.to_string(df)),
                    ("date", "<=", fields.Date.to_string(dt))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return (c - d) if is_income else (d - c)
