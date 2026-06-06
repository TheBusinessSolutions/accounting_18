# -*- coding: utf-8 -*-
"""Pricing Power Index — average discount % trend."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class PricingPower(models.AbstractModel):
    _name = "finance.pricing.power"
    _description = "Pricing Power Index"

    @api.model
    def get_pricing_data(self, options=None):
        options = self._sanitize(options or {})
        as_of = fields.Date.from_string(options["as_of"])
        company_ids = options["company_ids"]
        Move = self.env["account.move"]

        df = date(as_of.year, as_of.month, 1) - relativedelta(months=11)
        labels, disc_pct, list_total, net_total = [], [], [], []
        cursor = df
        for _i in range(12):
            end = cursor + relativedelta(months=1) - timedelta(days=1)
            moves = Move.search([("state", "=", "posted"),
                                 ("move_type", "=", "out_invoice"),
                                 ("company_id", "in", company_ids),
                                 ("invoice_date", ">=", fields.Date.to_string(cursor)),
                                 ("invoice_date", "<=", fields.Date.to_string(end))])
            gross = 0.0; net = 0.0
            for m in moves:
                for ln in m.invoice_line_ids:
                    if ln.display_type and ln.display_type != "product":
                        continue
                    gross += ln.price_unit * ln.quantity
                    net += ln.price_subtotal
            disc = (gross - net) / gross * 100 if gross else 0
            labels.append(cursor.strftime("%b %Y"))
            disc_pct.append(float_round(disc, 2))
            list_total.append(float_round(gross, 2))
            net_total.append(float_round(net, 2))
            cursor += relativedelta(months=1)

        avg_disc = sum(disc_pct) / len(disc_pct) if disc_pct else 0
        # Power index: 100 - avg discount (so 100 = no discounts, 0 = full discount)
        power_idx = max(0, 100 - avg_disc)
        currency = self.env.company.currency_id
        return {"options": options,
                "labels": labels, "disc_pct": disc_pct,
                "list_total": list_total, "net_total": net_total,
                "avg_disc": float_round(avg_disc, 1),
                "power_index": float_round(power_idx, 1),
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"as_of": options.get("as_of") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
