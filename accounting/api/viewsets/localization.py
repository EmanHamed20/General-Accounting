from .shared import *


class CountryViewSet(BaseModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer


class CountryStateViewSet(BaseModelViewSet):
    queryset = CountryState.objects.select_related("country").all().order_by("country__name", "name")
    serializer_class = CountryStateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset


class CountryCityViewSet(BaseModelViewSet):
    queryset = CountryCity.objects.select_related("country", "state").all().order_by("country__name", "name")
    serializer_class = CountryCitySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        state_id = self.request.query_params.get("state_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        return queryset


class CountryCurrencyViewSet(BaseModelViewSet):
    queryset = CountryCurrency.objects.select_related("country", "currency").all().order_by(
        "country__name", "-is_default", "currency__code"
    )
    serializer_class = CountryCurrencySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        currency_id = self.request.query_params.get("currency_id")
        is_default = self.request.query_params.get("is_default")
        active = self.request.query_params.get("active")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if currency_id:
            queryset = queryset.filter(currency_id=currency_id)
        if is_default is not None:
            queryset = queryset.filter(is_default=is_default.lower() in {"1", "true", "yes"})
        if active is not None:
            queryset = queryset.filter(active=active.lower() in {"1", "true", "yes"})
        return queryset
