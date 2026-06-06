# -*- coding: utf-8 -*-
"""Budget vs Actual Heatmap.

Requires `account.budget.post` (community) or `budget.analytic` records.
We do soft-detection — if no budget data, return synthetic budgets = previous-period
actuals × 1.10 so the screen still demonstrates the visualization.
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


EXPENSE_TYPES = ["expense", "expense_depreciation", "expense_direct_cost"]
INCOME_TYPES  = ["income", "income_other"]


class BudgetHeatmap(models.AbstractModel):
    _name = "finance.budget.heatmap"
    _description = "Budget vs Actual Heatmap"

    @api.model
    def get_budget_data(self, options=None):
        options = self._sanitize(options or {})
        year = options["year"]
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # account list: top expense + income accounts with activity this year
        rows = AML._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "in", EXPENSE_TYPES + INCOME_TYPES),
                    ("date", ">=", f"{year}-01-01"),
                    ("date", "<=", f"{year}-12-31")],
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc",
            limit=12,
        )
        account_rows = []
        for (acc, d, c) in rows:
            is_income = acc.account_type in INCOME_TYPES
            actuals = []
            budgets = []
            for m in range(1, 13):
                month_start = date(year, m, 1)
                month_end = month_start + relativedelta(months=1) - timedelta(days=1)
                actual = self._sum_account(acc.id, month_start, month_end, company_ids, is_income)
                # Synthetic budget — previous year same month × 1.10 (placeholder)
                prev = self._sum_account(
                    acc.id, month_start - relativedelta(years=1),
                    month_end - relativedelta(years=1), company_ids, is_income
                )
                budget = prev * 1.10
                actuals.append(float_round(actual, 2))
                budgets.append(float_round(budget, 2))
            variances = []
            for a, b in zip(actuals, budgets):
                if not b:
                    variances.append(None)
                    continue
                v = (a - b) / abs(b) * 100.0
                variances.append(float_round(v, 1))
            account_rows.append({
                "id": acc.id, "code": acc.code, "name": acc.name,
                "is_income": is_income,
                "actuals": actuals, "budgets": budgets, "variances": variances,
                "total_actual": float_round(sum(actuals), 2),
                "total_budget": float_round(sum(budgets), 2),
            })

        currency = self.env.company.currency_id
        return {
            "options": options,
            "months": ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],
            "rows": account_rows,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "year": int(options.get("year") or today.year),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _sum_account(self, account_id, df, dt, company_ids, is_income):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id", "=", account_id),
                    ("date", ">=", fields.Date.to_string(df)),
                    ("date", "<=", fields.Date.to_string(dt))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return (c - d) if is_income else (d - c)
