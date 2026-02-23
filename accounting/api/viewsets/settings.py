from .shared import *


class AccountingSettingsViewSet(viewsets.ModelViewSet):
    queryset = AccountingSettings.objects.select_related(
        "company",
        "fiscal_localization_country",
        "chart_template_country",
        "account_fiscal_country",
        "currency",
        "default_sales_tax",
        "default_purchase_tax",
        "tax_return_journal",
        "currency_exchange_journal",
        "income_currency_exchange_account",
        "expense_currency_exchange_account",
        "bank_suspense_account",
        "account_journal_suspense_account",
        "transfer_account",
        "tax_cash_basis_journal",
        "account_cash_basis_base_account",
        "account_discount_expense_allocation",
        "account_discount_income_allocation",
        "account_journal_early_pay_discount_gain_account",
        "account_journal_early_pay_discount_loss_account",
        "default_sale_payment_term",
        "default_purchase_payment_term",
        "deferred_expense_journal",
        "deferred_expense_account",
        "deferred_revenue_journal",
        "deferred_revenue_account",
    ).all().order_by("company_id")
    serializer_class = AccountingSettingsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset

    def _build_configuration_payload(self, company):
        settings_obj = (
            AccountingSettings.objects.select_related(
                "company",
                "fiscal_localization_country",
                "chart_template_country",
                "account_fiscal_country",
                "currency",
            )
            .filter(company_id=company.id)
            .first()
        )

        settings_currency = settings_obj.currency if settings_obj and settings_obj.currency_id else None
        default_country_currency = None
        if company.country_id:
            default_country_currency = (
                CountryCurrency.objects.select_related("currency")
                .filter(country_id=company.country_id, is_default=True, active=True)
                .first()
            )

        effective_currency = settings_currency or (
            default_country_currency.currency if default_country_currency else None
        )

        return {
            "company": {
                "id": company.id,
                "name": company.name,
                "code": company.code,
                "country": (
                    {
                        "id": company.country.id,
                        "code": company.country.code,
                        "name": company.country.name,
                    }
                    if company.country_id
                    else None
                ),
                "currency": (
                    {
                        "id": effective_currency.id,
                        "code": effective_currency.code,
                        "name": effective_currency.name,
                        "symbol": effective_currency.symbol,
                    }
                    if effective_currency
                    else None
                ),
            },
            "settings": self.get_serializer(settings_obj).data if settings_obj else None,
            "derived": {
                "currency_source": (
                    "settings.currency"
                    if settings_currency
                    else ("country_default_currency" if default_country_currency else None)
                )
            },
        }

    @action(detail=False, methods=["get"], url_path="configuration")
    def configuration(self, request):
        company_id = request.query_params.get("company_id")
        if not company_id:
            return Response({"company_id": "This query param is required."}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.objects.select_related("country").filter(id=company_id).first()
        if not company:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = self._build_configuration_payload(company)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="my-configuration")
    def my_configuration(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "Authentication required."}, status=status.HTTP_401_UNAUTHORIZED)

        company_id = None

        # Preferred: user-company mapping if present in your auth model.
        if hasattr(request.user, "company_id") and request.user.company_id:
            company_id = request.user.company_id
        elif hasattr(request.user, "company") and getattr(request.user, "company", None):
            company_id = request.user.company.id

        # Fallback: explicit header from frontend session context.
        if not company_id:
            header_company_id = request.headers.get("X-Company-Id")
            if header_company_id:
                company_id = header_company_id

        # Last fallback: if there is exactly one company in system.
        if not company_id:
            total_companies = Company.objects.count()
            if total_companies == 1:
                company_id = Company.objects.values_list("id", flat=True).first()
            else:
                return Response(
                    {
                        "detail": (
                            "Cannot resolve company for current user. "
                            "Configure user->company mapping, send X-Company-Id header, "
                            "or use /api/accounting-settings/configuration/?company_id=<id>."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        company = Company.objects.select_related("country").filter(id=company_id).first()
        if not company:
            return Response({"detail": "Company not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = self._build_configuration_payload(company)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="upsert-by-company")
    def upsert_by_company(self, request):
        company_id = request.data.get("company")
        if not company_id:
            return Response({"company": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        instance = AccountingSettings.objects.filter(company_id=company_id).first()
        serializer = self.get_serializer(instance=instance, data=request.data, partial=bool(instance))
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        try:
            record.full_clean()
            record.save()
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="reload-template")
    def reload_template(self, request):
        company_id = request.data.get("company")
        if not company_id:
            return Response({"company": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        settings_obj = AccountingSettings.objects.filter(company_id=company_id).first()
        if not settings_obj:
            return Response({"detail": "Accounting settings not found for company."}, status=status.HTTP_404_NOT_FOUND)

        country = settings_obj.chart_template_country or settings_obj.fiscal_localization_country
        if not country:
            return Response(
                {"detail": "Set chart_template_country or fiscal_localization_country first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stats = apply_chart_template_to_company(company=settings_obj.company, country=country)
        settings_obj.has_chart_of_accounts = True
        settings_obj.save(update_fields=["has_chart_of_accounts", "updated_at"])

        response = {
            "settings": self.get_serializer(settings_obj).data,
            "template_reload": stats,
        }
        return Response(response, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="update-terms")
    def update_terms(self, request):
        company_id = request.data.get("company")
        if not company_id:
            return Response({"company": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)

        settings_obj = AccountingSettings.objects.filter(company_id=company_id).first()
        if not settings_obj:
            return Response({"detail": "Accounting settings not found for company."}, status=status.HTTP_404_NOT_FOUND)

        allowed = {"use_invoice_terms", "invoice_terms", "terms_type", "preview_ready"}
        updated_fields = []
        for field in allowed:
            if field in request.data:
                setattr(settings_obj, field, request.data[field])
                updated_fields.append(field)

        if not updated_fields:
            return Response(
                {"detail": "No updatable fields provided. Use one of: use_invoice_terms, invoice_terms, terms_type, preview_ready."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            settings_obj.full_clean()
            settings_obj.save(update_fields=updated_fields + ["updated_at"])
        except DjangoValidationError as exc:
            payload = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(settings_obj).data, status=status.HTTP_200_OK)


class FollowupLevelViewSet(viewsets.ModelViewSet):
    queryset = FollowupLevel.objects.select_related("company").all().order_by("company_id", "delay_days", "id")
    serializer_class = FollowupLevelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        return queryset


class BankAccountViewSet(viewsets.ModelViewSet):
    queryset = BankAccount.objects.select_related("company", "journal").all().order_by("company_id", "id")
    serializer_class = BankAccountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        journal_id = self.request.query_params.get("journal_id")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        return queryset


class ReconciliationModelViewSet(viewsets.ModelViewSet):
    queryset = ReconciliationModel.objects.select_related("company", "journal").all().order_by("company_id", "name")
    serializer_class = ReconciliationModelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class ReconciliationModelLineViewSet(viewsets.ModelViewSet):
    queryset = ReconciliationModelLine.objects.select_related("reconciliation_model", "account", "tax").all().order_by(
        "reconciliation_model_id", "sequence", "id"
    )
    serializer_class = ReconciliationModelLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        reconciliation_model_id = self.request.query_params.get("reconciliation_model_id")
        company_id = self.request.query_params.get("company_id")
        if reconciliation_model_id:
            queryset = queryset.filter(reconciliation_model_id=reconciliation_model_id)
        if company_id:
            queryset = queryset.filter(reconciliation_model__company_id=company_id)
        return queryset


class FiscalPositionViewSet(viewsets.ModelViewSet):
    queryset = FiscalPosition.objects.select_related("company", "country").all().order_by("company_id", "name")
    serializer_class = FiscalPositionSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class FiscalPositionTaxMapViewSet(viewsets.ModelViewSet):
    queryset = FiscalPositionTaxMap.objects.select_related("fiscal_position", "tax_src", "tax_dest").all().order_by(
        "fiscal_position_id", "id"
    )
    serializer_class = FiscalPositionTaxMapSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        fiscal_position_id = self.request.query_params.get("fiscal_position_id")
        company_id = self.request.query_params.get("company_id")
        if fiscal_position_id:
            queryset = queryset.filter(fiscal_position_id=fiscal_position_id)
        if company_id:
            queryset = queryset.filter(fiscal_position__company_id=company_id)
        return queryset


class FiscalPositionAccountMapViewSet(viewsets.ModelViewSet):
    queryset = FiscalPositionAccountMap.objects.select_related("fiscal_position", "account_src", "account_dest").all().order_by(
        "fiscal_position_id", "id"
    )
    serializer_class = FiscalPositionAccountMapSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        fiscal_position_id = self.request.query_params.get("fiscal_position_id")
        company_id = self.request.query_params.get("company_id")
        if fiscal_position_id:
            queryset = queryset.filter(fiscal_position_id=fiscal_position_id)
        if company_id:
            queryset = queryset.filter(fiscal_position__company_id=company_id)
        return queryset


class LedgerViewSet(viewsets.ModelViewSet):
    queryset = Ledger.objects.select_related("company", "currency").all().order_by("company_id", "code")
    serializer_class = LedgerSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class FinancialBudgetViewSet(viewsets.ModelViewSet):
    queryset = FinancialBudget.objects.select_related("company").all().order_by("company_id", "-date_from", "-id")
    serializer_class = FinancialBudgetSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        return queryset


class FinancialBudgetLineViewSet(viewsets.ModelViewSet):
    queryset = FinancialBudgetLine.objects.select_related("budget", "account").all().order_by("budget_id", "id")
    serializer_class = FinancialBudgetLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        budget_id = self.request.query_params.get("budget_id")
        company_id = self.request.query_params.get("company_id")
        if budget_id:
            queryset = queryset.filter(budget_id=budget_id)
        if company_id:
            queryset = queryset.filter(budget__company_id=company_id)
        return queryset


class AssetModelViewSet(viewsets.ModelViewSet):
    queryset = AssetModel.objects.select_related(
        "company",
        "account_asset",
        "account_depreciation",
        "account_expense",
        "journal",
    ).all().order_by("company_id", "name")
    serializer_class = AssetModelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class DisallowedExpenseCategoryViewSet(viewsets.ModelViewSet):
    queryset = DisallowedExpenseCategory.objects.select_related("company", "expense_account").all().order_by("company_id", "name")
    serializer_class = DisallowedExpenseCategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentProviderViewSet(viewsets.ModelViewSet):
    queryset = PaymentProvider.objects.select_related("company", "journal").all().order_by("company_id", "name")
    serializer_class = PaymentProviderSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        state = self.request.query_params.get("state")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if state:
            queryset = queryset.filter(state=state)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class PaymentProviderMethodViewSet(viewsets.ModelViewSet):
    queryset = PaymentProviderMethod.objects.select_related("provider", "payment_method").all().order_by("provider_id", "id")
    serializer_class = PaymentProviderMethodSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        provider_id = self.request.query_params.get("provider_id")
        company_id = self.request.query_params.get("company_id")
        if provider_id:
            queryset = queryset.filter(provider_id=provider_id)
        if company_id:
            queryset = queryset.filter(provider__company_id=company_id)
        return queryset
