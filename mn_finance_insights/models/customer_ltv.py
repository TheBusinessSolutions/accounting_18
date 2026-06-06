# -*- coding: utf-8 -*-
"""Customer Lifetime Value — total revenue per customer over all time."""
from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerLTV(models.AbstractModel):
    _name = "finance.customer.ltv"
    _description = "Customer Lifetime Value"

    @api.model
    def get_ltv_data(self, options=None):
        options = self._sanitize(options or {})
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
            ("account_id.account_type", "in", ["income", "income_other"]),
            ("partner_id", "!=", False)],
            groupby=["partner_id"], aggregates=["debit:sum", "credit:sum"],
            order="credit:sum desc", limit=100)

        Move = self.env["account.move"]
        out = []
        for (p, d, c) in rows:
            ltv = (c or 0) - (d or 0)
            # first + last invoice date
            firsts = Move.search([("partner_id", "=", p.id),
                                  ("move_type", "in", ["out_invoice", "out_refund"]),
                                  ("state", "=", "posted")],
                                 order="invoice_date asc", limit=1)
            lasts = Move.search([("partner_id", "=", p.id),
                                 ("move_type", "in", ["out_invoice", "out_refund"]),
                                 ("state", "=", "posted")],
                                order="invoice_date desc", limit=1)
            invoice_count = Move.search_count([("partner_id", "=", p.id),
                                               ("move_type", "=", "out_invoice"),
                                               ("state", "=", "posted")])
            first_date = firsts.invoice_date.isoformat() if firsts and firsts.invoice_date else None
            last_date = lasts.invoice_date.isoformat() if lasts and lasts.invoice_date else None
            tenure_days = ((lasts.invoice_date - firsts.invoice_date).days
                           if firsts and lasts and firsts.invoice_date and lasts.invoice_date else 0)
            avg_invoice = (ltv / invoice_count) if invoice_count else 0
            out.append({"id": p.id, "name": p.display_name,
                        "ltv": float_round(ltv, 2),
                        "invoices": invoice_count,
                        "avg_invoice": float_round(avg_invoice, 2),
                        "first_date": first_date, "last_date": last_date,
                        "tenure_days": tenure_days})
        total_ltv = sum(r["ltv"] for r in out)
        currency = self.env.company.currency_id
        return {"options": options, "rows": out,
                "total_ltv": float_round(total_ltv, 2),
                "customer_count": len(out),
                "avg_ltv": float_round((total_ltv / len(out)) if out else 0, 2),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        return {"company_ids": list(options.get("company_ids") or self.env.companies.ids)}
