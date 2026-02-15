from django.db import models

from .base import AccountingBaseModel


class AccountGroupTemplate(AccountingBaseModel):
    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, related_name="account_group_templates")
    code_prefix_start = models.CharField(max_length=16)
    code_prefix_end = models.CharField(max_length=16)
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")

    class Meta:
        db_table = "ga_account_group_template"
        unique_together = (("country", "code_prefix_start", "code_prefix_end"),)
        ordering = ("country_id", "code_prefix_start", "id")

    def __str__(self) -> str:
        return f"{self.country.code} - {self.name}"


class AccountTemplate(AccountingBaseModel):
    ACCOUNT_TYPE_CHOICES = (
        ("asset", "Asset"),
        ("liability", "Liability"),
        ("equity", "Equity"),
        ("income", "Income"),
        ("expense", "Expense"),
    )

    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, related_name="account_templates")
    group = models.ForeignKey(
        "accounting.AccountGroupTemplate",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounts",
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=32, choices=ACCOUNT_TYPE_CHOICES)
    reconcile = models.BooleanField(default=False)
    deprecated = models.BooleanField(default=False)

    class Meta:
        db_table = "ga_account_template"
        unique_together = (("country", "code"),)
        ordering = ("country_id", "code")

    def __str__(self) -> str:
        return f"{self.country.code} - {self.code} - {self.name}"
