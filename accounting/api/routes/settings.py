from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import AccountingSettingsViewSet

router = DefaultRouter()
router.register("accounting-settings", AccountingSettingsViewSet, basename="accounting-settings")

urlpatterns = [
    path("", include(router.urls)),
]
