# -*- coding: utf-8 -*-
"""Customer Profitability — Revenue − Discounts − Returns − COGS − AR carrying cost.

AR carrying cost approximation: avg_AR × annual_cost_of_capital × (days/365).
Default cost of capital = 8% (configurable per company-wide ir.config_parameter).
"""
from datetime import date

from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerProfitability(models.AbstractModel):
    _name = "finance.customer.profitability"
    _description = "Customer Profitability Analysis"

    @api.model
    def get_profit_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        cost_of_capital = float(
            self.env["ir.config_parameter"].sudo().get_param(
                "mn_finance_insights.cost_of_capital_pct", "8.0")
        ) / 100.0
        days = max(1, (dt - df).days + 1)

        partner_data = self._aggregate(df, dt, company_ids)
        avg_ar = self._avg_ar(df, dt, company_ids)

        rows = []
        for pid, p in partner_data.items():
            revenue = p["revenue"]
            cogs = p["cogs"]
            returns = p["returns"]
            discounts = p["discounts"]
            ar_cost = (avg_ar.get(pid, 0.0)) * cost_of_capital * (days / 365.0)
            net = revenue - returns - discounts - cogs - ar_cost
            margin = (net / revenue * 100.0) if revenue else 0.0
            rows.append({
                "partner_id": pid, "name": p["name"],
                "revenue":   float_round(revenue, 2),
                "returns":   float_round(returns, 2),
                "discounts": float_round(discounts, 2),
                "cogs":      float_round(cogs, 2),
                "ar_cost":   float_round(ar_cost, 2),
                "net_profit":float_round(net, 2),
                "margin_pct":float_round(margin, 1),
            })
        rows.sort(key=lambda r: -r["net_profit"])

        currency = self.env.company.currency_id
        totals = {
            k: float_round(sum(r[k] for r in rows), 2)
            for k in ("revenue", "returns", "discounts", "cogs", "ar_cost", "net_profit")
        }
        return {
            "options": options,
            "rows": rows,
            "totals": totals,
            "cost_of_capital_pct": cost_of_capital * 100.0,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
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
    def _aggregate(self, df, dt, company_ids):
        Move = self.env["account.move"]
        moves = Move.search([
            ("state", "=", "posted"),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(dt)),
            ("company_id", "in", company_ids),
            ("partner_id", "!=", False),
        ])
        out = {}
        for m in moves:
            pid = m.partner_id.id
            d = out.setdefault(pid, {"name": m.partner_id.display_name, "revenue": 0, "cogs": 0,
                                     "returns": 0, "discounts": 0})
            sign = -1.0 if m.move_type == "out_refund" else 1.0
            for ln in m.invoice_line_ids:
                if ln.display_type and ln.display_type != "product":
                    continue
                amount = ln.price_subtotal
                disc = (ln.price_unit * ln.quantity) - ln.price_subtotal
                if m.move_type == "out_refund":
                    d["returns"] += amount
                else:
                    d["revenue"] += amount
                    if disc > 0:
                        d["discounts"] += disc
                # COGS approximation: standard_price × quantity
                if ln.product_id:
                    d["cogs"] += sign * ln.product_id.standard_price * ln.quantity
        return out

    @api.model
    def _avg_ar(self, df, dt, company_ids):
        """Average accounts-receivable balance per partner over the period.

        Approximation: half of (opening AR + closing AR) for each partner.
        """
        AML = self.env["account.move.line"]
        def balance(partner_id, as_of):
            rows = AML._read_group(
                domain=[("parent_state", "=", "posted"),
                        ("company_id", "in", company_ids),
                        ("partner_id", "=", partner_id),
                        ("account_id.account_type", "=", "asset_receivable"),
                        ("date", "<=", fields.Date.to_string(as_of))],
                groupby=[], aggregates=["debit:sum", "credit:sum"],
            )
            if not rows:
                return 0.0
            d, c = rows[0][0] or 0.0, rows[0][1] or 0.0
            return d - c
        # collect partners with AR activity
        partners = AML._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "=", "asset_receivable"),
                    ("date", ">=", fields.Date.to_string(df)),
                    ("date", "<=", fields.Date.to_string(dt))],
            groupby=["partner_id"],
            aggregates=["debit:sum"],
        )
        return {p.id: (balance(p.id, df) + balance(p.id, dt)) / 2.0 for (p, _d) in partners if p}
