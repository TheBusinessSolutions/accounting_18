# CBE Exchange Rate Updater - Technical Documentation

## Overview
This module automates the retrieval of daily exchange rates from the Central Bank of Egypt (CBE) website and updates the `res.currency.rate` model in Odoo. It supports both manual refreshes via the UI and automated daily cron jobs.

## Architecture

### Models
1. **`res.currency` (Inherited)**
   - **New Field:** `cbe_name` (Char): Stores the exact currency name as it appears on the CBE website (e.g., "US Dollar"). This ensures robust matching regardless of whitespace or formatting changes.
   - **Method:** `action_refresh_cbe_rate()`: Triggered by the UI button. Fetches data, updates the rate, and returns a reload action to refresh the view.
   - **Method:** `_fetch_cbe_rate_for_currency()`: Handles the HTTP request, HTML parsing, and normalization logic.

2. **`res.currency.rate` (Inherited)**
   - **Method:** `cron_update_cbe_rates()`: Executed by the scheduled action. Fetches all rates from CBE once and updates all mapped Odoo currencies in a single pass for efficiency.

### Data Files
- **`data/currency_mapping_data.xml`**: Pre-configures the `cbe_name` field for standard currencies (USD, EUR, GBP, etc.) during installation. Marked as `noupdate="1"` to preserve manual changes.
- **`data/cron_data.xml`**: Defines the daily scheduled action.

### Key Logic: Normalization
To handle inconsistencies between the website HTML and user input, the module uses a `_normalize_str()` helper:
1. Removes all whitespace (spaces, tabs, newlines).
2. Converts text to uppercase.
3. Example: `" US Dollar "` becomes `"USDOLLAR"`.

## Maintenance & Troubleshooting

### Adding New Currencies
1. Go to **Accounting > Configuration > Currencies**.
2. Create or Open the currency (e.g., `TRY`).
3. In the **CBE Integration** section, set **CBE Currency Name** to the exact name found on the CBE website (e.g., `Turkish Lira`).
4. Save and click **Refresh from CBE**.

### If the Cron Fails
1. Check **Settings > Technical > Scheduled Actions**.
2. Find **CBE: Update Currency Rates Daily**.
3. Click **Run Manually**.
4. Check the server logs for errors. Common issues:
   - **"Request Rejected"**: The CBE firewall is blocking the server IP. Wait 10-15 minutes and try again.
   - **"Table not found"**: The CBE website structure may have changed. Inspect the HTML source of the CBE page to verify the table class (`table-comp`).

### Dependencies
- `requests`
- `beautifulsoup4`

## Author
Business Solutions
www.thebusinesssolutions.net