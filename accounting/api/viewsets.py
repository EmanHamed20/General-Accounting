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
    PaymentTermLine,
    ProductCategory,
    TaxGroup,
    Tax,
    TaxRepartitionLine,
    Partner,
    PaymentMethod,
    PaymentMethodLine,
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
from accounting.services.invoice_service import generate_journal_lines_and_post_invoice
from accounting.services.move_service import post_move

from .serializers import (
    AccountGroupTemplateSerializer,
    AccountTemplateSerializer,
    ApplyChartTemplateSerializer,
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
    IncotermSerializer,
    PaymentTermLineSerializer,
    PaymentTermSerializer,
    TaxGroupSerializer,
    TaxRepartitionLineSerializer,
    TaxSerializer,
    AccountRootSerializer,
    AccountGroupSerializer,
    AccountSerializer,
    AssetDepreciationLineSerializer,
    AssetSerializer,
    InvoiceLineSerializer,
    InvoiceSerializer,
    ProductCategorySerializer,
)


# ══════════════════════════════════════════════════════════════
# HELPER
# ══════════════════════════════════════════════════════════════

def _handle_validation(exc: DjangoValidationError) -> Response:
    payload = (
        exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
    )
    return Response(payload, status=status.HTTP_400_BAD_REQUEST)


class StandardListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200


class BaseModelViewSet(viewsets.ModelViewSet):
    pagination_class = StandardListPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = "__all__"


# ══════════════════════════════════════════════════════════════
# UNCHANGED VIEWSETS
# ══════════════════════════════════════════════════════════════

class CurrencyViewSet(BaseModelViewSet):
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer


class CompanyViewSet(BaseModelViewSet):
    queryset = Company.objects.all().order_by("name")
    serializer_class = CompanySerializer

    @action(detail=True, methods=["post"], url_path="apply-chart-template")
    def apply_chart_template(self, request, pk=None):
        company = self.get_object()
        serializer = ApplyChartTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        country_id = serializer.validated_data["country_id"]
        country = Country.objects.filter(id=country_id).first()
        if not country:
            return Response({"country_id": "Country not found."}, status=status.HTTP_400_BAD_REQUEST)

        stats = apply_chart_template_to_company(company=company, country=country)
        return Response(stats, status=status.HTTP_200_OK)


class MoveViewSet(BaseModelViewSet):
    queryset = Move.objects.select_related(
        "company", "journal", "partner", "currency", "payment_term", "incoterm",
    ).all().order_by("-date", "-id")
    serializer_class = MoveSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state      = self.request.query_params.get("state")
        move_type  = self.request.query_params.get("move_type")
        journal_id = self.request.query_params.get("journal_id")
        date_from  = self.request.query_params.get("date_from")
        date_to    = self.request.query_params.get("date_to")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if state:      queryset = queryset.filter(state=state)
        if move_type:  queryset = queryset.filter(move_type=move_type)
        if journal_id: queryset = queryset.filter(journal_id=journal_id)
        if date_from:  queryset = queryset.filter(date__gte=date_from)
        if date_to:    queryset = queryset.filter(date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        if self.get_object().state != "draft":
            raise DRFValidationError("Only draft moves can be updated.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.state != "draft":
            raise DRFValidationError("Only draft moves can be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="post")
    def post_entry(self, request, pk=None):
        move = self.get_object()
        try:
            stats = post_move(move=move)
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(stats, status=status.HTTP_200_OK)


class MoveLineViewSet(BaseModelViewSet):
    queryset = MoveLine.objects.select_related(
        "move", "account", "partner", "currency", "tax", "tax_repartition_line",
    ).all().order_by("-date", "-id")
    serializer_class = MoveLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        move_id    = self.request.query_params.get("move_id")
        company_id = self.request.query_params.get("company_id")
        account_id = self.request.query_params.get("account_id")
        date_from  = self.request.query_params.get("date_from")
        date_to    = self.request.query_params.get("date_to")
        if move_id:    queryset = queryset.filter(move_id=move_id)
        if company_id: queryset = queryset.filter(move__company_id=company_id)
        if account_id: queryset = queryset.filter(account_id=account_id)
        if date_from:  queryset = queryset.filter(date__gte=date_from)
        if date_to:    queryset = queryset.filter(date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        if self.get_object().move.state != "draft":
            raise DRFValidationError("Cannot update lines of a posted/cancelled move.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.move.state != "draft":
            raise DRFValidationError("Cannot delete lines of a posted/cancelled move.")
        instance.delete()


class InvoiceViewSet(BaseModelViewSet):
    queryset = (
        Move.objects.select_related("company", "journal", "partner", "currency", "payment_term", "incoterm")
        .filter(move_type__in=["out_invoice", "in_invoice", "out_refund", "in_refund"])
        .annotate(
            amount_untaxed=Coalesce(Sum("invoice_lines__line_subtotal"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_tax=Coalesce(Sum("invoice_lines__line_tax"),       Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_total=Coalesce(Sum("invoice_lines__line_total"),   Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
        )
        .order_by("-date", "-id")
    )
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state      = self.request.query_params.get("state")
        move_type  = self.request.query_params.get("move_type")
        journal_id = self.request.query_params.get("journal_id")
        date_from  = self.request.query_params.get("date_from")
        date_to    = self.request.query_params.get("date_to")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if state:      queryset = queryset.filter(state=state)
        if move_type:  queryset = queryset.filter(move_type=move_type)
        if journal_id: queryset = queryset.filter(journal_id=journal_id)
        if date_from:  queryset = queryset.filter(date__gte=date_from)
        if date_to:    queryset = queryset.filter(date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(state="draft")
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        if self.get_object().state != "draft":
            raise DRFValidationError("Only draft invoices can be updated.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.state != "draft":
            raise DRFValidationError("Only draft invoices can be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="post")
    def post_invoice(self, request, pk=None):
        invoice = self.get_object()
        try:
            stats = generate_journal_lines_and_post_invoice(invoice=invoice)
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(stats, status=status.HTTP_200_OK)


class InvoiceLineViewSet(BaseModelViewSet):
    queryset = InvoiceLine.objects.select_related("move", "account", "tax").all().order_by("move_id", "id")
    serializer_class = InvoiceLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        move_id    = self.request.query_params.get("move_id")
        company_id = self.request.query_params.get("company_id")
        if move_id:    queryset = queryset.filter(move_id=move_id)
        if company_id: queryset = queryset.filter(move__company_id=company_id)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        if self.get_object().move.state != "draft":
            raise DRFValidationError("Cannot update lines of a posted/cancelled invoice.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.move.state != "draft":
            raise DRFValidationError("Cannot delete lines of a posted/cancelled invoice.")
        instance.delete()


class PartnerViewSet(BaseModelViewSet):
    queryset = Partner.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = PartnerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id: queryset = queryset.filter(company_id=company_id)
        return queryset


class VendorViewSet(BaseModelViewSet):
    queryset = Partner.objects.select_related("company").filter(supplier_rank__gt=0).order_by("-supplier_rank", "name", "id")
    serializer_class = VendorSerializer
    pagination_class = StandardListPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "name", "email", "supplier_rank", "customer_rank", "created_at"]
    ordering = ["-supplier_rank", "name", "id"]

    def filter_queryset(self, queryset):
        if not self.request.query_params.get("ordering"):
            search_mode = self.request.query_params.get("res_partner_search_mode", "supplier")
            if search_mode == "customer":
                self.ordering = ["-customer_rank", "name", "id"]
            else:
                self.ordering = ["-supplier_rank", "name", "id"]
        return super().filter_queryset(queryset)

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .annotate(
                supplier_invoice_count=Count(
                    "moves",
                    filter=Q(moves__move_type__in=["in_invoice", "in_refund"]),
                    distinct=True,
                )
            )
        )

        company_id = self.request.query_params.get("company_id")
        is_company = self.request.query_params.get("is_company")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if is_company is not None:
            queryset = queryset.filter(is_company=is_company.lower() in {"1", "true", "yes"})
        return queryset

    def perform_create(self, serializer):
        defaults = {}
        if "supplier_rank" not in self.request.data:
            defaults["supplier_rank"] = 1
        if "is_company" not in self.request.data:
            defaults["is_company"] = True
        instance = serializer.save(**defaults)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    @action(detail=True, methods=["post"], url_path="increase-rank")
    def increase_rank(self, request, pk=None):
        partner = self.get_object()
        field = request.data.get("field", "supplier_rank")
        n = request.data.get("n", 1)

        if field not in {"supplier_rank", "customer_rank"}:
            raise DRFValidationError({"field": "Field must be supplier_rank or customer_rank."})

        try:
            n = int(n)
        except (TypeError, ValueError):
            raise DRFValidationError({"n": "n must be an integer."})
        if n <= 0:
            raise DRFValidationError({"n": "n must be greater than 0."})

        Partner.objects.filter(pk=partner.pk).update(**{field: F(field) + n})
        partner.refresh_from_db()
        serializer = self.get_serializer(partner)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="vendor-bills")
    def vendor_bills(self, request, pk=None):
        partner = self.get_object()
        bills = (
            Move.objects.select_related("company", "journal", "partner", "currency", "payment_term", "incoterm")
            .filter(partner_id=partner.id, move_type__in=["in_invoice", "in_refund"])
            .order_by("-date", "-id")
        )
        page = self.paginate_queryset(bills)
        if page is not None:
            serializer = MoveSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MoveSerializer(bills, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AccountRootViewSet(BaseModelViewSet):
    queryset = AccountRoot.objects.select_related("company").all().order_by("company_id", "code")
    serializer_class = AccountRootSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id: queryset = queryset.filter(company_id=company_id)
        return queryset


class AccountGroupViewSet(BaseModelViewSet):
    queryset = AccountGroup.objects.select_related("company", "parent").all().order_by("company_id", "code_prefix_start")
    serializer_class = AccountGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        parent_id  = self.request.query_params.get("parent_id")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if parent_id:
            if parent_id.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        return queryset


class AccountViewSet(BaseModelViewSet):
    queryset = Account.objects.select_related("company", "root", "group", "currency").all().order_by("company_id", "code")
    serializer_class = AccountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id   = self.request.query_params.get("company_id")
        account_type = self.request.query_params.get("account_type")
        deprecated   = self.request.query_params.get("deprecated")
        if company_id:   queryset = queryset.filter(company_id=company_id)
        if account_type: queryset = queryset.filter(account_type=account_type)
        if deprecated is not None:
            queryset = queryset.filter(deprecated=deprecated.lower() in {"1", "true", "yes"})
        return queryset


# ══════════════════════════════════════════════════════════════
# ✅ AssetViewSet — CRUD + 6 NEW ACTIONS
# ══════════════════════════════════════════════════════════════

class AssetViewSet(BaseModelViewSet):
    queryset = Asset.objects.select_related(
        "company",
        "partner",
        "currency",
        "asset_account",
        "depreciation_account",
        "expense_account",
        "journal",
    ).all().order_by("company_id", "-acquisition_date", "id")
    serializer_class = AssetSerializer
    pagination_class = StandardListPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "name", "code", "acquisition_date", "state", "created_at"]
    ordering = ["company_id", "-acquisition_date", "id"]

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id       = self.request.query_params.get("company_id")
        state            = self.request.query_params.get("state")
        method           = self.request.query_params.get("method")
        active           = self.request.query_params.get("active")
        asset_account_id = self.request.query_params.get("asset_account_id")
        if company_id:       queryset = queryset.filter(company_id=company_id)
        if state:            queryset = queryset.filter(state=state)
        if method:           queryset = queryset.filter(method=method)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        if asset_account_id: queryset = queryset.filter(asset_account_id=asset_account_id)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        current = self.get_object()
        if current.state in {"closed", "cancelled"}:
            raise DRFValidationError("Closed/cancelled assets cannot be edited.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.state in {"running", "closed"}:
            raise DRFValidationError("Running/closed assets cannot be deleted.")
        instance.delete()

    # ── ACTION 1 ──────────────────────────────────────────────
    # POST /assets/{id}/compute-depreciation/
    @action(detail=True, methods=["post"], url_path="compute-depreciation")
    def compute_depreciation(self, request, pk=None):
        asset = self.get_object()
        try:
            stats = generate_depreciation_lines(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(stats, status=status.HTTP_200_OK)

    # ── ACTION 2 ──────────────────────────────────────────────
    # POST /assets/{id}/set-running/
    @action(detail=True, methods=["post"], url_path="set-running")
    def set_running(self, request, pk=None):
        """draft → running"""
        asset = self.get_object()
        try:
            asset = set_asset_running(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    # ── ACTION 3 ──────────────────────────────────────────────
    # POST /assets/{id}/pause/
    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        """running → paused"""
        asset = self.get_object()
        try:
            asset = pause_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    # ── ACTION 4 ──────────────────────────────────────────────
    # POST /assets/{id}/resume/
    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        """paused → running"""
        asset = self.get_object()
        try:
            asset = resume_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    # ── ACTION 5 ──────────────────────────────────────────────
    # POST /assets/{id}/close/
    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        """running → closed """
        asset = self.get_object()
        try:
            asset = close_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    # ── ACTION 6 ──────────────────────────────────────────────
    # POST /assets/{id}/cancel/
    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        """draft / paused → cancelled"""
        asset = self.get_object()
        try:
            asset = cancel_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════════════
# ✅ AssetDepreciationLineViewSet — CRUD + 1 NEW ACTION
# ══════════════════════════════════════════════════════════════

class AssetDepreciationLineViewSet(BaseModelViewSet):
    queryset = AssetDepreciationLine.objects.select_related(
        "asset", "move"
    ).all().order_by("asset_id", "sequence", "id")
    serializer_class = AssetDepreciationLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id   = self.request.query_params.get("asset_id")
        company_id = self.request.query_params.get("company_id")
        state      = self.request.query_params.get("state")
        date_from  = self.request.query_params.get("date_from")
        date_to    = self.request.query_params.get("date_to")
        if asset_id:   queryset = queryset.filter(asset_id=asset_id)
        if company_id: queryset = queryset.filter(asset__company_id=company_id)
        if state:      queryset = queryset.filter(state=state)
        if date_from:  queryset = queryset.filter(date__gte=date_from)
        if date_to:    queryset = queryset.filter(date__lte=date_to)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        current = self.get_object()
        if current.state == "posted":
            raise DRFValidationError("Posted depreciation lines cannot be edited.")
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.state == "posted":
            raise DRFValidationError("Posted depreciation lines cannot be deleted.")
        instance.delete()

    # ── ACTION ────────────────────────────────────────────────
    # POST /asset-depreciation-lines/{id}/post/
    @action(detail=True, methods=["post"], url_path="post")
    def post_line(self, request, pk=None):
        """
        ينشئ القيد المحاسبي لسطر الإهلاك:
          مدين  → expense_account      (مصروف الإهلاك)
          دائن  → depreciation_account (مجمع الإهلاك)
        ثم يغير state → posted
        """
        line = self.get_object()
        try:
            result = post_depreciation_line(line=line)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(result, status=status.HTTP_200_OK)


# ══════════════════════════════════════════════════════════════
# UNCHANGED VIEWSETS (CONTINUED)
# ══════════════════════════════════════════════════════════════

class JournalGroupViewSet(BaseModelViewSet):
    queryset = JournalGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = JournalGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id: queryset = queryset.filter(company_id=company_id)
        return queryset


class JournalViewSet(BaseModelViewSet):
    queryset = Journal.objects.select_related("company", "group", "currency", "default_account").all().order_by("company_id", "code")
    serializer_class = JournalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id   = self.request.query_params.get("company_id")
        journal_type = self.request.query_params.get("journal_type")
        active       = self.request.query_params.get("active")
        if company_id:   queryset = queryset.filter(company_id=company_id)
        if journal_type: queryset = queryset.filter(journal_type=journal_type)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentTermViewSet(BaseModelViewSet):
    queryset = PaymentTerm.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = PaymentTermSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active     = self.request.query_params.get("active")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class IncotermViewSet(BaseModelViewSet):
    queryset = Incoterm.objects.all().order_by("code")
    serializer_class = IncotermSerializer
    pagination_class = StandardListPagination
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["id", "code", "name", "active", "created_at"]
    ordering = ["code"]

    def get_queryset(self):
        queryset = super().get_queryset()
        active = self.request.query_params.get("active")
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentTermLineViewSet(BaseModelViewSet):
    queryset = PaymentTermLine.objects.select_related("payment_term").all().order_by("payment_term_id", "sequence", "id")
    serializer_class = PaymentTermLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        payment_term_id = self.request.query_params.get("payment_term_id")
        company_id      = self.request.query_params.get("company_id")
        if payment_term_id: queryset = queryset.filter(payment_term_id=payment_term_id)
        if company_id:      queryset = queryset.filter(payment_term__company_id=company_id)
        return queryset


class TaxGroupViewSet(BaseModelViewSet):
    queryset = TaxGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = TaxGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id: queryset = queryset.filter(company_id=company_id)
        return queryset


class TaxViewSet(BaseModelViewSet):
    queryset = Tax.objects.select_related("company", "tax_group", "account").all().order_by("company_id", "name")
    serializer_class = TaxSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        scope      = self.request.query_params.get("scope")
        active     = self.request.query_params.get("active")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if scope:      queryset = queryset.filter(scope=scope)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class TaxRepartitionLineViewSet(BaseModelViewSet):
    queryset = TaxRepartitionLine.objects.select_related("tax", "account").all().order_by("tax_id", "document_type", "sequence", "id")
    serializer_class = TaxRepartitionLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tax_id        = self.request.query_params.get("tax_id")
        company_id    = self.request.query_params.get("company_id")
        document_type = self.request.query_params.get("document_type")
        if tax_id:        queryset = queryset.filter(tax_id=tax_id)
        if company_id:    queryset = queryset.filter(tax__company_id=company_id)
        if document_type: queryset = queryset.filter(document_type=document_type)
        return queryset


class PaymentMethodViewSet(BaseModelViewSet):
    queryset = PaymentMethod.objects.all().order_by("name")
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        payment_direction = self.request.query_params.get("payment_direction")
        active            = self.request.query_params.get("active")
        if payment_direction: queryset = queryset.filter(payment_direction=payment_direction)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentMethodLineViewSet(BaseModelViewSet):
    queryset = PaymentMethodLine.objects.select_related("journal", "payment_method").all().order_by("journal_id", "sequence", "id")
    serializer_class = PaymentMethodLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        journal_id        = self.request.query_params.get("journal_id")
        payment_method_id = self.request.query_params.get("payment_method_id")
        company_id        = self.request.query_params.get("company_id")
        active            = self.request.query_params.get("active")
        if journal_id:        queryset = queryset.filter(journal_id=journal_id)
        if payment_method_id: queryset = queryset.filter(payment_method_id=payment_method_id)
        if company_id:        queryset = queryset.filter(journal__company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class CountryViewSet(BaseModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer


class CountryStateViewSet(BaseModelViewSet):
    queryset = CountryState.objects.select_related("country").all().order_by("country__name", "name")
    serializer_class = CountryStateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id: queryset = queryset.filter(country_id=country_id)
        return queryset


class CountryCityViewSet(BaseModelViewSet):
    queryset = CountryCity.objects.select_related("country", "state").all().order_by("country__name", "name")
    serializer_class = CountryCitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        state_id   = self.request.query_params.get("state_id")
        if country_id: queryset = queryset.filter(country_id=country_id)
        if state_id:   queryset = queryset.filter(state_id=state_id)
        return queryset


class CountryCurrencyViewSet(BaseModelViewSet):
    queryset = CountryCurrency.objects.select_related("country", "currency").all().order_by(
        "country__name", "-is_default", "currency__code"
    )
    serializer_class = CountryCurrencySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id  = self.request.query_params.get("country_id")
        currency_id = self.request.query_params.get("currency_id")
        is_default  = self.request.query_params.get("is_default")
        active      = self.request.query_params.get("active")
        if country_id:  queryset = queryset.filter(country_id=country_id)
        if currency_id: queryset = queryset.filter(currency_id=currency_id)
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() in {"1", "true", "yes"})
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class ProductCategoryViewSet(BaseModelViewSet):
    queryset = ProductCategory.objects.select_related(
        "company", "parent", "income_account", "expense_account", "valuation_account",
    ).all().order_by("company_id", "name")
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        parent_id  = self.request.query_params.get("parent_id")
        active     = self.request.query_params.get("active")
        if company_id: queryset = queryset.filter(company_id=company_id)
        if parent_id:
            if parent_id.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class AccountGroupTemplateViewSet(BaseModelViewSet):
    queryset = AccountGroupTemplate.objects.select_related("country", "parent").all().order_by(
        "country__name", "code_prefix_start", "id"
    )
    serializer_class = AccountGroupTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id: queryset = queryset.filter(country_id=country_id)
        return queryset


class AccountTemplateViewSet(BaseModelViewSet):
    queryset = AccountTemplate.objects.select_related("country", "group").all().order_by("country__name", "code")
    serializer_class = AccountTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        group_id   = self.request.query_params.get("group_id")
        if country_id: queryset = queryset.filter(country_id=country_id)
        if group_id:   queryset = queryset.filter(group_id=group_id)
        return queryset

