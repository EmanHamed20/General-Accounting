from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import MoveLineViewSet, MoveViewSet

router = DefaultRouter()
router.register("moves", MoveViewSet, basename="move")
router.register("move-lines", MoveLineViewSet, basename="move-line")

urlpatterns = [
    path("", include(router.urls)),
]
