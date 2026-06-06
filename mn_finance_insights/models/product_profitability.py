# -*- coding: utf-8 -*-
"""Product Profitability Trend with Margin Erosion Alerts.

For each product sold in the period, compute monthly revenue, COGS, margin %.
Flag products whose latest-month margin dropped > threshold vs trailing 6-mo avg.
"""
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.tools import float_round


class ProductProfitability(models.AbstractModel):
    _name = "finance.product.profitability"
    _description = "Product Profitability Trend"

    @api.model
    def get_product_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        erosion_threshold = float(options.get("erosion_threshold") or 5.0)

        Move = self.env["account.move"]
        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        moves = Move.search([
            ("state", "=", "posted"),
            ("move_type", "in", ["out_invoice", "out_refund"]),
            ("invoice_date", ">=", fields.Date.to_string(df)),
            ("invoice_date", "<=", fields.Date.to_string(as_of)),
            ("company_id", "in", company_ids),
        ])

        # product -> month_index -> {revenue, cogs}
        from collections import defaultdict
        store = defaultdict(lambda: {"name": "", "revenue": [0.0]*12, "cogs": [0.0]*12})

        def month_index(d):
            return (d.year - df.year) * 12 + (d.month - df.month)

        for m in moves:
            mi = month_index(m.invoice_date)
            if mi < 0 or mi >= 12:
                continue
            sign = -1.0 if m.move_type == "out_refund" else 1.0
            for ln in m.invoice_line_ids:
                if not ln.product_id or (ln.display_type and ln.display_type != "product"):
                    continue
                rev = sign * ln.price_subtotal
                cogs = sign * ln.product_id.standard_price * ln.quantity
                d = store[ln.product_id.id]
                d["name"] = ln.product_id.display_name
                d["revenue"][mi] += rev
                d["cogs"][mi] += cogs

        labels = []
        cursor = df
        for _i in range(12):
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)

        rows = []
        for pid, d in store.items():
            margins = []
            for r, c in zip(d["revenue"], d["cogs"]):
                if r:
                    margins.append((r - c) / r * 100.0)
                else:
                    margins.append(None)
            last = margins[-1]
            trail = [v for v in margins[-7:-1] if v is not None]
            trail_avg = sum(trail) / len(trail) if trail else None
            erosion = None
            if last is not None and trail_avg is not None:
                erosion = trail_avg - last
            alert = (erosion is not None and erosion >= erosion_threshold)
            total_rev = sum(d["revenue"])
            total_cogs = sum(d["cogs"])
            total_margin = ((total_rev - total_cogs) / total_rev * 100.0) if total_rev else 0.0
            rows.append({
                "product_id": pid,
                "name": d["name"],
                "revenue_series": [float_round(x, 2) for x in d["revenue"]],
                "margin_series":  [None if v is None else float_round(v, 1) for v in margins],
                "total_revenue":  float_round(total_rev, 2),
                "total_margin":   float_round(total_margin, 1),
                "last_margin":    None if last is None else float_round(last, 1),
                "trail_avg":      None if trail_avg is None else float_round(trail_avg, 1),
                "erosion":        None if erosion is None else float_round(erosion, 1),
                "alert":          alert,
            })
        rows.sort(key=lambda r: -r["total_revenue"])
        rows = rows[:30]

        currency = self.env.company.currency_id
        return {
            "options": options,
            "labels": labels,
            "rows": rows,
            "erosion_threshold": erosion_threshold,
            "alert_count": sum(1 for r in rows if r["alert"]),
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "erosion_threshold": options.get("erosion_threshold") or 5.0,
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }
