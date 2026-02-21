from .shared import *
from .shared import _handle_validation


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
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        method = self.request.query_params.get("method")
        active = self.request.query_params.get("active")
        asset_account_id = self.request.query_params.get("asset_account_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        if method:
            queryset = queryset.filter(method=method)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        if asset_account_id:
            queryset = queryset.filter(asset_account_id=asset_account_id)
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

    @action(detail=True, methods=["post"], url_path="compute-depreciation")
    def compute_depreciation(self, request, pk=None):
        asset = self.get_object()
        try:
            stats = generate_depreciation_lines(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(stats, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="set-running")
    def set_running(self, request, pk=None):
        asset = self.get_object()
        try:
            asset = set_asset_running(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="pause")
    def pause(self, request, pk=None):
        asset = self.get_object()
        try:
            asset = pause_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="resume")
    def resume(self, request, pk=None):
        asset = self.get_object()
        try:
            asset = resume_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        asset = self.get_object()
        try:
            asset = close_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        asset = self.get_object()
        try:
            asset = cancel_asset(asset=asset)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(AssetSerializer(asset).data, status=status.HTTP_200_OK)


class AssetDepreciationLineViewSet(BaseModelViewSet):
    queryset = AssetDepreciationLine.objects.select_related("asset", "move").all().order_by("asset_id", "sequence", "id")
    serializer_class = AssetDepreciationLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get("asset_id")
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        if company_id:
            queryset = queryset.filter(asset__company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
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

    @action(detail=True, methods=["post"], url_path="post")
    def post_line(self, request, pk=None):
        line = self.get_object()
        try:
            result = post_depreciation_line(line=line)
        except DjangoValidationError as exc:
            return _handle_validation(exc)
        return Response(result, status=status.HTTP_200_OK)
