from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import ProductCategoryViewSet, ProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("product-categories", ProductCategoryViewSet, basename="product-category")

urlpatterns = [
    path("", include(router.urls)),
]
