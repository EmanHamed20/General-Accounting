from django.db import models

from .base import AccountingBaseModel


class Company(AccountingBaseModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=32, unique=True)
    lock_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "ga_company"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Partner(AccountingBaseModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    is_company = models.BooleanField(default=False)
    supplier_rank = models.IntegerField(default=0)
    customer_rank = models.IntegerField(default=0)
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="partners")

    class Meta:
        db_table = "ga_partner"

    def __str__(self) -> str:
        return self.name
