from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounting.models import Move, MoveLine
from accounting.services.move_service import post_move


INVOICE_MOVE_TYPES = {"out_invoice", "in_invoice", "out_refund", "in_refund"}


@transaction.atomic
def generate_journal_lines_and_post_invoice(*, invoice: Move) -> dict:
    if invoice.move_type not in INVOICE_MOVE_TYPES:
        raise ValidationError("Move is not an invoice/bill/refund.")
    if invoice.state != "draft":
        raise ValidationError("Only draft invoices can be posted.")

    invoice_lines = list(invoice.invoice_lines.select_related("account", "tax", "tax__account").all())
    if not invoice_lines:
        raise ValidationError("Cannot post invoice without invoice lines.")

    counterpart_account = invoice.journal.default_account
    if not counterpart_account:
        raise ValidationError("Journal default_account is required to post invoice.")
    if counterpart_account.company_id != invoice.company_id:
        raise ValidationError("Journal default account company must match invoice company.")

    # Rebuild accounting lines from invoice lines to avoid stale draft journal lines.
    invoice.lines.all().delete()

    business_debit = invoice.move_type in {"out_refund", "in_invoice"}
    counterpart_debit = not business_debit

    total_amount = Decimal("0")
    created_lines = 0

    for line in invoice_lines:
        if line.account.company_id != invoice.company_id:
            raise ValidationError(f"Invoice line account company mismatch for line {line.id}.")

        subtotal = line.line_subtotal
        tax_amount = line.line_tax
        total_amount += line.line_total

        if subtotal:
            debit = subtotal if business_debit else Decimal("0")
            credit = subtotal if not business_debit else Decimal("0")
            MoveLine.objects.create(
                move=invoice,
                account=line.account,
                partner=invoice.partner,
                currency=invoice.currency,
                tax=line.tax,
                name=line.name,
                date=invoice.date,
                debit=debit,
                credit=credit,
                amount_currency=debit if debit else -credit,
            )
            created_lines += 1

        if tax_amount:
            if not line.tax or not line.tax.account_id:
                raise ValidationError(f"Tax account is required for taxed invoice line {line.id}.")
            if line.tax.account.company_id != invoice.company_id:
                raise ValidationError(f"Tax account company mismatch for line {line.id}.")

            debit = tax_amount if business_debit else Decimal("0")
            credit = tax_amount if not business_debit else Decimal("0")
            MoveLine.objects.create(
                move=invoice,
                account=line.tax.account,
                partner=invoice.partner,
                currency=invoice.currency,
                tax=line.tax,
                name=f"Tax: {line.tax.name}",
                date=invoice.date,
                debit=debit,
                credit=credit,
                amount_currency=debit if debit else -credit,
            )
            created_lines += 1

    if total_amount <= 0:
        raise ValidationError("Invoice total must be greater than zero.")

    counterpart_debit_amount = total_amount if counterpart_debit else Decimal("0")
    counterpart_credit_amount = total_amount if not counterpart_debit else Decimal("0")

    MoveLine.objects.create(
        move=invoice,
        account=counterpart_account,
        partner=invoice.partner,
        currency=invoice.currency,
        name=invoice.reference or invoice.name or f"Invoice {invoice.id}",
        date=invoice.date,
        debit=counterpart_debit_amount,
        credit=counterpart_credit_amount,
        amount_currency=counterpart_debit_amount if counterpart_debit_amount else -counterpart_credit_amount,
    )
    created_lines += 1

    post_stats = post_move(move=invoice)
    post_stats["generated_lines"] = created_lines
    post_stats["invoice_total"] = str(total_amount)
    return post_stats


@transaction.atomic
def reverse_invoice_to_credit_note(*, invoice: Move, date=None, reason: str = "") -> Move:
    if invoice.move_type not in {"out_invoice", "in_invoice"}:
        raise ValidationError("Only customer invoices and vendor bills can be reversed from this action.")
    if invoice.state != "posted":
        raise ValidationError("Only posted invoices can be reversed.")

    reverse_move_type = "out_refund" if invoice.move_type == "out_invoice" else "in_refund"
    reverse_date = date or timezone.localdate()
    reverse_reference = f"Reversal of {invoice.name or invoice.id}"
    if reason:
        reverse_reference = f"{reverse_reference} - {reason}"

    credit_note = Move.objects.create(
        company=invoice.company,
        journal=invoice.journal,
        partner=invoice.partner,
        currency=invoice.currency,
        payment_term=invoice.payment_term,
        reference=reverse_reference,
        name="",
        invoice_date=reverse_date,
        date=reverse_date,
        state="draft",
        move_type=reverse_move_type,
        reversed_entry=invoice,
    )

    for line in invoice.invoice_lines.select_related("account", "tax").all():
        credit_note.invoice_lines.create(
            account=line.account,
            tax=line.tax,
            name=line.name,
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_percent=line.discount_percent,
        )

    return credit_note


@transaction.atomic
def create_debit_note_from_invoice(*, invoice: Move, date=None, reason: str = "") -> Move:
    if invoice.move_type not in {"out_invoice", "in_invoice"}:
        raise ValidationError("Only customer invoices and vendor bills can generate debit notes.")
    if invoice.state != "posted":
        raise ValidationError("Only posted invoices can generate debit notes.")

    debit_date = date or timezone.localdate()
    debit_reference = f"Debit note for {invoice.name or invoice.id}"
    if reason:
        debit_reference = f"{debit_reference} - {reason}"

    debit_note = Move.objects.create(
        company=invoice.company,
        journal=invoice.journal,
        partner=invoice.partner,
        currency=invoice.currency,
        payment_term=invoice.payment_term,
        reference=debit_reference,
        name="",
        invoice_date=debit_date,
        date=debit_date,
        state="draft",
        move_type=invoice.move_type,
        debit_origin=invoice,
        is_debit_note=True,
    )

    for line in invoice.invoice_lines.select_related("account", "tax").all():
        debit_note.invoice_lines.create(
            account=line.account,
            tax=line.tax,
            name=line.name,
            quantity=line.quantity,
            unit_price=line.unit_price,
            discount_percent=line.discount_percent,
        )

    return debit_note
