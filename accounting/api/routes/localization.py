from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import (
    CountryCityViewSet,
    CountryCurrencyViewSet,
    CountryStateViewSet,
    CountryViewSet,
    CurrencyViewSet,
)

router = DefaultRouter()
router.register("currencies", CurrencyViewSet, basename="currency")
router.register("countries", CountryViewSet, basename="country")
router.register("states", CountryStateViewSet, basename="country-state")
router.register("cities", CountryCityViewSet, basename="country-city")
router.register("country-currencies", CountryCurrencyViewSet, basename="country-currency")

urlpatterns = [
    path("", include(router.urls)),
]
