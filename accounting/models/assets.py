from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class Asset(AccountingBaseModel):
    METHOD_CHOICES = (
        ("linear", "Linear"),
        ("degressive", "Degressive"),
    )
    STATE_CHOICES = (
        ("draft", "Draft"),
        ("running", "Running"),
        ("paused", "Paused"),
        ("closed", "Closed"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="assets")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, null=True, blank=True)
    partner = models.ForeignKey("accounting.Partner", on_delete=models.PROTECT, null=True, blank=True, related_name="assets")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, null=True, blank=True, related_name="assets")
    asset_account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="assets")
    depreciation_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assets_depreciation",
    )
    expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assets_expense",
    )
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, null=True, blank=True, related_name="assets")
    acquisition_date = models.DateField()
    first_depreciation_date = models.DateField(null=True, blank=True)
    original_value = models.DecimalField(max_digits=18, decimal_places=6)
    salvage_value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    method = models.CharField(max_length=16, choices=METHOD_CHOICES, default="linear")
    method_number = models.PositiveIntegerField(default=5)
    method_period = models.PositiveIntegerField(default=12)
    prorata = models.BooleanField(default=False)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="draft")
    active = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "ga_asset"
        unique_together = ("company", "code")
        indexes = [
            models.Index(fields=["company", "acquisition_date"], name="ga_asset_company_bbf708_idx"),
            models.Index(fields=["state"], name="ga_asset_state_4f0a6c_idx"),
            models.Index(fields=["active"], name="ga_asset_active_63fdc0_idx"),
        ]

    def clean(self) -> None:
        if self.original_value <= 0:
            raise ValidationError("Original value must be greater than zero.")
        if self.salvage_value < 0:
            raise ValidationError("Salvage value cannot be negative.")
        if self.salvage_value >= self.original_value:
            raise ValidationError("Salvage value must be lower than original value.")
        if self.first_depreciation_date and self.first_depreciation_date < self.acquisition_date:
            raise ValidationError("First depreciation date cannot be before acquisition date.")

        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Partner company must match asset company.")
        if self.journal_id and self.journal.company_id != self.company_id:
            raise ValidationError("Journal company must match asset company.")
        if self.asset_account_id and self.asset_account.company_id != self.company_id:
            raise ValidationError("Asset account company must match asset company.")
        if self.depreciation_account_id and self.depreciation_account.company_id != self.company_id:
            raise ValidationError("Depreciation account company must match asset company.")
        if self.expense_account_id and self.expense_account.company_id != self.company_id:
            raise ValidationError("Expense account company must match asset company.")


class AssetDepreciationLine(AccountingBaseModel):
    STATE_CHOICES = (
        ("draft", "Draft"),
        ("posted", "Posted"),
    )

    asset = models.ForeignKey("accounting.Asset", on_delete=models.CASCADE, related_name="depreciation_lines")
    move = models.ForeignKey(
        "accounting.Move",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="asset_depreciation_lines",
    )
    sequence = models.PositiveIntegerField(default=1)
    date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=6)
    depreciated_value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    residual_value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="draft")

    class Meta:
        db_table = "ga_asset_depreciation_line"
        ordering = ("asset_id", "sequence", "id")
        unique_together = ("asset", "sequence")
        indexes = [
            models.Index(fields=["asset", "date"], name="ga_asset_de_asset_i_077152_idx"),
            models.Index(fields=["state"], name="ga_asset_de_state_0d2332_idx"),
        ]

    def clean(self) -> None:
        if self.amount <= 0:
            raise ValidationError("Depreciation amount must be greater than zero.")
        if self.residual_value < 0:
            raise ValidationError("Residual value cannot be negative.")
        if self.move_id and self.move.company_id != self.asset.company_id:
            raise ValidationError("Depreciation move company must match asset company.")
        if self.state == "posted" and not self.move_id:
            raise ValidationError("Posted depreciation line requires a move.")
