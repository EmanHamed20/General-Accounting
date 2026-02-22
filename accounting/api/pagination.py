from rest_framework.pagination import PageNumberPagination


class StandardListPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

    def paginate_queryset(self, queryset, request, view=None):
        # Make pagination opt-in: when page is omitted, return full dataset.
        if request.query_params.get(self.page_query_param) in (None, ""):
            return None
        return super().paginate_queryset(queryset, request, view=view)
