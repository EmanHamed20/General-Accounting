from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class AnalyticPlan(AccountingBaseModel):
    APPLICABILITY_CHOICES = (
        ("optional", "Optional"),
        ("mandatory", "Mandatory"),
        ("unavailable", "Unavailable"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_plans")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    default_applicability = models.CharField(max_length=16, choices=APPLICABILITY_CHOICES, default="optional")
    color = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_plan"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.parent_id and self.parent.company_id != self.company_id:
            raise ValidationError("Analytic plan parent company must match plan company.")

    def __str__(self):
        return self.name


class AnalyticAccount(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_accounts")
    plan = models.ForeignKey("accounting.AnalyticPlan", on_delete=models.PROTECT, related_name="accounts")
    partner = models.ForeignKey(
        "accounting.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_accounts",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_account"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.plan.company_id != self.company_id:
            raise ValidationError("Analytic account plan company must match account company.")
        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Analytic account partner company must match account company.")

    def __str__(self):
        return self.name


class AnalyticDistributionModel(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_distribution_models")
    name = models.CharField(max_length=255)
    partner = models.ForeignKey(
        "accounting.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_distribution_models",
    )
    product_category = models.ForeignKey(
        "accounting.ProductCategory",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_distribution_models",
    )
    account_prefix = models.CharField(max_length=16, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_distribution_model"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Distribution model partner company must match model company.")
        if self.product_category_id and self.product_category.company_id != self.company_id:
            raise ValidationError("Distribution model product category company must match model company.")

    def __str__(self):
        return self.name


class AnalyticDistributionModelLine(AccountingBaseModel):
    model = models.ForeignKey("accounting.AnalyticDistributionModel", on_delete=models.CASCADE, related_name="lines")
    analytic_account = models.ForeignKey(
        "accounting.AnalyticAccount",
        on_delete=models.PROTECT,
        related_name="distribution_lines",
    )
    percentage = models.DecimalField(max_digits=7, decimal_places=4)

    class Meta:
        db_table = "ga_analytic_distribution_model_line"
        unique_together = (("model", "analytic_account"),)
        ordering = ("model_id", "id")

    def clean(self):
        if self.analytic_account.company_id != self.model.company_id:
            raise ValidationError("Distribution line analytic account company must match model company.")
        if self.percentage <= Decimal("0") or self.percentage > Decimal("100"):
            raise ValidationError("Distribution percentage must be greater than 0 and less than or equal to 100.")

    def __str__(self):
        return f"{self.model.name} - {self.analytic_account.name}: {self.percentage}%"
