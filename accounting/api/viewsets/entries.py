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


class JournalEntryViewSet(MoveViewSet):
    queryset = Move.objects.select_related(
        "company", "journal", "partner", "currency", "payment_term", "incoterm",
    ).filter(move_type="entry").order_by("-date", "-id")
    serializer_class = JournalEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(move_type="entry")

    def perform_create(self, serializer):
        instance = serializer.save(move_type="entry")
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    @action(detail=True, methods=["post"], url_path="set-draft")
    def set_draft(self, request, pk=None):
        move = self.get_object()
        try:
            set_move_to_draft(move=move)
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": move.id, "state": move.state, "posted_at": move.posted_at}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        move = self.get_object()
        try:
            cancel_move(move=move)
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response({"id": move.id, "state": move.state}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse(self, request, pk=None):
        move = self.get_object()
        payload = ReverseMoveSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            reversed_move = reverse_move(
                move=move,
                date=payload.validated_data.get("date"),
                reason=payload.validated_data.get("reason", ""),
                post=payload.validated_data.get("post", False),
            )
        except DjangoValidationError as exc:
            error_payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(error_payload, status=status.HTTP_400_BAD_REQUEST)
        data = JournalEntrySerializer(reversed_move, context=self.get_serializer_context()).data
        return Response(data, status=status.HTTP_201_CREATED)


class JournalEntryLineViewSet(MoveLineViewSet):
    queryset = MoveLine.objects.select_related(
        "move", "account", "partner", "currency", "tax", "tax_repartition_line",
    ).filter(move__move_type="entry").order_by("-date", "-id")
    serializer_class = JournalEntryLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(move__move_type="entry")
