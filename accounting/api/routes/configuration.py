from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import (
    AccountGroupViewSet,
    AccountRootViewSet,
    AccountViewSet,
    AssetModelViewSet,
    BankAccountViewSet,
    DisallowedExpenseCategoryViewSet,
    FinancialBudgetLineViewSet,
    FinancialBudgetViewSet,
    FiscalPositionAccountMapViewSet,
    FiscalPositionTaxMapViewSet,
    FiscalPositionViewSet,
    FollowupLevelViewSet,
    JournalGroupViewSet,
    JournalViewSet,
    IncotermViewSet,
    PartnerViewSet,
    VendorViewSet,
    LedgerViewSet,
    PartnerViewSet,
    PaymentProviderMethodViewSet,
    PaymentProviderViewSet,
    PaymentMethodLineViewSet,
    PaymentMethodViewSet,
    PaymentTermLineViewSet,
    PaymentTermViewSet,
    ReconciliationModelLineViewSet,
    ReconciliationModelViewSet,
    TaxGroupViewSet,
    TaxRepartitionLineViewSet,
    TaxViewSet,
)

router = DefaultRouter()
router.register("partners", PartnerViewSet, basename="partner")
router.register("vendors", VendorViewSet, basename="vendor")
router.register("account-roots", AccountRootViewSet, basename="account-root")
router.register("account-groups", AccountGroupViewSet, basename="account-group")
router.register("accounts", AccountViewSet, basename="account")
router.register("journal-groups", JournalGroupViewSet, basename="journal-group")
router.register("journals", JournalViewSet, basename="journal")
router.register("incoterms", IncotermViewSet, basename="incoterm")
router.register("payment-terms", PaymentTermViewSet, basename="payment-term")
router.register("payment-term-lines", PaymentTermLineViewSet, basename="payment-term-line")
router.register("tax-groups", TaxGroupViewSet, basename="tax-group")
router.register("taxes", TaxViewSet, basename="tax")
router.register("tax-repartition-lines", TaxRepartitionLineViewSet, basename="tax-repartition-line")
router.register("payment-methods", PaymentMethodViewSet, basename="payment-method")
router.register("payment-method-lines", PaymentMethodLineViewSet, basename="payment-method-line")
router.register("followup-levels", FollowupLevelViewSet, basename="followup-level")
router.register("bank-accounts", BankAccountViewSet, basename="bank-account")
router.register("reconciliation-models", ReconciliationModelViewSet, basename="reconciliation-model")
router.register("reconciliation-model-lines", ReconciliationModelLineViewSet, basename="reconciliation-model-line")
router.register("fiscal-positions", FiscalPositionViewSet, basename="fiscal-position")
router.register("fiscal-position-tax-maps", FiscalPositionTaxMapViewSet, basename="fiscal-position-tax-map")
router.register("fiscal-position-account-maps", FiscalPositionAccountMapViewSet, basename="fiscal-position-account-map")
router.register("ledgers", LedgerViewSet, basename="ledger")
router.register("financial-budgets", FinancialBudgetViewSet, basename="financial-budget")
router.register("financial-budget-lines", FinancialBudgetLineViewSet, basename="financial-budget-line")
router.register("asset-models", AssetModelViewSet, basename="asset-model")
router.register("disallowed-expense-categories", DisallowedExpenseCategoryViewSet, basename="disallowed-expense-category")
router.register("payment-providers", PaymentProviderViewSet, basename="payment-provider")
router.register("payment-provider-methods", PaymentProviderMethodViewSet, basename="payment-provider-method")

urlpatterns = [
    path("", include(router.urls)),
]
