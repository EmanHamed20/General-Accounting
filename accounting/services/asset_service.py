from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.db import transaction

from accounting.models import Asset, AssetDepreciationLine, Move, MoveLine


# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════

def _round(value: Decimal) -> Decimal:
    """تقريب لـ 6 خانات عشرية — نفس الـ DecimalField في الموديل"""
    return value.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


# ══════════════════════════════════════════════════════════════
# STEP 1 — حساب جدول الإهلاك (بدون حفظ في الداتابيز)
# ══════════════════════════════════════════════════════════════

def compute_depreciation_board(asset: Asset) -> list[dict]:
    """
    يحسب جدول الإهلاك الكامل ويرجعه كـ list of dicts.
    مش بيحفظ أي حاجة — بس بيحسب.

    يدعم:
      - linear    : إهلاك قسط ثابت
      - degressive: إهلاك متناقص (Double Declining Balance)
    """
    if asset.original_value <= 0:
        raise ValidationError("Original value must be positive.")

    depreciable = _round(asset.original_value - asset.salvage_value)

    if depreciable <= 0:
        raise ValidationError(
            "Nothing to depreciate: original_value equals salvage_value."
        )

    if asset.method_number <= 0:
        raise ValidationError("method_number must be greater than zero.")

    start_date = asset.first_depreciation_date or asset.acquisition_date
    lines: list[dict] = []

    # ── Linear ──────────────────────────────────────────────────
    if asset.method == "linear":
        amount_per = _round(depreciable / Decimal(asset.method_number))
        depreciated_so_far = Decimal("0")

        for seq in range(1, asset.method_number + 1):
            # آخر سطر: نحط الباقي بالضبط عشان نتجنب فروق التقريب
            if seq == asset.method_number:
                amount = _round(depreciable - depreciated_so_far)
            else:
                amount = amount_per

            residual = _round(depreciable - depreciated_so_far - amount)

            lines.append({
                "sequence":          seq,
                "date":              start_date + relativedelta(months=asset.method_period * (seq - 1)),
                "amount":            amount,
                "depreciated_value": _round(depreciated_so_far),
                "residual_value":    max(residual, Decimal("0")),
            })

            depreciated_so_far += amount

    # ── Degressive (Double Declining Balance) ───────────────────
    elif asset.method == "degressive":
        # معدل = (1 / عدد الفترات) * 2
        rate = _round(Decimal("2") / Decimal(asset.method_number))
        residual = depreciable
        depreciated_so_far = Decimal("0")

        for seq in range(1, asset.method_number + 1):
            # آخر سطر: نمسح الباقي كله
            if seq == asset.method_number:
                amount = _round(residual)
            else:
                amount = _round(residual * rate)

            residual = _round(residual - amount)

            lines.append({
                "sequence":          seq,
                "date":              start_date + relativedelta(months=asset.method_period * (seq - 1)),
                "amount":            amount,
                "depreciated_value": _round(depreciated_so_far),
                "residual_value":    max(residual, Decimal("0")),
            })

            depreciated_so_far += amount

    else:
        raise ValidationError(f"Unknown depreciation method: '{asset.method}'.")

    return lines


# ══════════════════════════════════════════════════════════════
# STEP 2 — حفظ جدول الإهلاك في الداتابيز
# ══════════════════════════════════════════════════════════════

@transaction.atomic
def generate_depreciation_lines(asset: Asset) -> dict:
    """
    1. يتحقق إن الأصل في حالة تسمح بالحساب
    2. يمسح الـ draft lines القديمة
    3. يحسب الجدول الجديد
    4. يحفظه في الداتابيز

    الـ posted lines مش بتتمسح أبداً.
    """
    if asset.state in {"closed", "cancelled"}:
        raise ValidationError(
            "Cannot compute depreciation for a closed or cancelled asset."
        )

    # تحقق إن مفيش posted lines — مش ممكن نعيد الحساب لو في lines اتنفذت
    posted_count = asset.depreciation_lines.filter(state="posted").count()
    if posted_count > 0:
        raise ValidationError(
            f"Asset has {posted_count} posted depreciation line(s). "
            "Reset posted lines before recomputing."
        )

    # امسح الـ draft القديمة بس
    deleted_count, _ = asset.depreciation_lines.filter(state="draft").delete()

    # احسب الجدول
    board = compute_depreciation_board(asset)

    # احفظ في الداتابيز
    created_count = 0
    for line_data in board:
        line = AssetDepreciationLine(asset=asset, state="draft", **line_data)
        line.full_clean()
        line.save()
        created_count += 1

    return {
        "deleted": deleted_count,
        "created": created_count,
        "total_depreciation": str(sum(d["amount"] for d in board)),
    }


# ══════════════════════════════════════════════════════════════
# STEP 3 — Post سطر إهلاك (إنشاء القيد المحاسبي)
# ══════════════════════════════════════════════════════════════

@transaction.atomic
def post_depreciation_line(line: AssetDepreciationLine) -> dict:
    """
    1. ينشئ Move (قيد محاسبي)
    2. ينشئ سطرين في المحاسبة:
         مدين  → expense_account      (مصروف الإهلاك)
         دائن  → depreciation_account (مجمع الإهلاك)
    3. يعمل post للـ Move
    4. يربط الـ Move بالـ line ويغير state → posted
    """
    asset = line.asset

    if line.state == "posted":
        raise ValidationError("This depreciation line is already posted.")

    # تحقق من البيانات المطلوبة على الأصل
    if not asset.journal_id:
        raise ValidationError(
            "Asset must have a journal assigned before posting depreciation."
        )
    if not asset.depreciation_account_id:
        raise ValidationError(
            "Asset must have a depreciation account assigned before posting."
        )
    if not asset.expense_account_id:
        raise ValidationError(
            "Asset must have an expense account assigned before posting."
        )

    # ── إنشاء الـ Move ──────────────────────────────────────────
    move = Move(
        company=asset.company,
        journal=asset.journal,
        partner=asset.partner,
        currency=asset.currency,
        date=line.date,
        move_type="entry",
        state="draft",
        name=f"Depreciation – {asset.name} (seq {line.sequence})",
    )
    move.full_clean()
    move.save()

    # ── مدين: مصروف الإهلاك ────────────────────────────────────
    debit_line = MoveLine(
        move=move,
        account=asset.expense_account,
        date=line.date,
        debit=line.amount,
        credit=Decimal("0"),
        name=f"Depreciation expense – {asset.name}",
    )
    debit_line.full_clean()
    debit_line.save()

    # ── دائن: مجمع الإهلاك ─────────────────────────────────────
    credit_line = MoveLine(
        move=move,
        account=asset.depreciation_account,
        date=line.date,
        debit=Decimal("0"),
        credit=line.amount,
        name=f"Accumulated depreciation – {asset.name}",
    )
    credit_line.full_clean()
    credit_line.save()

    # ── Post الـ Move ───────────────────────────────────────────
    from accounting.services.move_service import post_move
    post_move(move=move)

    # ── ربط الـ Move بالـ Line ──────────────────────────────────
    line.move = move
    line.state = "posted"
    line.full_clean()
    line.save()

    return {
        "line_id":  line.id,
        "move_id":  move.id,
        "sequence": line.sequence,
        "amount":   str(line.amount),
        "date":     str(line.date),
        "state":    line.state,
    }


# ══════════════════════════════════════════════════════════════
# STEP 4 — إدارة State الأصل
# ══════════════════════════════════════════════════════════════

@transaction.atomic
def set_asset_running(asset: Asset) -> Asset:
    """draft → running"""
    if asset.state != "draft":
        raise ValidationError(
            f"Cannot set to running: asset is '{asset.state}', expected 'draft'."
        )
    asset.state = "running"
    asset.full_clean()
    asset.save()
    return asset


@transaction.atomic
def pause_asset(asset: Asset) -> Asset:
    """running → paused"""
    if asset.state != "running":
        raise ValidationError(
            f"Cannot pause: asset is '{asset.state}', expected 'running'."
        )
    asset.state = "paused"
    asset.full_clean()
    asset.save()
    return asset


@transaction.atomic
def resume_asset(asset: Asset) -> Asset:
    """paused → running"""
    if asset.state != "paused":
        raise ValidationError(
            f"Cannot resume: asset is '{asset.state}', expected 'paused'."
        )
    asset.state = "running"
    asset.full_clean()
    asset.save()
    return asset


@transaction.atomic
def close_asset(asset: Asset) -> Asset:
    """
    running → closed
    بيتحقق إن كل الـ depreciation lines اتعملت post قبل الإغلاق.
    """
    if asset.state != "running":
        raise ValidationError(
            f"Cannot close: asset is '{asset.state}', expected 'running'."
        )

    pending = asset.depreciation_lines.filter(state="draft").count()
    if pending > 0:
        raise ValidationError(
            f"Cannot close asset: {pending} depreciation line(s) are still in draft."
        )

    asset.state = "closed"
    asset.full_clean()
    asset.save()
    return asset


@transaction.atomic
def cancel_asset(asset: Asset) -> Asset:
    """
    draft / paused → cancelled
    مش ممكن تلغي أصل running أو closed.
    """
    if asset.state in {"running", "closed"}:
        raise ValidationError(
            f"Cannot cancel a '{asset.state}' asset. "
            "Pause or close it first."
        )
    if asset.state == "cancelled":
        raise ValidationError("Asset is already cancelled.")

    asset.state = "cancelled"
    asset.full_clean()
    asset.save()
    return asset