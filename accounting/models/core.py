from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class Company(AccountingBaseModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(max_length=32, unique=True)
    legal_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=64, blank=True)
    mobile = models.CharField(max_length=64, blank=True)
    website = models.CharField(max_length=255, blank=True)
    street = models.CharField(max_length=255, blank=True)
    street2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=128, blank=True)
    zip = models.CharField(max_length=24, blank=True)
    country = models.ForeignKey(
        "accounting.Country",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="companies",
    )
    state = models.ForeignKey(
        "accounting.CountryState",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="companies",
    )
    vat = models.CharField(max_length=64, blank=True)
    document_layout = models.CharField(max_length=32, default="standard")
    report_header = models.TextField(blank=True)
    report_footer = models.TextField(blank=True)
    company_details = models.TextField(blank=True)
    logo_url = models.CharField(max_length=500, blank=True)
    logo_web_url = models.CharField(max_length=500, blank=True)
    email_header_color = models.CharField(max_length=7, default="#000000")
    email_button_color = models.CharField(max_length=7, default="#875A7B")
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


class UserCompanyAccess(AccountingBaseModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="company_access",
    )
    current_company = models.ForeignKey(
        "accounting.Company",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="current_for_users",
    )
    allowed_companies = models.ManyToManyField(
        "accounting.Company",
        blank=True,
        related_name="allowed_for_users",
    )
    active_companies = models.ManyToManyField(
        "accounting.Company",
        blank=True,
        related_name="active_for_users",
    )

    class Meta:
        db_table = "ga_user_company_access"

    def clean(self):
        if not self.pk:
            return
        if self.current_company_id and not self.allowed_companies.filter(id=self.current_company_id).exists():
            raise ValidationError("Current company must be included in allowed companies.")
        invalid_active_exists = self.active_companies.exclude(id__in=self.allowed_companies.values("id")).exists()
        if invalid_active_exists:
            raise ValidationError("Active companies must be included in allowed companies.")
        if self.current_company_id and not self.active_companies.filter(id=self.current_company_id).exists():
            raise ValidationError("Current company must be included in active companies.")

    def __str__(self) -> str:
        return f"{self.user} company access"
