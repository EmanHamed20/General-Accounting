from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import AccountGroupTemplateViewSet, AccountTemplateViewSet

router = DefaultRouter()
router.register("account-group-templates", AccountGroupTemplateViewSet, basename="account-group-template")
router.register("account-templates", AccountTemplateViewSet, basename="account-template")

urlpatterns = [
    path("", include(router.urls)),
]
