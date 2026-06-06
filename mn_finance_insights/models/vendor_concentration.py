# -*- coding: utf-8 -*-
"""Vendor Concentration (Pareto 80/20)."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class VendorConcentration(models.AbstractModel):
    _name = "finance.vendor.concentration"
    _description = "Vendor Concentration (Pareto)"

    @api.model
    def get_concentration_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
            ("account_id.account_type", "in", ["expense","expense_direct_cost","expense_depreciation"]),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt)),
            ("partner_id", "!=", False)],
            groupby=["partner_id"], aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc")
        vendors = [{"id": p.id, "name": p.display_name,
                    "amount": float_round((d or 0) - (c or 0), 2)} for (p, d, c) in rows]
        total = sum(v["amount"] for v in vendors) or 1
        cum = 0
        eighty_index = None
        for i, v in enumerate(vendors):
            v["pct"] = float_round(v["amount"] / total * 100, 1)
            cum += v["pct"]; v["cum_pct"] = float_round(cum, 1)
            if eighty_index is None and cum >= 80:
                eighty_index = i + 1
        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": vendors[:50],
            "total": float_round(total, 2),
            "vendor_count": len(vendors),
            "vendors_to_80pct": eighty_index or len(vendors),
            "top5_pct": float_round(sum(v["pct"] for v in vendors[:5]), 1),
            "top10_pct": float_round(sum(v["pct"] for v in vendors[:10]), 1),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
