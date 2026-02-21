from .shared import *


class InvoiceViewSet(BaseModelViewSet):
    queryset = (
        Move.objects.select_related("company", "journal", "partner", "currency", "payment_term", "incoterm", "reversed_entry")
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

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_invoice(self, request, pk=None):
        invoice = self.get_object()
        if invoice.state == "cancelled":
            return Response({"detail": "Invoice is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        invoice.state = "cancelled"
        invoice.save(update_fields=["state", "updated_at"])
        return Response(self.get_serializer(invoice).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reset-to-draft")
    def reset_to_draft(self, request, pk=None):
        invoice = self.get_object()
        if invoice.state != "cancelled":
            return Response({"detail": "Only cancelled invoices can be reset to draft."}, status=status.HTTP_400_BAD_REQUEST)
        invoice.state = "draft"
        invoice.posted_at = None
        invoice.save(update_fields=["state", "posted_at", "updated_at"])
        return Response(self.get_serializer(invoice).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse_invoice(self, request, pk=None):
        invoice = self.get_object()
        payload = ReverseInvoiceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            credit_note = reverse_invoice_to_credit_note(
                invoice=invoice,
                date=payload.validated_data.get("date"),
                reason=payload.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            result = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(credit_note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="create-debit-note")
    def create_debit_note(self, request, pk=None):
        invoice = self.get_object()
        payload = CreateDebitNoteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        try:
            debit_note = create_debit_note_from_invoice(
                invoice=invoice,
                date=payload.validated_data.get("date"),
                reason=payload.validated_data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            result = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(debit_note).data, status=status.HTTP_201_CREATED)


class CreditNoteViewSet(InvoiceViewSet):
    queryset = (
        Move.objects.select_related("company", "journal", "partner", "currency", "payment_term", "reversed_entry")
        .filter(move_type__in=["out_refund", "in_refund"])
        .annotate(
            amount_untaxed=Coalesce(Sum("invoice_lines__line_subtotal"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_tax=Coalesce(Sum("invoice_lines__line_tax"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_total=Coalesce(Sum("invoice_lines__line_total"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
        )
        .order_by("-date", "-id")
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        move_type = self.request.query_params.get("move_type")
        if move_type in {"out_refund", "in_refund"}:
            queryset = queryset.filter(move_type=move_type)
        return queryset

    def perform_create(self, serializer):
        move_type = serializer.validated_data.get("move_type") or "out_refund"
        if move_type not in {"out_refund", "in_refund"}:
            raise DRFValidationError({"move_type": "Credit note move_type must be out_refund or in_refund."})
        instance = serializer.save(state="draft", move_type=move_type)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        current = self.get_object()
        if current.state != "draft":
            raise DRFValidationError("Only draft credit notes can be updated.")
        new_move_type = serializer.validated_data.get("move_type", current.move_type)
        if new_move_type not in {"out_refund", "in_refund"}:
            raise DRFValidationError({"move_type": "Credit note move_type must be out_refund or in_refund."})
        instance = serializer.save(move_type=new_move_type)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse_invoice(self, request, pk=None):
        return Response({"detail": "Reverse is available from invoices endpoint, not credit notes."}, status=status.HTTP_400_BAD_REQUEST)


class DebitNoteViewSet(InvoiceViewSet):
    queryset = (
        Move.objects.select_related("company", "journal", "partner", "currency", "payment_term", "debit_origin")
        .filter(move_type__in=["out_invoice", "in_invoice"], is_debit_note=True)
        .annotate(
            amount_untaxed=Coalesce(Sum("invoice_lines__line_subtotal"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_tax=Coalesce(Sum("invoice_lines__line_tax"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
            amount_total=Coalesce(Sum("invoice_lines__line_total"), Value(0), output_field=DecimalField(max_digits=24, decimal_places=6)),
        )
        .order_by("-date", "-id")
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        move_type = self.request.query_params.get("move_type")
        if move_type in {"out_invoice", "in_invoice"}:
            queryset = queryset.filter(move_type=move_type)
        return queryset

    def perform_create(self, serializer):
        move_type = serializer.validated_data.get("move_type") or "out_invoice"
        if move_type not in {"out_invoice", "in_invoice"}:
            raise DRFValidationError({"move_type": "Debit note move_type must be out_invoice or in_invoice."})
        instance = serializer.save(state="draft", move_type=move_type, is_debit_note=True)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        current = self.get_object()
        if current.state != "draft":
            raise DRFValidationError("Only draft debit notes can be updated.")
        new_move_type = serializer.validated_data.get("move_type", current.move_type)
        if new_move_type not in {"out_invoice", "in_invoice"}:
            raise DRFValidationError({"move_type": "Debit note move_type must be out_invoice or in_invoice."})
        instance = serializer.save(move_type=new_move_type, is_debit_note=True)
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    @action(detail=True, methods=["post"], url_path="reverse")
    def reverse_invoice(self, request, pk=None):
        return Response({"detail": "Reverse is available from invoices endpoint, not debit notes."}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="create-debit-note")
    def create_debit_note(self, request, pk=None):
        return Response({"detail": "Already a debit note."}, status=status.HTTP_400_BAD_REQUEST)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("company", "partner", "journal", "payment_method_line", "move", "currency").all().order_by(
        "-date", "-id"
    )
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        payment_type = self.request.query_params.get("payment_type")
        journal_id = self.request.query_params.get("journal_id")
        partner_id = self.request.query_params.get("partner_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        if payment_type:
            queryset = queryset.filter(payment_type=payment_type)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        return queryset

    def perform_create(self, serializer):
        payment = serializer.save(state="draft")
        try:
            payment.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        payment.save()

    def perform_update(self, serializer):
        if self.get_object().state != "draft":
            raise DRFValidationError("Only draft payments can be updated.")
        payment = serializer.save()
        try:
            payment.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        payment.save()

    def perform_destroy(self, instance):
        if instance.state != "draft":
            raise DRFValidationError("Only draft payments can be deleted.")
        instance.delete()

    @action(detail=True, methods=["post"], url_path="post")
    def post_action(self, request, pk=None):
        payment = self.get_object()
        try:
            result = post_payment(payment=payment)
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel_action(self, request, pk=None):
        payment = self.get_object()
        if payment.state == "cancelled":
            return Response({"detail": "Payment is already cancelled."}, status=status.HTTP_400_BAD_REQUEST)
        payment.state = "cancelled"
        payment.save(update_fields=["state", "updated_at"])
        if payment.move_id and payment.move.state == "posted":
            payment.move.state = "cancelled"
            payment.move.save(update_fields=["state", "updated_at"])
        return Response(self.get_serializer(payment).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reset-to-draft")
    def reset_to_draft(self, request, pk=None):
        payment = self.get_object()
        if payment.state != "cancelled":
            return Response({"detail": "Only cancelled payments can be reset to draft."}, status=status.HTTP_400_BAD_REQUEST)
        payment.state = "draft"
        payment.save(update_fields=["state", "updated_at"])
        return Response(self.get_serializer(payment).data, status=status.HTTP_200_OK)


class InvoiceLineViewSet(BaseModelViewSet):
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
