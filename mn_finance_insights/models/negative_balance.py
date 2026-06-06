# -*- coding: utf-8 -*-
"""Negative Balance Alerts — accounts with unexpected sign."""
from odoo import _, api, fields, models
from odoo.tools import float_round


# Asset / expense → normally debit (positive when d-c > 0)
NORMAL_DEBIT = ["asset_receivable", "asset_cash", "asset_current", "asset_prepayments",
                "asset_non_current", "asset_fixed", "expense", "expense_direct_cost",
                "expense_depreciation"]
# Liability / equity / income → normally credit
NORMAL_CREDIT = ["liability_payable", "liability_credit_card", "liability_current",
                 "liability_non_current", "equity", "equity_unaffected",
                 "income", "income_other"]


class NegativeBalance(models.AbstractModel):
    _name = "finance.negative.balance"
    _description = "Negative Balance Alerts"

    @api.model
    def get_negative_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("date", "<=", fields.Date.to_string(as_of))],
            groupby=["account_id"], aggregates=["debit:sum", "credit:sum"])

        anomalies = []
        for (acc, d, c) in rows:
            if not acc: continue
            debit, credit = d or 0, c or 0
            balance = debit - credit
            atype = acc.account_type
            if atype in NORMAL_DEBIT and balance < -0.01:
                anomalies.append({"id": acc.id, "code": acc.code, "name": acc.name,
                                  "type": atype, "balance": float_round(balance, 2),
                                  "severity": "bad" if abs(balance) > 1000 else "ok",
                                  "expected": "Debit (positive)"})
            elif atype in NORMAL_CREDIT and balance > 0.01:
                anomalies.append({"id": acc.id, "code": acc.code, "name": acc.name,
                                  "type": atype, "balance": float_round(balance, 2),
                                  "severity": "bad" if abs(balance) > 1000 else "ok",
                                  "expected": "Credit (negative)"})
        anomalies.sort(key=lambda r: -abs(r["balance"]))
        currency = self.env.company.currency_id
        return {"options": options, "rows": anomalies,
                "count": len(anomalies),
                "critical_count": sum(1 for a in anomalies if a["severity"] == "bad"),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
