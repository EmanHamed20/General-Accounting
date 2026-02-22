from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from accounting.models import (
    Move,
    MoveLine,
    AnalyticLine,
    AnalyticAccount,
    AnalyticDistributionModel,
    AnalyticDistributionModelLine,
    AnalyticPlan,
    InvoiceLine,
    AccountGroupTemplate,
    Asset,
    AssetDepreciationLine,
    AccountRoot,
    AccountGroup,
    Account,
    AccountTemplate,
    Company,
    Country,
    CountryCity,
    CountryCurrency,
    CountryState,
    Currency,
    JournalGroup,
    Journal,
    Incoterm,
    PaymentTerm,
    Product,
    PaymentTermLine,
    ProductCategory,
    TaxGroup,
    Tax,
    TaxRepartitionLine,
    Partner,
    Payment,
    PaymentMethod,
    PaymentMethodLine,
    AccountingSettings,
    FollowupLevel,
    BankAccount,
    ReconciliationModel,
    ReconciliationModelLine,
    FiscalPosition,
    FiscalPositionTaxMap,
    FiscalPositionAccountMap,
    Ledger,
    FinancialBudget,
    FinancialBudgetLine,
    AssetModel,
    DisallowedExpenseCategory,
    PaymentProvider,
    PaymentProviderMethod,
    TransferModel,
    TransferModelLine,
)
from accounting.services.asset_service import (
    cancel_asset,
    close_asset,
    generate_depreciation_lines,
    pause_asset,
    post_depreciation_line,
    resume_asset,
    set_asset_running,
)
from accounting.services.chart_template_service import apply_chart_template_to_company
from accounting.services.invoice_service import (
    create_debit_note_from_invoice,
    generate_journal_lines_and_post_invoice,
    reverse_invoice_to_credit_note,
)
from accounting.services.move_service import cancel_move, post_move, reverse_move, set_move_to_draft
from accounting.services.payment_service import post_payment

from ..serializers import (
    AccountGroupTemplateSerializer,
    AccountTemplateSerializer,
    ApplyChartTemplateSerializer,
    CreateDebitNoteSerializer,
    JournalEntryLineSerializer,
    JournalEntrySerializer,
    ReverseInvoiceSerializer,
    ReverseMoveSerializer,
    CompanySerializer,
    CountryCitySerializer,
    CountryCurrencySerializer,
    CountrySerializer,
    CountryStateSerializer,
    CurrencySerializer,
    JournalGroupSerializer,
    JournalSerializer,
    MoveLineSerializer,
    MoveSerializer,
    PartnerSerializer,
    VendorSerializer,
    PaymentMethodLineSerializer,
    PaymentMethodSerializer,
    PaymentSerializer,
    IncotermSerializer,
    PaymentTermLineSerializer,
    PaymentTermSerializer,
    AnalyticAccountSerializer,
    AnalyticLineSerializer,
    AnalyticDistributionModelLineSerializer,
    AnalyticDistributionModelSerializer,
    AnalyticPlanSerializer,
    TaxGroupSerializer,
    TaxRepartitionLineSerializer,
    TaxSerializer,
    AccountRootSerializer,
    AccountGroupSerializer,
    AccountSerializer,
    AssetDepreciationLineSerializer,
    AssetSerializer,
    AccountingSettingsSerializer,
    FollowupLevelSerializer,
    BankAccountSerializer,
    ReconciliationModelSerializer,
    ReconciliationModelLineSerializer,
    FiscalPositionSerializer,
    FiscalPositionTaxMapSerializer,
    FiscalPositionAccountMapSerializer,
    LedgerSerializer,
    FinancialBudgetSerializer,
    FinancialBudgetLineSerializer,
    AssetModelSerializer,
    DisallowedExpenseCategorySerializer,
    PaymentProviderSerializer,
    PaymentProviderMethodSerializer,
    InvoiceLineSerializer,
    InvoiceSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    TransferModelSerializer,
    TransferModelLineSerializer,
)


def _handle_validation(exc: DjangoValidationError) -> Response:
    payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


class StandardListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class BaseModelViewSet(viewsets.ModelViewSet):
    pagination_class = StandardListPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = "__all__"
