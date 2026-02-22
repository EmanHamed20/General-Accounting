from __future__ import annotations

import calendar
from datetime import timedelta
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from .base import AccountingBaseModel


class TransferModel(AccountingBaseModel):
    FREQUENCY_CHOICES = (
        ("month", "Monthly"),
        ("quarter", "Quarterly"),
        ("year", "Yearly"),
    )
    STATE_CHOICES = (
        ("disabled", "Disabled"),
        ("in_progress", "Running"),
    )

    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    journal = models.ForeignKey("accounting.Journal", on_delete=models.CASCADE, related_name="transfer_models")
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="transfer_models")
    date_start = models.DateField()
    date_stop = models.DateField(null=True, blank=True)
    frequency = models.CharField(max_length=16, choices=FREQUENCY_CHOICES, default="month")
    accounts = models.ManyToManyField("accounting.Account", related_name="source_transfer_models", blank=True)
    move_ids_count = models.PositiveIntegerField(default=0)
    total_percent = models.DecimalField(max_digits=9, decimal_places=6, default=Decimal("0"))
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="disabled")

    class Meta:
        db_table = "ga_transfer_model"
        indexes = [
            models.Index(fields=["company", "state"]),
            models.Index(fields=["journal", "date_start"]),
        ]
        unique_together = (("company", "name"),)

    # DEFAULTS
    def _get_default_date_start(self):
        today = timezone.localdate()
        month = 12
        day = 31
        try:
            from accounting.models import AccountingSettings

            settings = AccountingSettings.objects.filter(company_id=self.company_id).only(
                "fiscalyear_last_day", "fiscalyear_last_month"
            ).first()
            if settings:
                month = int(settings.fiscalyear_last_month)
                day = int(settings.fiscalyear_last_day)
        except Exception:
            pass

        fy_end_day = min(day, calendar.monthrange(today.year, month)[1])
        fy_end_this_year = today.replace(month=month, day=fy_end_day)
        if today <= fy_end_this_year:
            prev_year = today.year - 1
            prev_end_day = min(day, calendar.monthrange(prev_year, month)[1])
            return today.replace(year=prev_year, month=month, day=prev_end_day) + timedelta(days=1)
        return fy_end_this_year + timedelta(days=1)

    def _get_default_journal(self):
        from accounting.models import Journal

        qs = Journal.objects.filter(journal_type="general")
        if self.company_id:
            qs = qs.filter(company_id=self.company_id)
        return qs.order_by("id").first()

    @transaction.atomic
    def copy(self, default=None):
        default = default or {}
        duplicate = TransferModel.objects.create(
            name=default.get("name", f"{self.name} (copy)"),
            active=default.get("active", self.active),
            journal=default.get("journal", self.journal),
            company=default.get("company", self.company),
            date_start=default.get("date_start", self.date_start),
            date_stop=default.get("date_stop", self.date_stop),
            frequency=default.get("frequency", self.frequency),
            state=default.get("state", "disabled"),
        )
        duplicate.accounts.set(self.accounts.all())
        for line in self.lines.prefetch_related("analytic_accounts", "partners").all().order_by("sequence", "id"):
            new_line = TransferModelLine.objects.create(
                transfer_model=duplicate,
                account=line.account,
                percent=line.percent,
                sequence=line.sequence,
            )
            new_line.analytic_accounts.set(line.analytic_accounts.all())
            new_line.partners.set(line.partners.all())
            new_line._compute_percent_is_readonly()
            new_line.save(update_fields=["percent_is_readonly", "updated_at"])

        duplicate._compute_total_percent()
        duplicate._check_line_ids_percent()
        duplicate.save(update_fields=["total_percent", "updated_at"])
        return duplicate

    def _unlink_with_check_moves(self):
        if not self.moves.exists():
            return
        if self.moves.filter(state="posted").exists():
            raise ValidationError(
                f"You cannot delete an automatic transfer that has posted moves attached ('{self.name}')."
            )
        if self.moves.filter(state="draft").exists():
            raise ValidationError(
                f"You cannot delete an automatic transfer that has draft moves attached ('{self.name}'). "
                "Please delete them before deleting this transfer."
            )

    def action_archive(self):
        self.action_disable()
        self.active = False
        self.save(update_fields=["active", "updated_at"])
        return self

    # COMPUTEDS / CONSTRAINS
    def _compute_move_ids_count(self):
        self.move_ids_count = self.moves.count()

    def _check_line_ids_percent(self):
        if not (Decimal("0") < self.total_percent <= Decimal("100")):
            raise ValidationError(f"The total percentage ({self.total_percent}) should be less or equal to 100.")

    def _check_line_ids_filters(self):
        combinations = set()
        for line in self.lines.prefetch_related("partners", "analytic_accounts").all():
            partner_ids = list(line.partners.values_list("id", flat=True))
            analytic_ids = list(line.analytic_accounts.values_list("id", flat=True))
            if partner_ids and analytic_ids:
                for partner_id in partner_ids:
                    for analytic_id in analytic_ids:
                        combo = (partner_id, analytic_id)
                        if combo in combinations:
                            raise ValidationError("The combination of partner filter and analytic filter is duplicated.")
                        combinations.add(combo)
            elif partner_ids:
                for partner_id in partner_ids:
                    combo = (partner_id, None)
                    if combo in combinations:
                        raise ValidationError("The partner filter is duplicated.")
                    combinations.add(combo)
            elif analytic_ids:
                for analytic_id in analytic_ids:
                    combo = (None, analytic_id)
                    if combo in combinations:
                        raise ValidationError("The analytic filter is duplicated.")
                    combinations.add(combo)

    def _compute_total_percent(self):
        lines = list(self.lines.prefetch_related("partners", "analytic_accounts").all())
        non_filtered = [l for l in lines if not l.partners.exists() and not l.analytic_accounts.exists()]
        if lines and not non_filtered:
            self.total_percent = Decimal("100")
            return
        total = sum((l.percent for l in non_filtered), Decimal("0"))
        if abs(total - Decimal("100")) <= Decimal("0.000001"):
            total = Decimal("100")
        self.total_percent = total

    # ACTIONS
    def action_activate(self):
        self.state = "in_progress"
        self.save(update_fields=["state", "updated_at"])
        return self

    def action_disable(self):
        self.state = "disabled"
        self.save(update_fields=["state", "updated_at"])
        return self

    @classmethod
    def action_cron_auto_transfer(cls):
        for record in cls.objects.filter(state="in_progress", active=True):
            record.action_perform_auto_transfer()

    def action_perform_auto_transfer(self):
        if not self.accounts.exists() or not self.lines.exists():
            return False
        today = timezone.localdate()
        max_date = min(today, self.date_stop) if self.date_stop else today
        start_date = self._determine_start_date()
        next_move_date = self._get_next_move_date(start_date)

        while next_move_date <= max_date:
            self._create_or_update_move_for_period(start_date, next_move_date)
            start_date = next_move_date + timedelta(days=1)
            next_move_date = self._get_next_move_date(start_date)

        if not self.date_stop:
            self._create_or_update_move_for_period(start_date, next_move_date)
        elif today < self.date_stop:
            self._create_or_update_move_for_period(start_date, min(next_move_date, self.date_stop))
        return False

    def _get_move_lines_base_domain(self, start_date, end_date):
        account_ids = list(self.accounts.values_list("id", flat=True))
        return {
            "account_id__in": account_ids,
            "date__gte": start_date,
            "date__lte": end_date,
            "move__state": "posted",
        }

    @transaction.atomic
    def _create_or_update_move_for_period(self, start_date, end_date):
        from accounting.models import Move, MoveLine

        current_move = self._get_move_for_period(end_date)
        line_values = self._get_auto_transfer_move_line_values(start_date, end_date)
        if not line_values:
            return current_move

        move_currency = self.journal.currency
        if not move_currency:
            from accounting.models import AccountingSettings

            settings = AccountingSettings.objects.filter(company_id=self.company_id).only("currency").first()
            move_currency = settings.currency if settings and settings.currency_id else None
        if not move_currency:
            raise ValidationError("Destination journal or accounting settings must define a currency for automatic transfer.")

        if current_move is None:
            current_move = Move.objects.create(
                company=self.company,
                journal=self.journal,
                partner=None,
                currency=move_currency,
                payment_term=None,
                reference=f"{self.name}: {start_date} --> {end_date}",
                name="",
                invoice_date=end_date,
                date=end_date,
                state="draft",
                move_type="entry",
                transfer_model=self,
            )

        current_move.lines.all().delete()
        move_lines = []
        for value in line_values:
            debit = Decimal(value.get("debit", 0))
            credit = Decimal(value.get("credit", 0))
            move_lines.append(
                MoveLine(
                    move=current_move,
                    account_id=value["account_id"],
                    partner_id=value.get("partner_id"),
                    analytic_account_id=value.get("analytic_account_id"),
                    analytic_distribution=value.get("analytic_distribution", {}),
                    currency=move_currency,
                    name=value.get("name", "Automatic Transfer"),
                    date=end_date,
                    debit=debit,
                    credit=credit,
                    amount_currency=debit if debit else -credit,
                )
            )
        MoveLine.objects.bulk_create(move_lines)
        self._compute_move_ids_count()
        self.save(update_fields=["move_ids_count", "updated_at"])
        return current_move

    def _get_move_for_period(self, end_date):
        return self.moves.filter(date=end_date, state="draft").order_by("-date").first()

    def _determine_start_date(self):
        last_move = self.moves.filter(state="posted", company_id=self.company_id).order_by("-date").first()
        return (last_move.date + timedelta(days=1)) if last_move else self.date_start

    def _get_next_move_date(self, base_date):
        if self.frequency == "month":
            delta = relativedelta(months=1)
        elif self.frequency == "quarter":
            delta = relativedelta(months=3)
        else:
            delta = relativedelta(years=1)
        return base_date + delta - timedelta(days=1)

    def _get_auto_transfer_move_line_values(self, start_date, end_date):
        values = []
        filtered_lines = self.lines.filter(
            models.Q(analytic_accounts__isnull=False) | models.Q(partners__isnull=False)
        ).distinct()
        if filtered_lines.exists():
            values += filtered_lines._get_transfer_move_lines_values(start_date, end_date)

        non_filtered_lines = self.lines.exclude(id__in=filtered_lines.values_list("id", flat=True))
        if non_filtered_lines.exists():
            values += self._get_non_filtered_auto_transfer_move_line_values(non_filtered_lines, start_date, end_date)
        return values

    def _get_non_filtered_auto_transfer_move_line_values(self, lines, start_date, end_date):
        from accounting.models import MoveLine

        domain = self._get_move_lines_base_domain(start_date, end_date)
        qs = MoveLine.objects.filter(**domain)

        excluded_partner_ids = [pid for pid in self.lines.values_list("partners__id", flat=True) if pid]
        if excluded_partner_ids:
            qs = qs.exclude(partner_id__in=excluded_partner_ids)
        excluded_analytic_ids = {aid for aid in self.lines.values_list("analytic_accounts__id", flat=True) if aid}
        if excluded_analytic_ids:
            qs = [ml for ml in qs if not self._line_has_any_analytic(ml, excluded_analytic_ids)]
        else:
            qs = list(qs)

        totals_map = {}
        for line in qs:
            bucket = totals_map.setdefault(line.account_id, {"debit_sum": Decimal("0"), "credit_sum": Decimal("0")})
            bucket["debit_sum"] += Decimal(line.debit)
            bucket["credit_sum"] += Decimal(line.credit)

        values_list = []
        lines_list = list(lines)
        for account_id, sums in totals_map.items():
            balance = sums["debit_sum"] - sums["credit_sum"]
            initial_amount = abs(balance)
            source_account_is_debit = balance >= 0
            if initial_amount == 0:
                continue
            move_lines_values, amount_left = self._get_non_analytic_transfer_values(
                account_id=account_id,
                lines=lines_list,
                write_date=end_date,
                amount=initial_amount,
                is_debit=source_account_is_debit,
            )
            subtracted_amount = initial_amount - amount_left
            source_move_line = {
                "name": f"Automatic Transfer (-{self.total_percent}%)",
                "account_id": account_id,
                "credit" if source_account_is_debit else "debit": subtracted_amount,
            }
            values_list.extend(move_lines_values)
            values_list.append(source_move_line)
        return values_list

    @staticmethod
    def _line_has_any_analytic(move_line, analytic_ids):
        if move_line.analytic_account_id and move_line.analytic_account_id in analytic_ids:
            return True
        distribution = move_line.analytic_distribution or {}
        if isinstance(distribution, dict):
            for key in distribution.keys():
                try:
                    if int(key) in analytic_ids:
                        return True
                except (TypeError, ValueError):
                    continue
        return False

    def _get_non_analytic_transfer_values(self, account_id, lines, write_date, amount, is_debit):
        amount_left = Decimal(amount)
        take_the_rest = self.total_percent == Decimal("100")
        values_list = []
        line_count = len(lines)

        for idx, line in enumerate(lines):
            if take_the_rest and idx == line_count - 1:
                line_amount = amount_left
                amount_left = Decimal("0")
            else:
                line_amount = (line.percent / Decimal("100")) * Decimal(amount)
                line_amount = line_amount.quantize(Decimal("0.000001"))
                amount_left -= line_amount

            values_list.append(
                line._get_destination_account_transfer_move_line_values(
                    origin_account_id=account_id,
                    amount=line_amount,
                    is_debit=is_debit,
                    write_date=write_date,
                )
            )
        return values_list, amount_left

    def clean(self):
        if self.journal and self.company_id and self.journal.company_id != self.company_id:
            raise ValidationError("Journal and transfer model company must match.")
        if self.date_stop and self.date_stop < self.date_start:
            raise ValidationError("Stop date cannot be before start date.")
        if self.pk:
            self._compute_total_percent()
            if self.lines.exists():
                self._check_line_ids_percent()
                self._check_line_ids_filters()

    def save(self, *args, **kwargs):
        if not self.company_id and self.journal_id:
            self.company_id = self.journal.company_id
        if not self.date_start:
            self.date_start = self._get_default_date_start()
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        self._unlink_with_check_moves()
        return super().delete(using=using, keep_parents=keep_parents)


class TransferModelLineQuerySet(models.QuerySet):
    def _get_transfer_move_lines_values(self, start_date, end_date):
        from accounting.models import MoveLine

        transfer_values = []
        already_handled_move_line_ids = []

        for line in self:
            qs = MoveLine.objects.filter(line._get_move_lines_domain(start_date, end_date, already_handled_move_line_ids))
            qs = [ml for ml in qs if line._line_matches_filters(ml)]
            totals_map = {}
            for move_line in qs:
                bucket = totals_map.setdefault(
                    move_line.account_id,
                    {"debit_sum": Decimal("0"), "credit_sum": Decimal("0"), "ids": []},
                )
                bucket["debit_sum"] += Decimal(move_line.debit)
                bucket["credit_sum"] += Decimal(move_line.credit)
                bucket["ids"].append(move_line.id)

            for account_id, sums in totals_map.items():
                already_handled_move_line_ids.extend(sums["ids"])
                balance = sums["debit_sum"] - sums["credit_sum"]
                if balance == 0:
                    continue
                transfer_values.extend(
                    line._get_transfer_values(
                        account_id=account_id,
                        amount=abs(balance),
                        is_debit=(balance > 0),
                        write_date=end_date,
                    )
                )
        return transfer_values


class TransferModelLine(AccountingBaseModel):
    transfer_model = models.ForeignKey("accounting.TransferModel", on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="destination_transfer_lines")
    percent = models.DecimalField(max_digits=9, decimal_places=6, default=Decimal("100"))
    analytic_accounts = models.ManyToManyField("accounting.AnalyticAccount", related_name="transfer_model_lines", blank=True)
    partners = models.ManyToManyField("accounting.Partner", related_name="transfer_model_lines", blank=True)
    percent_is_readonly = models.BooleanField(default=False)
    sequence = models.IntegerField(default=10)

    objects = TransferModelLineQuerySet.as_manager()

    class Meta:
        db_table = "ga_transfer_model_line"
        ordering = ("sequence", "id")
        unique_together = (("transfer_model", "account"),)

    def set_percent_if_analytic_account_ids(self):
        if self.analytic_accounts.exists() or self.partners.exists():
            self.percent = Decimal("100")

    def _get_transfer_move_lines_values(self, start_date, end_date):
        return TransferModelLine.objects.filter(id=self.id)._get_transfer_move_lines_values(start_date, end_date)

    def _get_move_lines_domain(self, start_date, end_date, avoid_move_line_ids=None):
        from accounting.models import MoveLine

        base_filters = self.transfer_model._get_move_lines_base_domain(start_date, end_date)
        qs = MoveLine.objects.filter(**base_filters)
        if avoid_move_line_ids:
            qs = qs.exclude(id__in=avoid_move_line_ids)
        if self.partners.exists():
            qs = qs.filter(partner_id__in=self.partners.values_list("id", flat=True))
        return models.Q(id__in=qs.values("id"))

    def _line_matches_filters(self, move_line):
        analytic_ids = set(self.analytic_accounts.values_list("id", flat=True))
        partner_ids = set(self.partners.values_list("id", flat=True))

        if partner_ids and move_line.partner_id not in partner_ids:
            return False

        if not analytic_ids:
            return True
        if move_line.analytic_account_id and move_line.analytic_account_id in analytic_ids:
            return True
        distribution = move_line.analytic_distribution or {}
        if isinstance(distribution, dict):
            for key in distribution.keys():
                try:
                    if int(key) in analytic_ids:
                        return True
                except (TypeError, ValueError):
                    continue
        return False

    def _get_transfer_values(self, account_id, amount, is_debit, write_date):
        return [
            self._get_destination_account_transfer_move_line_values(account_id, amount, is_debit, write_date),
            self._get_origin_account_transfer_move_line_values(account_id, amount, is_debit, write_date),
        ]

    def _get_origin_account_transfer_move_line_values(self, origin_account_id, amount, is_debit, write_date):
        from accounting.models import Account

        origin_account = Account.objects.get(id=origin_account_id)
        analytic_names = ", ".join(self.analytic_accounts.values_list("name", flat=True))
        partner_names = ", ".join(self.partners.values_list("name", flat=True))

        if analytic_names and partner_names:
            name = f"Automatic Transfer (entries with analytic account(s): {analytic_names} and partner(s): {partner_names})"
        elif analytic_names:
            name = f"Automatic Transfer (entries with analytic account(s): {analytic_names})"
        elif partner_names:
            name = f"Automatic Transfer (entries with partner(s): {partner_names})"
        else:
            name = f"Automatic Transfer (to account {self.account.code})"

        return {
            "name": name,
            "account_id": origin_account.id,
            "credit" if is_debit else "debit": amount,
        }

    def _get_destination_account_transfer_move_line_values(self, origin_account_id, amount, is_debit, write_date):
        from accounting.models import Account

        origin_account = Account.objects.get(id=origin_account_id)
        analytic_names = ", ".join(self.analytic_accounts.values_list("name", flat=True))
        partner_names = ", ".join(self.partners.values_list("name", flat=True))

        if analytic_names and partner_names:
            name = (
                f"Automatic Transfer (from account {origin_account.code} "
                f"with analytic account(s): {analytic_names} and partner(s): {partner_names})"
            )
        elif analytic_names:
            name = f"Automatic Transfer (from account {origin_account.code} with analytic account(s): {analytic_names})"
        elif partner_names:
            name = f"Automatic Transfer (from account {origin_account.code} with partner(s): {partner_names})"
        else:
            name = f"Automatic Transfer ({self.percent}% from account {origin_account.code})"

        return {
            "name": name,
            "account_id": self.account_id,
            "debit" if is_debit else "credit": amount,
        }

    def _compute_percent_is_readonly(self):
        self.percent_is_readonly = self.analytic_accounts.exists() or self.partners.exists()

    def clean(self):
        if self.transfer_model_id and self.account_id and self.transfer_model.company_id != self.account.company_id:
            raise ValidationError("Destination account company must match transfer model company.")
        if self.percent <= 0:
            raise ValidationError("Percent must be greater than zero.")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._compute_percent_is_readonly()
        self.set_percent_if_analytic_account_ids()
        super().save(update_fields=["percent_is_readonly", "percent", "updated_at"])
        self.transfer_model._compute_total_percent()
        self.transfer_model._compute_move_ids_count()
        self.transfer_model.save(update_fields=["total_percent", "move_ids_count", "updated_at"])

    def delete(self, using=None, keep_parents=False):
        transfer_model = self.transfer_model
        result = super().delete(using=using, keep_parents=keep_parents)
        transfer_model._compute_total_percent()
        transfer_model._compute_move_ids_count()
        transfer_model.save(update_fields=["total_percent", "move_ids_count", "updated_at"])
        return result
