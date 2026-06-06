# -*- coding: utf-8 -*-
"""Excel exports for cash flow forecast and aged receivable."""
import io
import json

from odoo import http
from odoo.http import request, content_disposition

try:
    import xlsxwriter
except ImportError:  # pragma: no cover
    xlsxwriter = None


class FinanceInsightsExport(http.Controller):

    @http.route("/mn_finance_insights/cash_flow/xlsx", type="http", auth="user")
    def export_cash_flow(self, options=None, **kw):
        if xlsxwriter is None:
            return request.not_found()
        opts = json.loads(options) if options else {}
        data = request.env["cash.flow.forecast"].get_forecast_data(opts)

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        bold = wb.add_format({"bold": True, "bg_color": "#6366f1", "color": "white", "border": 1})
        money = wb.add_format({"num_format": "#,##0.00"})
        money_b = wb.add_format({"num_format": "#,##0.00", "bold": True, "top": 1})

        for scenario, rows in data["scenarios"].items():
            ws = wb.add_worksheet(scenario.title())
            ws.set_column(0, 0, 7)
            ws.set_column(1, 2, 14)
            ws.set_column(3, 6, 16)
            for col, h in enumerate(["Week", "From", "To", "Inflow", "Outflow", "Net", "Cumulative"]):
                ws.write(0, col, h, bold)
            for i, r in enumerate(rows, start=1):
                ws.write(i, 0, r["week"])
                ws.write(i, 1, r["date_from"])
                ws.write(i, 2, r["date_to"])
                ws.write_number(i, 3, r["inflow"], money)
                ws.write_number(i, 4, r["outflow"], money)
                ws.write_number(i, 5, r["net"], money)
                ws.write_number(i, 6, r["cumulative"], money_b)
        wb.close()
        buf.seek(0)
        return request.make_response(
            buf.read(),
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", content_disposition("cash_flow_forecast.xlsx")),
            ],
        )

    @http.route("/mn_finance_insights/aged_receivable/xlsx", type="http", auth="user")
    def export_aged_receivable(self, options=None, **kw):
        if xlsxwriter is None:
            return request.not_found()
        opts = json.loads(options) if options else {}
        data = request.env["finance.aged.receivable"].get_aged_data(opts)

        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {"in_memory": True})
        bold = wb.add_format({"bold": True, "bg_color": "#6366f1", "color": "white", "border": 1})
        money = wb.add_format({"num_format": "#,##0.00"})

        ws = wb.add_worksheet("Aged Receivable")
        ws.set_column(0, 0, 36)
        ws.set_column(1, 6, 14)
        headers = ["Customer"] + [b["label"] for b in data["buckets"]] + ["Total"]
        for col, h in enumerate(headers):
            ws.write(0, col, h, bold)
        for i, row in enumerate(data["rows"], start=1):
            ws.write(i, 0, row["partner_name"])
            for j, amt in enumerate(row["bucket_amounts"], start=1):
                ws.write_number(i, j, amt, money)
            ws.write_number(i, len(headers) - 1, row["total"], money)

        wb.close()
        buf.seek(0)
        return request.make_response(
            buf.read(),
            headers=[
                ("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                ("Content-Disposition", content_disposition("aged_receivable.xlsx")),
            ],
        )
