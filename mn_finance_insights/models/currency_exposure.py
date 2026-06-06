# -*- coding: utf-8 -*-
"""Currency Exposure — open balances by currency."""
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class CurrencyExposure(models.AbstractModel):
    _name = "finance.currency.exposure"
    _description = "Currency Exposure"

    @api.model
    def get_exposure_data(self, options=None):
        options = self._sanitize(options or {})
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # Group open AR/AP/cash lines by currency
        lines = AML.search_read(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "in", ["asset_receivable", "liability_payable", "asset_cash"]),
            ("currency_id", "!=", False)],
            fields=["currency_id", "account_id", "amount_currency", "amount_residual",
                    "amount_residual_currency", "reconciled"])

        agg = defaultdict(lambda: {"ar": 0.0, "ar_company": 0.0, "ap": 0.0, "ap_company": 0.0,
                                   "cash": 0.0, "cash_company": 0.0})
        company_currency = self.env.company.currency_id
        for ln in lines:
            cid = ln["currency_id"][0]
            acc = self.env["account.account"].browse(ln["account_id"][0])
            d = agg[cid]
            kind = ("ar" if acc.account_type == "asset_receivable"
                    else "ap" if acc.account_type == "liability_payable"
                    else "cash")
            if kind in ("ar", "ap") and ln["reconciled"]:
                continue
            d[kind] += ln["amount_residual_currency"] if kind != "cash" else ln["amount_currency"]
            d[kind + "_company"] += ln["amount_residual"] if kind != "cash" else 0  # cash company side approx

        rows = []
        for cid, d in agg.items():
            cur = self.env["res.currency"].browse(cid)
            net = d["ar"] + d["cash"] - abs(d["ap"])
            rows.append({
                "currency_id": cid, "code": cur.name, "symbol": cur.symbol,
                "ar": float_round(d["ar"], 2),
                "ap": float_round(-d["ap"], 2),
                "cash": float_round(d["cash"], 2),
                "net": float_round(net, 2),
                "rate": cur.rate,
            })
        rows.sort(key=lambda r: -abs(r["net"]))

        return {
            "options": options,
            "rows": rows,
            "company_currency": {"name": company_currency.name, "symbol": company_currency.symbol},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        return {"company_ids": list(options.get("company_ids") or self.env.companies.ids)}
