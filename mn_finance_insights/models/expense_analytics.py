# -*- coding: utf-8 -*-
"""Expense Analytics — bills/expenses by category, vendor, month, account."""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


EXPENSE_TYPES = ["expense", "expense_depreciation", "expense_direct_cost"]


class ExpenseAnalytics(models.AbstractModel):
    _name = "finance.expense.analytics"
    _description = "Expense Analytics"

    @api.model
    def get_expense_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        total_expense = self._sum(EXPENSE_TYPES, df, dt, company_ids)

        Move = self.env["account.move"]
        bills = Move.search([
            ("state", "=", "posted"),
            ("move_type", "in", ["in_invoice", "in_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("company_id", "in", company_ids),
        ])
        bill_count   = len([b for b in bills if b.move_type == "in_invoice"])
        refund_count = len([b for b in bills if b.move_type == "in_refund"])
        avg_bill = (total_expense / bill_count) if bill_count else 0.0
        unpaid = sum(b.amount_residual_signed for b in bills if b.payment_state != "paid")

        return {
            "options": options,
            "kpis": {
                "total_expense": float_round(total_expense, 2),
                "bill_count":    bill_count,
                "refund_count":  refund_count,
                "avg_bill":      float_round(avg_bill, 2),
                "unpaid":        float_round(abs(unpaid), 2),
            },
            "monthly_trend":  self._monthly_trend(df, dt, company_ids),
            "by_account":     self._by_account(df, dt, company_ids, limit=10),
            "top_vendors":    self._top_vendors(df, dt, company_ids, limit=10),
            "currency": self._currency(),
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
            "date_to":   options.get("date_to")   or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _currency(self):
        c = self.env.company.currency_id
        return {"id": c.id, "symbol": c.symbol, "decimals": c.decimal_places}

    @api.model
    def _sum(self, types, df, dt, company_ids):
        rows = self.env["account.move.line"]._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt)),
            ],
            groupby=[],
            aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0]
        return (d or 0) - (c or 0)

    @api.model
    def _monthly_trend(self, df, dt, company_ids):
        labels, values = [], []
        cursor = date(df.year, df.month, 1)
        while cursor <= dt:
            end = min(cursor + relativedelta(months=1) - timedelta(days=1), dt)
            values.append(float_round(self._sum(EXPENSE_TYPES, cursor, end, company_ids), 2))
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)
        return {"labels": labels, "values": values}

    @api.model
    def _by_account(self, df, dt, company_ids, limit=10):
        rows = self.env["account.move.line"]._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "in", EXPENSE_TYPES),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt)),
            ],
            groupby=["account_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc",
            limit=limit,
        )
        return [{"id": a.id, "code": a.code, "name": a.name,
                 "amount": float_round((d or 0) - (c or 0), 2)}
                for (a, d, c) in rows]

    @api.model
    def _top_vendors(self, df, dt, company_ids, limit=10):
        rows = self.env["account.move.line"]._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
                ("account_id.account_type", "in", EXPENSE_TYPES),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt)),
                ("partner_id", "!=", False),
            ],
            groupby=["partner_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc",
            limit=limit,
        )
        return [{"id": p.id, "name": p.display_name,
                 "amount": float_round((d or 0) - (c or 0), 2)}
                for (p, d, c) in rows]
