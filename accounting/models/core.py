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
    TYPE_CHOICES = (
        ("contact", "Contact"),
        ("invoice", "Invoice Address"),
        ("delivery", "Delivery Address"),
        ("other", "Other Address"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="partners")
    parent = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True, related_name="children")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default="contact")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    mobile = models.CharField(max_length=64, blank=True)
    street = models.CharField(max_length=255, blank=True)
    street2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    zip = models.CharField(max_length=24, blank=True)
    country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="partners",
    )
    state = models.ForeignKey(
        "accounting.CountryState",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="partners",
    )
    vat = models.CharField(max_length=64, blank=True)
    is_company = models.BooleanField(default=False)
    customer_rank = models.PositiveIntegerField(default=0)
    supplier_rank = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_partner"
        indexes = [
            models.Index(fields=["company", "name"]),
            models.Index(fields=["company", "customer_rank"]),
            models.Index(fields=["active"]),
        ]

    def __str__(self) -> str:
        return self.name
