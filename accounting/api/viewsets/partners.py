from .shared import *


class PartnerViewSet(BaseModelViewSet):
    queryset = Partner.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = PartnerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.select_related("company", "parent", "country", "state").filter(customer_rank__gt=0).order_by(
        "company_id", "name"
    )
    serializer_class = PartnerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        is_company = self.request.query_params.get("is_company")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        if is_company is not None:
            queryset = queryset.filter(is_company=is_company.lower() in {"1", "true", "yes"})
        return queryset

    def perform_create(self, serializer):
        payload = dict(serializer.validated_data)
        payload["customer_rank"] = max(1, int(payload.get("customer_rank") or 1))
        instance = serializer.save(**payload)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()


class VendorViewSet(viewsets.ModelViewSet):
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
