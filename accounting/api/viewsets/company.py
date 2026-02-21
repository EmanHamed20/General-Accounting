from .shared import *


class CurrencyViewSet(BaseModelViewSet):
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer


class CompanyViewSet(BaseModelViewSet):
    queryset = Company.objects.all().order_by("name")
    serializer_class = CompanySerializer

    @action(detail=True, methods=["post"], url_path="apply-chart-template")
    def apply_chart_template(self, request, pk=None):
        company = self.get_object()
        serializer = ApplyChartTemplateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        country_id = serializer.validated_data["country_id"]
        country = Country.objects.filter(id=country_id).first()
        if not country:
            return Response({"country_id": "Country not found."}, status=status.HTTP_400_BAD_REQUEST)

        stats = apply_chart_template_to_company(company=company, country=country)
        return Response(stats, status=status.HTTP_200_OK)
