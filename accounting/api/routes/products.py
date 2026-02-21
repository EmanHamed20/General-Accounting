from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import ProductCategoryViewSet, ProductViewSet, VendorProductViewSet

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("vendor-products", VendorProductViewSet, basename="vendor-product")
router.register("product-categories", ProductCategoryViewSet, basename="product-category")

urlpatterns = [
    path("", include(router.urls)),
]
