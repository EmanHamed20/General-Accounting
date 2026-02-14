from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models


class AccountingBaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Company(AccountingBaseModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=32, unique=True)
    lock_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "ga_company"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Currency(AccountingBaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=3, unique=True)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)

    class Meta:
        db_table = "ga_currency"

    def __str__(self) -> str:
        return self.code


class Partner(AccountingBaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    is_company = models.BooleanField(default=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="partners")

    class Meta:
        db_table = "ga_partner"

    def __str__(self) -> str:
        return self.name


class AccountRoot(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="account_roots")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "ga_account_root"
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AccountGroup(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="account_groups")
    code_prefix_start = models.CharField(max_length=16)
    code_prefix_end = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")

    class Meta:
        db_table = "ga_account_group"
        unique_together = ("company", "code_prefix_start", "code_prefix_end")

    def __str__(self) -> str:
        return self.name


class Account(AccountingBaseModel):
    ACCOUNT_TYPE_CHOICES = (
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("income", "Income"),
        ("expense", "Expense"),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="accounts")
    root = models.ForeignKey(AccountRoot, on_delete=models.PROTECT, related_name="accounts", null=True, blank=True)
    group = models.ForeignKey(AccountGroup, on_delete=models.PROTECT, related_name="accounts", null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="accounts")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES)
    reconcile = models.BooleanField(default=False)
    deprecated = models.BooleanField(default=False)

    class Meta:
        db_table = "ga_account"
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class JournalGroup(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="journal_groups")
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "ga_journal_group"
        unique_together = ("company", "name")


class Journal(AccountingBaseModel):
    JOURNAL_TYPE_CHOICES = (
        ("sale", "Sale"),
        ("purchase", "Purchase"),
        ("bank", "Bank"),
        ("cash", "Cash"),
        ("general", "General"),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="journals")
    group = models.ForeignKey(JournalGroup, on_delete=models.PROTECT, null=True, blank=True, related_name="journals")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="journals")
    default_account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name="default_for_journals")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    journal_type = models.CharField(max_length=16, choices=JOURNAL_TYPE_CHOICES, default="general")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_journal"
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class PaymentTerm(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="payment_terms")
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_term"
        unique_together = ("company", "name")


class PaymentTermLine(AccountingBaseModel):
    VALUE_TYPE_CHOICES = (
        ("percent", "Percent"),
        ("fixed", "Fixed"),
        ("balance", "Balance"),
    )
    DUE_TYPE_CHOICES = (
        ("days_after_invoice_date", "Days After Invoice Date"),
        ("days_after_end_of_month", "Days After End Of Month"),
    )

    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.CASCADE, related_name="lines")
    sequence = models.PositiveIntegerField(default=10)
    value_type = models.CharField(max_length=16, choices=VALUE_TYPE_CHOICES)
    value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    due_type = models.CharField(max_length=32, choices=DUE_TYPE_CHOICES, default="days_after_invoice_date")
    due_days = models.IntegerField(default=0)

    class Meta:
        db_table = "ga_payment_term_line"
        ordering = ("payment_term_id", "sequence", "id")


class TaxGroup(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="tax_groups")
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "ga_tax_group"
        unique_together = ("company", "name")


class Tax(AccountingBaseModel):
    AMOUNT_TYPE_CHOICES = (
        ("percent", "Percent"),
        ("fixed", "Fixed"),
        ("division", "Division"),
    )
    SCOPE_CHOICES = (
        ("sale", "Sale"),
        ("purchase", "Purchase"),
        ("none", "None"),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="taxes")
    tax_group = models.ForeignKey(TaxGroup, on_delete=models.PROTECT, related_name="taxes")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name="taxes")
    name = models.CharField(max_length=255)
    amount_type = models.CharField(max_length=16, choices=AMOUNT_TYPE_CHOICES, default="percent")
    amount = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    scope = models.CharField(max_length=16, choices=SCOPE_CHOICES, default="none")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_tax"
        unique_together = ("company", "name")


class TaxRepartitionLine(AccountingBaseModel):
    DOCUMENT_TYPE_CHOICES = (
        ("invoice", "Invoice"),
        ("refund", "Refund"),
    )
    REPARTITION_TYPE_CHOICES = (
        ("base", "Base"),
        ("tax", "Tax"),
    )

    tax = models.ForeignKey(Tax, on_delete=models.CASCADE, related_name="repartition_lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name="tax_repartition_lines")
    document_type = models.CharField(max_length=16, choices=DOCUMENT_TYPE_CHOICES)
    repartition_type = models.CharField(max_length=8, choices=REPARTITION_TYPE_CHOICES)
    factor_percent = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("100"))
    sequence = models.PositiveIntegerField(default=10)

    class Meta:
        db_table = "ga_tax_repartition_line"
        ordering = ("tax_id", "document_type", "sequence", "id")


class Move(AccountingBaseModel):
    MOVE_STATE_CHOICES = (
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancelled", "Cancelled"),
    )
    MOVE_TYPE_CHOICES = (
        ("entry", "Journal Entry"),
        ("out_invoice", "Customer Invoice"),
        ("in_invoice", "Vendor Bill"),
        ("out_refund", "Customer Credit Note"),
        ("in_refund", "Vendor Credit Note"),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="moves")
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name="moves")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, null=True, blank=True, related_name="moves")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="moves")
    payment_term = models.ForeignKey(PaymentTerm, on_delete=models.PROTECT, null=True, blank=True, related_name="moves")
    reference = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=64, blank=True)
    invoice_date = models.DateField(null=True, blank=True)
    date = models.DateField()
    state = models.CharField(max_length=16, choices=MOVE_STATE_CHOICES, default="draft")
    move_type = models.CharField(max_length=32, choices=MOVE_TYPE_CHOICES, default="entry")
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ga_move"
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["state"]),
        ]

    def clean(self) -> None:
        if self.journal and self.company_id and self.journal.company_id != self.company_id:
            raise ValidationError("Journal and move company must match.")
        if self.partner and self.company_id and self.partner.company_id != self.company_id:
            raise ValidationError("Partner and move company must match.")

    @property
    def balance(self) -> Decimal:
        totals = self.lines.aggregate(
            debit=models.Sum("debit", default=Decimal("0")),
            credit=models.Sum("credit", default=Decimal("0")),
        )
        return totals["debit"] - totals["credit"]


class MoveLine(AccountingBaseModel):
    move = models.ForeignKey(Move, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="move_lines")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    tax = models.ForeignKey(Tax, on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    tax_repartition_line = models.ForeignKey(
        TaxRepartitionLine,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="move_lines",
    )
    name = models.CharField(max_length=255, blank=True)
    date = models.DateField()
    debit = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    credit = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    amount_currency = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))

    class Meta:
        db_table = "ga_move_line"
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["move"]),
        ]

    def clean(self) -> None:
        if self.debit < 0 or self.credit < 0:
            raise ValidationError("Debit/Credit must be positive.")
        if self.debit > 0 and self.credit > 0:
            raise ValidationError("Line cannot have both debit and credit.")
        if self.move_id and self.account_id and self.move.company_id != self.account.company_id:
            raise ValidationError("Move line account company must match move company.")


class PaymentMethod(AccountingBaseModel):
    PAYMENT_DIRECTION_CHOICES = (
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, unique=True)
    payment_direction = models.CharField(max_length=16, choices=PAYMENT_DIRECTION_CHOICES)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_method"


class PaymentMethodLine(AccountingBaseModel):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="payment_method_lines")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, related_name="journal_lines")
    sequence = models.PositiveIntegerField(default=10)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_method_line"
        unique_together = ("journal", "payment_method")


class Payment(AccountingBaseModel):
    PAYMENT_TYPE_CHOICES = (
        ("inbound", "Inbound"),
        ("outbound", "Outbound"),
    )
    PAYMENT_STATE_CHOICES = (
        ("draft", "Draft"),
        ("posted", "Posted"),
        ("cancelled", "Cancelled"),
    )

    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="payments")
    partner = models.ForeignKey(Partner, on_delete=models.PROTECT, null=True, blank=True, related_name="payments")
    journal = models.ForeignKey(Journal, on_delete=models.PROTECT, related_name="payments")
    payment_method_line = models.ForeignKey(PaymentMethodLine, on_delete=models.PROTECT, related_name="payments")
    move = models.OneToOneField(Move, on_delete=models.PROTECT, related_name="payment", null=True, blank=True)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=6)
    payment_type = models.CharField(max_length=16, choices=PAYMENT_TYPE_CHOICES)
    state = models.CharField(max_length=16, choices=PAYMENT_STATE_CHOICES, default="draft")
    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "ga_payment"
        indexes = [models.Index(fields=["company", "date"]), models.Index(fields=["state"])]


class FullReconcile(AccountingBaseModel):
    exchange_move = models.ForeignKey(Move, on_delete=models.PROTECT, null=True, blank=True, related_name="full_reconcile_exchanges")

    class Meta:
        db_table = "ga_full_reconcile"


class PartialReconcile(AccountingBaseModel):
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name="partial_reconciles")
    debit_move_line = models.ForeignKey(MoveLine, on_delete=models.PROTECT, related_name="partial_debits")
    credit_move_line = models.ForeignKey(MoveLine, on_delete=models.PROTECT, related_name="partial_credits")
    full_reconcile = models.ForeignKey(FullReconcile, on_delete=models.PROTECT, null=True, blank=True, related_name="partials")
    amount = models.DecimalField(max_digits=18, decimal_places=6)
    max_date = models.DateField()

    class Meta:
        db_table = "ga_partial_reconcile"
        indexes = [models.Index(fields=["company"]), models.Index(fields=["max_date"])]

    def clean(self) -> None:
        if self.debit_move_line_id == self.credit_move_line_id:
            raise ValidationError("Debit and credit lines must be different.")
        if self.amount <= 0:
            raise ValidationError("Reconciled amount must be positive.")

