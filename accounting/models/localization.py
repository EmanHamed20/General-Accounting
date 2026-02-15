from django.core.exceptions import ValidationError
from django.db import models

from .base import AccountingBaseModel


class Currency(AccountingBaseModel):
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=3, unique=True)
    symbol = models.CharField(max_length=8, blank=True)
    decimal_places = models.PositiveSmallIntegerField(default=2)

    class Meta:
        db_table = "ga_currency"

    def __str__(self) -> str:
        return self.code


class Country(AccountingBaseModel):
    name = models.CharField(max_length=128, unique=True)
    code = models.CharField(max_length=2, unique=True)
    phone_code = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_country"
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class CountryState(AccountingBaseModel):
    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, related_name="states")
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=8, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_country_state"
        unique_together = (("country", "name"),)
        constraints = [
            models.UniqueConstraint(
                fields=["country", "code"],
                condition=~models.Q(code=""),
                name="uniq_country_state_country_code_non_empty",
            )
        ]
        ordering = ("country_id", "name")

    def __str__(self) -> str:
        state_code = f" ({self.code})" if self.code else ""
        return f"{self.country.code} - {self.name}{state_code}"


class CountryCity(AccountingBaseModel):
    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, related_name="cities")
    state = models.ForeignKey(
        "accounting.CountryState",
        on_delete=models.PROTECT,
        related_name="cities",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=128)
    postal_code = models.CharField(max_length=16, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_country_city"
        unique_together = (("country", "state", "name"),)
        ordering = ("country_id", "name")

    def __str__(self) -> str:
        return f"{self.country.code} - {self.name}"

    def clean(self) -> None:
        if self.state_id and self.state.country_id != self.country_id:
            raise ValidationError("City state must belong to the selected country.")


class CountryCurrency(AccountingBaseModel):
    country = models.ForeignKey("accounting.Country", on_delete=models.PROTECT, related_name="country_currencies")
    currency = models.ForeignKey("accounting.Currency", on_delete=models.PROTECT, related_name="country_currencies")
    is_default = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_country_currency"
        unique_together = (("country", "currency"),)
        constraints = [
            models.UniqueConstraint(
                fields=["country"],
                condition=models.Q(is_default=True),
                name="uniq_country_default_currency",
            )
        ]
        ordering = ("country_id", "-is_default", "currency_id")

    def __str__(self) -> str:
        suffix = " (default)" if self.is_default else ""
        return f"{self.country.code} - {self.currency.code}{suffix}"
