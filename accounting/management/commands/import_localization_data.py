import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import Country, CountryCity, CountryState, Currency


class Command(BaseCommand):
    help = "Import localization CSV data (currencies, countries, states, cities)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="data/localization",
            help="Directory containing currencies.csv, countries.csv, states.csv, cities.csv",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and simulate import without committing database changes.",
        )

    def handle(self, *args, **options):
        base_path = Path(options["path"]).resolve()
        dry_run = options["dry_run"]

        if not base_path.exists() or not base_path.is_dir():
            raise CommandError(f"Invalid path: {base_path}")

        files = {
            "currencies": base_path / "currencies.csv",
            "countries": base_path / "countries.csv",
            "states": base_path / "states.csv",
            "cities": base_path / "cities.csv",
        }

        for label, file_path in files.items():
            if not file_path.exists():
                raise CommandError(f"Missing required file for {label}: {file_path}")

        self.stdout.write(self.style.NOTICE(f"Importing localization data from: {base_path}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode. No data will be committed."))

        try:
            with transaction.atomic():
                summary = {
                    "currencies": self._import_currencies(files["currencies"]),
                    "countries": self._import_countries(files["countries"]),
                    "states": self._import_states(files["states"]),
                    "cities": self._import_cities(files["cities"]),
                }

                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            pass

        self._print_summary(summary, dry_run)

    def _import_currencies(self, path: Path):
        created = 0
        updated = 0

        for row_number, row in self._read_csv(path, ["code", "name", "symbol", "decimal_places"]):
            code = row["code"].strip().upper()
            name = row["name"].strip()
            symbol = row["symbol"].strip()
            decimal_places = self._parse_int(row["decimal_places"], "decimal_places", row_number)

            if not code or not name:
                raise CommandError(f"currencies.csv row {row_number}: code and name are required")

            obj, was_created = Currency.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "symbol": symbol,
                    "decimal_places": decimal_places,
                },
            )
            obj.full_clean()
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": 0}

    def _import_countries(self, path: Path):
        created = 0
        updated = 0

        for row_number, row in self._read_csv(path, ["code", "name", "phone_code", "active"]):
            code = row["code"].strip().upper()
            name = row["name"].strip()
            phone_code = row["phone_code"].strip()
            active = self._parse_bool(row["active"], "active", row_number)

            if not code or not name:
                raise CommandError(f"countries.csv row {row_number}: code and name are required")

            obj, was_created = Country.objects.update_or_create(
                code=code,
                defaults={
                    "name": name,
                    "phone_code": phone_code,
                    "active": active,
                },
            )
            obj.full_clean()
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": 0}

    def _import_states(self, path: Path):
        created = 0
        updated = 0
        skipped = 0

        country_by_code = {country.code: country for country in Country.objects.all()}

        for row_number, row in self._read_csv(path, ["country_code", "code", "name", "active"]):
            country_code = row["country_code"].strip().upper()
            state_code = row["code"].strip()
            name = row["name"].strip()
            active = self._parse_bool(row["active"], "active", row_number)

            country = country_by_code.get(country_code)
            if not country:
                skipped += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"states.csv row {row_number}: country_code '{country_code}' not found, skipping"
                    )
                )
                continue

            if not name:
                raise CommandError(f"states.csv row {row_number}: name is required")

            lookup = {"country": country, "code": state_code} if state_code else {"country": country, "name": name}
            obj, was_created = CountryState.objects.update_or_create(
                **lookup,
                defaults={
                    "name": name,
                    "code": state_code,
                    "active": active,
                },
            )
            obj.full_clean()
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": skipped}

    def _import_cities(self, path: Path):
        created = 0
        updated = 0
        skipped = 0

        country_by_code = {country.code: country for country in Country.objects.all()}
        state_by_country_code = {
            (state.country_id, state.code): state
            for state in CountryState.objects.exclude(code="").all()
        }

        for row_number, row in self._read_csv(path, ["country_code", "state_code", "name", "postal_code", "active"]):
            country_code = row["country_code"].strip().upper()
            state_code = row["state_code"].strip()
            name = row["name"].strip()
            postal_code = row["postal_code"].strip()
            active = self._parse_bool(row["active"], "active", row_number)

            country = country_by_code.get(country_code)
            if not country:
                skipped += 1
                self.stderr.write(
                    self.style.WARNING(
                        f"cities.csv row {row_number}: country_code '{country_code}' not found, skipping"
                    )
                )
                continue

            state = None
            if state_code:
                state = state_by_country_code.get((country.id, state_code))
                if not state:
                    skipped += 1
                    self.stderr.write(
                        self.style.WARNING(
                            f"cities.csv row {row_number}: state_code '{state_code}' not found for country '{country_code}', skipping"
                        )
                    )
                    continue

            if not name:
                raise CommandError(f"cities.csv row {row_number}: name is required")

            obj, was_created = CountryCity.objects.update_or_create(
                country=country,
                state=state,
                name=name,
                defaults={
                    "postal_code": postal_code,
                    "active": active,
                },
            )
            obj.full_clean()
            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": skipped}

    @staticmethod
    def _read_csv(path: Path, required_columns):
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CommandError(f"CSV has no header: {path}")

            missing = [col for col in required_columns if col not in reader.fieldnames]
            if missing:
                raise CommandError(f"CSV {path.name} is missing required columns: {', '.join(missing)}")

            for row_number, row in enumerate(reader, start=2):
                yield row_number, row

    @staticmethod
    def _parse_bool(value: str, field_name: str, row_number: int):
        normalized = (value or "").strip().lower()
        if normalized in {"1", "true", "yes", "y"}:
            return True
        if normalized in {"0", "false", "no", "n"}:
            return False
        raise CommandError(f"row {row_number}: invalid boolean for {field_name}: '{value}'")

    @staticmethod
    def _parse_int(value: str, field_name: str, row_number: int):
        try:
            return int((value or "").strip())
        except ValueError as exc:
            raise CommandError(f"row {row_number}: invalid integer for {field_name}: '{value}'") from exc

    def _print_summary(self, summary, dry_run: bool):
        mode = "DRY RUN" if dry_run else "COMMITTED"
        self.stdout.write(self.style.SUCCESS(f"Localization import finished ({mode})."))
        for section, counts in summary.items():
            self.stdout.write(
                f"- {section}: created={counts['created']} updated={counts['updated']} skipped={counts['skipped']}"
            )


class _DryRunRollback(Exception):
    """Internal exception used to rollback transaction in dry-run mode."""
