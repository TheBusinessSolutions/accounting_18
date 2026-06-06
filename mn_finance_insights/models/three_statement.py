# -*- coding: utf-8 -*-
"""Three-Statement Linked View — P&L + Cash + BS summary on one screen."""
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class ThreeStatement(models.AbstractModel):
    _name = "finance.three.statement"
    _description = "Three-Statement Linked View"

    @api.model
    def get_three_statement_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        # P&L
        revenue = self._flow(["income", "income_other"], df, dt, company_ids, is_income=True)
        cogs    = self._flow(["expense_direct_cost"],   df, dt, company_ids, is_income=False)
        opex    = self._flow(["expense"],               df, dt, company_ids, is_income=False)
        depr    = self._flow(["expense_depreciation"],  df, dt, company_ids, is_income=False)
        gross_profit = revenue - cogs
        operating_profit = gross_profit - opex - depr
        net_income = operating_profit

        # Cash
        cash_open  = self._balance(["asset_cash"], df - relativedelta(days=1), company_ids, signed=True)
        cash_close = self._balance(["asset_cash"], dt, company_ids, signed=True)
        net_cash_change = cash_close - cash_open

        # Balance Sheet @ dt
        ca = self._balance(["asset_receivable","asset_cash","asset_current","asset_prepayments"],
                           dt, company_ids, signed=True)
        nca = self._balance(["asset_non_current","asset_fixed"], dt, company_ids, signed=True)
        total_assets = ca + nca
        cl = -self._balance(["liability_payable","liability_credit_card","liability_current"],
                            dt, company_ids, signed=True)
        ncl = -self._balance(["liability_non_current"], dt, company_ids, signed=True)
        total_liab = cl + ncl
        equity = -self._balance(["equity","equity_unaffected"], dt, company_ids, signed=True)

        currency = self.env.company.currency_id

        def r(v): return float_round(v, 2)

        return {
            "options": options,
            "pnl": {
                "revenue": r(revenue), "cogs": r(cogs), "gross_profit": r(gross_profit),
                "opex": r(opex), "depreciation": r(depr),
                "operating_profit": r(operating_profit), "net_income": r(net_income),
                "gross_margin_pct": r((gross_profit / revenue * 100) if revenue else 0),
                "net_margin_pct":   r((net_income   / revenue * 100) if revenue else 0),
            },
            "cash": {
                "opening": r(cash_open), "closing": r(cash_close),
                "net_change": r(net_cash_change),
            },
            "balance_sheet": {
                "current_assets": r(ca), "non_current_assets": r(nca), "total_assets": r(total_assets),
                "current_liab": r(cl), "non_current_liab": r(ncl), "total_liab": r(total_liab),
                "equity": r(equity),
                "balance_diff": r(total_assets - (total_liab + equity)),
            },
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
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
