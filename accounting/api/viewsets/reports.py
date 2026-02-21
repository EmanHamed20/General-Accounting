from datetime import date

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounting.services.report_service import BalanceSheetOptions, build_balance_sheet


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "y"}


class BalanceSheetReportView(APIView):
    def get(self, request):
        company_id = request.query_params.get("company_id")
        if not company_id:
            raise DRFValidationError({"company_id": "This query parameter is required."})
        try:
            company_id = int(company_id)
        except ValueError as exc:
            raise DRFValidationError({"company_id": "Must be an integer."}) from exc

        date_to_raw = request.query_params.get("date_to")
        if date_to_raw:
            try:
                date_to = date.fromisoformat(date_to_raw)
            except ValueError as exc:
                raise DRFValidationError({"date_to": "Use YYYY-MM-DD format."}) from exc
        else:
            date_to = date.today()

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
