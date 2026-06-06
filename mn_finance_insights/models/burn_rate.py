# -*- coding: utf-8 -*-
"""Burn Rate & Runway.

Burn = -(net cash change) when negative. We compute monthly net cash change
for last N months, then derive:
  * Current burn (last 3 months avg)
  * 6-month burn
  * 12-month burn
  * Cash on hand
  * Runway months at each burn rate
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class BurnRate(models.AbstractModel):
    _name = "finance.burn.rate"
    _description = "Burn Rate & Runway"

    @api.model
    def get_burn_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]

        months = options["months"]
        labels, cash_balances, net_changes = [], [], []
        cursor = date(as_of.year, as_of.month, 1) - relativedelta(months=months - 1)
        previous_balance = self._cash_balance(cursor - timedelta(days=1), company_ids)
        for _i in range(months):
            month_end = min(cursor + relativedelta(months=1) - timedelta(days=1), as_of)
            balance = self._cash_balance(month_end, company_ids)
            net = balance - previous_balance
            labels.append(cursor.strftime("%b %Y"))
            cash_balances.append(float_round(balance, 2))
            net_changes.append(float_round(net, 2))
            previous_balance = balance
            cursor += relativedelta(months=1)

        cash = cash_balances[-1] if cash_balances else 0.0

        def avg_burn(n):
            tail = net_changes[-n:]
            losses = [-x for x in tail if x < 0]
            return (sum(losses) / len(tail)) if tail else 0.0

        burn_3 = avg_burn(3)
        burn_6 = avg_burn(6)
        burn_12 = avg_burn(12)

        def runway(burn):
            return (cash / burn) if burn > 0 else None

        currency = self.env.company.currency_id
        return {
            "options": options,
            "cash": float_round(cash, 2),
            "burn_3":  float_round(burn_3, 2),
            "burn_6":  float_round(burn_6, 2),
            "burn_12": float_round(burn_12, 2),
            "runway_3":  None if runway(burn_3)  is None else float_round(runway(burn_3),  1),
            "runway_6":  None if runway(burn_6)  is None else float_round(runway(burn_6),  1),
            "runway_12": None if runway(burn_12) is None else float_round(runway(burn_12), 1),
            "labels": labels,
            "cash_balances": cash_balances,
            "net_changes": net_changes,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "months": int(options.get("months") or 12),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _cash_balance(self, as_of, company_ids):
        rows = self.env["account.move.line"]._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "=", "asset_cash"),
                    ("date", "<=", fields.Date.to_string(as_of))],
            groupby=[], aggregates=["debit:sum", "credit:sum"],
        )
        if not rows:
            return 0.0
        d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
        return d - c
