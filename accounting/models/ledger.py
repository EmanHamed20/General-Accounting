from django.db import models

from .base import AccountingBaseModel


class AccountRoot(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="account_roots")
    code = models.CharField(max_length=16)
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "ga_account_root"
        unique_together = ("company", "code")

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class AccountGroup(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="account_groups")
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

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="accounts")
    root = models.ForeignKey("accounting.AccountRoot", on_delete=models.PROTECT, related_name="accounts", null=True, blank=True)
    group = models.ForeignKey("accounting.AccountGroup", on_delete=models.PROTECT, related_name="accounts", null=True, blank=True)
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, null=True, blank=True, related_name="accounts")
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
