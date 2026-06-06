# -*- coding: utf-8 -*-
"""Tax Reconciliation Audit — VAT collected vs declared vs paid."""
from datetime import date
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class TaxReconciliation(models.AbstractModel):
    _name = "finance.tax.reconciliation"
    _description = "Tax Reconciliation Audit"

    @api.model
    def get_tax_rec_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # for each tax: sum on customer + on vendor + on tax control account
        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("tax_line_id", "!=", False),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=["tax_line_id", "move_id.move_type"],
            aggregates=["debit:sum", "credit:sum"])

        agg = defaultdict(lambda: {"out_collected": 0.0, "in_paid": 0.0,
                                   "out_refund": 0.0, "in_refund": 0.0})
        for (tax, mt, d, c) in rows:
            if not tax: continue
            v = (c or 0) - (d or 0)
            if mt == "out_invoice": agg[(tax.id, tax.name)]["out_collected"] += v
            elif mt == "in_invoice": agg[(tax.id, tax.name)]["in_paid"] += -v
            elif mt == "out_refund": agg[(tax.id, tax.name)]["out_refund"] += -v
            elif mt == "in_refund": agg[(tax.id, tax.name)]["in_refund"] += v

        out = []
        for (tid, tname), d in agg.items():
            net_collected = d["out_collected"] - d["out_refund"]
            net_paid = d["in_paid"] - d["in_refund"]
            net_due = net_collected - net_paid
            out.append({"id": tid, "name": tname,
                        "out_collected": float_round(d["out_collected"], 2),
                        "out_refund": float_round(d["out_refund"], 2),
                        "in_paid": float_round(d["in_paid"], 2),
                        "in_refund": float_round(d["in_refund"], 2),
                        "net_collected": float_round(net_collected, 2),
                        "net_paid": float_round(net_paid, 2),
                        "net_due": float_round(net_due, 2)})
        out.sort(key=lambda r: -r["net_due"])
        total_due = sum(r["net_due"] for r in out)
        currency = self.env.company.currency_id
        return {"options": options, "rows": out,
                "total_due": float_round(total_due, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
