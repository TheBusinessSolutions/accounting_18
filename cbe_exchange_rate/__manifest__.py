{
    'name': 'CBE Exchange Rate Updater',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Update currency rates from Central Bank of Egypt (CBE)',
    'description': """
        This module automatically updates currency exchange rates from the Central Bank of Egypt (CBE) website.
        Features:
        - Automated daily update via Cron.
        - Manual refresh button on each currency.
        - Mapping system to handle currency name differences between CBE and Odoo.
    """,
    'author': 'Business Solutions',
    'website': 'https://www.thebusinesssolutions.net',
    'depends': ['base', 'account'],  # account depends on base and includes res.currency
    'data': [
        'security/ir.model.access.csv',
        'views/cbe_currency_mapping_views.xml',
        'views/res_currency_views.xml',
        'data/cron_data.xml',
        'data/currency_mapping_data.xml', 
    ],
    'external_dependencies': {
        'python': ['beautifulsoup4', 'requests'],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}