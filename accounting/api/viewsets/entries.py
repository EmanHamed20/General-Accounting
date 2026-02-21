from .shared import *


class MoveViewSet(BaseModelViewSet):
    queryset = Move.objects.select_related(
        "company", "journal", "partner", "currency", "payment_term", "incoterm",
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


class MoveLineViewSet(BaseModelViewSet):
    queryset = MoveLine.objects.select_related(
        "move", "account", "partner", "currency", "tax", "tax_repartition_line",
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
