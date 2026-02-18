from django.urls import include, path

urlpatterns = [
    path("", include("accounting.api.routes.company")),
    path("", include("accounting.api.routes.configuration")),
    path("", include("accounting.api.routes.assets")),
    path("", include("accounting.api.routes.settings")),
    path("", include("accounting.api.routes.localization")),
    path("", include("accounting.api.routes.templates")),
    path("", include("accounting.api.routes.products")),
    path("", include("accounting.api.routes.entries")),
    path("", include("accounting.api.routes.invoicing")),
]
