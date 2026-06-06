# -*- coding: utf-8 -*-
"""Bank Reconciliation Status."""
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class BankRecStatus(models.AbstractModel):
    _name = "finance.bank.reconciliation"
    _description = "Bank Reconciliation Status"

    @api.model
    def get_rec_data(self, options=None):
        options = self._sanitize(options or {})
        company_ids = options["company_ids"]
        today = fields.Date.context_today(self)

        cash_accounts = self.env["account.account"].search([
            ("account_type", "=", "asset_cash"),
            ("company_ids", "in", company_ids),
        ])
        AML = self.env["account.move.line"]
        out = []
        for acc in cash_accounts:
            total = AML.search_count([("account_id", "=", acc.id), ("parent_state", "=", "posted")])
            rec_count = AML.search_count([("account_id", "=", acc.id), ("parent_state", "=", "posted"), ("reconciled", "=", True)])
            unrec_count = total - rec_count
            # oldest unreconciled
            oldest = AML.search([("account_id", "=", acc.id), ("parent_state", "=", "posted"), ("reconciled", "=", False)],
                                order="date asc", limit=1)
            oldest_date = oldest.date if oldest else None
            oldest_days = (today - oldest_date).days if oldest_date else 0
            unrec_amount = sum(AML.search([("account_id", "=", acc.id), ("parent_state", "=", "posted"), ("reconciled", "=", False)]).mapped("amount_residual"))
            out.append({
                "id": acc.id, "code": acc.code, "name": acc.name,
                "total": total, "reconciled": rec_count, "unreconciled": unrec_count,
                "rec_pct": float_round((rec_count / total * 100) if total else 100, 1),
                "oldest_unreconciled_date": oldest_date.isoformat() if oldest_date else None,
                "oldest_unreconciled_days": oldest_days,
                "unreconciled_amount": float_round(unrec_amount, 2),
            })
        currency = self.env.company.currency_id
        return {
            "options": options, "rows": out,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        return {"company_ids": list(options.get("company_ids") or self.env.companies.ids)}
