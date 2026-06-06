# -*- coding: utf-8 -*-
"""Financial Ratios — Liquidity, Profitability, Efficiency.

Each ratio has:
    * current value
    * health rating (good / ok / bad) against rule-of-thumb thresholds
    * 12-month sparkline trend
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


CURRENT_ASSET_TYPES = ["asset_receivable", "asset_cash", "asset_current", "asset_prepayments"]
CURRENT_LIAB_TYPES  = ["liability_payable", "liability_credit_card", "liability_current"]
ALL_ASSET_TYPES = CURRENT_ASSET_TYPES + ["asset_non_current", "asset_fixed"]
EQUITY_TYPES = ["equity", "equity_unaffected"]
INCOME_TYPES = ["income", "income_other"]
EXPENSE_TYPES = ["expense", "expense_depreciation", "expense_direct_cost"]
COGS_TYPES = ["expense_direct_cost"]


class FinancialRatios(models.AbstractModel):
    _name = "financial.ratios"
    _description = "Financial Ratios"

    @api.model
    def get_ratios_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]

        ratios = self._compute_all(as_of, company_ids)

        # 12-month sparkline: re-compute each ratio at end of each of last 12 months
        sparklines = {name: [] for name in ratios.keys()}
        labels = []
        cursor = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        for _i in range(12):
            month_end = cursor + relativedelta(months=1) - timedelta(days=1)
            snapshot = self._compute_all(month_end, company_ids)
            for name, val in snapshot.items():
                sparklines[name].append(val["value"])
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)

        return {
            "options": options,
            "ratios": ratios,
            "sparklines": sparklines,
            "sparkline_labels": labels,
            "company_name": self.env.company.name,
        }

    # ------------------------------------------------------------------
    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _compute_all(self, as_of, company_ids):
        # Year-to-date period for flow figures
        year_start = date(as_of.year, 1, 1)
        days_in_period = max(1, (as_of - year_start).days + 1)

        ca = self._sum(CURRENT_ASSET_TYPES, None, as_of, company_ids, signed=True)
        cl = -self._sum(CURRENT_LIAB_TYPES, None, as_of, company_ids, signed=True)
        cash = self._sum(["asset_cash"], None, as_of, company_ids, signed=True)
        ar = self._sum(["asset_receivable"], None, as_of, company_ids, signed=True)
        ap = -self._sum(["liability_payable"], None, as_of, company_ids, signed=True)
        total_assets = self._sum(ALL_ASSET_TYPES, None, as_of, company_ids, signed=True)
        equity = -self._sum(EQUITY_TYPES, None, as_of, company_ids, signed=True)

        revenue = self._sum_pl(INCOME_TYPES, year_start, as_of, company_ids, is_income=True)
        expenses = self._sum_pl(EXPENSE_TYPES, year_start, as_of, company_ids, is_income=False)
        cogs = self._sum_pl(COGS_TYPES, year_start, as_of, company_ids, is_income=False)
        net_profit = revenue - expenses

        def safe_div(a, b):
            return (a / b) if b else 0.0

        ratios = {
            "current_ratio": self._wrap(_("Current Ratio"), "liquidity",
                                        safe_div(ca, cl), unit="x",
                                        thresholds=(1.2, 2.0), higher_is_better=True,
                                        formula="Current Assets ÷ Current Liabilities"),
            "cash_ratio": self._wrap(_("Cash Ratio"), "liquidity",
                                     safe_div(cash, cl), unit="x",
                                     thresholds=(0.2, 0.5), higher_is_better=True,
                                     formula="Cash ÷ Current Liabilities"),
            "gross_margin": self._wrap(_("Gross Margin"), "profitability",
                                       safe_div(revenue - cogs, revenue) * 100, unit="%",
                                       thresholds=(20, 40), higher_is_better=True,
                                       formula="(Revenue − COGS) ÷ Revenue"),
            "net_margin": self._wrap(_("Net Margin"), "profitability",
                                     safe_div(net_profit, revenue) * 100, unit="%",
                                     thresholds=(5, 15), higher_is_better=True,
                                     formula="Net Profit ÷ Revenue"),
            "roa": self._wrap(_("Return on Assets"), "profitability",
                              safe_div(net_profit, total_assets) * 100, unit="%",
                              thresholds=(5, 10), higher_is_better=True,
                              formula="Net Profit ÷ Total Assets"),
            "roe": self._wrap(_("Return on Equity"), "profitability",
                              safe_div(net_profit, equity) * 100, unit="%",
                              thresholds=(10, 20), higher_is_better=True,
                              formula="Net Profit ÷ Equity"),
            "dso": self._wrap(_("Days Sales Outstanding"), "efficiency",
                              safe_div(ar, revenue) * days_in_period, unit=_("days"),
                              thresholds=(30, 60), higher_is_better=False,
                              formula="(AR ÷ Revenue) × period days"),
            "dpo": self._wrap(_("Days Payables Outstanding"), "efficiency",
                              safe_div(ap, cogs or expenses) * days_in_period, unit=_("days"),
                              thresholds=(30, 60), higher_is_better=True,
                              formula="(AP ÷ COGS) × period days"),
        }
        return ratios

    @api.model
    def _wrap(self, label, group, value, unit, thresholds, higher_is_better, formula):
        v = float_round(value, precision_digits=2)
        low, high = thresholds
        if higher_is_better:
            health = "good" if v >= high else ("ok" if v >= low else "bad")
        else:
            health = "good" if v <= low else ("ok" if v <= high else "bad")
        return {
            "label": label,
            "group": group,
            "value": v,
            "unit": unit,
            "health": health,
            "formula": formula,
        }

    @api.model
    def _sum(self, account_types, date_from, date_to, company_ids, signed=False):
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
        rows = AML._read_group(domain, [], ["debit:sum", "credit:sum"])
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return (d - c) if signed else (c - d)

    @api.model
    def _sum_pl(self, account_types, date_from, date_to, company_ids, is_income):
        AML = self.env["account.move.line"]
        domain = [
            ("parent_state", "=", "posted"),
            ("company_id", "in", company_ids),
            ("account_id.account_type", "in", account_types),
            ("date", ">=", fields.Date.to_string(date_from)),
            ("date", "<=", fields.Date.to_string(date_to)),
        ]
        rows = AML._read_group(domain, [], ["debit:sum", "credit:sum"])
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return (c - d) if is_income else (d - c)
