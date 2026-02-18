from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.models import AccountingSettings, Move, MoveLine, Payment
from accounting.services.move_service import post_move


@transaction.atomic
def post_payment(*, payment: Payment) -> dict:
    if payment.state != "draft":
        raise ValidationError("Only draft payments can be posted.")
    if payment.move_id:
        raise ValidationError("Payment is already linked to a journal entry.")
    if payment.amount <= 0:
        raise ValidationError("Payment amount must be greater than zero.")

    journal_default_account = payment.journal.default_account
    if not journal_default_account:
        raise ValidationError("Journal default_account is required to post payment.")
    if journal_default_account.company_id != payment.company_id:
        raise ValidationError("Journal default account company must match payment company.")

    settings = AccountingSettings.objects.filter(company_id=payment.company_id).first()
    counterpart_account = settings.transfer_account if settings and settings.transfer_account_id else None
    if counterpart_account is None:
        counterpart_account = journal_default_account
    if counterpart_account.company_id != payment.company_id:
        raise ValidationError("Counterpart account company must match payment company.")

    move = Move.objects.create(
        company=payment.company,
        journal=payment.journal,
        partner=payment.partner,
        currency=payment.currency,
        payment_term=None,
        reference=payment.reference or f"Payment {payment.id}",
        name="",
        invoice_date=payment.date,
        date=payment.date,
        state="draft",
        move_type="entry",
    )

    amount = Decimal(payment.amount)
    inbound = payment.payment_type == "inbound"

    liquidity_debit = amount if inbound else Decimal("0")
    liquidity_credit = amount if not inbound else Decimal("0")
    counterpart_debit = amount if not inbound else Decimal("0")
    counterpart_credit = amount if inbound else Decimal("0")

    MoveLine.objects.create(
        move=move,
        account=journal_default_account,
        partner=payment.partner,
        currency=payment.currency,
        name=payment.reference or "Payment",
        date=payment.date,
        debit=liquidity_debit,
        credit=liquidity_credit,
        amount_currency=liquidity_debit if liquidity_debit else -liquidity_credit,
    )
    MoveLine.objects.create(
        move=move,
        account=counterpart_account,
        partner=payment.partner,
        currency=payment.currency,
        name=payment.reference or "Payment Counterpart",
        date=payment.date,
        debit=counterpart_debit,
        credit=counterpart_credit,
        amount_currency=counterpart_debit if counterpart_debit else -counterpart_credit,
    )

    post_move(move=move)
    payment.move = move
    payment.state = "posted"
    payment.full_clean()
    payment.save(update_fields=["move", "state", "updated_at"])

    return {"payment_id": payment.id, "move_id": move.id, "state": payment.state}
