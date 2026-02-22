from .shared import *


class CurrencyViewSet(BaseModelViewSet):
    queryset = Currency.objects.all().order_by("code")
    serializer_class = CurrencySerializer


class CompanyViewSet(BaseModelViewSet):
    queryset = Company.objects.all().order_by("name")
    serializer_class = CompanySerializer

    @action(detail=True, methods=["post"], url_path="update-info")
    def update_info(self, request, pk=None):
        company = self.get_object()
        allowed = {
            "name",
            "code",
            "legal_name",
            "email",
            "phone",
            "mobile",
            "website",
            "street",
            "street2",
            "city",
            "zip",
            "country",
            "state",
            "vat",
            "lock_date",
        }
        payload = {k: v for k, v in request.data.items() if k in allowed}
        serializer = self.get_serializer(company, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="update-mail-layout")
    def update_mail_layout(self, request, pk=None):
        company = self.get_object()
        allowed = {"email_header_color", "email_button_color"}
        payload = {k: v for k, v in request.data.items() if k in allowed}
        if not payload:
            return Response(
                {"detail": "Provide email_header_color and/or email_button_color."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(company, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="configure-document-layout")
    def configure_document_layout(self, request, pk=None):
        company = self.get_object()
        allowed = {
            "document_layout",
            "report_header",
            "report_footer",
            "company_details",
            "logo_url",
            "logo_web_url",
        }
        payload = {k: v for k, v in request.data.items() if k in allowed}
        serializer = self.get_serializer(company, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        record = serializer.save()
        return Response(self.get_serializer(record).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="preview-document")
    def preview_document(self, request, pk=None):
        company = self.get_object()
        return Response(
            {
                "company": self.get_serializer(company).data,
                "preview": {
                    "layout": company.document_layout,
                    "header": company.report_header,
                    "footer": company.report_footer,
                    "company_details": company.company_details,
                    "logo_url": company.logo_url,
                    "logo_web_url": company.logo_web_url,
                },
            },
            status=status.HTTP_200_OK,
        )

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
