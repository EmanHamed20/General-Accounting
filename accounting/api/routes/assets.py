from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import AssetDepreciationLineViewSet, AssetViewSet

router = DefaultRouter()
router.register("assets", AssetViewSet, basename="asset")
router.register("asset-depreciation-lines", AssetDepreciationLineViewSet, basename="asset-depreciation-line")

urlpatterns = [
    path("", include(router.urls)),
]
