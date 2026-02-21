from rest_framework import serializers

from accounting.models import (
    Account,
    AccountGroup,
    AccountGroupTemplate,
    AccountRoot,
    AccountTemplate,
    AnalyticAccount,
    AnalyticDistributionModel,
    AnalyticDistributionModelLine,
    AnalyticPlan,
    Asset,
    AssetDepreciationLine,
    Company,
    Country,
    CountryCity,
    CountryCurrency,
    CountryState,
    Currency,
    Incoterm,
    Journal,
    InvoiceLine,
    Move,
    MoveLine,
    Payment,
    PaymentMethod,
    PaymentMethodLine,
    PaymentTermLine,
    Partner,
    PaymentTerm,
    Product,
    ProductCategory,
    JournalGroup,
    TaxGroup,
    Tax,
    TaxRepartitionLine,
    AccountingSettings,
    FollowupLevel,
    BankAccount,
    ReconciliationModel,
    ReconciliationModelLine,
    FiscalPosition,
    FiscalPositionTaxMap,
    FiscalPositionAccountMap,
    Ledger,
    FinancialBudget,
    FinancialBudgetLine,
    AssetModel,
    DisallowedExpenseCategory,
    PaymentProvider,
    PaymentProviderMethod,
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


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [
            "id",
            "company",
            "category",
            "name",
            "default_code",
            "barcode",
            "product_type",
            "sale_ok",
            "purchase_ok",
            "list_price",
            "standard_price",
            "income_account",
            "expense_account",
            "sale_tax",
            "purchase_tax",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        category = attrs.get("category") if "category" in attrs else getattr(self.instance, "category", None)
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
        sale_tax = attrs.get("sale_tax") if "sale_tax" in attrs else getattr(self.instance, "sale_tax", None)
        purchase_tax = (
            attrs.get("purchase_tax")
            if "purchase_tax" in attrs
            else getattr(self.instance, "purchase_tax", None)
        )
        if company and category and category.company_id != company.id:
            raise serializers.ValidationError({"category": "Product category company must match product company."})
        if company and income_account and income_account.company_id != company.id:
            raise serializers.ValidationError({"income_account": "Income account company must match product company."})
        if company and expense_account and expense_account.company_id != company.id:
            raise serializers.ValidationError({"expense_account": "Expense account company must match product company."})
        if company and sale_tax and sale_tax.company_id != company.id:
            raise serializers.ValidationError({"sale_tax": "Sale tax company must match product company."})
        if company and purchase_tax and purchase_tax.company_id != company.id:
            raise serializers.ValidationError({"purchase_tax": "Purchase tax company must match product company."})
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


class ReverseInvoiceSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


class ReverseMoveSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)
    post = serializers.BooleanField(required=False, default=False)


class CreateDebitNoteSerializer(serializers.Serializer):
    date = serializers.DateField(required=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=255)


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
            "incoterm",
            "incoterm_location",
            "reference",
            "name",
            "invoice_date",
            "date",
            "state",
            "move_type",
            "reversed_entry",
            "debit_origin",
            "is_debit_note",
            "posted_at",
            "balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "reversed_entry", "debit_origin", "posted_at", "balance", "created_at", "updated_at"]

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


class JournalEntrySerializer(MoveSerializer):
    class Meta(MoveSerializer.Meta):
        read_only_fields = list(MoveSerializer.Meta.read_only_fields) + ["move_type"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        move_type = attrs.get("move_type") or getattr(self.instance, "move_type", "entry")
        if move_type != "entry":
            raise serializers.ValidationError({"move_type": "Journal entry move_type must be entry."})
        return attrs

    def create(self, validated_data):
        validated_data["move_type"] = "entry"
        return super().create(validated_data)


class JournalEntryLineSerializer(MoveLineSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        move = attrs.get("move") or getattr(self.instance, "move", None)
        if move and move.move_type != "entry":
            raise serializers.ValidationError({"move": "Journal entry line requires a move with move_type=entry."})
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
            "incoterm",
            "incoterm_location",
            "reference",
            "name",
            "invoice_date",
            "date",
            "state",
            "move_type",
            "reversed_entry",
            "debit_origin",
            "is_debit_note",
            "posted_at",
            "amount_untaxed",
            "amount_tax",
            "amount_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "reversed_entry",
            "debit_origin",
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
        fields = [
            "id",
            "company",
            "parent",
            "name",
            "type",
            "email",
            "phone",
            "mobile",
            "street",
            "street2",
            "city",
            "zip",
            "country",
            "state",
            "vat",
            "is_company",
            "customer_rank",
            "supplier_rank",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        parent = attrs.get("parent") if "parent" in attrs else getattr(self.instance, "parent", None)
        country = attrs.get("country") if "country" in attrs else getattr(self.instance, "country", None)
        state = attrs.get("state") if "state" in attrs else getattr(self.instance, "state", None)

        if company and parent and parent.company_id != company.id:
            raise serializers.ValidationError({"parent": "Parent contact company must match contact company."})
        if country and state and state.country_id != country.id:
            raise serializers.ValidationError({"state": "State must belong to selected country."})
        return attrs


class VendorSerializer(serializers.ModelSerializer):
    supplier_invoice_count = serializers.SerializerMethodField()
    purchase_order_count = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            "id",
            "name",
            "email",
            "is_company",
            "supplier_rank",
            "customer_rank",
            "supplier_invoice_count",
            "purchase_order_count",
            "company",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "supplier_invoice_count", "purchase_order_count", "created_at", "updated_at"]

    def get_supplier_invoice_count(self, obj):
        return getattr(obj, "supplier_invoice_count", 0)

    def get_purchase_order_count(self, obj):
        # Purchase module is not implemented in this project yet.
        return 0


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


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            "id",
            "company",
            "name",
            "code",
            "partner",
            "currency",
            "asset_account",
            "depreciation_account",
            "expense_account",
            "journal",
            "acquisition_date",
            "first_depreciation_date",
            "original_value",
            "salvage_value",
            "method",
            "method_number",
            "method_period",
            "prorata",
            "state",
            "active",
            "note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        journal = attrs.get("journal") if "journal" in attrs else getattr(self.instance, "journal", None)
        asset_account = (
            attrs.get("asset_account")
            if "asset_account" in attrs
            else getattr(self.instance, "asset_account", None)
        )
        depreciation_account = (
            attrs.get("depreciation_account")
            if "depreciation_account" in attrs
            else getattr(self.instance, "depreciation_account", None)
        )
        expense_account = (
            attrs.get("expense_account")
            if "expense_account" in attrs
            else getattr(self.instance, "expense_account", None)
        )
        original_value = attrs.get("original_value", getattr(self.instance, "original_value", None))
        salvage_value = attrs.get("salvage_value", getattr(self.instance, "salvage_value", None))
        acquisition_date = attrs.get("acquisition_date", getattr(self.instance, "acquisition_date", None))
        first_depreciation_date = attrs.get(
            "first_depreciation_date",
            getattr(self.instance, "first_depreciation_date", None),
        )

        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match asset company."})
        if company and journal and journal.company_id != company.id:
            raise serializers.ValidationError({"journal": "Journal company must match asset company."})
        if company and asset_account and asset_account.company_id != company.id:
            raise serializers.ValidationError({"asset_account": "Asset account company must match asset company."})
        if company and depreciation_account and depreciation_account.company_id != company.id:
            raise serializers.ValidationError(
                {"depreciation_account": "Depreciation account company must match asset company."}
            )
        if company and expense_account and expense_account.company_id != company.id:
            raise serializers.ValidationError({"expense_account": "Expense account company must match asset company."})

        if original_value is not None and original_value <= 0:
            raise serializers.ValidationError({"original_value": "Original value must be greater than zero."})
        if salvage_value is not None and salvage_value < 0:
            raise serializers.ValidationError({"salvage_value": "Salvage value cannot be negative."})
        if (
            original_value is not None
            and salvage_value is not None
            and salvage_value >= original_value
        ):
            raise serializers.ValidationError({"salvage_value": "Salvage value must be lower than original value."})
        if first_depreciation_date and acquisition_date and first_depreciation_date < acquisition_date:
            raise serializers.ValidationError(
                {"first_depreciation_date": "First depreciation date cannot be before acquisition date."}
            )
        return attrs


class AssetDepreciationLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetDepreciationLine
        fields = [
            "id",
            "asset",
            "move",
            "sequence",
            "date",
            "amount",
            "depreciated_value",
            "residual_value",
            "state",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        asset = attrs.get("asset") or getattr(self.instance, "asset", None)
        move = attrs.get("move") if "move" in attrs else getattr(self.instance, "move", None)
        state = attrs.get("state", getattr(self.instance, "state", None))
        amount = attrs.get("amount", getattr(self.instance, "amount", None))
        residual_value = attrs.get("residual_value", getattr(self.instance, "residual_value", None))

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Depreciation amount must be greater than zero."})
        if residual_value is not None and residual_value < 0:
            raise serializers.ValidationError({"residual_value": "Residual value cannot be negative."})
        if asset and move and move.company_id != asset.company_id:
            raise serializers.ValidationError({"move": "Depreciation move company must match asset company."})
        if state == "posted" and not move:
            raise serializers.ValidationError({"move": "Posted depreciation line requires a move."})
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


class IncotermSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incoterm
        fields = ["id", "code", "name", "active", "created_at", "updated_at"]
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


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = [
            "id",
            "company",
            "partner",
            "journal",
            "payment_method_line",
            "move",
            "currency",
            "date",
            "amount",
            "payment_type",
            "state",
            "reference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "move", "state", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        journal = attrs.get("journal") if "journal" in attrs else getattr(self.instance, "journal", None)
        payment_method_line = (
            attrs.get("payment_method_line")
            if "payment_method_line" in attrs
            else getattr(self.instance, "payment_method_line", None)
        )
        currency = attrs.get("currency") if "currency" in attrs else getattr(self.instance, "currency", None)
        payment_type = attrs.get("payment_type") or getattr(self.instance, "payment_type", None)
        amount = attrs.get("amount") if "amount" in attrs else getattr(self.instance, "amount", None)

        if amount is not None and amount <= 0:
            raise serializers.ValidationError({"amount": "Payment amount must be greater than zero."})
        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match payment company."})
        if company and journal and journal.company_id != company.id:
            raise serializers.ValidationError({"journal": "Journal company must match payment company."})
        if journal and payment_method_line and payment_method_line.journal_id != journal.id:
            raise serializers.ValidationError({"payment_method_line": "Payment method line must belong to selected journal."})
        if payment_method_line and payment_type and payment_method_line.payment_method.payment_direction != payment_type:
            raise serializers.ValidationError({"payment_type": "Payment type must match payment method direction."})
        if journal and currency and journal.currency_id and journal.currency_id != currency.id:
            raise serializers.ValidationError({"currency": "Currency must match journal currency when journal currency is set."})
        return attrs


class AnalyticPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticPlan
        fields = [
            "id",
            "company",
            "parent",
            "name",
            "default_applicability",
            "color",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AnalyticAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticAccount
        fields = ["id", "company", "plan", "partner", "name", "code", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        plan = attrs.get("plan") if "plan" in attrs else getattr(self.instance, "plan", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        if company and plan and plan.company_id != company.id:
            raise serializers.ValidationError({"plan": "Analytic plan company must match analytic account company."})
        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match analytic account company."})
        return attrs


class AnalyticDistributionModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticDistributionModel
        fields = [
            "id",
            "company",
            "name",
            "partner",
            "product_category",
            "account_prefix",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        company = attrs.get("company") or getattr(self.instance, "company", None)
        partner = attrs.get("partner") if "partner" in attrs else getattr(self.instance, "partner", None)
        product_category = (
            attrs.get("product_category")
            if "product_category" in attrs
            else getattr(self.instance, "product_category", None)
        )
        if company and partner and partner.company_id != company.id:
            raise serializers.ValidationError({"partner": "Partner company must match distribution model company."})
        if company and product_category and product_category.company_id != company.id:
            raise serializers.ValidationError(
                {"product_category": "Product category company must match distribution model company."}
            )
        return attrs


class AnalyticDistributionModelLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticDistributionModelLine
        fields = ["id", "model", "analytic_account", "percentage", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        model = attrs.get("model") or getattr(self.instance, "model", None)
        analytic_account = (
            attrs.get("analytic_account")
            if "analytic_account" in attrs
            else getattr(self.instance, "analytic_account", None)
        )
        if model and analytic_account and model.company_id != analytic_account.company_id:
            raise serializers.ValidationError(
                {"analytic_account": "Analytic account company must match distribution model company."}
            )
        return attrs


class AccountingSettingsSerializer(serializers.ModelSerializer):
    sale_tax = serializers.PrimaryKeyRelatedField(
        source="default_sales_tax",
        queryset=Tax.objects.all(),
        required=False,
        allow_null=True,
    )
    purchase_tax = serializers.PrimaryKeyRelatedField(
        source="default_purchase_tax",
        queryset=Tax.objects.all(),
        required=False,
        allow_null=True,
    )
    tax_calculation_rounding_method = serializers.ChoiceField(
        source="tax_rounding_method",
        choices=AccountingSettings.TAX_ROUNDING_METHOD_CHOICES,
        required=False,
    )

    class Meta:
        model = AccountingSettings
        fields = [
            "id",
            "company",
            "country_code",
            "fiscal_localization_country",
            "chart_template_country",
            "account_fiscal_country",
            "chart_template",
            "has_chart_of_accounts",
            "has_accounting_entries",
            "currency",
            "group_multi_currency",
            "module_currency_rate_live",
            "default_sales_tax",
            "default_purchase_tax",
            "sale_tax",
            "purchase_tax",
            "tax_return_periodicity",
            "tax_return_reminder_days",
            "tax_return_journal",
            "tax_rounding_method",
            "tax_calculation_rounding_method",
            "account_price_include",
            "currency_exchange_journal",
            "income_currency_exchange_account",
            "expense_currency_exchange_account",
            "bank_suspense_account",
            "account_journal_suspense_account",
            "transfer_account",
            "tax_exigibility",
            "tax_cash_basis_journal",
            "account_cash_basis_base_account",
            "account_discount_expense_allocation",
            "account_discount_income_allocation",
            "account_journal_early_pay_discount_gain_account",
            "account_journal_early_pay_discount_loss_account",
            "default_sale_payment_term",
            "default_purchase_payment_term",
            "fiscalyear_last_day",
            "fiscalyear_last_month",
            "use_anglo_saxon",
            "invoicing_switch_threshold",
            "predict_bill_product",
            "followup_enabled",
            "multi_ledger_enabled",
            "budgets_enabled",
            "assets_enabled",
            "online_payments_enabled",
            "quick_edit_mode",
            "check_account_audit_trail",
            "autopost_bills",
            "account_use_credit_limit",
            "account_default_credit_limit",
            "account_storno",
            "qr_code",
            "module_l10n_eu_oss",
            "module_snailmail_account",
            "group_sale_delivery_address",
            "group_warning_account",
            "group_cash_rounding",
            "module_account_intrastat",
            "incoterm",
            "group_show_sale_receipts",
            "terms_type",
            "preview_ready",
            "display_invoice_amount_total_words",
            "display_invoice_tax_company_currency",
            "group_uom",
            "module_account_payment",
            "module_account_batch_payment",
            "module_account_sepa_direct_debit",
            "group_show_purchase_receipts",
            "module_account_check_printing",
            "module_account_iso20022",
            "module_account_extract",
            "module_account_bank_statement_import_csv",
            "module_account_bank_statement_import_qif",
            "module_account_bank_statement_import_ofx",
            "module_account_bank_statement_import_camt",
            "module_account_reports",
            "group_analytic_accounting",
            "module_account_budget",
            "module_product_margin",
            "is_account_peppol_eligible",
            "module_account_peppol",
            "invoice_terms",
            "use_invoice_terms",
            "deferred_expense_journal",
            "deferred_expense_account",
            "generate_deferred_expense_entries_method",
            "deferred_expense_amount_computation_method",
            "deferred_revenue_journal",
            "deferred_revenue_account",
            "generate_deferred_revenue_entries_method",
            "deferred_revenue_amount_computation_method",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FollowupLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = FollowupLevel
        fields = ["id", "company", "name", "delay_days", "action", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = [
            "id",
            "company",
            "journal",
            "bank_name",
            "account_holder",
            "iban",
            "swift",
            "account_number",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReconciliationModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationModel
        fields = ["id", "company", "name", "journal", "auto_reconcile", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReconciliationModelLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReconciliationModelLine
        fields = [
            "id",
            "reconciliation_model",
            "sequence",
            "label",
            "account",
            "tax",
            "amount_type",
            "amount",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class FiscalPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPosition
        fields = ["id", "company", "name", "country", "auto_apply", "vat_required", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FiscalPositionTaxMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPositionTaxMap
        fields = ["id", "fiscal_position", "tax_src", "tax_dest", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FiscalPositionAccountMapSerializer(serializers.ModelSerializer):
    class Meta:
        model = FiscalPositionAccountMap
        fields = ["id", "fiscal_position", "account_src", "account_dest", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ledger
        fields = ["id", "company", "currency", "name", "code", "is_default", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FinancialBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialBudget
        fields = ["id", "company", "name", "date_from", "date_to", "state", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class FinancialBudgetLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialBudgetLine
        fields = ["id", "budget", "account", "name", "planned_amount", "practical_amount", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class AssetModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetModel
        fields = [
            "id",
            "company",
            "name",
            "method",
            "method_number",
            "method_period_months",
            "prorata",
            "account_asset",
            "account_depreciation",
            "account_expense",
            "journal",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DisallowedExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DisallowedExpenseCategory
        fields = ["id", "company", "name", "disallow_percent", "expense_account", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProvider
        fields = ["id", "company", "journal", "name", "code", "state", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class PaymentProviderMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentProviderMethod
        fields = ["id", "provider", "payment_method", "active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
