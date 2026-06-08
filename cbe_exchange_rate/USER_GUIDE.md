# CBE Exchange Rate Updater - User Guide

## Introduction
This module helps you keep your Odoo currency rates up-to-date with the official rates from the Central Bank of Egypt (CBE). It eliminates the need for manual data entry.

## Installation
1. Install the module **CBE Exchange Rate Updater**.
2. Ensure your server has internet access to reach `https://www.cbe.org.eg`.
3. Upon installation, major currencies (USD, EUR, GBP, SAR, etc.) are automatically configured.

## How to Use

### 1. Manual Refresh (Single Currency)
If you need to update a specific currency immediately:
1. Go to **Accounting > Configuration > Currencies**.
2. Open the currency you want to update (e.g., **US Dollar**).
3. You will see a **Refresh from CBE** button at the top right.
4. Click the button.
5. A success message will appear, and the page will reload to show the new rate in the **Rates** tab.

### 2. Automated Daily Update
The module is configured to automatically update all active currencies every day.
- No user intervention is required.
- The update runs in the background.
- You can verify the update by checking the **Rates** tab in any currency form.

## Configuration

### Setting Up a New Currency
If you activate a new currency in Odoo (e.g., Turkish Lira - TRY):
1. Go to the **CBE Website** ([CBE Exchange Rates](https://www.cbe.org.eg/en/economic-research/statistics/cbe-exchange-rates)).
2. Find the exact name of the currency in the table (e.g., `Turkish Lira`).
3. In Odoo, go to **Accounting > Configuration > Currencies** and open **TRY**.
4. In the **CBE Integration** section, paste the name (`Turkish Lira`) into the **CBE Currency Name** field.
5. Click **Save**.
6. Click **Refresh from CBE** to test.

### Important Notes
- **Exact Match:** The name in the **CBE Currency Name** field must match the website exactly. Copy-pasting is recommended.
- **Base Currency:** You cannot update the rate for your company's base currency (usually EGP) as it is always 1.0.
- **Firewall:** If you see an error saying "Access Blocked," the CBE website may have temporarily blocked your server. Wait 10 minutes and try again.

## Support
For technical support or customizations, please contact:
**Business Solutions**
www.thebusinesssolutions.net