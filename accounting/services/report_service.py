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


@dataclass(frozen=True)
class ProfitAndLossOptions:
    company_id: int
    date_from: date
    date_to: date
    posted_only: bool = True


@dataclass(frozen=True)
class TrialBalanceOptions:
    company_id: int
    date_from: date
    date_to: date
    posted_only: bool = True
    hide_zero_lines: bool = False


@dataclass(frozen=True)
class GeneralLedgerOptions:
    company_id: int
    date_from: date
    date_to: date
    posted_only: bool = True
    account_id: int | None = None
    hide_zero_lines: bool = False


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


def build_profit_and_loss(options: ProfitAndLossOptions) -> dict:
    lines = MoveLine.objects.select_related("account", "move").filter(
        move__company_id=options.company_id,
        date__gte=options.date_from,
        date__lte=options.date_to,
        account__deprecated=False,
        account__account_type__in=["income", "expense"],
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

    income_lines: list[dict] = []
    expense_lines: list[dict] = []

    for row in grouped:
        account_type = row["account__account_type"]
        debit = _d(row["debit"])
        credit = _d(row["credit"])
        if account_type == "income":
            balance = credit - debit
        else:
            balance = debit - credit

        line = {
            "account_id": row["account_id"],
            "code": row["account__code"],
            "name": row["account__name"],
            "account_type": account_type,
            "debit": str(debit),
            "credit": str(credit),
            "balance": str(balance),
        }
        if account_type == "income":
            income_lines.append(line)
        else:
            expense_lines.append(line)

    total_income = sum((Decimal(l["balance"]) for l in income_lines), Decimal("0"))
    total_expenses = sum((Decimal(l["balance"]) for l in expense_lines), Decimal("0"))
    net_profit = total_income - total_expenses

    return {
        "company_id": options.company_id,
        "date_from": options.date_from.isoformat(),
        "date_to": options.date_to.isoformat(),
        "posted_only": options.posted_only,
        "sections": [
            {"key": "income", "label": "INCOME", "total": str(total_income), "lines": income_lines},
            {"key": "expenses", "label": "EXPENSES", "total": str(total_expenses), "lines": expense_lines},
        ],
        "totals": {
            "income": str(total_income),
            "expenses": str(total_expenses),
            "net_profit": str(net_profit),
        },
    }


def build_trial_balance(options: TrialBalanceOptions) -> dict:
    base_lines = MoveLine.objects.select_related("account", "move").filter(
        move__company_id=options.company_id,
        account__deprecated=False,
    )
    if options.posted_only:
        base_lines = base_lines.filter(move__state="posted")

    opening_qs = base_lines.filter(date__lt=options.date_from)
    period_qs = base_lines.filter(date__gte=options.date_from, date__lte=options.date_to)

    opening_rows = {
        row["account_id"]: row
        for row in opening_qs.values("account_id").annotate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
    }
    period_rows = {
        row["account_id"]: row
        for row in period_qs.values(
            "account_id",
            "account__code",
            "account__name",
            "account__account_type",
        ).annotate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
    }
    # ensure accounts with only opening balances are included
    opening_meta = {
        row["account_id"]: row
        for row in opening_qs.values(
            "account_id",
            "account__code",
            "account__name",
            "account__account_type",
        ).annotate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
    }

    all_ids = sorted(
        set(opening_rows.keys()) | set(period_rows.keys()),
        key=lambda acc_id: (
            (period_rows.get(acc_id) or opening_meta.get(acc_id) or {}).get("account__code", ""),
            acc_id,
        ),
    )

    lines: list[dict] = []
    totals = {
        "opening_debit": Decimal("0"),
        "opening_credit": Decimal("0"),
        "period_debit": Decimal("0"),
        "period_credit": Decimal("0"),
        "ending_debit": Decimal("0"),
        "ending_credit": Decimal("0"),
    }

    for account_id in all_ids:
        meta = period_rows.get(account_id) or opening_meta.get(account_id)
        opening = opening_rows.get(account_id, {})
        period = period_rows.get(account_id, {})

        opening_debit = _d(opening.get("debit"))
        opening_credit = _d(opening.get("credit"))
        period_debit = _d(period.get("debit"))
        period_credit = _d(period.get("credit"))

        net = (opening_debit + period_debit) - (opening_credit + period_credit)
        ending_debit = net if net > 0 else Decimal("0")
        ending_credit = -net if net < 0 else Decimal("0")

        if options.hide_zero_lines and not any(
            [opening_debit, opening_credit, period_debit, period_credit, ending_debit, ending_credit]
        ):
            continue

        line = {
            "account_id": account_id,
            "code": meta["account__code"],
            "name": meta["account__name"],
            "account_type": meta["account__account_type"],
            "opening_debit": str(opening_debit),
            "opening_credit": str(opening_credit),
            "period_debit": str(period_debit),
            "period_credit": str(period_credit),
            "ending_debit": str(ending_debit),
            "ending_credit": str(ending_credit),
        }
        lines.append(line)

        totals["opening_debit"] += opening_debit
        totals["opening_credit"] += opening_credit
        totals["period_debit"] += period_debit
        totals["period_credit"] += period_credit
        totals["ending_debit"] += ending_debit
        totals["ending_credit"] += ending_credit

    return {
        "company_id": options.company_id,
        "date_from": options.date_from.isoformat(),
        "date_to": options.date_to.isoformat(),
        "posted_only": options.posted_only,
        "hide_zero_lines": options.hide_zero_lines,
        "lines": lines,
        "totals": {k: str(v) for k, v in totals.items()},
        "checks": {
            "opening_balanced": totals["opening_debit"] == totals["opening_credit"],
            "period_balanced": totals["period_debit"] == totals["period_credit"],
            "ending_balanced": totals["ending_debit"] == totals["ending_credit"],
        },
    }


def build_general_ledger(options: GeneralLedgerOptions) -> dict:
    base_qs = (
        MoveLine.objects.select_related("account", "move", "partner")
        .filter(move__company_id=options.company_id, account__deprecated=False)
        .order_by("account__code", "date", "id")
    )
    if options.posted_only:
        base_qs = base_qs.filter(move__state="posted")
    if options.account_id:
        base_qs = base_qs.filter(account_id=options.account_id)

    opening_rows = {
        row["account_id"]: row
        for row in base_qs.filter(date__lt=options.date_from)
        .values("account_id", "account__code", "account__name", "account__account_type")
        .annotate(
            debit=Coalesce(Sum("debit"), Decimal("0")),
            credit=Coalesce(Sum("credit"), Decimal("0")),
        )
    }

    period_lines = list(base_qs.filter(date__gte=options.date_from, date__lte=options.date_to))

    grouped: dict[int, dict] = {}
    for ml in period_lines:
        bucket = grouped.setdefault(
            ml.account_id,
            {
                "account_id": ml.account_id,
                "code": ml.account.code,
                "name": ml.account.name,
                "account_type": ml.account.account_type,
                "opening_debit": Decimal("0"),
                "opening_credit": Decimal("0"),
                "opening_balance": Decimal("0"),
                "lines": [],
                "period_debit": Decimal("0"),
                "period_credit": Decimal("0"),
                "closing_balance": Decimal("0"),
            },
        )
        bucket["period_debit"] += ml.debit
        bucket["period_credit"] += ml.credit

    # ensure accounts with only opening balance are included
    for account_id, row in opening_rows.items():
        grouped.setdefault(
            account_id,
            {
                "account_id": account_id,
                "code": row["account__code"],
                "name": row["account__name"],
                "account_type": row["account__account_type"],
                "opening_debit": Decimal("0"),
                "opening_credit": Decimal("0"),
                "opening_balance": Decimal("0"),
                "lines": [],
                "period_debit": Decimal("0"),
                "period_credit": Decimal("0"),
                "closing_balance": Decimal("0"),
            },
        )

    for account_id, row in opening_rows.items():
        bucket = grouped[account_id]
        opening_debit = _d(row["debit"])
        opening_credit = _d(row["credit"])
        bucket["opening_debit"] = opening_debit
        bucket["opening_credit"] = opening_credit
        bucket["opening_balance"] = opening_debit - opening_credit

    # add period lines with running balance
    running_map = {acc_id: grouped[acc_id]["opening_balance"] for acc_id in grouped.keys()}
    for ml in period_lines:
        running_map[ml.account_id] += ml.debit - ml.credit
        grouped[ml.account_id]["lines"].append(
            {
                "id": ml.id,
                "date": ml.date.isoformat(),
                "move_id": ml.move_id,
                "move_name": ml.move.name,
                "move_reference": ml.move.reference,
                "partner_id": ml.partner_id,
                "partner_name": ml.partner.name if ml.partner_id else "",
                "label": ml.name,
                "debit": str(ml.debit),
                "credit": str(ml.credit),
                "running_balance": str(running_map[ml.account_id]),
            }
        )

    account_entries: list[dict] = []
    total_opening = Decimal("0")
    total_period_debit = Decimal("0")
    total_period_credit = Decimal("0")
    total_closing = Decimal("0")

    for account_id in sorted(grouped.keys(), key=lambda i: (grouped[i]["code"], i)):
        g = grouped[account_id]
        g["closing_balance"] = g["opening_balance"] + g["period_debit"] - g["period_credit"]

        if options.hide_zero_lines and not (
            g["opening_debit"]
            or g["opening_credit"]
            or g["period_debit"]
            or g["period_credit"]
            or g["closing_balance"]
        ):
            continue

        account_entries.append(
            {
                "account_id": g["account_id"],
                "code": g["code"],
                "name": g["name"],
                "account_type": g["account_type"],
                "opening_debit": str(g["opening_debit"]),
                "opening_credit": str(g["opening_credit"]),
                "opening_balance": str(g["opening_balance"]),
                "period_debit": str(g["period_debit"]),
                "period_credit": str(g["period_credit"]),
                "closing_balance": str(g["closing_balance"]),
                "lines": g["lines"],
            }
        )
        total_opening += g["opening_balance"]
        total_period_debit += g["period_debit"]
        total_period_credit += g["period_credit"]
        total_closing += g["closing_balance"]

    return {
        "company_id": options.company_id,
        "account_id": options.account_id,
        "date_from": options.date_from.isoformat(),
        "date_to": options.date_to.isoformat(),
        "posted_only": options.posted_only,
        "hide_zero_lines": options.hide_zero_lines,
        "accounts": account_entries,
        "totals": {
            "opening_balance": str(total_opening),
            "period_debit": str(total_period_debit),
            "period_credit": str(total_period_credit),
            "closing_balance": str(total_closing),
        },
    }
