from decimal import Decimal

from django.db import models

from .base import AccountingBaseModel


class JournalGroup(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="journal_groups")
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

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="journals")
    group = models.ForeignKey("accounting.JournalGroup", on_delete=models.PROTECT, null=True, blank=True, related_name="journals")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, null=True, blank=True, related_name="journals")
    default_account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, null=True, blank=True, related_name="default_for_journals")
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
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="payment_terms")
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_payment_term"
        unique_together = ("company", "name")


class Incoterm(AccountingBaseModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_incoterm"
        ordering = ("code",)


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

    payment_term = models.ForeignKey("accounting.PaymentTerm", on_delete=models.CASCADE, related_name="lines")
    sequence = models.PositiveIntegerField(default=10)
    value_type = models.CharField(max_length=16, choices=VALUE_TYPE_CHOICES)
    value = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    due_type = models.CharField(max_length=32, choices=DUE_TYPE_CHOICES, default="days_after_invoice_date")
    due_days = models.IntegerField(default=0)

    class Meta:
        db_table = "ga_payment_term_line"
        ordering = ("payment_term_id", "sequence", "id")


class TaxGroup(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="tax_groups")
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True)
    sequence = models.PositiveIntegerField(default=10)
    country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_groups",
    )
    tax_payable_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_groups_payable",
    )
    tax_receivable_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tax_groups_receivable",
    )
    active = models.BooleanField(default=True)

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

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="taxes")
    tax_group = models.ForeignKey("accounting.TaxGroup", on_delete=models.PROTECT, related_name="taxes")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, null=True, blank=True, related_name="taxes")
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

    tax = models.ForeignKey("accounting.Tax", on_delete=models.CASCADE, related_name="repartition_lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, null=True, blank=True, related_name="tax_repartition_lines")
    document_type = models.CharField(max_length=16, choices=DOCUMENT_TYPE_CHOICES)
    repartition_type = models.CharField(max_length=8, choices=REPARTITION_TYPE_CHOICES)
    factor_percent = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("100"))
    sequence = models.PositiveIntegerField(default=10)

    class Meta:
        db_table = "ga_tax_repartition_line"
        ordering = ("tax_id", "document_type", "sequence", "id")
