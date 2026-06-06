# -*- coding: utf-8 -*-
"""Receivables Forecast — open AR converts to cash, by maturity week."""
from datetime import timedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class ReceivablesForecast(models.AbstractModel):
    _name = "finance.receivables.forecast"
    _description = "Receivables Forecast"

    @api.model
    def get_forecast_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        horizon = int(options.get("horizon") or 12)
        company_ids = options["company_ids"]

        lines = self.env["account.move.line"].search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "asset_receivable"),
            ("reconciled", "=", False), ("amount_residual", "!=", 0)],
            fields=["amount_residual", "date_maturity"])

        buckets = [0.0] * horizon
        overdue = 0.0
        for ln in lines:
            due = ln["date_maturity"] or as_of
            week = (due - as_of).days // 7
            if week < 0:
                overdue += ln["amount_residual"]
            elif week < horizon:
                buckets[week] += ln["amount_residual"]
        labels = [f"W{i+1}" for i in range(horizon)]
        total = sum(buckets) + overdue
        cumulative, cum = [], 0
        for v in buckets:
            cum += v
            cumulative.append(float_round(cum, 2))
        currency = self.env.company.currency_id
        return {"options": options, "labels": labels,
                "values": [float_round(v, 2) for v in buckets],
                "cumulative": cumulative,
                "overdue": float_round(overdue, 2),
                "total": float_round(total, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "horizon": int(options.get("horizon") or 12),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
