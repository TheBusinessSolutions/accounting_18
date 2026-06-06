# -*- coding: utf-8 -*-
"""Sales Analytics — invoices grouped by salesperson / product / partner / month."""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class SalesAnalytics(models.AbstractModel):
    _name = "finance.sales.analytics"
    _description = "Sales Analytics"

    @api.model
    def get_sales_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        # KPIs
        invoice_domain = [
            ("state", "=", "posted"),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("company_id", "in", company_ids),
        ]
        Move = self.env["account.move"]
        moves = Move.search(invoice_domain)
        total_revenue = sum(m.amount_untaxed_signed for m in moves)
        invoice_count = len([m for m in moves if m.move_type == "out_invoice"])
        refund_count = len([m for m in moves if m.move_type == "out_refund"])
        avg_invoice = (total_revenue / invoice_count) if invoice_count else 0.0
        paid_amount = sum(m.amount_total_signed - m.amount_residual_signed for m in moves)
        collection_rate = (paid_amount / sum(m.amount_total_signed for m in moves) * 100.0) if moves else 0.0

        return {
            "options": options,
            "kpis": {
                "revenue":         float_round(total_revenue, 2),
                "invoice_count":   invoice_count,
                "refund_count":    refund_count,
                "avg_invoice":     float_round(avg_invoice, 2),
                "collection_rate": float_round(collection_rate, 1),
            },
            "monthly_trend": self._monthly_trend(df, dt, company_ids),
            "top_products":  self._top_products(df, dt, company_ids, limit=10),
            "top_customers": self._top_customers(df, dt, company_ids, limit=10),
            "by_salesperson": self._by_salesperson(df, dt, company_ids),
            "currency": self._currency(),
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
            "date_to":   options.get("date_to")   or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _currency(self):
        c = self.env.company.currency_id
        return {"id": c.id, "symbol": c.symbol, "decimals": c.decimal_places}

    @api.model
    def _monthly_trend(self, df, dt, company_ids):
        labels, values = [], []
        cursor = date(df.year, df.month, 1)
        while cursor <= dt:
            end = min(cursor + relativedelta(months=1) - timedelta(days=1), dt)
            rows = self.env["account.move.line"]._read_group(
                domain=[
                    ("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "in", ["income", "income_other"]),
                    ("date", ">=", fields.Date.to_string(cursor)),
                    ("date", "<=", fields.Date.to_string(end)),
                ],
                groupby=[],
                aggregates=["debit:sum", "credit:sum"],
            )
            d, c = (rows[0] if rows else (0, 0))
            values.append(float_round((c or 0) - (d or 0), 2))
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)
        return {"labels": labels, "values": values}

    @api.model
    def _top_products(self, df, dt, company_ids, limit=10):
        AML = self.env["account.move.line"]
        rows = AML._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt)),
                ("product_id", "!=", False),
            ],
            groupby=["product_id"],
            aggregates=["price_subtotal:sum", "quantity:sum"],
            order="price_subtotal:sum desc",
            limit=limit,
        )
        return [{"id": p.id, "name": p.display_name,
                 "amount": float_round(amount or 0, 2), "qty": float_round(qty or 0, 2)}
                for (p, amount, qty) in rows]

    @api.model
    def _top_customers(self, df, dt, company_ids, limit=10):
        AML = self.env["account.move.line"]
        rows = AML._read_group(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", company_ids),
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt)),
                ("partner_id", "!=", False),
                ("account_id.account_type", "in", ["income", "income_other"]),
            ],
            groupby=["partner_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="credit:sum desc",
            limit=limit,
        )
        return [{"id": p.id, "name": p.display_name,
                 "amount": float_round((c or 0) - (d or 0), 2)}
                for (p, d, c) in rows]

    @api.model
    def _by_salesperson(self, df, dt, company_ids):
        Move = self.env["account.move"]
        moves = Move.search([
            ("state", "=", "posted"),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("company_id", "in", company_ids),
            ("invoice_user_id", "!=", False),
        ])
        agg = {}
        for m in moves:
            uid = m.invoice_user_id.id
            agg.setdefault(uid, {"id": uid, "name": m.invoice_user_id.name, "amount": 0.0, "count": 0})
            agg[uid]["amount"] += m.amount_untaxed_signed
            agg[uid]["count"] += 1
        items = sorted(agg.values(), key=lambda r: -r["amount"])[:10]
        for r in items:
            r["amount"] = float_round(r["amount"], 2)
        return items
