# -*- coding: utf-8 -*-
"""Free Cash Flow — operating cash − capex."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class FreeCashFlow(models.AbstractModel):
    _name = "finance.free.cash.flow"
    _description = "Free Cash Flow"

    @api.model
    def get_fcf_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # YTD operating cash flow approximation: net income + non-cash (depreciation) + ΔAR + ΔAP + Δinventory
        ystart = date(as_of.year, 1, 1)

        def flow(types, df, dt, is_income):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return ((c or 0) - (d or 0)) if is_income else ((d or 0) - (c or 0))

        def bal(types, dt, signed=True):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("account_id.account_type", "in", types),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return ((d or 0) - (c or 0)) if signed else ((c or 0) - (d or 0))

        revenue = flow(["income", "income_other"], ystart, as_of, True)
        expense = flow(["expense", "expense_direct_cost"], ystart, as_of, False)
        depreciation = flow(["expense_depreciation"], ystart, as_of, False)
        net_income = revenue - expense - depreciation

        ar_change = bal(["asset_receivable"], as_of) - bal(["asset_receivable"], ystart - timedelta(days=1))
        ap_change = -bal(["liability_payable"], as_of) - (-bal(["liability_payable"], ystart - timedelta(days=1)))
        inv_change = bal(["asset_current"], as_of) - bal(["asset_current"], ystart - timedelta(days=1))

        # Operating cash = net income + dep − ΔAR + ΔAP − Δinv
        operating_cash = net_income + depreciation - ar_change + ap_change - inv_change
        # Capex = change in fixed assets (net of disposals approximated by debit balance change)
        fixed_change = bal(["asset_fixed"], as_of) - bal(["asset_fixed"], ystart - timedelta(days=1))
        capex = fixed_change
        fcf = operating_cash - capex

        currency = self.env.company.currency_id
        return {"options": options,
                "net_income": float_round(net_income, 2),
                "depreciation": float_round(depreciation, 2),
                "ar_change": float_round(ar_change, 2),
                "ap_change": float_round(ap_change, 2),
                "inv_change": float_round(inv_change, 2),
                "operating_cash": float_round(operating_cash, 2),
                "capex": float_round(capex, 2),
                "free_cash_flow": float_round(fcf, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
