from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


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

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="moves")
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, related_name="moves")
    partner = models.ForeignKey("accounting.Partner", on_delete=models.PROTECT, null=True, blank=True, related_name="moves")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, related_name="moves")
    payment_term = models.ForeignKey("accounting.PaymentTerm", on_delete=models.PROTECT, null=True, blank=True, related_name="moves")
    incoterm = models.ForeignKey("accounting.Incoterm", on_delete=models.PROTECT, null=True, blank=True, related_name="moves")
    incoterm_location = models.CharField(max_length=255, blank=True)
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
    move = models.ForeignKey("accounting.Move", on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="move_lines")
    partner = models.ForeignKey("accounting.Partner", on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    tax = models.ForeignKey("accounting.Tax", on_delete=models.PROTECT, null=True, blank=True, related_name="move_lines")
    tax_repartition_line = models.ForeignKey(
        "accounting.TaxRepartitionLine",
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
