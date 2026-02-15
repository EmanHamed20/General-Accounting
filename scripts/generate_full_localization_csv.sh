#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$BASE_DIR/data/localization"
TMP_DIR="$BASE_DIR/.tmp/localization"

mkdir -p "$OUT_DIR" "$TMP_DIR"

COUNTRY_INFO="$TMP_DIR/countryInfo.txt"
ADMIN1_INFO="$TMP_DIR/admin1CodesASCII.txt"
CITIES_ZIP="$TMP_DIR/cities5000.zip"
CITIES_TXT="$TMP_DIR/cities5000.txt"

curl -fsSL "https://download.geonames.org/export/dump/countryInfo.txt" -o "$COUNTRY_INFO"
curl -fsSL "https://download.geonames.org/export/dump/admin1CodesASCII.txt" -o "$ADMIN1_INFO"
curl -fsSL "https://download.geonames.org/export/dump/cities5000.zip" -o "$CITIES_ZIP"
unzip -o -q "$CITIES_ZIP" -d "$TMP_DIR"

python3 - << 'PY'
import csv
from collections import OrderedDict
from pathlib import Path

base = Path.cwd()
out_dir = base / "data" / "localization"
tmp_dir = base / ".tmp" / "localization"

country_info = tmp_dir / "countryInfo.txt"
admin1_info = tmp_dir / "admin1CodesASCII.txt"
cities_txt = tmp_dir / "cities5000.txt"

countries = []
currencies = OrderedDict()
with country_info.open("r", encoding="utf-8") as f:
    for raw in f:
        if not raw.strip() or raw.startswith("#"):
            continue
        cols = raw.rstrip("\n").split("\t")
        if len(cols) < 17:
            continue
        code = cols[0].strip()
        name = cols[4].strip()
        phone = cols[12].strip()
        currency_code = cols[10].strip()
        currency_name = cols[11].strip()
        if not code or not name:
            continue
        countries.append({
            "code": code,
            "name": name,
            "phone_code": f"+{phone}" if phone else "",
            "active": "true",
        })
        if currency_code:
            currencies.setdefault(currency_code, {
                "code": currency_code,
                "name": currency_name or currency_code,
                "symbol": "",
                "decimal_places": "2",
            })

states = []
with admin1_info.open("r", encoding="utf-8") as f:
    for raw in f:
        if not raw.strip() or raw.startswith("#"):
            continue
        cols = raw.rstrip("\n").split("\t")
        if len(cols) < 3:
            continue
        full_code = cols[0].strip()  # e.g. US.CA
        name = cols[1].strip()
        if "." not in full_code:
            continue
        country_code, state_code = full_code.split(".", 1)
        if not country_code or not state_code or not name:
            continue
        states.append({
            "country_code": country_code,
            "code": state_code,
            "name": name,
            "active": "true",
        })

cities = []
seen = set()
with cities_txt.open("r", encoding="utf-8") as f:
    for raw in f:
        if not raw.strip():
            continue
        cols = raw.rstrip("\n").split("\t")
        if len(cols) < 15:
            continue
        name = cols[1].strip()
        country_code = cols[8].strip()
        state_code = cols[10].strip()  # admin1 code
        postal_code = ""
        if not name or not country_code:
            continue
        key = (country_code, state_code, name.casefold())
        if key in seen:
            continue
        seen.add(key)
        cities.append({
            "country_code": country_code,
            "state_code": state_code,
            "name": name,
            "postal_code": postal_code,
            "active": "true",
        })

countries.sort(key=lambda r: (r["name"], r["code"]))
states.sort(key=lambda r: (r["country_code"], r["name"], r["code"]))
cities.sort(key=lambda r: (r["country_code"], r["state_code"], r["name"]))


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

write_csv(
    out_dir / "currencies.csv",
    ["code", "name", "symbol", "decimal_places"],
    list(currencies.values()),
)
write_csv(
    out_dir / "countries.csv",
    ["code", "name", "phone_code", "active"],
    countries,
)
write_csv(
    out_dir / "states.csv",
    ["country_code", "code", "name", "active"],
    states,
)
write_csv(
    out_dir / "cities.csv",
    ["country_code", "state_code", "name", "postal_code", "active"],
    cities,
)

print(f"countries={len(countries)}")
print(f"currencies={len(currencies)}")
print(f"states={len(states)}")
print(f"cities={len(cities)}")
PY

