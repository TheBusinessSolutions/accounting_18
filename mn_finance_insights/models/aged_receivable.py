# -*- coding: utf-8 -*-
"""Beautified Aged Receivable.

* Configurable buckets (defaults 30/60/90/120 via res.config.settings).
* Per-partner roll-up with drill-down to underlying journal items.
* "Send statement" action — emails the bilingual PDF statement to the partner.
"""
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools import float_round


class AgedReceivable(models.AbstractModel):
    _name = "finance.aged.receivable"
    _description = "Aged Receivable Report"

    # ------------------------------------------------------------------
    @api.model
    def get_aged_data(self, options=None):
        options = self._sanitize(options or {})
        buckets = self._buckets()
        AML = self.env["account.move.line"]
        as_of = fields.Date.from_string(options["as_of"])

        lines = AML.search_read(
            domain=[
                ("parent_state", "=", "posted"),
                ("company_id", "in", options["company_ids"]),
                ("account_id.account_type", "=", "asset_receivable"),
                ("reconciled", "=", False),
                ("amount_residual", "!=", 0),
                ("partner_id", "!=", False),
            ],
            fields=["partner_id", "date_maturity", "amount_residual", "move_id"],
        )

        # partner -> bucket index -> amount
        partner_data = defaultdict(lambda: {"name": "", "amounts": [0.0] * len(buckets), "total": 0.0})
        bucket_totals = [0.0] * len(buckets)

        for ln in lines:
            partner_id, partner_name = ln["partner_id"]
            due = ln["date_maturity"] or as_of
            days = (as_of - due).days
            idx = self._bucket_index(days, buckets)
            amount = ln["amount_residual"]
            partner_data[partner_id]["name"] = partner_name
            partner_data[partner_id]["amounts"][idx] += amount
            partner_data[partner_id]["total"] += amount
            bucket_totals[idx] += amount

        rows = sorted(
            [
                {
                    "partner_id": pid,
                    "partner_name": p["name"],
                    "bucket_amounts": [float_round(a, precision_digits=2) for a in p["amounts"]],
                    "total": float_round(p["total"], precision_digits=2),
                }
                for pid, p in partner_data.items()
            ],
            key=lambda r: -r["total"],
        )

        currency = self.env.company.currency_id
        return {
            "options": options,
            "buckets": buckets,
            "rows": rows,
            "bucket_totals": [float_round(t, precision_digits=2) for t in bucket_totals],
            "grand_total": float_round(sum(bucket_totals), precision_digits=2),
            "currency": {
                "id": currency.id,
                "symbol": currency.symbol,
                "decimals": currency.decimal_places,
            },
            "company_name": self.env.company.name,
        }

    # ------------------------------------------------------------------
    @api.model
    def _sanitize(self, options):
        today = fields.Date.context_today(self)
        return {
            "as_of": options.get("as_of") or today.isoformat(),
            "company_ids": list(options.get("company_ids") or self.env.companies.ids),
        }

    @api.model
    def _buckets(self):
        get = self.env["ir.config_parameter"].sudo().get_param
        b1 = int(get("mn_finance_insights.aging_bucket_1", 30))
        b2 = int(get("mn_finance_insights.aging_bucket_2", 60))
        b3 = int(get("mn_finance_insights.aging_bucket_3", 90))
        b4 = int(get("mn_finance_insights.aging_bucket_4", 120))
        return [
            {"label": _("Not due"),         "min": -10 ** 6, "max": -1},
            {"label": _("1 - %d", b1),      "min": 0,        "max": b1},
            {"label": _("%d - %d", b1 + 1, b2), "min": b1 + 1, "max": b2},
            {"label": _("%d - %d", b2 + 1, b3), "min": b2 + 1, "max": b3},
            {"label": _("%d - %d", b3 + 1, b4), "min": b3 + 1, "max": b4},
            {"label": _("%d+",      b4 + 1),   "min": b4 + 1, "max": 10 ** 9},
        ]

    @api.model
    def _bucket_index(self, days, buckets):
        for i, b in enumerate(buckets):
            if b["min"] <= days <= b["max"]:
                return i
        return len(buckets) - 1

    # ------------------------------------------------------------------
    @api.model
    def action_partner_drilldown(self, partner_id):
        return {
            "type": "ir.actions.act_window",
            "name": _("Open receivables"),
            "res_model": "account.move.line",
            "view_mode": "list,form",
            "domain": [
                ("partner_id", "=", partner_id),
                ("account_id.account_type", "=", "asset_receivable"),
                ("reconciled", "=", False),
                ("parent_state", "=", "posted"),
            ],
            "context": {"search_default_group_by_move": 1},
        }

    @api.model
    def action_send_statement(self, partner_id):
        """Generate the statement PDF and open the mail composer."""
        partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            return False
        report = self.env.ref("mn_finance_insights.action_report_statement_of_account", raise_if_not_found=False)
        if not report:
            return False
        ctx = {
            "default_model": "res.partner",
            "default_res_ids": [partner.id],
            "default_subject": _("Statement of Account — %s") % self.env.company.name,
            "default_partner_ids": [partner.id],
            "default_use_template": False,
            "default_attachment_ids": [],
            "force_email": True,
        }
        return {
            "type": "ir.actions.act_window",
            "name": _("Send statement"),
            "res_model": "mail.compose.message",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
