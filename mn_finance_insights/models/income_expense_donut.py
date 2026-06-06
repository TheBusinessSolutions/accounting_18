# -*- coding: utf-8 -*-
"""Income vs Expense Breakdown (donut)."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


INCOME_TYPES = ["income", "income_other"]
EXPENSE_TYPES = ["expense", "expense_depreciation", "expense_direct_cost"]


class IncomeExpenseDonut(models.AbstractModel):
    _name = "finance.income.expense.donut"
    _description = "Income vs Expense Breakdown"

    @api.model
    def get_donut_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def by_account(types, is_income):
            rows = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=["account_id"], aggregates=["debit:sum", "credit:sum"],
                order="credit:sum desc" if is_income else "debit:sum desc",
                limit=10)
            return [{"id": a.id, "code": a.code, "name": a.name,
                     "amount": float_round(((c or 0) - (d or 0)) if is_income else ((d or 0) - (c or 0)), 2)}
                    for (a, d, c) in rows]

        income_rows = by_account(INCOME_TYPES, True)
        expense_rows = by_account(EXPENSE_TYPES, False)
        income_total = sum(r["amount"] for r in income_rows)
        expense_total = sum(r["amount"] for r in expense_rows)
        currency = self.env.company.currency_id
        return {"options": options,
                "income": income_rows, "expense": expense_rows,
                "income_total": float_round(income_total, 2),
                "expense_total": float_round(expense_total, 2),
                "net": float_round(income_total - expense_total, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
