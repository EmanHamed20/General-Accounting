from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class ProductCategory(AccountingBaseModel):
    COSTING_METHOD_CHOICES = (
        ("standard", "Standard Price"),
        ("avco", "Average Cost (AVCO)"),
        ("fifo", "FIFO"),
    )
    VALUATION_METHOD_CHOICES = (
        ("manual_periodic", "Manual Periodic"),
        ("automated", "Automated"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="product_categories")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=32, blank=True)
    income_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="income_product_categories",
    )
    expense_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_product_categories",
    )
    valuation_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="valuation_product_categories",
    )
    costing_method = models.CharField(max_length=16, choices=COSTING_METHOD_CHOICES, default="standard")
    valuation_method = models.CharField(max_length=16, choices=VALUATION_METHOD_CHOICES, default="manual_periodic")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_product_category"
        unique_together = (("company", "parent", "name"),)
        constraints = [
            models.UniqueConstraint(
                fields=["company", "code"],
                condition=~models.Q(code=""),
                name="uniq_product_category_company_code_non_empty",
            )
        ]
        ordering = ("company_id", "name")

    def __str__(self) -> str:
        return self.name

    def clean(self) -> None:
        if self.parent_id and self.parent.company_id != self.company_id:
            raise ValidationError("Parent category must belong to the same company.")
        if self.income_account_id and self.income_account.company_id != self.company_id:
            raise ValidationError("Income account company must match category company.")
        if self.expense_account_id and self.expense_account.company_id != self.company_id:
            raise ValidationError("Expense account company must match category company.")
        if self.valuation_account_id and self.valuation_account.company_id != self.company_id:
            raise ValidationError("Valuation account company must match category company.")
