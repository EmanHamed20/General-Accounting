from rest_framework import serializers

from accounting.models import (
    Account,
    AccountGroup,
    AccountGroupTemplate,
    AccountRoot,
    AccountTemplate,
    Company,
    Country,
    CountryCity,
    CountryCurrency,
    CountryState,
    Currency,
    Journal,
    InvoiceLine,
    Move,
    MoveLine,
    PaymentMethod,
    PaymentMethodLine,
    PaymentTermLine,
    Partner,
    PaymentTerm,
    ProductCategory,
    JournalGroup,
    TaxGroup,
    Tax,
    TaxRepartitionLine,
)


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "name", "code", "symbol", "decimal_places", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code", "phone_code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountryStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryState
        fields = ["id", "country", "name", "code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CountryCitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryCity
        fields = ["id", "country", "state", "name", "postal_code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        country = attrs.get("country") or getattr(self.instance, "country", None)
        state = attrs.get("state") if "state" in attrs else getattr(self.instance, "state", None)
        if state and country and state.country_id != country.id:
            raise serializers.ValidationError({"state": "State must belong to selected country."})
        return attrs


class CountryCurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = CountryCurrency
        fields = ["id", "country", "currency", "is_default", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = [
            "id",
            "company",
            "parent",
            "name",
            "code",
            "income_account",
            "expense_account",
            "valuation_account",
            "costing_method",
            "valuation_method",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        parent = attrs.get("parent") if "parent" in attrs else getattr(self.instance, "parent", None)
        income_account = (
            attrs.get("income_account")
            if "income_account" in attrs
            else getattr(self.instance, "income_account", None)
        )
        expense_account = (
            attrs.get("expense_account")
            if "expense_account" in attrs
            else getattr(self.instance, "expense_account", None)
        )
        valuation_account = (
            attrs.get("valuation_account")
            if "valuation_account" in attrs
            else getattr(self.instance, "valuation_account", None)
        )

        if company and parent and parent.company_id != company.id:
            raise serializers.ValidationError({"parent": "Parent category must belong to the same company."})
        if company and income_account and income_account.company_id != company.id:
            raise serializers.ValidationError({"income_account": "Income account company must match category company."})
        if company and expense_account and expense_account.company_id != company.id:
            raise serializers.ValidationError({"expense_account": "Expense account company must match category company."})
        if company and valuation_account and valuation_account.company_id != company.id:
            raise serializers.ValidationError({"valuation_account": "Valuation account company must match category company."})
        return attrs


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ["id", "name", "code", "lock_date", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AccountGroupTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountGroupTemplate
        fields = [
            "id",
            "country",
            "code_prefix_start",
            "code_prefix_end",
            "name",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        country = attrs.get("country") or getattr(self.instance, "country", None)
        parent = attrs.get("parent") if "parent" in attrs else getattr(self.instance, "parent", None)
        if country and parent and parent.country_id != country.id:
            raise serializers.ValidationError({"parent": "Parent template must belong to the same country."})
        return attrs


class AccountTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountTemplate
        fields = [
            "id",
            "country",
            "group",
            "code",
            "name",
            "account_type",
            "reconcile",
            "deprecated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        country = attrs.get("country") or getattr(self.instance, "country", None)
        group = attrs.get("group") if "group" in attrs else getattr(self.instance, "group", None)
        if country and group and group.country_id != country.id:
            raise serializers.ValidationError({"group": "Group template must belong to the same country."})
        return attrs


class ApplyChartTemplateSerializer(serializers.Serializer):
    country_id = serializers.IntegerField()


class MoveSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=24, decimal_places=6, read_only=True)

    class Meta:
        model = Move
        fields = [
            "id",
            "company",
            "journal",
            "partner",
            "currency",
            "payment_term",
            "reference",
            "name",
            "invoice_date",
            "date",
            "state",
            "move_type",
            "posted_at",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "posted_at", "balance", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        journal = attrs.get("journal") if "journal" in attrs else getattr(self.instance, "journal", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        payment_term = attrs.get("payment_term") if "payment_term" in attrs else getattr(self.instance, "payment_term", None)

        if company and journal and journal.company_id != company.id:
            raise serializers.ValidationError({"journal": "Journal company must match move company."})
        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match move company."})
        if company and payment_term and payment_term.company_id != company.id:
            raise serializers.ValidationError({"payment_term": "Payment term company must match move company."})
        return attrs


class MoveLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = MoveLine
        fields = [
            "id",
            "move",
            "account",
            "partner",
            "currency",
            "tax",
            "tax_repartition_line",
            "name",
            "date",
            "debit",
            "credit",
            "amount_currency",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        move = attrs.get("move") or getattr(self.instance, "move", None)
        account = attrs.get("account") if "account" in attrs else getattr(self.instance, "account", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)

        if move and move.state != "draft":
            raise serializers.ValidationError({"move": "Cannot add or modify lines on a posted/cancelled move."})
        if move and account and move.company_id != account.company_id:
            raise serializers.ValidationError({"account": "Account company must match move company."})
        if move and partner and move.company_id != partner.company_id:
            raise serializers.ValidationError({"partner": "Partner company must match move company."})
        return attrs


class InvoiceSerializer(serializers.ModelSerializer):
    amount_untaxed = serializers.DecimalField(max_digits=24, decimal_places=6, read_only=True)
    amount_tax = serializers.DecimalField(max_digits=24, decimal_places=6, read_only=True)
    amount_total = serializers.DecimalField(max_digits=24, decimal_places=6, read_only=True)

    class Meta:
        model = Move
        fields = [
            "id",
            "company",
            "journal",
            "partner",
            "currency",
            "payment_term",
            "reference",
            "name",
            "invoice_date",
            "date",
            "state",
            "move_type",
            "posted_at",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "state",
            "posted_at",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        invoice_types = {"out_invoice", "in_invoice", "out_refund", "in_refund"}
        move_type = attrs.get("move_type") or getattr(self.instance, "move_type", None)
        if move_type not in invoice_types:
            raise serializers.ValidationError({"move_type": "Invoice move_type must be out_invoice/in_invoice/out_refund/in_refund."})

        company = attrs.get("company") or getattr(self.instance, "company", None)
        journal = attrs.get("journal") if "journal" in attrs else getattr(self.instance, "journal", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        payment_term = attrs.get("payment_term") if "payment_term" in attrs else getattr(self.instance, "payment_term", None)

        if company and journal and journal.company_id != company.id:
            raise serializers.ValidationError({"journal": "Journal company must match invoice company."})
        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match invoice company."})
        if company and payment_term and payment_term.company_id != company.id:
            raise serializers.ValidationError({"payment_term": "Payment term company must match invoice company."})
        return attrs


class InvoiceLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLine
        fields = [
            "id",
            "move",
            "account",
            "tax",
            "name",
            "quantity",
            "unit_price",
            "discount_percent",
            "line_subtotal",
            "line_tax",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "line_subtotal", "line_tax", "line_total", "created_at", "updated_at"]

    def validate(self, attrs):
        move = attrs.get("move") or getattr(self.instance, "move", None)
        account = attrs.get("account") if "account" in attrs else getattr(self.instance, "account", None)
        tax = attrs.get("tax") if "tax" in attrs else getattr(self.instance, "tax", None)

        if move and move.state != "draft":
            raise serializers.ValidationError({"move": "Cannot add or modify lines on a posted/cancelled invoice."})
        if move and move.move_type not in {"out_invoice", "in_invoice", "out_refund", "in_refund"}:
            raise serializers.ValidationError({"move": "Invoice line requires an invoice/bill/refund move."})
        if move and account and move.company_id != account.company_id:
            raise serializers.ValidationError({"account": "Account company must match invoice company."})
        if move and tax and move.company_id != tax.company_id:
            raise serializers.ValidationError({"tax": "Tax company must match invoice company."})
        return attrs


class PartnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ["id", "name", "email", "is_company", "company", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AccountRootSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountRoot
        fields = ["id", "company", "code", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AccountGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountGroup
        fields = [
            "id",
            "company",
            "code_prefix_start",
            "code_prefix_end",
            "name",
            "parent",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        parent = attrs.get("parent") if "parent" in attrs else getattr(self.instance, "parent", None)
        if company and parent and parent.company_id != company.id:
            raise serializers.ValidationError({"parent": "Parent account group must belong to same company."})
        return attrs


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "company",
            "root",
            "group",
            "currency",
            "code",
            "name",
            "account_type",
            "reconcile",
            "deprecated",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        root = attrs.get("root") if "root" in attrs else getattr(self.instance, "root", None)
        group = attrs.get("group") if "group" in attrs else getattr(self.instance, "group", None)
        if company and root and root.company_id != company.id:
            raise serializers.ValidationError({"root": "Account root company must match account company."})
        if company and group and group.company_id != company.id:
            raise serializers.ValidationError({"group": "Account group company must match account company."})
        return attrs


class JournalGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = JournalGroup
        fields = ["id", "company", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class JournalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Journal
        fields = [
            "id",
            "company",
            "group",
            "currency",
            "default_account",
            "code",
            "name",
            "journal_type",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        group = attrs.get("group") if "group" in attrs else getattr(self.instance, "group", None)
        default_account = (
            attrs.get("default_account")
            if "default_account" in attrs
            else getattr(self.instance, "default_account", None)
        )
        if company and group and group.company_id != company.id:
            raise serializers.ValidationError({"group": "Journal group company must match journal company."})
        if company and default_account and default_account.company_id != company.id:
            raise serializers.ValidationError({"default_account": "Default account company must match journal company."})
        return attrs


class PaymentTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTerm
        fields = ["id", "company", "name", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentTermLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTermLine
        fields = [
            "id",
            "payment_term",
            "sequence",
            "value_type",
            "value",
            "due_type",
            "due_days",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class TaxGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxGroup
        fields = ["id", "company", "name", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class TaxSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tax
        fields = [
            "id",
            "company",
            "tax_group",
            "account",
            "name",
            "amount_type",
            "amount",
            "scope",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        tax_group = attrs.get("tax_group") if "tax_group" in attrs else getattr(self.instance, "tax_group", None)
        account = attrs.get("account") if "account" in attrs else getattr(self.instance, "account", None)
        if company and tax_group and tax_group.company_id != company.id:
            raise serializers.ValidationError({"tax_group": "Tax group company must match tax company."})
        if company and account and account.company_id != company.id:
            raise serializers.ValidationError({"account": "Tax account company must match tax company."})
        return attrs


class TaxRepartitionLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRepartitionLine
        fields = [
            "id",
            "tax",
            "account",
            "document_type",
            "repartition_type",
            "factor_percent",
            "sequence",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        tax = attrs.get("tax") or getattr(self.instance, "tax", None)
        account = attrs.get("account") if "account" in attrs else getattr(self.instance, "account", None)
        if tax and account and tax.company_id != account.company_id:
            raise serializers.ValidationError({"account": "Repartition account company must match tax company."})
        return attrs


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = ["id", "name", "code", "payment_direction", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentMethodLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethodLine
        fields = ["id", "journal", "payment_method", "sequence", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
    InvoiceLine,
