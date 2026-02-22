from django.urls import path

from accounting.api.viewsets import (
    BalanceSheetReportView,
    GeneralLedgerReportView,
    ProfitAndLossReportView,
    TrialBalanceReportView,
)

urlpatterns = [
    path("reports/balance-sheet/", BalanceSheetReportView.as_view(), name="balance-sheet-report"),
    path("reports/profit-and-loss/", ProfitAndLossReportView.as_view(), name="profit-and-loss-report"),
    path("reports/trial-balance/", TrialBalanceReportView.as_view(), name="trial-balance-report"),
    path("reports/general-ledger/", GeneralLedgerReportView.as_view(), name="general-ledger-report"),
]
