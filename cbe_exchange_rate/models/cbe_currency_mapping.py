from odoo import models, fields, api

class CbeCurrencyMapping(models.Model):
    _name = 'cbe.currency.mapping'
    _description = 'CBE Currency Name to Odoo Currency Mapping'

    name = fields.Char(string='CBE Currency Name', required=True, help="Exact name as it appears on CBE website, e.g., 'US Dollar'")
    currency_id = fields.Many2one('res.currency', string='Odoo Currency', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_cbe_name', 'unique(name)', 'The CBE Currency Name must be unique!'),
    ]

    @api.model
    def get_mapped_currency(self, cbe_name):
        """Return the Odoo currency record for a given CBE name."""
        mapping = self.search([('name', '=', cbe_name), ('active', '=', True)], limit=1)
        return mapping.currency_id if mapping else False