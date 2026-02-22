from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import (
    JournalEntryLineViewSet,
    JournalEntryViewSet,
    MoveLineViewSet,
    MoveViewSet,
)

router = DefaultRouter()
router.register("moves", MoveViewSet, basename="move")
router.register("move-lines", MoveLineViewSet, basename="move-line")
router.register("journal-items", MoveLineViewSet, basename="journal-item")
router.register("journal-entries", JournalEntryViewSet, basename="journal-entry")
router.register("journal-entry-lines", JournalEntryLineViewSet, basename="journal-entry-line")

urlpatterns = [
    path("", include(router.urls)),
]
