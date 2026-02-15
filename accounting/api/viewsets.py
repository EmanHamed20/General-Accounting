from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import DecimalField, Sum, Value
from django.db.models.functions import Coalesce
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response

from accounting.models import (
    Move,
    MoveLine,
    InvoiceLine,
    AccountGroupTemplate,
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
    PaymentMethodLineSerializer,
    PaymentMethodSerializer,
    PaymentTermLineSerializer,
    PaymentTermSerializer,
    TaxGroupSerializer,
    TaxRepartitionLineSerializer,
    TaxSerializer,
    AccountRootSerializer,
    AccountGroupSerializer,
    AccountSerializer,
    InvoiceLineSerializer,
    InvoiceSerializer,
    ProductCategorySerializer,
)


class CurrencyViewSet(viewsets.ModelViewSet):
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer


class CompanyViewSet(viewsets.ModelViewSet):
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


class MoveViewSet(viewsets.ModelViewSet):
    queryset = Move.objects.select_related(
        "company",
        "journal",
        "partner",
        "currency",
        "payment_term",
    ).all().order_by("-date", "-id")
    serializer_class = MoveSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        move_type = self.request.query_params.get("move_type")
        journal_id = self.request.query_params.get("journal_id")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        if move_type:
            queryset = queryset.filter(move_type=move_type)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
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


class MoveLineViewSet(viewsets.ModelViewSet):
    queryset = MoveLine.objects.select_related(
        "move",
        "account",
        "partner",
        "currency",
        "tax",
        "tax_repartition_line",
    ).all().order_by("-date", "-id")
    serializer_class = MoveLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        move_id = self.request.query_params.get("move_id")
        company_id = self.request.query_params.get("company_id")
        account_id = self.request.query_params.get("account_id")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if move_id:
            queryset = queryset.filter(move_id=move_id)
        if company_id:
            queryset = queryset.filter(move__company_id=company_id)
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
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
        if current.move.state != "draft":
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


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = (
        Move.objects.select_related("company", "journal", "partner", "currency", "payment_term")
        .filter(move_type__in=["out_invoice", "in_invoice", "out_refund", "in_refund"])
        .annotate(
            amount_untaxed=Coalesce(Sum("invoice_lines__line_subtotal"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_tax=Coalesce(Sum("invoice_lines__line_tax"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_total=Coalesce(Sum("invoice_lines__line_total"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
        )
        .order_by("-date", "-id")
    )
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        move_type = self.request.query_params.get("move_type")
        journal_id = self.request.query_params.get("journal_id")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        if move_type:
            queryset = queryset.filter(move_type=move_type)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
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


class InvoiceLineViewSet(viewsets.ModelViewSet):
    queryset = InvoiceLine.objects.select_related("move", "account", "tax").all().order_by("move_id", "id")
    serializer_class = InvoiceLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        move_id = self.request.query_params.get("move_id")
        company_id = self.request.query_params.get("company_id")
        if move_id:
            queryset = queryset.filter(move_id=move_id)
        if company_id:
            queryset = queryset.filter(move__company_id=company_id)
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
        if current.move.state != "draft":
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


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = PartnerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class AccountRootViewSet(viewsets.ModelViewSet):
    queryset = AccountRoot.objects.select_related("company").all().order_by("company_id", "code")
    serializer_class = AccountRootSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class AccountGroupViewSet(viewsets.ModelViewSet):
    queryset = AccountGroup.objects.select_related("company", "parent").all().order_by("company_id", "code_prefix_start")
    serializer_class = AccountGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        parent_id = self.request.query_params.get("parent_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if parent_id:
            if parent_id.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        return queryset


class AccountViewSet(viewsets.ModelViewSet):
    queryset = Account.objects.select_related("company", "root", "group", "currency").all().order_by("company_id", "code")
    serializer_class = AccountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        account_type = self.request.query_params.get("account_type")
        deprecated = self.request.query_params.get("deprecated")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        if deprecated is not None:
            queryset = queryset.filter(deprecated=deprecated.lower() in {"1", "true", "yes"})
        return queryset


class JournalGroupViewSet(viewsets.ModelViewSet):
    queryset = JournalGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = JournalGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class JournalViewSet(viewsets.ModelViewSet):
    queryset = Journal.objects.select_related("company", "group", "currency", "default_account").all().order_by("company_id", "code")
    serializer_class = JournalSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        journal_type = self.request.query_params.get("journal_type")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if journal_type:
            queryset = queryset.filter(journal_type=journal_type)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentTermViewSet(viewsets.ModelViewSet):
    queryset = PaymentTerm.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = PaymentTermSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentTermLineViewSet(viewsets.ModelViewSet):
    queryset = PaymentTermLine.objects.select_related("payment_term").all().order_by("payment_term_id", "sequence", "id")
    serializer_class = PaymentTermLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        payment_term_id = self.request.query_params.get("payment_term_id")
        company_id = self.request.query_params.get("company_id")
        if payment_term_id:
            queryset = queryset.filter(payment_term_id=payment_term_id)
        if company_id:
            queryset = queryset.filter(payment_term__company_id=company_id)
        return queryset


class TaxGroupViewSet(viewsets.ModelViewSet):
    queryset = TaxGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = TaxGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class TaxViewSet(viewsets.ModelViewSet):
    queryset = Tax.objects.select_related("company", "tax_group", "account").all().order_by("company_id", "name")
    serializer_class = TaxSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        scope = self.request.query_params.get("scope")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if scope:
            queryset = queryset.filter(scope=scope)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class TaxRepartitionLineViewSet(viewsets.ModelViewSet):
    queryset = TaxRepartitionLine.objects.select_related("tax", "account").all().order_by("tax_id", "document_type", "sequence", "id")
    serializer_class = TaxRepartitionLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tax_id = self.request.query_params.get("tax_id")
        company_id = self.request.query_params.get("company_id")
        document_type = self.request.query_params.get("document_type")
        if tax_id:
            queryset = queryset.filter(tax_id=tax_id)
        if company_id:
            queryset = queryset.filter(tax__company_id=company_id)
        if document_type:
            queryset = queryset.filter(document_type=document_type)
        return queryset


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all().order_by("name")
    serializer_class = PaymentMethodSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        payment_direction = self.request.query_params.get("payment_direction")
        active = self.request.query_params.get("active")
        if payment_direction:
            queryset = queryset.filter(payment_direction=payment_direction)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentMethodLineViewSet(viewsets.ModelViewSet):
    queryset = PaymentMethodLine.objects.select_related("journal", "payment_method").all().order_by("journal_id", "sequence", "id")
    serializer_class = PaymentMethodLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        journal_id = self.request.query_params.get("journal_id")
        payment_method_id = self.request.query_params.get("payment_method_id")
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if payment_method_id:
            queryset = queryset.filter(payment_method_id=payment_method_id)
        if company_id:
            queryset = queryset.filter(journal__company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer


class CountryStateViewSet(viewsets.ModelViewSet):
    queryset = CountryState.objects.select_related("country").all().order_by("country__name", "name")
    serializer_class = CountryStateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset


class CountryCityViewSet(viewsets.ModelViewSet):
    queryset = CountryCity.objects.select_related("country", "state").all().order_by("country__name", "name")
    serializer_class = CountryCitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        state_id = self.request.query_params.get("state_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        return queryset


class CountryCurrencyViewSet(viewsets.ModelViewSet):
    queryset = CountryCurrency.objects.select_related("country", "currency").all().order_by(
        "country__name", "-is_default", "currency__code"
    )
    serializer_class = CountryCurrencySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        currency_id = self.request.query_params.get("currency_id")
        is_default = self.request.query_params.get("is_default")
        active = self.request.query_params.get("active")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if currency_id:
            queryset = queryset.filter(currency_id=currency_id)
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() in {"1", "true", "yes"})
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.select_related(
        "company",
        "parent",
        "income_account",
        "expense_account",
        "valuation_account",
    ).all().order_by("company_id", "name")
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        parent_id = self.request.query_params.get("parent_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if parent_id:
            if parent_id.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class AccountGroupTemplateViewSet(viewsets.ModelViewSet):
    queryset = AccountGroupTemplate.objects.select_related("country", "parent").all().order_by(
        "country__name", "code_prefix_start", "id"
    )
    serializer_class = AccountGroupTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset


class AccountTemplateViewSet(viewsets.ModelViewSet):
    queryset = AccountTemplate.objects.select_related("country", "group").all().order_by("country__name", "code")
    serializer_class = AccountTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        group_id = self.request.query_params.get("group_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset
