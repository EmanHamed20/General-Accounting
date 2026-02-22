from django.db.models.deletion import ProtectedError

from .shared import *


class AccountRootViewSet(BaseModelViewSet):
    queryset = AccountRoot.objects.select_related("company").all().order_by("company_id", "code")
    serializer_class = AccountRootSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class AccountGroupViewSet(BaseModelViewSet):
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


class AccountViewSet(BaseModelViewSet):
    queryset = Account.objects.select_related("company", "root", "group", "currency").all().order_by("company_id", "code")
    serializer_class = AccountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        root_id = self.request.query_params.get("root_id")
        group_id = self.request.query_params.get("group_id")
        account_type = self.request.query_params.get("account_type")
        code = self.request.query_params.get("code")
        name = self.request.query_params.get("name")
        reconcile = self.request.query_params.get("reconcile")
        deprecated = self.request.query_params.get("deprecated")
        q = self.request.query_params.get("q")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if root_id:
            if root_id.lower() == "null":
                queryset = queryset.filter(root__isnull=True)
            else:
                queryset = queryset.filter(root_id=root_id)
        if group_id:
            if group_id.lower() == "null":
                queryset = queryset.filter(group__isnull=True)
            else:
                queryset = queryset.filter(group_id=group_id)
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        if code:
            queryset = queryset.filter(code__icontains=code)
        if name:
            queryset = queryset.filter(name__icontains=name)
        if reconcile is not None:
            queryset = queryset.filter(reconcile=reconcile.lower() in {"1", "true", "yes"})
        if deprecated is not None:
            queryset = queryset.filter(deprecated=deprecated.lower() in {"1", "true", "yes"})
        if q:
            queryset = queryset.filter(Q(code__icontains=q) | Q(name__icontains=q))
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
        if current.move_lines.exists():
            immutable_fields = {"company", "code", "account_type"}
            changed = [field for field in immutable_fields if field in serializer.validated_data]
            for field in changed:
                new_value = serializer.validated_data.get(field)
                old_value = getattr(current, field)
                old_comp = getattr(old_value, "id", old_value)
                new_comp = getattr(new_value, "id", new_value)
                if old_comp != new_comp:
                    raise DRFValidationError(
                        {field: "Cannot change this field after the account has journal entries."}
                    )
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_destroy(self, instance):
        if instance.move_lines.exists():
            raise DRFValidationError(
                "Account has journal entry lines. Archive it instead by setting deprecated=true or using /archive/."
            )
        try:
            instance.delete()
        except ProtectedError as exc:
            raise DRFValidationError(
                {"detail": f"Account is referenced by other records and cannot be deleted: {exc}"}
            ) from exc

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        account = self.get_object()
        if account.deprecated:
            return Response({"detail": "Account is already archived."}, status=status.HTTP_400_BAD_REQUEST)
        account.deprecated = True
        account.save(update_fields=["deprecated", "updated_at"])
        return Response(self.get_serializer(account).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, pk=None):
        account = self.get_object()
        if not account.deprecated:
            return Response({"detail": "Account is already active."}, status=status.HTTP_400_BAD_REQUEST)
        account.deprecated = False
        account.save(update_fields=["deprecated", "updated_at"])
        return Response(self.get_serializer(account).data, status=status.HTTP_200_OK)


class JournalGroupViewSet(BaseModelViewSet):
    queryset = JournalGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = JournalGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class JournalViewSet(BaseModelViewSet):
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


class PaymentTermViewSet(BaseModelViewSet):
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
        company_id = self.request.query_params.get("company_id")
        if payment_term_id:
            queryset = queryset.filter(payment_term_id=payment_term_id)
        if company_id:
            queryset = queryset.filter(payment_term__company_id=company_id)
        return queryset


class TaxGroupViewSet(BaseModelViewSet):
    queryset = TaxGroup.objects.select_related("company").all().order_by("company_id", "name")
    serializer_class = TaxGroupSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        country_id = self.request.query_params.get("country_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset.order_by("company_id", "sequence", "name")


class TaxViewSet(BaseModelViewSet):
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


class TaxRepartitionLineViewSet(BaseModelViewSet):
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


class PaymentMethodViewSet(BaseModelViewSet):
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


class PaymentMethodLineViewSet(BaseModelViewSet):
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


class TransferModelViewSet(BaseModelViewSet):
    queryset = (
        TransferModel.objects.select_related("company", "journal")
        .prefetch_related("accounts")
        .all()
        .order_by("-id")
    )
    serializer_class = TransferModelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        journal_id = self.request.query_params.get("journal_id")
        state = self.request.query_params.get("state")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if state:
            queryset = queryset.filter(state=state)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        instance = self.get_object()
        instance.action_activate()
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="disable")
    def disable(self, request, pk=None):
        instance = self.get_object()
        instance.action_disable()
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="archive")
    def archive(self, request, pk=None):
        instance = self.get_object()
        instance.action_archive()
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="perform-auto-transfer")
    def perform_auto_transfer(self, request, pk=None):
        instance = self.get_object()
        try:
            instance.action_perform_auto_transfer()
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(instance).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="cron-auto-transfer")
    def cron_auto_transfer(self, request):
        TransferModel.action_cron_auto_transfer()
        return Response({"detail": "Auto transfer cron executed."}, status=status.HTTP_200_OK)


class TransferModelLineViewSet(BaseModelViewSet):
    queryset = (
        TransferModelLine.objects.select_related("transfer_model", "account")
        .prefetch_related("analytic_accounts", "partners")
        .all()
        .order_by("transfer_model_id", "sequence", "id")
    )
    serializer_class = TransferModelLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        transfer_model_id = self.request.query_params.get("transfer_model_id")
        company_id = self.request.query_params.get("company_id")
        if transfer_model_id:
            queryset = queryset.filter(transfer_model_id=transfer_model_id)
        if company_id:
            queryset = queryset.filter(transfer_model__company_id=company_id)
        return queryset
