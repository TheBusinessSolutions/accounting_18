# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    fi_aging_bucket_1 = fields.Integer(
        string="Aging bucket 1 (days)", default=30, config_parameter="mn_finance_insights.aging_bucket_1"
    )
    fi_aging_bucket_2 = fields.Integer(
        string="Aging bucket 2 (days)", default=60, config_parameter="mn_finance_insights.aging_bucket_2"
    )
    fi_aging_bucket_3 = fields.Integer(
        string="Aging bucket 3 (days)", default=90, config_parameter="mn_finance_insights.aging_bucket_3"
    )
    fi_aging_bucket_4 = fields.Integer(
        string="Aging bucket 4 (days)", default=120, config_parameter="mn_finance_insights.aging_bucket_4"
    )
