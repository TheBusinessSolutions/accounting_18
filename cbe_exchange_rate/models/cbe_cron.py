import logging
from odoo import models, api, fields
import requests
from bs4 import BeautifulSoup
import re

_logger = logging.getLogger(__name__)

CBE_URL = "https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates"

class CbeCron(models.Model):
    _inherit = 'res.currency.rate'

    def _normalize_str(self, text):
        """Normalize string by removing all whitespace and converting to upper case."""
        if not text:
            return ""
        return re.sub(r'\s+', '', text).upper()

    def _get_cbe_table_data(self):
        """Fetches and parses the CBE table, returning a dict of {Normalized Name: Rate}."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Connection': 'keep-alive',
            }
            session = requests.Session()
            response = session.get(CBE_URL, headers=headers, timeout=20)
            response.raise_for_status()
            
            if "Request Rejected" in response.text:
                _logger.error("CBE Cron: Access Blocked by Firewall")
                return {}

            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table', class_='table-comp')
            if not table:
                table = soup.find('table')
            
            if not table:
                _logger.error("CBE Cron: Table not found")
                return {}

            rates = {}
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    raw_name = cols[0].get_text()
                    norm_name = self._normalize_str(raw_name)
                    sell_rate_text = cols[2].get_text(strip=True)
                    try:
                        rate_val = float(sell_rate_text.replace(',', ''))
                        rates[norm_name] = rate_val
                    except ValueError:
                        continue
            return rates

        except Exception as e:
            _logger.error(f"CBE Cron Error: {e}", exc_info=True)
            return {}

    @api.model
    def cron_update_cbe_rates(self):
        """Scheduled action to update all active mapped currencies."""
        _logger.info("Starting CBE Currency Rate Update Cron...")
        
        # 1. Fetch all rates from CBE once
        cbe_rates = self._get_cbe_table_data()
        if not cbe_rates:
            _logger.warning("CBE Cron: No data fetched from website.")
            return

        # 2. Get all Odoo currencies with CBE Name set
        currency_model = self.env['res.currency']
        rate_model = self.env['res.currency.rate']
        today = fields.Date.context_today(self)
        
        currencies = currency_model.search([('active', '=', True), ('cbe_name', '!=', False), ('name', '!=', 'EGP')])
        
        updated_count = 0
        for curr in currencies:
            norm_cbe_name = self._normalize_str(curr.cbe_name)
            
            # 3. Check if we have a rate for this normalized name
            if norm_cbe_name in cbe_rates:
                rate_value = cbe_rates[norm_cbe_name]
                
                # 4. Update or Create Rate
                existing_rate = rate_model.search([
                    ('currency_id', '=', curr.id),
                    ('name', '=', today)
                ], limit=1)
                
                if existing_rate:
                    if existing_rate.rate != rate_value:
                        existing_rate.write({'rate': rate_value})
                        _logger.info(f"Updated {curr.name} to {rate_value}")
                        updated_count += 1
                else:
                    rate_model.create({
                        'currency_id': curr.id,
                        'name': today,
                        'rate': rate_value
                    })
                    _logger.info(f"Created new rate for {curr.name}: {rate_value}")
                    updated_count += 1
            else:
                _logger.debug(f"No CBE rate found for {curr.name} (CBE Name: {curr.cbe_name})")

        _logger.info(f"CBE Cron Finished. Updated {updated_count} currencies.")