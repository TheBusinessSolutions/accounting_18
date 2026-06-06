# -*- coding: utf-8 -*-
"""Anomalous Transactions — z-score outliers per account."""
from datetime import date
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class AnomalousTransactions(models.AbstractModel):
    _name = "finance.anomalous.transactions"
    _description = "Anomalous Transactions"

    @api.model
    def get_anomaly_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        z_threshold = float(options.get("z_threshold") or 2.5)

        AML = self.env["account.move.line"]
        lines = AML.search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            fields=["account_id", "move_id", "partner_id", "debit", "credit", "date", "name"],
            limit=10000)
        # per account stats
        per_acc = defaultdict(list)
        for ln in lines:
            ln["amount"] = abs(ln["debit"] - ln["credit"])
            per_acc[ln["account_id"][0] if ln["account_id"] else 0].append(ln["amount"])
        stats = {}
        for acc_id, amounts in per_acc.items():
            n = len(amounts)
            if n < 5: continue
            mean = sum(amounts) / n
            var = sum((a - mean) ** 2 for a in amounts) / n
            stddev = var ** 0.5
            stats[acc_id] = (mean, stddev)
        out = []
        for ln in lines:
            acc_id = ln["account_id"][0] if ln["account_id"] else 0
            if acc_id not in stats: continue
            mean, stddev = stats[acc_id]
            if stddev == 0: continue
            z = (ln["amount"] - mean) / stddev
            if z >= z_threshold:
                out.append({
                    "id": ln["id"], "date": ln["date"],
                    "account": ln["account_id"][1] if ln["account_id"] else "",
                    "move": ln["move_id"][1] if ln["move_id"] else "",
                    "partner": ln["partner_id"][1] if ln["partner_id"] else "",
                    "label": ln.get("name") or "",
                    "amount": float_round(ln["amount"], 2),
                    "z_score": float_round(z, 2),
                    "expected": float_round(mean, 2),
                })
        out.sort(key=lambda r: -r["z_score"])
        currency = self.env.company.currency_id
        return {"options": options, "rows": out[:100],
                "count": len(out),
                "z_threshold": z_threshold,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "z_threshold": float(options.get("z_threshold") or 2.5),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
