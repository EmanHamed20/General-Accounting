from .shared import *


class AccountGroupTemplateViewSet(BaseModelViewSet):
    queryset = AccountGroupTemplate.objects.select_related("country", "parent").all().order_by(
        "country__name", "code_prefix_start", "id"
    )
    serializer_class = AccountGroupTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        return queryset


class AccountTemplateViewSet(BaseModelViewSet):
    queryset = AccountTemplate.objects.select_related("country", "group").all().order_by("country__name", "code")
    serializer_class = AccountTemplateSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        country_id = self.request.query_params.get("country_id")
        group_id = self.request.query_params.get("group_id")
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        if group_id:
            queryset = queryset.filter(group_id=group_id)
        return queryset
