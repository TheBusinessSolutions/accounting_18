# -*- coding: utf-8 -*-
"""Cash Position 360 — daily running balance across all bank/cash accounts."""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class CashPosition(models.AbstractModel):
    _name = "finance.cash.position"
    _description = "Cash Position 360"

    @api.model
    def get_cash_position_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        # All cash accounts
        accounts = self.env["account.account"].search([
            ("account_type", "=", "asset_cash"),
            ("company_ids", "in", company_ids),
        ])

        labels, totals_by_day = [], []
        per_account_series = {a.id: {"id": a.id, "code": a.code, "name": a.name, "values": []} for a in accounts}

        # opening balance per account
        opening = {a.id: self._balance_at(a.id, df - timedelta(days=1)) for a in accounts}

        cursor = df
        while cursor <= dt:
            labels.append(cursor.isoformat())
            day_total = 0.0
            for acc in accounts:
                # add daily net to running balance
                net = self._daily_net(acc.id, cursor)
                opening[acc.id] += net
                bal = float_round(opening[acc.id], 2)
                per_account_series[acc.id]["values"].append(bal)
                day_total += bal
            totals_by_day.append(float_round(day_total, 2))
            cursor += timedelta(days=1)

        # reconciliation status — % reconciled lines per bank
        bank_status = []
        for acc in accounts:
            recd, total = self._reconciliation_stats(acc.id, company_ids)
            bank_status.append({
                "id": acc.id, "code": acc.code, "name": acc.name,
                "balance": float_round(opening[acc.id], 2),
                "reconciled_pct": float_round((recd / total * 100.0) if total else 100.0, 1),
            })

        currency = self.env.company.currency_id
        return {
            "options": options,
            "labels": labels,
            "totals_by_day": totals_by_day,
            "per_account": list(per_account_series.values()),
            "bank_status": bank_status,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        df = options.get("date_from") or (today - relativedelta(months=3)).isoformat()
        dt = options.get("date_to")   or today.isoformat()
        return {
            "date_from": df, "date_to": dt,
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _balance_at(self, account_id, as_of):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"), ("account_id", "=", account_id),
                    ("date", "<=", fields.Date.to_string(as_of))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return d - c

    @api.model
    def _daily_net(self, account_id, day):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"), ("account_id", "=", account_id),
                    ("date", "=", fields.Date.to_string(day))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return d - c

    @api.model
    def _reconciliation_stats(self, account_id, company_ids):
        AML = self.env["account.move.line"]
        all_lines = AML.search_count([
            ("account_id", "=", account_id),
            ("company_id", "in", company_ids),
            ("parent_state", "=", "posted"),
        ])
        recd = AML.search_count([
            ("account_id", "=", account_id),
            ("company_id", "in", company_ids),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", True),
        ])
        return recd, all_lines
