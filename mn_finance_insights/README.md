# Finance Insights — Advanced Financial Reports & Dashboards for Odoo 19

Free, open-source (**LGPL-3**) Odoo 19 app that turns Odoo's plain financial
reports into modern, interactive **OWL dashboards** — and adds forward-looking
reports Odoo lacks out of the box.

**Works on Odoo 19 Community AND Enterprise** — no `account_reports` dependency.

## Features

### 1. Executive Finance Dashboard
- KPI cards: Revenue, Expenses, Net Profit, Cash, AR, AP, Gross Margin %, Net Margin %
- Comparison: vs previous year / vs previous period (% delta with arrow)
- Charts (Chart.js 4, bundled locally): Revenue vs Expenses (12-mo), Cash Trend, Top 5 Customers, AR Aging
- Date range + multi-company filters
- Click any KPI → drill to the underlying journal entries

### 2. Cash Flow Forecast
- Forward **4 / 8 / 13 / 26 week** projection
- Built from open AR + AP by due date
- **Best / Expected / Worst** scenarios (one click to switch)
- Stacked bar (weekly flow) + line (cumulative cash)
- **Excel export** with one sheet per scenario

### 3. Beautified Aged Receivable
- Configurable buckets (defaults 30 / 60 / 90 / 120 — change in Settings)
- Customer roll-up + drill-down to invoices
- **Bilingual (Arabic + English) Statement of Account PDF**
- Send statement to customer (mail composer)
- Excel export

### 4. Financial Ratios
- **Liquidity** — Current Ratio, Cash Ratio
- **Profitability** — Gross Margin, Net Margin, ROA, ROE
- **Efficiency** — DSO, DPO
- Each ratio: current value · health rating (good / ok / bad) · 12-month sparkline

## Bilingual
Full Arabic + English UI with proper RTL layout. Both `ar` and `ar_001`
translations bundled.

## Technical
- Reads directly from `account.move.line` — accurate, no shadow tables
- AbstractModels for all data providers — clean, no DB clutter
- Python 3, Odoo 19, OWL 2, Chart.js 4
- Optional `xlsxwriter` for Excel exports (graceful fallback if missing)

## Install
1. Drop `mn_finance_insights/` into your Odoo addons path.
2. Restart Odoo and update the app list.
3. Install **Finance Insights**.
4. Open the **Finance Insights** menu.

## Permissions
Two security groups (Odoo 19 `res.groups.privilege` based):
- **User: View Dashboards & Reports** — read-only access to all screens
- **Manager: Full Access** — implies `account.group_account_manager`

## License
LGPL-3 — free for any use, including commercial.

## Author
**Moaz Nabil** — Odoo developer, MENA
[GitHub](https://github.com/moaaznaabilali) · moaaznaabilali@gmail.com
