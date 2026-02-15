from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import (
    AccountGroupViewSet,
    AccountRootViewSet,
    AccountViewSet,
    JournalGroupViewSet,
    JournalViewSet,
    PartnerViewSet,
    PaymentMethodLineViewSet,
    PaymentMethodViewSet,
    PaymentTermLineViewSet,
    PaymentTermViewSet,
    TaxGroupViewSet,
    TaxRepartitionLineViewSet,
    TaxViewSet,
)

router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="partner")
router.register("account-roots", AccountRootViewSet, basename="account-root")
router.register("account-groups", AccountGroupViewSet, basename="account-group")
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-groups", JournalGroupViewSet, basename="journal-group")
router.register("journals", JournalViewSet, basename="journal")
router.register("payment-terms", PaymentTermViewSet, basename="payment-term")
router.register("payment-term-lines", PaymentTermLineViewSet, basename="payment-term-line")
router.register("tax-groups", TaxGroupViewSet, basename="tax-group")
router.register("taxes", TaxViewSet, basename="tax")
router.register("tax-repartition-lines", TaxRepartitionLineViewSet, basename="tax-repartition-line")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register("payment-method-lines", PaymentMethodLineViewSet, basename="payment-method-line")

urlpatterns = [
    path("", include(router.urls)),
]
