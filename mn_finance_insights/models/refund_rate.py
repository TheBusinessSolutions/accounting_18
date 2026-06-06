# -*- coding: utf-8 -*-
"""Refund Rate Tracker — refunds as % of revenue."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class RefundRate(models.AbstractModel):
    _name = "finance.refund.rate"
    _description = "Refund Rate Tracker"

    @api.model
    def get_refund_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        def amount(move_type):
            r = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("move_id.move_type", "=", move_type),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("date", ">=", fields.Date.to_string(df)),
                ("date", "<=", fields.Date.to_string(dt))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            if not r: return 0.0
            d, c = r[0]; return (c or 0) - (d or 0)

        gross_revenue = amount("out_invoice")
        refunds = -amount("out_refund")  # refunds are credit notes
        if refunds < 0:
            refunds = abs(refunds)
        net_revenue = gross_revenue - refunds
        refund_rate = (refunds / gross_revenue * 100) if gross_revenue else 0

        # Monthly trend
        labels, rev_series, ref_series, rate_series = [], [], [], []
        cursor = date(df.year, df.month, 1)
        while cursor <= dt:
            end = min(cursor + relativedelta(months=1) - timedelta(days=1), dt)
            r_lo = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("move_id.move_type", "=", "out_invoice"),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("date", ">=", fields.Date.to_string(cursor)),
                ("date", "<=", fields.Date.to_string(end))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            f_lo = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("move_id.move_type", "=", "out_refund"),
                ("account_id.account_type", "in", ["income", "income_other"]),
                ("date", ">=", fields.Date.to_string(cursor)),
                ("date", "<=", fields.Date.to_string(end))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            rd, rc = (r_lo[0] if r_lo else (0, 0))
            fd, fc = (f_lo[0] if f_lo else (0, 0))
            rev = (rc or 0) - (rd or 0)
            ref = abs((fc or 0) - (fd or 0))
            rate = (ref / rev * 100) if rev else 0
            rev_series.append(float_round(rev, 2))
            ref_series.append(float_round(ref, 2))
            rate_series.append(float_round(rate, 1))
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)

        currency = self.env.company.currency_id
        return {"options": options,
                "gross_revenue": float_round(gross_revenue, 2),
                "refunds": float_round(refunds, 2),
                "net_revenue": float_round(net_revenue, 2),
                "refund_rate_pct": float_round(refund_rate, 2),
                "labels": labels, "revenue": rev_series, "refunds_series": ref_series, "rate_series": rate_series,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
