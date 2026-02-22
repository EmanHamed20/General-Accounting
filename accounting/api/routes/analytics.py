from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounting.api.viewsets import (
    AnalyticAccountViewSet,
    AnalyticItemViewSet,
    AnalyticDistributionModelLineViewSet,
    AnalyticDistributionModelViewSet,
    AnalyticPlanViewSet,
)

router = DefaultRouter()
router.register("analytic-items", AnalyticItemViewSet, basename="analytic-item")
router.register("analytic-plans", AnalyticPlanViewSet, basename="analytic-plan")
router.register("analytic-accounts", AnalyticAccountViewSet, basename="analytic-account")
router.register("analytic-distribution-models", AnalyticDistributionModelViewSet, basename="analytic-distribution-model")
router.register("analytic-distribution-model-lines", AnalyticDistributionModelLineViewSet, basename="analytic-distribution-model-line")

urlpatterns = [
    path("", include(router.urls)),
]
