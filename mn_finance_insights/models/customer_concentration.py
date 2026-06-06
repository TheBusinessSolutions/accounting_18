# -*- coding: utf-8 -*-
"""Customer Concentration (Pareto 80/20)."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerConcentration(models.AbstractModel):
    _name = "finance.customer.concentration"
    _description = "Customer Concentration (Pareto)"

    @api.model
    def get_concentration_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
            ("account_id.account_type", "in", ["income", "income_other"]),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt)),
            ("partner_id", "!=", False)],
            groupby=["partner_id"], aggregates=["debit:sum", "credit:sum"],
            order="credit:sum desc")
        customers = [{"id": p.id, "name": p.display_name,
                      "amount": float_round((c or 0) - (d or 0), 2)} for (p, d, c) in rows]
        total = sum(c["amount"] for c in customers) or 1
        cum = 0
        eighty_index = None
        for i, c in enumerate(customers):
            c["pct"] = float_round(c["amount"] / total * 100, 1)
            cum += c["pct"]
            c["cum_pct"] = float_round(cum, 1)
            if eighty_index is None and cum >= 80:
                eighty_index = i + 1
        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": customers[:50],
            "total": float_round(total, 2),
            "customer_count": len(customers),
            "customers_to_80pct": eighty_index or len(customers),
            "top5_pct": float_round(sum(c["pct"] for c in customers[:5]), 1),
            "top10_pct": float_round(sum(c["pct"] for c in customers[:10]), 1),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
