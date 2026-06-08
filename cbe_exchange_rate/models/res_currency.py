import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
from bs4 import BeautifulSoup
import re

_logger = logging.getLogger(__name__)

CBE_URL = "https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates"

class ResCurrency(models.Model):
    _inherit = 'res.currency'

    # Field to store the exact name from CBE website for robust matching
    cbe_name = fields.Char(
        string='CBE Currency Name', 
        help="Exact currency name as displayed on CBE website (e.g., 'US Dollar'). Copy this exactly from the website."
    )

    def action_refresh_cbe_rate(self):
        """Manual button action to refresh rate for specific currency/currencies."""
        for currency in self:
            if currency.name == 'EGP':
                raise UserError(_("Cannot update rate for Base Currency (EGP)."))
            
            if not currency.cbe_name:
                raise UserError(_("Please set the 'CBE Currency Name' in the currency form for %s.") % currency.name)

            rate, debug_info = self._fetch_cbe_rate_for_currency(currency)
            
            if rate:
                self._update_currency_rate(currency, rate)
            else:
                # Show debug info in error message to help troubleshooting
                msg = _("Could not find rate for '%s'.\n\nDebug Info:\n%s") % (currency.cbe_name, debug_info)
                raise UserError(msg)
        
        # Return an action to reload the current view/list automatically
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _normalize_str(self, text):
        """Normalize string by removing all whitespace and converting to upper case."""
        if not text:
            return ""
        # Replace any unicode whitespace (including non-breaking space \xa0) with empty string
        return re.sub(r'\s+', '', text).upper()

    def _fetch_cbe_rate_for_currency(self, currency):
        """Fetches the selling rate for a specific currency from CBE."""
        try:
            # Comprehensive headers to mimic a real Chrome browser on Windows
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            }
            
            session = requests.Session()
            response = session.get(CBE_URL, headers=headers, timeout=15)
            response.raise_for_status()
            
            if "Request Rejected" in response.text:
                return False, "Access Blocked by CBE Firewall. Wait a few minutes and try again."

            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Try to find the table by its specific class
            table = soup.find('table', class_='table-comp')
            if not table:
                table = soup.find('table')

            if not table:
                return False, f"Table not found in HTML. Page Title: {soup.title.string if soup.title else 'No Title'}"

            # Normalize the target CBE name from Odoo configuration
            target_cbe_name = self._normalize_str(currency.cbe_name)
            
            rows = table.find_all('tr')
            found_names = []
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    raw_cbe_name = cols[0].get_text()
                    normalized_cbe_name = self._normalize_str(raw_cbe_name)
                    sell_rate_text = cols[2].get_text(strip=True)
                    
                    if len(found_names) < 5:
                        found_names.append(f"'{raw_cbe_name.strip()}' -> '{normalized_cbe_name}'")
                    
                    # Compare normalized strings
                    if normalized_cbe_name == target_cbe_name:
                        try:
                            rate = float(sell_rate_text.replace(',', ''))
                            return rate, "Match found!"
                        except ValueError:
                            return False, f"Invalid rate format: {sell_rate_text}"
            
            debug_msg = f"Target: '{target_cbe_name}'.\nFirst 5 currencies found: {', '.join(found_names)}"
            return False, debug_msg

        except Exception as e:
            return False, f"Error: {str(e)}"

    def _update_currency_rate(self, currency, rate):
        """Create or update the rate in res.currency.rate"""
        today = fields.Date.context_today(self)
        Rate = self.env['res.currency.rate']
        
        existing_rate = Rate.search([
            ('currency_id', '=', currency.id),
            ('name', '=', today)
        ], limit=1)
        
        if existing_rate:
            existing_rate.write({'rate': rate})
        else:
            Rate.create({
                'currency_id': currency.id,
                'name': today,
                'rate': rate
            })
        _logger.info(f"Updated rate for {currency.name} to {rate}")