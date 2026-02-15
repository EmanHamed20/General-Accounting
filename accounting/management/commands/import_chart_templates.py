import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounting.models import AccountGroupTemplate, AccountTemplate, Country


class Command(BaseCommand):
    help = "Import chart template CSV data (account group templates and account templates)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            default="data/chart_templates",
            help="Directory containing account_group_templates.csv and account_templates.csv",
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
            "groups": base_path / "account_group_templates.csv",
            "accounts": base_path / "account_templates.csv",
        }
        for label, file_path in files.items():
            if not file_path.exists():
                raise CommandError(f"Missing required file for {label}: {file_path}")

        self.stdout.write(self.style.NOTICE(f"Importing chart templates from: {base_path}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Running in dry-run mode. No data will be committed."))

        try:
            with transaction.atomic():
                summary = {
                    "groups": self._import_groups(files["groups"]),
                    "accounts": self._import_accounts(files["accounts"]),
                }

                if dry_run:
                    raise _DryRunRollback()
        except _DryRunRollback:
            pass

        self._print_summary(summary, dry_run)

    def _import_groups(self, path: Path):
        created = 0
        updated = 0

        rows = list(
            self._read_csv(
                path,
                [
                    "country_code",
                    "code_prefix_start",
                    "code_prefix_end",
                    "name",
                    "parent_code_prefix_start",
                    "parent_code_prefix_end",
                ],
            )
        )

        countries = {country.code: country for country in Country.objects.all()}
        template_by_key = {}

        pending = []
        for row_number, row in rows:
            country_code = row["country_code"].strip().upper()
            country = countries.get(country_code)
            if not country:
                raise CommandError(f"account_group_templates.csv row {row_number}: country_code '{country_code}' not found")

            code_start = row["code_prefix_start"].strip()
            code_end = row["code_prefix_end"].strip()
            name = row["name"].strip()
            parent_start = row["parent_code_prefix_start"].strip()
            parent_end = row["parent_code_prefix_end"].strip()

            if not code_start or not code_end or not name:
                raise CommandError(
                    f"account_group_templates.csv row {row_number}: code_prefix_start, code_prefix_end and name are required"
                )

            pending.append(
                {
                    "row_number": row_number,
                    "country": country,
                    "code_start": code_start,
                    "code_end": code_end,
                    "name": name,
                    "parent_start": parent_start,
                    "parent_end": parent_end,
                }
            )

        unresolved = pending
        while unresolved:
            next_unresolved = []
            progressed = False

            for item in unresolved:
                parent = None
                if item["parent_start"] or item["parent_end"]:
                    if not (item["parent_start"] and item["parent_end"]):
                        raise CommandError(
                            f"account_group_templates.csv row {item['row_number']}: parent start/end must both be set or empty"
                        )
                    parent_key = (
                        item["country"].id,
                        item["parent_start"],
                        item["parent_end"],
                    )
                    parent = template_by_key.get(parent_key)
                    if parent is None:
                        next_unresolved.append(item)
                        continue

                obj, was_created = AccountGroupTemplate.objects.update_or_create(
                    country=item["country"],
                    code_prefix_start=item["code_start"],
                    code_prefix_end=item["code_end"],
                    defaults={"name": item["name"], "parent": parent},
                )
                obj.full_clean()
                template_by_key[(item["country"].id, item["code_start"], item["code_end"])] = obj
                progressed = True

                if was_created:
                    created += 1
                else:
                    updated += 1

            if not progressed:
                bad_rows = ", ".join(str(item["row_number"]) for item in next_unresolved)
                raise CommandError(f"Could not resolve parent templates for rows: {bad_rows}")

            unresolved = next_unresolved

        return {"created": created, "updated": updated, "skipped": 0}

    def _import_accounts(self, path: Path):
        created = 0
        updated = 0

        countries = {country.code: country for country in Country.objects.all()}
        groups = {
            (group.country_id, group.code_prefix_start, group.code_prefix_end): group
            for group in AccountGroupTemplate.objects.all()
        }

        for row_number, row in self._read_csv(
            path,
            [
                "country_code",
                "group_code_prefix_start",
                "group_code_prefix_end",
                "code",
                "name",
                "account_type",
                "reconcile",
                "deprecated",
            ],
        ):
            country_code = row["country_code"].strip().upper()
            country = countries.get(country_code)
            if not country:
                raise CommandError(f"account_templates.csv row {row_number}: country_code '{country_code}' not found")

            group_start = row["group_code_prefix_start"].strip()
            group_end = row["group_code_prefix_end"].strip()
            code = row["code"].strip()
            name = row["name"].strip()
            account_type = row["account_type"].strip()
            reconcile = self._parse_bool(row["reconcile"], "reconcile", row_number)
            deprecated = self._parse_bool(row["deprecated"], "deprecated", row_number)

            if not code or not name or not account_type:
                raise CommandError(f"account_templates.csv row {row_number}: code, name and account_type are required")

            group = None
            if group_start or group_end:
                if not (group_start and group_end):
                    raise CommandError(
                        f"account_templates.csv row {row_number}: group start/end must both be set or empty"
                    )
                group = groups.get((country.id, group_start, group_end))
                if not group:
                    raise CommandError(
                        f"account_templates.csv row {row_number}: group ({group_start}-{group_end}) not found for {country.code}"
                    )

            obj, was_created = AccountTemplate.objects.update_or_create(
                country=country,
                code=code,
                defaults={
                    "group": group,
                    "name": name,
                    "account_type": account_type,
                    "reconcile": reconcile,
                    "deprecated": deprecated,
                },
            )
            obj.full_clean()

            if was_created:
                created += 1
            else:
                updated += 1

        return {"created": created, "updated": updated, "skipped": 0}

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

    def _print_summary(self, summary, dry_run: bool):
        mode = "DRY RUN" if dry_run else "COMMITTED"
        self.stdout.write(self.style.SUCCESS(f"Chart template import finished ({mode})."))
        for section, counts in summary.items():
            self.stdout.write(
                f"- {section}: created={counts['created']} updated={counts['updated']} skipped={counts['skipped']}"
            )


class _DryRunRollback(Exception):
    pass
