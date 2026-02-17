from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class FollowupLevel(AccountingBaseModel):
    ACTION_CHOICES = (
        ("email", "Send Email"),
        ("call", "Call"),
        ("manual", "Manual Action"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="followup_levels")
    name = models.CharField(max_length=255)
    delay_days = models.IntegerField(default=0)
    action = models.CharField(max_length=16, choices=ACTION_CHOICES, default="email")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_followup_level"
        unique_together = (("company", "name"),)
        ordering = ("company_id", "delay_days", "id")


class BankAccount(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="bank_accounts")
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, related_name="bank_accounts")
    bank_name = models.CharField(max_length=255)
    account_holder = models.CharField(max_length=255, blank=True)
    iban = models.CharField(max_length=64, blank=True)
    swift = models.CharField(max_length=32, blank=True)
    account_number = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_bank_account"
        unique_together = (("company", "journal"),)

    def clean(self):
        if self.journal_id and self.journal.company_id != self.company_id:
            raise ValidationError("Bank account journal company must match bank account company.")


class ReconciliationModel(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="reconciliation_models")
    name = models.CharField(max_length=255)
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, null=True, blank=True, related_name="reconciliation_models")
    auto_reconcile = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_reconciliation_model"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.journal_id and self.journal.company_id != self.company_id:
            raise ValidationError("Reconciliation model journal company must match company.")


class ReconciliationModelLine(AccountingBaseModel):
    AMOUNT_TYPE_CHOICES = (
        ("fixed", "Fixed"),
        ("percent", "Percent"),
    )

    reconciliation_model = models.ForeignKey("accounting.ReconciliationModel", on_delete=models.CASCADE, related_name="lines")
    sequence = models.PositiveIntegerField(default=10)
    label = models.CharField(max_length=255)
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="reconciliation_model_lines")
    tax = models.ForeignKey("accounting.Tax", on_delete=models.PROTECT, null=True, blank=True, related_name="reconciliation_model_lines")
    amount_type = models.CharField(max_length=16, choices=AMOUNT_TYPE_CHOICES, default="fixed")
    amount = models.DecimalField(max_digits=18, decimal_places=6, default=0)

    class Meta:
        db_table = "ga_reconciliation_model_line"
        ordering = ("reconciliation_model_id", "sequence", "id")

    def clean(self):
        company_id = self.reconciliation_model.company_id
        if self.account_id and self.account.company_id != company_id:
            raise ValidationError("Reconciliation line account company must match reconciliation model company.")
        if self.tax_id and self.tax.company_id != company_id:
            raise ValidationError("Reconciliation line tax company must match reconciliation model company.")


class FiscalPosition(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="fiscal_positions")
    name = models.CharField(max_length=255)
    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, null=True, blank=True, related_name="fiscal_positions")
    auto_apply = models.BooleanField(default=False)
    vat_required = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_fiscal_position"
        unique_together = (("company", "name"),)


class FiscalPositionTaxMap(AccountingBaseModel):
    fiscal_position = models.ForeignKey("accounting.FiscalPosition", on_delete=models.CASCADE, related_name="tax_maps")
    tax_src = models.ForeignKey("accounting.Tax", on_delete=models.PROTECT, related_name="fiscal_position_tax_src")
    tax_dest = models.ForeignKey("accounting.Tax", on_delete=models.PROTECT, related_name="fiscal_position_tax_dest")

    class Meta:
        db_table = "ga_fiscal_position_tax_map"
        unique_together = (("fiscal_position", "tax_src"),)

    def clean(self):
        company_id = self.fiscal_position.company_id
        if self.tax_src.company_id != company_id or self.tax_dest.company_id != company_id:
            raise ValidationError("Fiscal position tax map taxes must match fiscal position company.")


class FiscalPositionAccountMap(AccountingBaseModel):
    fiscal_position = models.ForeignKey("accounting.FiscalPosition", on_delete=models.CASCADE, related_name="account_maps")
    account_src = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="fiscal_position_account_src")
    account_dest = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="fiscal_position_account_dest")

    class Meta:
        db_table = "ga_fiscal_position_account_map"
        unique_together = (("fiscal_position", "account_src"),)

    def clean(self):
        company_id = self.fiscal_position.company_id
        if self.account_src.company_id != company_id or self.account_dest.company_id != company_id:
            raise ValidationError("Fiscal position account map accounts must match fiscal position company.")


class Ledger(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="ledgers")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, null=True, blank=True, related_name="ledgers")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32)
    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_ledger"
        unique_together = (("company", "code"),)
        constraints = [
            models.UniqueConstraint(
                fields=["company"],
                condition=models.Q(is_default=True),
                name="uniq_company_default_ledger",
            )
        ]


class FinancialBudget(AccountingBaseModel):
    STATE_CHOICES = (
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="budgets")
    name = models.CharField(max_length=255)
    date_from = models.DateField()
    date_to = models.DateField()
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="draft")

    class Meta:
        db_table = "ga_financial_budget"
        unique_together = (("company", "name"),)


class FinancialBudgetLine(AccountingBaseModel):
    budget = models.ForeignKey("accounting.FinancialBudget", on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="budget_lines")
    name = models.CharField(max_length=255, blank=True)
    planned_amount = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    practical_amount = models.DecimalField(max_digits=18, decimal_places=6, default=0)

    class Meta:
        db_table = "ga_financial_budget_line"

    def clean(self):
        if self.account.company_id != self.budget.company_id:
            raise ValidationError("Budget line account company must match budget company.")


class AssetModel(AccountingBaseModel):
    METHOD_CHOICES = (
        ("linear", "Linear"),
        ("degressive", "Degressive"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="asset_models")
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=16, choices=METHOD_CHOICES, default="linear")
    method_number = models.PositiveIntegerField(default=5)
    method_period_months = models.PositiveIntegerField(default=12)
    prorata = models.BooleanField(default=True)
    account_asset = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="asset_model_asset_accounts")
    account_depreciation = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="asset_model_depr_accounts")
    account_expense = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="asset_model_expense_accounts")
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, related_name="asset_models")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_asset_model"
        unique_together = (("company", "name"),)

    def clean(self):
        company_id = self.company_id
        account_fields = [self.account_asset, self.account_depreciation, self.account_expense]
        for account in account_fields:
            if account.company_id != company_id:
                raise ValidationError("Asset model accounts must belong to the same company.")
        if self.journal.company_id != company_id:
            raise ValidationError("Asset model journal must belong to the same company.")


class DisallowedExpenseCategory(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="disallowed_expense_categories")
    name = models.CharField(max_length=255)
    disallow_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    expense_account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, null=True, blank=True, related_name="disallowed_expense_categories")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_disallowed_expense_category"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.disallow_percent < 0 or self.disallow_percent > 100:
            raise ValidationError("Disallow percent must be between 0 and 100.")
        if self.expense_account_id and self.expense_account.company_id != self.company_id:
            raise ValidationError("Disallowed expense account company must match category company.")


class PaymentProvider(AccountingBaseModel):
    STATE_CHOICES = (
        ("disabled", "Disabled"),
        ("test", "Test"),
        ("enabled", "Enabled"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="payment_providers")
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, null=True, blank=True, related_name="payment_providers")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=STATE_CHOICES, default="disabled")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_provider"
        unique_together = (("company", "code"),)

    def clean(self):
        if self.journal_id and self.journal.company_id != self.company_id:
            raise ValidationError("Payment provider journal company must match provider company.")


class PaymentProviderMethod(AccountingBaseModel):
    provider = models.ForeignKey("accounting.PaymentProvider", on_delete=models.CASCADE, related_name="provider_methods")
    payment_method = models.ForeignKey("accounting.PaymentMethod", on_delete=models.PROTECT, related_name="provider_methods")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_provider_method"
        unique_together = (("provider", "payment_method"),)
