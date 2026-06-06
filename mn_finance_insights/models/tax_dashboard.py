# -*- coding: utf-8 -*-
"""Tax & VAT Dashboard."""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import _, api, fields, models
from odoo.tools import float_round


class TaxDashboard(models.AbstractModel):
    _name = "finance.tax.dashboard"
    _description = "Tax & VAT Dashboard"

    @api.model
    def get_tax_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]
        AML = self.env["account.move.line"]

        # Output VAT — credit balance on tax accounts from customer invoices
        out_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
            ("tax_line_id", "!=", False),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        out_d, out_c = (out_rows[0] if out_rows else (0, 0))
        output_vat = (out_c or 0) - (out_d or 0)

        # Input VAT — debit balance on tax accounts from vendor bills
        in_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
            ("tax_line_id", "!=", False),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=[], aggregates=["debit:sum", "credit:sum"])
        in_d, in_c = (in_rows[0] if in_rows else (0, 0))
        input_vat = (in_d or 0) - (in_c or 0)

        net_vat_due = output_vat - input_vat

        # Per-tax breakdown
        tax_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("tax_line_id", "!=", False),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt))],
            groupby=["tax_line_id"],
            aggregates=["debit:sum", "credit:sum"],
            order="credit:sum desc")
        by_tax = [{"id": t.id, "name": t.name,
                   "amount": float_round(((c or 0) - (d or 0)), 2)}
                  for (t, d, c) in tax_rows if t]

        # Monthly trend
        labels, output_series, input_series = [], [], []
        cursor = date(df.year, df.month, 1)
        while cursor <= dt:
            end = min(cursor + relativedelta(months=1) - timedelta(days=1), dt)
            o_rows = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("move_id.move_type", "in", ["out_invoice", "out_refund"]),
                ("tax_line_id", "!=", False),
                ("date", ">=", fields.Date.to_string(cursor)),
                ("date", "<=", fields.Date.to_string(end))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            i_rows = AML._read_group(domain=[
                ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
                ("move_id.move_type", "in", ["in_invoice", "in_refund"]),
                ("tax_line_id", "!=", False),
                ("date", ">=", fields.Date.to_string(cursor)),
                ("date", "<=", fields.Date.to_string(end))],
                groupby=[], aggregates=["debit:sum", "credit:sum"])
            od, oc = (o_rows[0] if o_rows else (0, 0))
            id_, ic = (i_rows[0] if i_rows else (0, 0))
            output_series.append(float_round((oc or 0) - (od or 0), 2))
            input_series.append(float_round((id_ or 0) - (ic or 0), 2))
            labels.append(cursor.strftime("%b %Y"))
            cursor += relativedelta(months=1)

        currency = self.env.company.currency_id
        return {
            "options": options,
            "output_vat": float_round(output_vat, 2),
            "input_vat": float_round(input_vat, 2),
            "net_vat_due": float_round(net_vat_due, 2),
            "by_tax": by_tax,
            "labels": labels,
            "output_series": output_series,
            "input_series": input_series,
            "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
            "company_name": self.env.company.name,
        }

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
