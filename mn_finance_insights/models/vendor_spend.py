# -*- coding: utf-8 -*-
"""Vendor Spend Analysis & Concentration."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class VendorSpend(models.AbstractModel):
    _name = "finance.vendor.spend"
    _description = "Vendor Spend Analysis"

    @api.model
    def get_vendor_data(self, options=None):
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
            groupby=["partner_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc")
        vendors = [{"id": p.id, "name": p.display_name,
                    "amount": float_round((d or 0) - (c or 0), 2)}
                   for (p, d, c) in rows]
        total = sum(v["amount"] for v in vendors)
        for v in vendors:
            v["pct"] = float_round((v["amount"] / total * 100) if total else 0, 1)
        # Concentration: cumulative %
        cum = 0
        for v in vendors:
            cum += v["pct"]; v["cum_pct"] = float_round(cum, 1)
        top5 = sum(v["pct"] for v in vendors[:5])
        top10 = sum(v["pct"] for v in vendors[:10])
        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": vendors[:50],
            "total": float_round(total, 2),
            "vendor_count": len(vendors),
            "top5_pct": float_round(top5, 1),
            "top10_pct": float_round(top10, 1),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
