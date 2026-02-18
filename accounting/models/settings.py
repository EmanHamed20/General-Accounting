from django.core.exceptions import ValidationError
from django.db import models
from django.apps import apps

from .base import AccountingBaseModel


class AccountingSettings(AccountingBaseModel):
    TAX_RETURN_PERIODICITY_CHOICES = (
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    )
    TAX_ROUNDING_METHOD_CHOICES = (
        ("round_per_line", "Round per Line"),
        ("round_globally", "Round Globally"),
    )
    PRICE_INCLUDE_CHOICES = (
        ("tax_included", "Tax Included"),
        ("tax_excluded", "Tax Excluded"),
    )
    FISCALYEAR_LAST_MONTH_CHOICES = (
        ("1", "January"),
        ("2", "February"),
        ("3", "March"),
        ("4", "April"),
        ("5", "May"),
        ("6", "June"),
        ("7", "July"),
        ("8", "August"),
        ("9", "September"),
        ("10", "October"),
        ("11", "November"),
        ("12", "December"),
    )
    QUICK_EDIT_MODE_CHOICES = (
        ("none", "Disabled"),
        ("warning", "Warning"),
        ("allow", "Allow"),
    )
    DEFERRED_GENERATION_CHOICES = (
        ("manual", "Manual"),
        ("on_posting", "On Posting"),
    )
    DEFERRED_AMOUNT_COMPUTATION_CHOICES = (
        ("day_count", "Day Count"),
        ("equal_per_period", "Equal per Period"),
    )
    TERMS_TYPE_CHOICES = (
        ("html", "HTML"),
        ("plain", "Plain Text"),
    )

    # General/company context fields used by Odoo settings view.
    company = models.OneToOneField("accounting.Company", on_delete=models.CASCADE, related_name="accounting_settings")
    country_code = models.CharField(max_length=2, blank=True, default="")

    # UI: Configuration > Settings > Fiscal Localization
    fiscal_localization_country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_settings_localization",
    )
    chart_template_country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_settings_chart_template",
    )
    account_fiscal_country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_settings_fiscal_country",
    )
    chart_template = models.CharField(max_length=255, blank=True, default="")
    has_chart_of_accounts = models.BooleanField(default=False)
    has_accounting_entries = models.BooleanField(default=False)
    currency = models.ForeignKey(
        "accounting.Currency",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_settings",
    )
    group_multi_currency = models.BooleanField(default=False)
    module_currency_rate_live = models.BooleanField(default=False)

    # UI: Configuration > Settings > Taxes
    default_sales_tax = models.ForeignKey(
        "accounting.Tax",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="default_sales_settings",
    )
    default_purchase_tax = models.ForeignKey(
        "accounting.Tax",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="default_purchase_settings",
    )
    tax_return_periodicity = models.CharField(
        max_length=16,
        choices=TAX_RETURN_PERIODICITY_CHOICES,
        default="monthly",
    )
    tax_return_reminder_days = models.PositiveSmallIntegerField(default=7)
    tax_return_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_return_settings",
    )
    tax_rounding_method = models.CharField(
        max_length=24,
        choices=TAX_ROUNDING_METHOD_CHOICES,
        default="round_per_line",
    )
    account_price_include = models.CharField(
        max_length=16,
        choices=PRICE_INCLUDE_CHOICES,
        default="tax_excluded",
    )

    # UI: Configuration > Settings > Default Accounts
    currency_exchange_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="currency_exchange_settings",
    )
    income_currency_exchange_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="income_currency_exchange_settings",
    )
    expense_currency_exchange_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_currency_exchange_settings",
    )
    bank_suspense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="bank_suspense_settings",
    )
    account_journal_suspense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_suspense_settings",
    )
    transfer_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transfer_settings",
    )
    tax_exigibility = models.BooleanField(default=False)
    tax_cash_basis_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_cash_basis_settings",
    )
    account_cash_basis_base_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cash_basis_base_settings",
    )
    account_discount_expense_allocation = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discount_expense_allocation_settings",
    )
    account_discount_income_allocation = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="discount_income_allocation_settings",
    )
    account_journal_early_pay_discount_gain_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="early_discount_gain_settings",
    )
    account_journal_early_pay_discount_loss_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="early_discount_loss_settings",
    )

    # UI: Configuration > Settings > Invoicing / Fiscal Periods
    default_sale_payment_term = models.ForeignKey(
        "accounting.PaymentTerm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="default_sale_settings",
    )
    default_purchase_payment_term = models.ForeignKey(
        "accounting.PaymentTerm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="default_purchase_settings",
    )
    fiscalyear_last_day = models.PositiveSmallIntegerField(default=31)
    fiscalyear_last_month = models.CharField(max_length=2, choices=FISCALYEAR_LAST_MONTH_CHOICES, default="12")
    use_anglo_saxon = models.BooleanField(default=False)
    invoicing_switch_threshold = models.DateField(null=True, blank=True)
    predict_bill_product = models.BooleanField(default=False)

    # UI: Configuration > Settings > Feature toggles (Invoices, Payments, Vendor Bills, Analytics, PEPPOL, Audit)
    followup_enabled = models.BooleanField(default=True)
    multi_ledger_enabled = models.BooleanField(default=False)
    budgets_enabled = models.BooleanField(default=False)
    assets_enabled = models.BooleanField(default=False)
    online_payments_enabled = models.BooleanField(default=False)
    quick_edit_mode = models.CharField(max_length=16, choices=QUICK_EDIT_MODE_CHOICES, default="none")
    check_account_audit_trail = models.BooleanField(default=False)
    autopost_bills = models.BooleanField(default=False)
    account_use_credit_limit = models.BooleanField(default=False)
    account_default_credit_limit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    account_storno = models.BooleanField(default=False)
    qr_code = models.BooleanField(default=False)
    module_l10n_eu_oss = models.BooleanField(default=False)
    module_snailmail_account = models.BooleanField(default=False)
    group_sale_delivery_address = models.BooleanField(default=False)
    group_warning_account = models.BooleanField(default=False)
    group_cash_rounding = models.BooleanField(default=False)
    module_account_intrastat = models.BooleanField(default=False)
    incoterm = models.CharField(max_length=255, blank=True, default="")
    group_show_sale_receipts = models.BooleanField(default=False)
    terms_type = models.CharField(max_length=16, choices=TERMS_TYPE_CHOICES, default="html")
    preview_ready = models.BooleanField(default=False)
    display_invoice_amount_total_words = models.BooleanField(default=False)
    display_invoice_tax_company_currency = models.BooleanField(default=False)
    group_uom = models.BooleanField(default=False)
    module_account_payment = models.BooleanField(default=False)
    module_account_batch_payment = models.BooleanField(default=False)
    module_account_sepa_direct_debit = models.BooleanField(default=False)
    group_show_purchase_receipts = models.BooleanField(default=False)
    module_account_check_printing = models.BooleanField(default=False)
    module_account_iso20022 = models.BooleanField(default=False)
    module_account_extract = models.BooleanField(default=False)
    module_account_bank_statement_import_csv = models.BooleanField(default=False)
    module_account_bank_statement_import_qif = models.BooleanField(default=False)
    module_account_bank_statement_import_ofx = models.BooleanField(default=False)
    module_account_bank_statement_import_camt = models.BooleanField(default=False)
    module_account_reports = models.BooleanField(default=False)
    group_analytic_accounting = models.BooleanField(default=False)
    module_account_budget = models.BooleanField(default=False)
    module_product_margin = models.BooleanField(default=False)
    is_account_peppol_eligible = models.BooleanField(default=False)
    module_account_peppol = models.BooleanField(default=False)
    invoice_terms = models.TextField(blank=True)
    use_invoice_terms = models.BooleanField(default=False)

    # UI: Configuration > Settings > Deferred management
    deferred_expense_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deferred_expense_journal_settings",
    )
    deferred_expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deferred_expense_account_settings",
    )
    generate_deferred_expense_entries_method = models.CharField(
        max_length=16,
        choices=DEFERRED_GENERATION_CHOICES,
        default="manual",
    )
    deferred_expense_amount_computation_method = models.CharField(
        max_length=24,
        choices=DEFERRED_AMOUNT_COMPUTATION_CHOICES,
        default="day_count",
    )
    deferred_revenue_journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deferred_revenue_journal_settings",
    )
    deferred_revenue_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="deferred_revenue_account_settings",
    )
    generate_deferred_revenue_entries_method = models.CharField(
        max_length=16,
        choices=DEFERRED_GENERATION_CHOICES,
        default="manual",
    )
    deferred_revenue_amount_computation_method = models.CharField(
        max_length=24,
        choices=DEFERRED_AMOUNT_COMPUTATION_CHOICES,
        default="day_count",
    )

    class Meta:
        db_table = "ga_accounting_settings"

    def clean(self):
        if self.default_sales_tax and self.default_sales_tax.company_id != self.company_id:
            raise ValidationError("Default sales tax company must match settings company.")
        if self.default_purchase_tax and self.default_purchase_tax.company_id != self.company_id:
            raise ValidationError("Default purchase tax company must match settings company.")
        if self.tax_return_journal and self.tax_return_journal.company_id != self.company_id:
            raise ValidationError("Tax return journal company must match settings company.")
        if self.default_sale_payment_term and self.default_sale_payment_term.company_id != self.company_id:
            raise ValidationError("Default sale payment term company must match settings company.")
        if self.default_purchase_payment_term and self.default_purchase_payment_term.company_id != self.company_id:
            raise ValidationError("Default purchase payment term company must match settings company.")
        account_fields = [
            self.income_currency_exchange_account,
            self.expense_currency_exchange_account,
            self.bank_suspense_account,
            self.account_journal_suspense_account,
            self.transfer_account,
            self.account_cash_basis_base_account,
            self.account_discount_expense_allocation,
            self.account_discount_income_allocation,
            self.account_journal_early_pay_discount_gain_account,
            self.account_journal_early_pay_discount_loss_account,
            self.deferred_expense_account,
            self.deferred_revenue_account,
        ]
        for account in account_fields:
            if account and account.company_id != self.company_id:
                raise ValidationError("All settings accounts must belong to the same company.")

        journal_fields = [
            self.tax_return_journal,
            self.currency_exchange_journal,
            self.tax_cash_basis_journal,
            self.deferred_expense_journal,
            self.deferred_revenue_journal,
        ]
        for journal in journal_fields:
            if journal and journal.company_id != self.company_id:
                raise ValidationError("All settings journals must belong to the same company.")

        if self.tax_exigibility:
            if not self.tax_cash_basis_journal_id:
                raise ValidationError("Cash basis journal is required when tax exigibility is enabled.")
            if not self.account_cash_basis_base_account_id:
                raise ValidationError("Cash basis base account is required when tax exigibility is enabled.")

        if self.pk:
            previous = AccountingSettings.objects.filter(pk=self.pk).only("check_account_audit_trail").first()
            if previous and previous.check_account_audit_trail and not self.check_account_audit_trail:
                MoveLine = apps.get_model("accounting", "MoveLine")
                has_journal_items = MoveLine.objects.filter(move__company_id=self.company_id).exists()
                if has_journal_items:
                    raise ValidationError("Audit Trail cannot be disabled once journal items exist.")

        if self.fiscalyear_last_day < 1 or self.fiscalyear_last_day > 31:
            raise ValidationError("Fiscal year last day must be between 1 and 31.")
