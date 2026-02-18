from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import CreditNoteViewSet, DebitNoteViewSet, InvoiceLineViewSet, InvoiceViewSet, PaymentViewSet

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("credit-notes", CreditNoteViewSet, basename="credit-note")
router.register("debit-notes", DebitNoteViewSet, basename="debit-note")
router.register("payments", PaymentViewSet, basename="payment")
router.register("invoice-lines", InvoiceLineViewSet, basename="invoice-line")

urlpatterns = [
    path("", include(router.urls)),
]
