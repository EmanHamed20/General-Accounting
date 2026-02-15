from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class InvoiceLine(AccountingBaseModel):
    move = models.ForeignKey("accounting.Move", on_delete=models.CASCADE, related_name="invoice_lines")
    account = models.ForeignKey("accounting.Account", on_delete=models.PROTECT, related_name="invoice_lines")
    tax = models.ForeignKey("accounting.Tax", on_delete=models.PROTECT, null=True, blank=True, related_name="invoice_lines")
    name = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("1"))
    unit_price = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    discount_percent = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal("0"))
    line_subtotal = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    line_tax = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    line_total = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))

    class Meta:
        db_table = "ga_invoice_line"
        indexes = [models.Index(fields=["move"]), models.Index(fields=["account"])]
        ordering = ("move_id", "id")

    def clean(self) -> None:
        if self.move.move_type not in {"out_invoice", "in_invoice", "out_refund", "in_refund"}:
            raise ValidationError("Invoice lines are only allowed on invoice/bill/refund moves.")
        if self.move.company_id != self.account.company_id:
            raise ValidationError("Invoice line account company must match invoice company.")
        if self.quantity <= 0:
            raise ValidationError("Quantity must be positive.")
        if self.unit_price < 0:
            raise ValidationError("Unit price cannot be negative.")
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError("Discount percent must be between 0 and 100.")

    def save(self, *args, **kwargs):
        discount_factor = Decimal("1") - (self.discount_percent / Decimal("100"))
        subtotal = self.quantity * self.unit_price * discount_factor

        tax_amount = Decimal("0")
        if self.tax_id:
            if self.tax.amount_type == "percent":
                tax_amount = subtotal * (self.tax.amount / Decimal("100"))
            elif self.tax.amount_type == "fixed":
                tax_amount = self.tax.amount * self.quantity
            elif self.tax.amount_type == "division" and self.tax.amount < Decimal("100"):
                tax_amount = subtotal * (self.tax.amount / (Decimal("100") - self.tax.amount))

        self.line_subtotal = subtotal
        self.line_tax = tax_amount
        self.line_total = subtotal + tax_amount

        super().save(*args, **kwargs)
