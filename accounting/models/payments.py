from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


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
    journal = models.ForeignKey("accounting.Journal", on_delete=models.CASCADE, related_name="payment_method_lines")
    payment_method = models.ForeignKey("accounting.PaymentMethod", on_delete=models.PROTECT, related_name="journal_lines")
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

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="payments")
    partner = models.ForeignKey("accounting.Partner", on_delete=models.PROTECT, null=True, blank=True, related_name="payments")
    journal = models.ForeignKey("accounting.Journal", on_delete=models.PROTECT, related_name="payments")
    payment_method_line = models.ForeignKey("accounting.PaymentMethodLine", on_delete=models.PROTECT, related_name="payments")
    move = models.OneToOneField("accounting.Move", on_delete=models.PROTECT, related_name="payment", null=True, blank=True)
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, related_name="payments")
    date = models.DateField()
    amount = models.DecimalField(max_digits=18, decimal_places=6)
    payment_type = models.CharField(max_length=16, choices=PAYMENT_TYPE_CHOICES)
    state = models.CharField(max_length=16, choices=PAYMENT_STATE_CHOICES, default="draft")
    reference = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "ga_payment"
        indexes = [models.Index(fields=["company", "date"]), models.Index(fields=["state"])]


class FullReconcile(AccountingBaseModel):
    exchange_move = models.ForeignKey("accounting.Move", on_delete=models.PROTECT, null=True, blank=True, related_name="full_reconcile_exchanges")

    class Meta:
        db_table = "ga_full_reconcile"


class PartialReconcile(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="partial_reconciles")
    debit_move_line = models.ForeignKey("accounting.MoveLine", on_delete=models.PROTECT, related_name="partial_debits")
    credit_move_line = models.ForeignKey("accounting.MoveLine", on_delete=models.PROTECT, related_name="partial_credits")
    full_reconcile = models.ForeignKey("accounting.FullReconcile", on_delete=models.PROTECT, null=True, blank=True, related_name="partials")
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
