from .shared import *


class ProductViewSet(BaseModelViewSet):
    queryset = Product.objects.select_related(
        "company",
        "category",
        "income_account",
        "expense_account",
        "sale_tax",
        "purchase_tax",
    ).all().order_by("company_id", "name")
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        category_id = self.request.query_params.get("category_id")
        product_type = self.request.query_params.get("product_type")
        sale_ok = self.request.query_params.get("sale_ok")
        purchase_ok = self.request.query_params.get("purchase_ok")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        if sale_ok is not None:
            queryset = queryset.filter(sale_ok=sale_ok.lower() in {"1", "true", "yes"})
        if purchase_ok is not None:
            queryset = queryset.filter(purchase_ok=purchase_ok.lower() in {"1", "true", "yes"})
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            instance.full_clean()
        except DjangoValidationError as exc:
            raise DRFValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        instance.save()


class ProductCategoryViewSet(BaseModelViewSet):
    queryset = ProductCategory.objects.select_related(
        "company", "parent", "income_account", "expense_account", "valuation_account",
    ).all().order_by("company_id", "name")
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        parent_id = self.request.query_params.get("parent_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if parent_id:
            if parent_id.lower() == "null":
                queryset = queryset.filter(parent__isnull=True)
            else:
                queryset = queryset.filter(parent_id=parent_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset
