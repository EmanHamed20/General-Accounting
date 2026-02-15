# Accounting Domain Model Layout

This package is organized by domain so we can map Odoo accounting features step by step.

- `core.py`: company and partner master data.
- `localization.py`: currency and future country/location models.
- `ledger.py`: chart of accounts (root/group/account).
- `journals.py`: journals, payment terms, taxes.
- `entries.py`: accounting moves and move lines.
- `payments.py`: payment methods, payments, reconciliations.

Planned next additions:
1. Country and country locations (state/city).
2. Country currency mapping and defaults per company.
3. Product category model and accounting properties.
4. Chart of accounts templates and localization presets.
