# Localization CSV Data

These CSV files contain broad global coverage generated from GeoNames exports:
- currencies
- countries
- states
- cities

## Files
- `currencies.csv`: `code,name,symbol,decimal_places`
- `countries.csv`: `code,name,phone_code,active`
- `states.csv`: `country_code,code,name,active`
- `cities.csv`: `country_code,state_code,name,postal_code,active`

## Notes
- Sources:
  - `countryInfo.txt`
  - `admin1CodesASCII.txt`
  - `cities5000.zip` (cities with population >= 5,000)
- `country_code` maps to `countries.csv.code`.
- `state_code` maps to `states.csv.code` within the same country.
- `active` uses `true/false`.
- `postal_code` is empty by default in generated city rows.

## Current Row Counts
- `currencies.csv`: 155
- `countries.csv`: 252
- `states.csv`: 3862
- `cities.csv`: 67307

## Import Into Database
- Dry-run:
  - `.venv/bin/python manage.py import_localization_data --path data/localization --dry-run`
- Commit:
  - `.venv/bin/python manage.py import_localization_data --path data/localization`
