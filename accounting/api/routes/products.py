from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import ProductCategoryViewSet

router = DefaultRouter()
router.register("product-categories", ProductCategoryViewSet, basename="product-category")

urlpatterns = [
    path("", include(router.urls)),
]
