from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .viewsets import CountryCityViewSet, CountryStateViewSet, CountryViewSet

router = DefaultRouter()
router.register("countries", CountryViewSet, basename="country")
router.register("states", CountryStateViewSet, basename="country-state")
router.register("cities", CountryCityViewSet, basename="country-city")

urlpatterns = [
    path("", include(router.urls)),
]
