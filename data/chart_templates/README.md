# Chart Template CSV Data

Starter chart template files:
- `account_group_templates.csv`
- `account_templates.csv`

## Schema

`account_group_templates.csv`
- `country_code`
- `code_prefix_start`
- `code_prefix_end`
- `name`
- `parent_code_prefix_start`
- `parent_code_prefix_end`

`account_templates.csv`
- `country_code`
- `group_code_prefix_start`
- `group_code_prefix_end`
- `code`
- `name`
- `account_type` (`asset`, `liability`, `equity`, `income`, `expense`)
- `reconcile` (`true/false`)
- `deprecated` (`true/false`)

## Import
- Dry-run:
  - `.venv/bin/python manage.py import_chart_templates --path data/chart_templates --dry-run`
- Commit:
  - `.venv/bin/python manage.py import_chart_templates --path data/chart_templates`
