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
        account_type = self.request.query_params.get("account_type")
        deprecated = self.request.query_params.get("deprecated")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if account_type:
            queryset = queryset.filter(account_type=account_type)
        if deprecated is not None:
            queryset = queryset.filter(deprecated=deprecated.lower() in {"1", "true", "yes"})
        return queryset


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
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


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
