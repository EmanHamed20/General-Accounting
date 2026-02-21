from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import Coalesce

from accounting.models import MoveLine


@dataclass(frozen=True)
class BalanceSheetOptions:
    company_id: int
    date_to: date
    posted_only: bool = True
    include_current_year_earnings: bool = True


def _d(value: Decimal | None) -> Decimal:
    return value or Decimal("0")


def build_balance_sheet(options: BalanceSheetOptions) -> dict:
    lines = MoveLine.objects.select_related("account", "move").filter(
        move__company_id=options.company_id,
        date__lte=options.date_to,
        account__deprecated=False,
    )
    if options.posted_only:
        lines = lines.filter(move__state="posted")

    grouped = (
        lines.values(
            "account_id",
            "account__code",
            "account__name",
            "account__account_type",
        )
        .annotate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
        .order_by("account__code")
    )

    assets: list[dict] = []
    liabilities: list[dict] = []
    equity: list[dict] = []

    for row in grouped:
        account_type = row["account__account_type"]
        debit = _d(row["debit"])
        credit = _d(row["credit"])
        if account_type == "asset":
            balance = debit - credit
        else:
            balance = credit - debit

        line = {
            "account_id": row["account_id"],
            "code": row["account__code"],
            "name": row["account__name"],
            "account_type": account_type,
            "debit": str(debit),
            "credit": str(credit),
            "balance": str(balance),
        }

        if account_type == "asset":
            assets.append(line)
        elif account_type == "liability":
            liabilities.append(line)
        elif account_type == "equity":
            equity.append(line)

    assets_total = sum((Decimal(l["balance"]) for l in assets), Decimal("0"))
    liabilities_total = sum((Decimal(l["balance"]) for l in liabilities), Decimal("0"))
    equity_total = sum((Decimal(l["balance"]) for l in equity), Decimal("0"))

    current_year_earnings = Decimal("0")
    if options.include_current_year_earnings:
        year_start = date(options.date_to.year, 1, 1)
        period_lines = lines.filter(date__gte=year_start)
        income = period_lines.filter(account__account_type="income").aggregate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
        expense = period_lines.filter(account__account_type="expense").aggregate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
        income_balance = _d(income["credit"]) - _d(income["debit"])
        expense_balance = _d(expense["debit"]) - _d(expense["credit"])
        current_year_earnings = income_balance - expense_balance
        equity_total += current_year_earnings

    liabilities_and_equity_total = liabilities_total + equity_total

    return {
        "company_id": options.company_id,
        "date_to": options.date_to.isoformat(),
        "posted_only": options.posted_only,
        "sections": [
            {"key": "assets", "label": "ASSETS", "total": str(assets_total), "lines": assets},
            {"key": "liabilities", "label": "LIABILITIES", "total": str(liabilities_total), "lines": liabilities},
            {"key": "equity", "label": "EQUITY", "total": str(equity_total), "lines": equity},
        ],
        "totals": {
            "assets": str(assets_total),
            "liabilities": str(liabilities_total),
            "equity": str(equity_total),
            "current_year_earnings": str(current_year_earnings),
            "liabilities_and_equity": str(liabilities_and_equity_total),
            "imbalance": str(assets_total - liabilities_and_equity_total),
        },
    }
