from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .base import AccountingBaseModel


class AnalyticPlanFieldsMixin:
    def _compute_auto_account(self):
        self.auto_account = self.analytic_account

    def _compute_partner_id(self):
        if self.partner_id:
            return
        if self.move_line_id and self.move_line.partner_id:
            self.partner = self.move_line.partner
        elif self.analytic_account_id and self.analytic_account.partner_id:
            self.partner = self.analytic_account.partner

    def _inverse_auto_account(self):
        if self.auto_account_id:
            self.analytic_account = self.auto_account

    def _search_auto_account(self, analytic_account_id):
        if not analytic_account_id:
            return self.__class__.objects.none()
        return self.__class__.objects.filter(analytic_account_id=analytic_account_id)

    def _get_plan_fnames(self):
        return ["analytic_account", "analytic_distribution"]

    def _get_analytic_accounts(self):
        accounts = []
        if self.analytic_account_id:
            accounts.append(self.analytic_account)
        distribution = self._get_analytic_distribution()
        if isinstance(distribution, dict):
            for key in distribution.keys():
                try:
                    acc_id = int(key)
                except (TypeError, ValueError):
                    continue
                if not any(a.id == acc_id for a in accounts):
                    account = AnalyticAccount.objects.filter(id=acc_id).first()
                    if account:
                        accounts.append(account)
        return accounts

    def _get_distribution_key(self):
        if self.analytic_account_id:
            return str(self.analytic_account_id)
        return ""

    def _get_analytic_distribution(self):
        return self.analytic_distribution or {}

    def _get_mandatory_plans(self):
        return AnalyticPlan.objects.filter(company_id=self.company_id, default_applicability="mandatory")

    def _get_plan_domain(self):
        return {"company_id": self.company_id, "active": True}

    def _get_account_node_context(self):
        return {"company_id": self.company_id}

    def _check_account_id(self):
        if self.analytic_account_id and self.analytic_account.company_id != self.company_id:
            raise ValidationError("Analytic account company must match analytic item company.")

    @classmethod
    def fields_get(cls):
        return [f.name for f in cls._meta.fields]

    @classmethod
    def _get_view(cls):
        return "analytic_items_form"

    @classmethod
    def _patch_view(cls, view_name):
        return view_name


class AnalyticPlan(AccountingBaseModel):
    APPLICABILITY_CHOICES = (
        ("optional", "Optional"),
        ("mandatory", "Mandatory"),
        ("unavailable", "Unavailable"),
    )

    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_plans")
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    name = models.CharField(max_length=255)
    default_applicability = models.CharField(max_length=16, choices=APPLICABILITY_CHOICES, default="optional")
    color = models.PositiveSmallIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_plan"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.parent_id and self.parent.company_id != self.company_id:
            raise ValidationError("Analytic plan parent company must match plan company.")

    def __str__(self):
        return self.name


class AnalyticAccount(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_accounts")
    plan = models.ForeignKey("accounting.AnalyticPlan", on_delete=models.PROTECT, related_name="accounts")
    partner = models.ForeignKey(
        "accounting.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_accounts",
    )
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=64, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_account"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.plan.company_id != self.company_id:
            raise ValidationError("Analytic account plan company must match account company.")
        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Analytic account partner company must match account company.")

    def __str__(self):
        return self.name


class AnalyticDistributionModel(AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_distribution_models")
    name = models.CharField(max_length=255)
    partner = models.ForeignKey(
        "accounting.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_distribution_models",
    )
    product_category = models.ForeignKey(
        "accounting.ProductCategory",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_distribution_models",
    )
    account_prefix = models.CharField(max_length=16, blank=True, default="")
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "ga_analytic_distribution_model"
        unique_together = (("company", "name"),)

    def clean(self):
        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Distribution model partner company must match model company.")
        if self.product_category_id and self.product_category.company_id != self.company_id:
            raise ValidationError("Distribution model product category company must match model company.")

    def __str__(self):
        return self.name


class AnalyticDistributionModelLine(AccountingBaseModel):
    model = models.ForeignKey("accounting.AnalyticDistributionModel", on_delete=models.CASCADE, related_name="lines")
    analytic_account = models.ForeignKey(
        "accounting.AnalyticAccount",
        on_delete=models.PROTECT,
        related_name="distribution_lines",
    )
    percentage = models.DecimalField(max_digits=7, decimal_places=4)

    class Meta:
        db_table = "ga_analytic_distribution_model_line"
        unique_together = (("model", "analytic_account"),)
        ordering = ("model_id", "id")

    def clean(self):
        if self.analytic_account.company_id != self.model.company_id:
            raise ValidationError("Distribution line analytic account company must match model company.")
        if self.percentage <= Decimal("0") or self.percentage > Decimal("100"):
            raise ValidationError("Distribution percentage must be greater than 0 and less than or equal to 100.")

    def __str__(self):
        return f"{self.model.name} - {self.analytic_account.name}: {self.percentage}%"


class AnalyticLine(AnalyticPlanFieldsMixin, AccountingBaseModel):
    company = models.ForeignKey("accounting.Company", on_delete=models.PROTECT, related_name="analytic_lines")
    name = models.CharField(max_length=255)
    date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    unit_amount = models.DecimalField(max_digits=18, decimal_places=6, default=Decimal("0"))
    uom_name = models.CharField(max_length=64, blank=True, default="")
    ref = models.CharField(max_length=255, blank=True, default="")
    partner = models.ForeignKey(
        "accounting.Partner",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    product = models.ForeignKey(
        "accounting.Product",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    journal = models.ForeignKey(
        "accounting.Journal",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    move_line = models.ForeignKey(
        "accounting.MoveLine",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    general_account = models.ForeignKey(
        "accounting.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    analytic_account = models.ForeignKey(
        "accounting.AnalyticAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="analytic_lines",
    )
    auto_account = models.ForeignKey(
        "accounting.AnalyticAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="auto_analytic_lines",
    )
    analytic_distribution = models.JSONField(default=dict, blank=True)
    project = models.CharField(max_length=255, blank=True, default="")
    task = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "ga_analytic_line"
        indexes = [
            models.Index(fields=["company", "date"]),
            models.Index(fields=["analytic_account"]),
            models.Index(fields=["move_line"]),
        ]

    def _compute_analytic_distribution(self):
        if self.analytic_account_id and not self.analytic_distribution:
            self.analytic_distribution = {str(self.analytic_account_id): 100.0}

    def _inverse_analytic_distribution(self):
        if self.analytic_distribution and isinstance(self.analytic_distribution, dict):
            keys = list(self.analytic_distribution.keys())
            if len(keys) == 1:
                try:
                    self.analytic_account_id = int(keys[0])
                except (TypeError, ValueError):
                    pass

    def _split_amount_fname(self):
        if self.amount >= 0:
            return "debit", self.amount
        return "credit", abs(self.amount)

    def _condition_to_sql(self, field_name, operator, value):
        operators = {"=": "=", "!=": "!=", ">": ">", ">=": ">=", "<": "<", "<=": "<=", "in": "IN", "not in": "NOT IN"}
        if operator not in operators:
            raise ValidationError(f"Unsupported operator '{operator}'.")
        return f"{field_name} {operators[operator]} {value}"

    def _compute_general_account_id(self):
        if self.move_line_id:
            self.general_account = self.move_line.account

    def _check_general_account_id(self):
        if self.general_account_id and self.general_account.company_id != self.company_id:
            raise ValidationError("Financial account company must match analytic item company.")
        if self.move_line_id and self.general_account_id and self.move_line.account_id != self.general_account_id:
            raise ValidationError("Financial account must match selected journal item account.")

    def on_change_unit_amount(self):
        if self.product_id:
            self.amount = (self.unit_amount * self.product.standard_price).quantize(Decimal("0.000001"))

    @classmethod
    def view_header_get(cls):
        return "Analytic Items"

    def write(self, vals: dict):
        for key, value in vals.items():
            setattr(self, key, value)
        self.save()
        return self

    def unlink(self):
        self.delete()
        return True

    def clean(self):
        self._check_account_id()
        self._check_general_account_id()

        if self.partner_id and self.partner.company_id != self.company_id:
            raise ValidationError("Partner company must match analytic item company.")
        if self.product_id and self.product.company_id != self.company_id:
            raise ValidationError("Product company must match analytic item company.")
        if self.journal_id and self.journal.company_id != self.company_id:
            raise ValidationError("Journal company must match analytic item company.")
        if self.move_line_id and self.move_line.move.company_id != self.company_id:
            raise ValidationError("Journal item company must match analytic item company.")

        if self.analytic_distribution and not isinstance(self.analytic_distribution, dict):
            raise ValidationError("Analytic distribution must be an object.")
        if self.analytic_distribution:
            total = Decimal("0")
            for key, pct in self.analytic_distribution.items():
                try:
                    analytic_id = int(key)
                except (TypeError, ValueError):
                    raise ValidationError("Analytic distribution keys must be analytic account ids.")
                account = AnalyticAccount.objects.filter(id=analytic_id).first()
                if not account or account.company_id != self.company_id:
                    raise ValidationError("Analytic distribution contains invalid analytic account.")
                total += Decimal(str(pct))
            if total <= 0 or total > Decimal("100.000001"):
                raise ValidationError("Analytic distribution total must be > 0 and <= 100.")

    def save(self, *args, **kwargs):
        self._compute_general_account_id()
        self._compute_partner_id()
        self._compute_auto_account()
        self._compute_analytic_distribution()
        self._inverse_analytic_distribution()
        self.full_clean()
        return super().save(*args, **kwargs)
