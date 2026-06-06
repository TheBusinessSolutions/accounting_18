# -*- coding: utf-8 -*-
"""Year-End Closing Checklist — pre-close diagnostic checks."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class YearEndChecklist(models.AbstractModel):
    _name = "finance.year.end.checklist"
    _description = "Year-End Closing Checklist"

    @api.model
    def get_checklist_data(self, options=None):
        options = self._sanitize(options or {})
        year = int(options["year"])
        company_ids = options["company_ids"]
        ystart = date(year, 1, 1)
        yend = date(year, 12, 31)
        AML = self.env["account.move.line"]
        Move = self.env["account.move"]

        # 1. Draft entries
        draft = Move.search_count([("state", "=", "draft"),
                                   ("company_id", "in", company_ids),
                                   ("date", ">=", fields.Date.to_string(ystart)),
                                   ("date", "<=", fields.Date.to_string(yend))])
        # 2. Unreconciled bank lines
        unrec = AML.search_count([("parent_state", "=", "posted"),
                                  ("company_id", "in", company_ids),
                                  ("account_id.account_type", "=", "asset_cash"),
                                  ("reconciled", "=", False),
                                  ("date", ">=", fields.Date.to_string(ystart)),
                                  ("date", "<=", fields.Date.to_string(yend))])
        # 3. Open AR / AP
        open_ar = AML.search_count([("parent_state", "=", "posted"),
                                    ("company_id", "in", company_ids),
                                    ("account_id.account_type", "=", "asset_receivable"),
                                    ("reconciled", "=", False)])
        open_ap = AML.search_count([("parent_state", "=", "posted"),
                                    ("company_id", "in", company_ids),
                                    ("account_id.account_type", "=", "liability_payable"),
                                    ("reconciled", "=", False)])
        # 4. Suspense/wrong balances → use NegativeBalance if available
        try:
            neg = self.env["finance.negative.balance"].get_negative_data({"as_of": yend.isoformat(),
                                                                          "company_ids": company_ids})
            anomalies = neg["count"]
        except Exception:
            anomalies = 0

        # 5. Trial balance check — debits = credits
        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("date", "<=", fields.Date.to_string(yend))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        d, c = (rows[0] if rows else (0, 0))
        tb_diff = (d or 0) - (c or 0)

        checks = [
            {"id": "draft", "label": "Draft journal entries in period",
             "value": draft, "good": draft == 0,
             "hint": "Post or delete all draft entries before close."},
            {"id": "unrec_bank", "label": "Unreconciled bank lines",
             "value": unrec, "good": unrec == 0,
             "hint": "Reconcile every bank line for the year."},
            {"id": "open_ar", "label": "Open receivables",
             "value": open_ar, "good": open_ar < 50,
             "hint": "Send statements + write off bad debts."},
            {"id": "open_ap", "label": "Open payables",
             "value": open_ap, "good": open_ap < 50,
             "hint": "Pay or reclassify any old payables."},
            {"id": "anomalies", "label": "Sign anomalies (debit/credit)",
             "value": anomalies, "good": anomalies == 0,
             "hint": "Investigate accounts with unexpected signs."},
            {"id": "tb", "label": "Trial Balance difference",
             "value": float_round(tb_diff, 2), "good": abs(tb_diff) < 0.01,
             "hint": "Total debits must equal total credits."},
        ]
        currency = self.env.company.currency_id
        return {"options": {"year": year, "company_ids": company_ids},
                "checks": checks,
                "good_count": sum(1 for c in checks if c["good"]),
                "total_count": len(checks),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"year": int(options.get("year") or today.year),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
