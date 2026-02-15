from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import InvoiceLineViewSet, InvoiceViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-lines", InvoiceLineViewSet, basename="invoice-line")

urlpatterns = [
    path("", include(router.urls)),
]
