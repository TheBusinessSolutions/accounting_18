# -*- coding: utf-8 -*-
"""Cross-Sell Opportunity Matrix — top customers × top products."""
from datetime import date
from collections import defaultdict
from odoo import _, api, fields, models
from odoo.tools import float_round


class CrossSell(models.AbstractModel):
    _name = "finance.cross.sell"
    _description = "Cross-Sell Opportunity Matrix"

    @api.model
    def get_matrix_data(self, options=None):
        options = self._sanitize(options or {})
        df = fields.Date.from_string(options["date_from"])
        dt = fields.Date.from_string(options["date_to"])
        company_ids = options["company_ids"]

        AML = self.env["account.move.line"]
        # top 10 customers
        cust_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "=", "out_invoice"),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt)),
            ("partner_id", "!=", False),
            ("product_id", "!=", False)],
            groupby=["partner_id"], aggregates=["price_subtotal:sum"],
            order="price_subtotal:sum desc", limit=10)
        top_customers = [(p.id, p.display_name) for (p, _amt) in cust_rows]
        # top 10 products
        prod_rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "=", "out_invoice"),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt)),
            ("product_id", "!=", False)],
            groupby=["product_id"], aggregates=["price_subtotal:sum"],
            order="price_subtotal:sum desc", limit=10)
        top_products = [(p.id, p.display_name) for (p, _amt) in prod_rows]

        # build matrix amount[customer][product]
        matrix = defaultdict(lambda: defaultdict(float))
        rows = AML._read_group(domain=[
            ("parent_state", "=", "posted"), ("company_id", "in", company_ids),
            ("move_id.move_type", "=", "out_invoice"),
            ("date", ">=", fields.Date.to_string(df)),
            ("date", "<=", fields.Date.to_string(dt)),
            ("partner_id", "in", [c[0] for c in top_customers]),
            ("product_id", "in", [p[0] for p in top_products])],
            groupby=["partner_id", "product_id"],
            aggregates=["price_subtotal:sum"])
        for (cust, prod, amt) in rows:
            matrix[cust.id][prod.id] = amt or 0
        # build rows for view
        result_rows = []
        for cid, cname in top_customers:
            row = {"id": cid, "name": cname, "cells": []}
            gap_count = 0
            for pid, pname in top_products:
                v = matrix[cid][pid]
                if not v: gap_count += 1
                row["cells"].append(float_round(v, 2))
            row["gaps"] = gap_count
            result_rows.append(row)

        currency = self.env.company.currency_id
        return {"options": options,
                "products": [p[1] for p in top_products],
                "rows": result_rows,
                "currency": {"id": currency.id, "symbol": currency.symbol, "decimals": currency.decimal_places},
                "company_name": self.env.company.name}

    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {"date_from": options.get("date_from") or date(today.year, 1, 1).isoformat(),
                "date_to": options.get("date_to") or today.isoformat(),
                "company_ids": list(options.get("company_ids") or self.env.companies.ids)}
