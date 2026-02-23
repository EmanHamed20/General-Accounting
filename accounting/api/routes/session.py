from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import SessionViewSet

router = DefaultRouter()
router.register("session", SessionViewSet, basename="session")

urlpatterns = [
    path("", include(router.urls)),
]

