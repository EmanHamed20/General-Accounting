from django.urls import include, path

try:
    from rest_framework.routers import DefaultRouter
    from accounting.api.viewsets import SessionViewSet
except ImportError:
    # JWT/session API is optional in local dev if simplejwt is not installed.
    urlpatterns = []
else:
    if SessionViewSet is None:
        urlpatterns = []
    else:
        router = DefaultRouter()
        router.register("session", SessionViewSet, basename="session")
        urlpatterns = [
            path("", include(router.urls)),
        ]
