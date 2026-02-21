from django.urls import path

from accounting.api.viewsets import BalanceSheetReportView

urlpatterns = [
    path("reports/balance-sheet/", BalanceSheetReportView.as_view(), name="balance-sheet-report"),
]
