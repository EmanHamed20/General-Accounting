from .shared import *


class AnalyticItemViewSet(viewsets.ModelViewSet):
    queryset = AnalyticLine.objects.select_related(
        "company",
        "partner",
        "product",
        "journal",
        "move_line",
        "general_account",
        "analytic_account",
        "auto_account",
    ).all().order_by("-date", "-id")
    serializer_class = AnalyticLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        analytic_account_id = self.request.query_params.get("analytic_account_id")
        partner_id = self.request.query_params.get("partner_id")
        product_id = self.request.query_params.get("product_id")
        journal_id = self.request.query_params.get("journal_id")
        move_line_id = self.request.query_params.get("move_line_id")
        general_account_id = self.request.query_params.get("general_account_id")
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        project = self.request.query_params.get("project")
        task = self.request.query_params.get("task")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if analytic_account_id:
            queryset = queryset.filter(analytic_account_id=analytic_account_id)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if journal_id:
            queryset = queryset.filter(journal_id=journal_id)
        if move_line_id:
            queryset = queryset.filter(move_line_id=move_line_id)
        if general_account_id:
            queryset = queryset.filter(general_account_id=general_account_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if project:
            queryset = queryset.filter(project__icontains=project)
        if task:
            queryset = queryset.filter(task__icontains=task)
        return queryset


class AnalyticPlanViewSet(viewsets.ModelViewSet):
    queryset = AnalyticPlan.objects.select_related("company", "parent").all().order_by("company_id", "name")
    serializer_class = AnalyticPlanSerializer

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


class AnalyticAccountViewSet(viewsets.ModelViewSet):
    queryset = AnalyticAccount.objects.select_related("company", "plan", "partner").all().order_by("company_id", "name")
    serializer_class = AnalyticAccountSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        plan_id = self.request.query_params.get("plan_id")
        partner_id = self.request.query_params.get("partner_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if plan_id:
            queryset = queryset.filter(plan_id=plan_id)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class AnalyticDistributionModelViewSet(viewsets.ModelViewSet):
    queryset = AnalyticDistributionModel.objects.select_related("company", "partner", "product_category").all().order_by(
        "company_id", "name"
    )
    serializer_class = AnalyticDistributionModelSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        company_id = self.request.query_params.get("company_id")
        partner_id = self.request.query_params.get("partner_id")
        product_category_id = self.request.query_params.get("product_category_id")
        active = self.request.query_params.get("active")
        if company_id:
            queryset = queryset.filter(company_id=company_id)
        if partner_id:
            queryset = queryset.filter(partner_id=partner_id)
        if product_category_id:
            queryset = queryset.filter(product_category_id=product_category_id)
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset


class AnalyticDistributionModelLineViewSet(viewsets.ModelViewSet):
    queryset = AnalyticDistributionModelLine.objects.select_related("model", "analytic_account").all().order_by("model_id", "id")
    serializer_class = AnalyticDistributionModelLineSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        model_id = self.request.query_params.get("model_id")
        company_id = self.request.query_params.get("company_id")
        analytic_account_id = self.request.query_params.get("analytic_account_id")
        if model_id:
            queryset = queryset.filter(model_id=model_id)
        if company_id:
            queryset = queryset.filter(model__company_id=company_id)
        if analytic_account_id:
            queryset = queryset.filter(analytic_account_id=analytic_account_id)
        return queryset
