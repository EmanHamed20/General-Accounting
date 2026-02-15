from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.utils import timezone

from accounting.models import Move


def post_move(*, move: Move) -> dict:
    if move.state != "draft":
        raise ValidationError("Only draft moves can be posted.")

    if move.company.lock_date and move.date <= move.company.lock_date:
        raise ValidationError(
            f"Move date {move.date} is on or before company lock date {move.company.lock_date}."
        )

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

    move.state = "posted"
    move.posted_at = timezone.now()
    move.save(update_fields=["state", "posted_at", "updated_at"])

    return {
        "move_id": move.id,
        "line_count": line_count,
        "total_debit": str(total_debit),
        "total_credit": str(total_credit),
        "state": move.state,
        "posted_at": move.posted_at,
    }
