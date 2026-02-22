from datetime import date

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.services.report_service import (
    BalanceSheetOptions,
    GeneralLedgerOptions,
    ProfitAndLossOptions,
    TrialBalanceOptions,
    build_balance_sheet,
    build_general_ledger,
    build_profit_and_loss,
    build_trial_balance,
)


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


def _parse_date(value: str | None, field_name: str, default: date | None = None) -> date:
    if not value:
        if default is not None:
            return default
        raise DRFValidationError({field_name: "This query parameter is required."})
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise DRFValidationError({field_name: "Use YYYY-MM-DD format."}) from exc


def _parse_company_id(value: str | None) -> int:
    if not value:
        raise DRFValidationError({"company_id": "This query parameter is required."})
    try:
        return int(value)
    except ValueError as exc:
        raise DRFValidationError({"company_id": "Must be an integer."}) from exc


class BalanceSheetReportView(APIView):
    def get(self, request):
        company_id = _parse_company_id(request.query_params.get("company_id"))
        date_to = _parse_date(request.query_params.get("date_to"), "date_to", default=date.today())

        options = BalanceSheetOptions(
            company_id=company_id,
            date_to=date_to,
            posted_only=_parse_bool(request.query_params.get("posted_only"), default=True),
            include_current_year_earnings=_parse_bool(
                request.query_params.get("include_current_year_earnings"),
                default=True,
            ),
        )
        payload = build_balance_sheet(options)
        return Response(payload, status=status.HTTP_200_OK)


class ProfitAndLossReportView(APIView):
    def get(self, request):
        company_id = _parse_company_id(request.query_params.get("company_id"))
        date_to = _parse_date(request.query_params.get("date_to"), "date_to", default=date.today())
        default_date_from = date(date_to.year, 1, 1)
        date_from = _parse_date(request.query_params.get("date_from"), "date_from", default=default_date_from)
        if date_from > date_to:
            raise DRFValidationError({"date_from": "date_from must be <= date_to."})

        options = ProfitAndLossOptions(
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
            posted_only=_parse_bool(request.query_params.get("posted_only"), default=True),
        )
        payload = build_profit_and_loss(options)
        return Response(payload, status=status.HTTP_200_OK)


class TrialBalanceReportView(APIView):
    def get(self, request):
        company_id = _parse_company_id(request.query_params.get("company_id"))
        date_to = _parse_date(request.query_params.get("date_to"), "date_to", default=date.today())
        default_date_from = date(date_to.year, 1, 1)
        date_from = _parse_date(request.query_params.get("date_from"), "date_from", default=default_date_from)
        if date_from > date_to:
            raise DRFValidationError({"date_from": "date_from must be <= date_to."})

        options = TrialBalanceOptions(
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
            posted_only=_parse_bool(request.query_params.get("posted_only"), default=True),
            hide_zero_lines=_parse_bool(request.query_params.get("hide_zero_lines"), default=False),
        )
        payload = build_trial_balance(options)
        return Response(payload, status=status.HTTP_200_OK)


class GeneralLedgerReportView(APIView):
    def get(self, request):
        company_id = _parse_company_id(request.query_params.get("company_id"))
        date_to = _parse_date(request.query_params.get("date_to"), "date_to", default=date.today())
        default_date_from = date(date_to.year, 1, 1)
        date_from = _parse_date(request.query_params.get("date_from"), "date_from", default=default_date_from)
        if date_from > date_to:
            raise DRFValidationError({"date_from": "date_from must be <= date_to."})

        account_id_raw = request.query_params.get("account_id")
        account_id = None
        if account_id_raw:
            try:
                account_id = int(account_id_raw)
            except ValueError as exc:
                raise DRFValidationError({"account_id": "Must be an integer."}) from exc

        options = GeneralLedgerOptions(
            company_id=company_id,
            date_from=date_from,
            date_to=date_to,
            posted_only=_parse_bool(request.query_params.get("posted_only"), default=True),
            account_id=account_id,
            hide_zero_lines=_parse_bool(request.query_params.get("hide_zero_lines"), default=False),
        )
        payload = build_general_ledger(options)
        return Response(payload, status=status.HTTP_200_OK)
