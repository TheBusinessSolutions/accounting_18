# -*- coding: utf-8 -*-
"""Executive Finance Dashboard data provider.

Reads directly from `account.move.line` so it works on Community AND Enterprise
without depending on the proprietary `account_reports` module.
"""
from collections import defaultdict
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class FinanceDashboard(models.AbstractModel):
    _name = "finance.dashboard"
    _description = "Executive Finance Dashboard"

    # ------------------------------------------------------------------
    # Public entrypoint — called from the OWL client action
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, options=None):
        """Return everything the dashboard needs in one round-trip.

        :param options: dict with keys
            - date_from (YYYY-MM-DD)        default: first day of current year
            - date_to   (YYYY-MM-DD)        default: today
            - company_ids (list of int)     default: env.companies.ids
            - compare ('previous_period' | 'previous_year' | None)
        """
        options = self._sanitize_options(options or {})
        currency = self.env.company.currency_id

        kpis = self._compute_kpis(options)
        charts = {
            "revenue_vs_expenses": self._chart_revenue_vs_expenses(options),
            "cash_trend": self._chart_cash_trend(options),
            "top_customers": self._chart_top_customers(options),
            "ar_aging": self._chart_ar_aging(options),
        }
        return {
            "options": options,
            "currency": {
                "id": currency.id,
                "symbol": currency.symbol,
                "position": currency.position,
                "decimals": currency.decimal_places,
            },
            "kpis": kpis,
            "charts": charts,
            "company_name": self.env.company.name,
        }

    # ------------------------------------------------------------------
    # Options
    # ------------------------------------------------------------------
    @api.model
    def _sanitize_options(self, options):
        today = fields.Date.context_today(self)
        date_from = options.get("date_from") or date(today.year, 1, 1).isoformat()
        date_to = options.get("date_to") or today.isoformat()
        company_ids = options.get("company_ids") or self.env.companies.ids
        compare = options.get("compare") or None
        return {
            "date_from": date_from,
            "date_to": date_to,
            "company_ids": list(company_ids),
            "compare": compare,
        }

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------
    @api.model
    def _compute_kpis(self, options):
        date_from = fields.Date.from_string(options["date_from"])
        date_to = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        # current period
        revenue = self._sum_by_account_type(["income", "income_other"], date_from, date_to, company_ids)
        expenses = self._sum_by_account_type(
            ["expense", "expense_depreciation", "expense_direct_cost"], date_from, date_to, company_ids
        )
        cogs = self._sum_by_account_type(["expense_direct_cost"], date_from, date_to, company_ids)
        net_profit = revenue - expenses

        # point-in-time (balance up to date_to)
        cash = self._sum_by_account_type(["asset_cash"], None, date_to, company_ids, signed=True)
        ar = self._sum_by_account_type(["asset_receivable"], None, date_to, company_ids, signed=True)
        ap = -self._sum_by_account_type(["liability_payable"], None, date_to, company_ids, signed=True)

        gross_margin_pct = ((revenue - cogs) / revenue * 100.0) if revenue else 0.0
        net_margin_pct = (net_profit / revenue * 100.0) if revenue else 0.0

        result = {
            "revenue": float_round(revenue, precision_digits=2),
            "expenses": float_round(expenses, precision_digits=2),
            "net_profit": float_round(net_profit, precision_digits=2),
            "cash": float_round(cash, precision_digits=2),
            "accounts_receivable": float_round(ar, precision_digits=2),
            "accounts_payable": float_round(ap, precision_digits=2),
            "gross_margin_pct": float_round(gross_margin_pct, precision_digits=1),
            "net_margin_pct": float_round(net_margin_pct, precision_digits=1),
        }

        # comparison vs previous period / previous year
        if options.get("compare"):
            cmp_from, cmp_to = self._compare_range(date_from, date_to, options["compare"])
            cmp_revenue = self._sum_by_account_type(
                ["income", "income_other"], cmp_from, cmp_to, company_ids
            )
            cmp_expenses = self._sum_by_account_type(
                ["expense", "expense_depreciation", "expense_direct_cost"], cmp_from, cmp_to, company_ids
            )
            cmp_net = cmp_revenue - cmp_expenses
            result["compare"] = {
                "label": self._compare_label(options["compare"]),
                "date_from": cmp_from.isoformat(),
                "date_to": cmp_to.isoformat(),
                "revenue_delta_pct": self._pct_delta(revenue, cmp_revenue),
                "expenses_delta_pct": self._pct_delta(expenses, cmp_expenses),
                "net_profit_delta_pct": self._pct_delta(net_profit, cmp_net),
            }
        return result

    @api.model
    def _compare_range(self, date_from, date_to, mode):
        if mode == "previous_year":
            return (date_from - relativedelta(years=1), date_to - relativedelta(years=1))
        # previous_period: same length, ending the day before date_from
        delta_days = (date_to - date_from).days
        new_to = date_from - timedelta(days=1)
        new_from = new_to - timedelta(days=delta_days)
        return (new_from, new_to)

    @api.model
    def _compare_label(self, mode):
        return {
            "previous_year": _("vs previous year"),
            "previous_period": _("vs previous period"),
        }.get(mode, "")

    @staticmethod
    def _pct_delta(current, previous):
        if not previous:
            return None
        return round((current - previous) / abs(previous) * 100.0, 1)

    # ------------------------------------------------------------------
    # Account-type queries
    # ------------------------------------------------------------------
    @api.model
    def _sum_by_account_type(self, account_types, date_from, date_to, company_ids, signed=False):
        """Return signed sum from account.move.line for given account types.

        For P&L accounts (income/expense) we return debit-credit-inverted-for-display:
          - income accounts have credit > debit, so we return credit - debit (positive)
          - expense accounts have debit > credit, so we return debit - credit (positive)
        For balance-sheet accounts we return debit - credit when `signed=True`.
        """
        if not account_types:
            return 0.0
        AML = self.env["account.move.line"]
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "in", company_ids),
            ("account_id.account_type", "in", account_types),
        ]
        if date_from:
            domain.append(("date", ">=", fields.Date.to_string(date_from)))
        if date_to:
            domain.append(("date", "<=", fields.Date.to_string(date_to)))

        groups = AML._read_group(domain, [], ["debit:sum", "credit:sum"])
        if not groups:
            return 0.0
        debit, credit = groups[0][0] or 0.0, groups[0][1] or 0.0

        if signed:
            return debit - credit
        # Income → credit-debit positive. Expense → debit-credit positive.
        is_income = any(t.startswith("income") for t in account_types)
        return (credit - debit) if is_income else (debit - credit)

    # ------------------------------------------------------------------
    # Charts
    # ------------------------------------------------------------------
    @api.model
    def _chart_revenue_vs_expenses(self, options):
        date_to = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        months = []
        revenues = []
        expenses = []
        cursor = date(date_to.year, date_to.month, 1) - relativedelta(months=11)
        for _i in range(12):
            month_end = cursor + relativedelta(months=1) - timedelta(days=1)
            revenues.append(
                float_round(
                    self._sum_by_account_type(["income", "income_other"], cursor, month_end, company_ids),
                    precision_digits=2,
                )
            )
            expenses.append(
                float_round(
                    self._sum_by_account_type(
                        ["expense", "expense_depreciation", "expense_direct_cost"],
                        cursor,
                        month_end,
                        company_ids,
                    ),
                    precision_digits=2,
                )
            )
            months.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)
        return {"labels": months, "revenue": revenues, "expenses": expenses}

    @api.model
    def _chart_cash_trend(self, options):
        date_to = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        labels, balances = [], []
        cursor = date(date_to.year, date_to.month, 1) - relativedelta(months=11)
        for _i in range(12):
            month_end = cursor + relativedelta(months=1) - timedelta(days=1)
            balance = self._sum_by_account_type(
                ["asset_cash"], None, month_end, company_ids, signed=True
            )
            labels.append(cursor.strftime("%b %Y"))
            balances.append(float_round(balance, precision_digits=2))
            cursor += relativedelta(months=1)
        return {"labels": labels, "balance": balances}

    @api.model
    def _chart_top_customers(self, options):
        date_from = options["date_from"]
        date_to = options["date_to"]
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]
        rows = AML._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("date", ">=", date_from),
                ("date", "<=", date_to),
                ("partner_id", "!=", False),
            ],
            groupby=["partner_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="credit:sum desc",
            limit=5,
        )
        labels, values = [], []
        for partner, debit, credit in rows:
            labels.append(partner.display_name)
            values.append(float_round((credit or 0.0) - (debit or 0.0), precision_digits=2))
        return {"labels": labels, "values": values}

    @api.model
    def _chart_ar_aging(self, options):
        """Quick aging snapshot: 0-30, 31-60, 61-90, 91+."""
        date_to = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]
        lines = AML.search_read(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("account_id.account_type", "=", "asset_receivable"),
                ("reconciled", "=", False),
                ("date_maturity", "!=", False),
            ],
            fields=["date_maturity", "amount_residual"],
        )
        buckets = defaultdict(float)
        for line in lines:
            due = line["date_maturity"]
            if not due:
                continue
            days = (date_to - due).days
            if days <= 30:
                buckets[_("0-30")] += line["amount_residual"]
            elif days <= 60:
                buckets[_("31-60")] += line["amount_residual"]
            elif days <= 90:
                buckets[_("61-90")] += line["amount_residual"]
            else:
                buckets[_("91+")] += line["amount_residual"]
        labels = [_("0-30"), _("31-60"), _("61-90"), _("91+")]
        return {"labels": labels, "values": [float_round(buckets[l], precision_digits=2) for l in labels]}

    # ------------------------------------------------------------------
    # Drill-down
    # ------------------------------------------------------------------
    @api.model
    def action_drilldown(self, kpi, options):
        """Return an act_window descriptor for the journal entries behind a KPI."""
        options = self._sanitize_options(options or {})
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "in", options["company_ids"]),
        ]
        type_map = {
            "revenue": (["income", "income_other"], True),
            "expenses": (["expense", "expense_depreciation", "expense_direct_cost"], True),
            "cash": (["asset_cash"], False),
            "accounts_receivable": (["asset_receivable"], False),
            "accounts_payable": (["liability_payable"], False),
        }
        if kpi not in type_map:
            return False
        account_types, period_filter = type_map[kpi]
        domain.append(("account_id.account_type", "in", account_types))
        if period_filter:
            domain.append(("date", ">=", options["date_from"]))
        domain.append(("date", "<=", options["date_to"]))
        return {
            "type": "ir.actions.act_window",
            "name": _("Journal entries — %s", kpi.replace("_", " ").title()),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": domain,
            "context": {"search_default_group_by_account": 1},
        }
