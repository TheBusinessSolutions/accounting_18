# -*- coding: utf-8 -*-
"""Customer Risk Score (0-100).

Composite of:
  * DSO factor          — 0 (good) to 30 (>120 days)
  * Aging factor        — % of AR > 90 days, scaled 0-25
  * Late-payment factor — % of invoices paid late, scaled 0-25
  * Credit usage        — current AR / credit limit, scaled 0-20

Score 0 = great. Score 100 = terrible. Maps to good/ok/bad.
"""
from datetime import date

from odoo import _, api, fields, models
from odoo.tools import float_round


class CustomerRisk(models.AbstractModel):
    _name = "finance.customer.risk"
    _description = "Customer Risk Score"

    @api.model
    def get_risk_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]
        Move = self.env["account.move"]

        # Collect partners with any AR activity
        partners = self.env["res.partner"].search([("customer_rank", ">", 0)])
        # Also include any partner with an unreconciled receivable line
        partner_ids_with_ar = AML._read_group(
            domain=[("parent_state", "=", "posted"),
                    ("company_id", "in", company_ids),
                    ("account_id.account_type", "=", "asset_receivable"),
                    ("reconciled", "=", False),
                    ("partner_id", "!=", False)],
            groupby=["partner_id"],
            aggregates=["debit:sum"],
        )
        partner_set = {p.id for (p, _) in partner_ids_with_ar} | set(partners.ids)

        rows = []
        for pid in partner_set:
            partner = self.env["res.partner"].browse(pid).exists()
            if not partner:
                continue

            # Open AR
            open_lines = AML.search_read(
                domain=[("parent_state", "=", "posted"),
                        ("company_id", "in", company_ids),
                        ("partner_id", "=", pid),
                        ("account_id.account_type", "=", "asset_receivable"),
                        ("reconciled", "=", False),
                        ("amount_residual", "!=", 0)],
                fields=["amount_residual", "date_maturity"],
            )
            if not open_lines and not partner.credit_limit:
                continue
            ar_total = sum(l["amount_residual"] for l in open_lines)
            ar_over_90 = sum(l["amount_residual"] for l in open_lines
                             if l["date_maturity"] and (as_of - l["date_maturity"]).days > 90)
            aging_pct = (ar_over_90 / ar_total * 100.0) if ar_total else 0.0

            # DSO — AR / (revenue/period) × period days
            year_start = date(as_of.year, 1, 1)
            days = max(1, (as_of - year_start).days + 1)
            rev_rows = AML._read_group(
                domain=[("parent_state", "=", "posted"),
                        ("company_id", "in", company_ids),
                        ("partner_id", "=", pid),
                        ("account_id.account_type", "in", ["income", "income_other"]),
                        ("date", ">=", fields.Date.to_string(year_start)),
                        ("date", "<=", fields.Date.to_string(as_of))],
                groupby=[], aggregates=["debit:sum", "credit:sum"],
            )
            d_r, c_r = (rev_rows[0] if rev_rows else (0, 0))
            revenue = (c_r or 0) - (d_r or 0)
            dso = (ar_total / revenue * days) if revenue else 0

            # late payment % — paid invoices that were paid after due date
            paid_moves = Move.search([
                ("partner_id", "=", pid),
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "=", "paid"),
                ("company_id", "in", company_ids),
                ("invoice_date", ">=", fields.Date.to_string(year_start)),
            ])
            late = sum(
                1 for m in paid_moves
                if m.invoice_date_due
                and m.write_date.date() > m.invoice_date_due
            )
            late_pct = (late / len(paid_moves) * 100.0) if paid_moves else 0.0

            # credit usage
            credit_limit = partner.credit_limit or 0.0
            credit_usage = (ar_total / credit_limit * 100.0) if credit_limit else 0.0

            # Score components (higher = worse)
            dso_pts   = min(30, max(0, (dso - 30) * 0.30))           # 0 at <=30d, 30 at >=130d
            aging_pts = min(25, aging_pct * 0.25)                    # 0 at 0%, 25 at 100%
            late_pts  = min(25, late_pct * 0.25)
            credit_pts= min(20, max(0, (credit_usage - 50) * 0.40))  # 0 at <=50%, 20 at >=100%
            score = round(dso_pts + aging_pts + late_pts + credit_pts)
            health = "good" if score <= 30 else ("ok" if score <= 60 else "bad")

            rows.append({
                "partner_id": pid,
                "name": partner.display_name,
                "ar_total":      float_round(ar_total, 2),
                "ar_over_90":    float_round(ar_over_90, 2),
                "aging_pct":     float_round(aging_pct, 1),
                "dso":           float_round(dso, 0),
                "late_pct":      float_round(late_pct, 1),
                "credit_limit":  float_round(credit_limit, 2),
                "credit_usage":  float_round(credit_usage, 1),
                "score":         score,
                "health":        health,
            })
        rows.sort(key=lambda r: -r["score"])

        currency = self.env.company.currency_id
        return {
            "options": options,
            "rows": rows,
            "summary": {
                "high_risk": sum(1 for r in rows if r["health"] == "bad"),
                "medium_risk": sum(1 for r in rows if r["health"] == "ok"),
                "low_risk": sum(1 for r in rows if r["health"] == "good"),
                "total_exposure": float_round(sum(r["ar_total"] for r in rows), 2),
                "at_risk_exposure": float_round(sum(r["ar_total"] for r in rows if r["health"] != "good"), 2),
            },
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }
