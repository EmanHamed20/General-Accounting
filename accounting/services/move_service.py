from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from accounting.models import Move, MoveLine


def is_entry(*, move: Move) -> bool:
    return move.move_type == "entry"


def _check_journal_move_type(*, move: Move) -> None:
    if move.move_type == "entry" and move.journal.journal_type not in {"general", "bank", "cash"}:
        raise ValidationError("Journal entry requires a general/bank/cash journal.")
    if move.move_type in {"out_invoice", "out_refund"} and move.journal.journal_type != "sale":
        raise ValidationError("Customer invoice/refund requires a sale journal.")
    if move.move_type in {"in_invoice", "in_refund"} and move.journal.journal_type != "purchase":
        raise ValidationError("Vendor bill/refund requires a purchase journal.")


def _check_fiscal_lock_dates(*, move: Move) -> None:
    if move.company.lock_date and move.date <= move.company.lock_date:
        raise ValidationError(
            f"Move date {move.date} is on or before company lock date {move.company.lock_date}."
        )


def _check_balanced(*, move: Move) -> dict:
    line_count = move.lines.count()
    if line_count == 0:
        raise ValidationError("Cannot post a move without lines.")

    totals = move.lines.aggregate(
        debit=Sum("debit", default=Decimal("0")),
        credit=Sum("credit", default=Decimal("0")),
    )
    total_debit = totals["debit"]
    total_credit = totals["credit"]

    if total_debit <= 0 and total_credit <= 0:
        raise ValidationError("Cannot post a move with zero totals.")
    if total_debit != total_credit:
        raise ValidationError(
            f"Move is not balanced. Debit={total_debit} Credit={total_credit}."
        )
    return {
        "line_count": line_count,
        "total_debit": total_debit,
        "total_credit": total_credit,
    }


def post_move(*, move: Move) -> dict:
    if move.state != "draft":
        raise ValidationError("Only draft moves can be posted.")

    _check_journal_move_type(move=move)
    _check_fiscal_lock_dates(move=move)
    balance_stats = _check_balanced(move=move)

    move.state = "posted"
    move.posted_at = timezone.now()
    move.save(update_fields=["state", "posted_at", "updated_at"])

    return {
        "move_id": move.id,
        "line_count": balance_stats["line_count"],
        "total_debit": str(balance_stats["total_debit"]),
        "total_credit": str(balance_stats["total_credit"]),
        "state": move.state,
        "posted_at": move.posted_at,
    }


def set_move_to_draft(*, move: Move) -> Move:
    if move.state == "draft":
        return move
    move.state = "draft"
    move.posted_at = None
    move.save(update_fields=["state", "posted_at", "updated_at"])
    return move


def cancel_move(*, move: Move) -> Move:
    if move.state == "cancelled":
        return move
    move.state = "cancelled"
    move.save(update_fields=["state", "updated_at"])
    return move


@transaction.atomic
def reverse_move(*, move: Move, date=None, reason: str = "", post: bool = False) -> Move:
    if move.state != "posted":
        raise ValidationError("Only posted moves can be reversed.")
    reverse_date = date or timezone.localdate()
    reverse_reference = f"Reversal of {move.name or move.id}"
    if reason:
        reverse_reference = f"{reverse_reference} - {reason}"

    reversed_move = Move.objects.create(
        company=move.company,
        journal=move.journal,
        partner=move.partner,
        currency=move.currency,
        payment_term=move.payment_term,
        incoterm=move.incoterm,
        incoterm_location=move.incoterm_location,
        reference=reverse_reference,
        name="",
        invoice_date=reverse_date,
        date=reverse_date,
        state="draft",
        move_type=move.move_type,
        reversed_entry=move,
    )

    lines = move.lines.select_related(
        "account", "partner", "currency", "tax", "tax_repartition_line",
    ).all()
    for line in lines:
        MoveLine.objects.create(
            move=reversed_move,
            account=line.account,
            partner=line.partner,
            currency=line.currency,
            tax=line.tax,
            tax_repartition_line=line.tax_repartition_line,
            name=line.name,
            date=reverse_date,
            debit=line.credit,
            credit=line.debit,
            amount_currency=-line.amount_currency,
        )

    if post:
        post_move(move=reversed_move)
    return reversed_move
