# -*- coding: utf-8 -*-
"""Customer Payment Method Mix — breakdown by payment journal."""
from datetime import date
from odoo import _, api, fields, models
from odoo.tools import float_round


class PaymentMethodMix(models.AbstractModel):
    _name = "finance.payment.method.mix"
    _description = "Payment Method Mix"

    @api.model
    def get_mix_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # inbound payments (customer payments) — debit on bank/cash, payment journal
        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("account_id.account_type", "=", "asset_cash"),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=["journal_id"], aggregates=["debit:sum", "credit:sum"],
            order="debit:sum desc")

        in_rows = []
        out_rows = []
        for (j, d, c) in rows:
            if not j: continue
            inbound = (d or 0)
            outbound = (c or 0)
            if inbound:
                in_rows.append({"id": j.id, "name": j.name, "amount": float_round(inbound, 2)})
            if outbound:
                out_rows.append({"id": j.id, "name": j.name, "amount": float_round(outbound, 2)})

        in_total = sum(r["amount"] for r in in_rows)
        out_total = sum(r["amount"] for r in out_rows)
        for r in in_rows: r["pct"] = float_round((r["amount"] / in_total * 100) if in_total else 0, 1)
        for r in out_rows: r["pct"] = float_round((r["amount"] / out_total * 100) if out_total else 0, 1)

        currency = self.env.company.currency_id
        return {"options": options,
                "inbound": in_rows, "outbound": out_rows,
                "in_total": float_round(in_total, 2),
                "out_total": float_round(out_total, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
