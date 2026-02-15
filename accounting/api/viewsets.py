from rest_framework import viewsets

from accounting.models import Country, CountryCity, CountryState

from .serializers import CountryCitySerializer, CountrySerializer, CountryStateSerializer


class CountryViewSet(viewsets.ModelViewSet):
    queryset = Country.objects.all().order_by("name")
    serializer_class = CountrySerializer


class CountryStateViewSet(viewsets.ModelViewSet):
    queryset = CountryState.objects.select_related("country").all().order_by("country__name", "name")
    serializer_class = CountryStateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset


class CountryCityViewSet(viewsets.ModelViewSet):
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
