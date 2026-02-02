from rest_framework.pagination import CursorPagination, PageNumberPagination
from rest_framework.response import Response
from collections import OrderedDict


class ChangeablePageSizeCursorPagination(CursorPagination):
    """
    Cursor pagination with cached queryset-count for better performance
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "id"

    def get_paginated_response(self, data):
        response_dict = OrderedDict(
            [
                ("count", getattr(self, "_queryset_count", 0)),
                ("next", self.get_next_link()),
                ("previous", self.get_previous_link()),
                ("results", data),
            ]
        )
        return Response(response_dict)


class ChangeablePageSizeCursorPaginationLarge(ChangeablePageSizeCursorPagination):
    max_page_size = 500


class ChangeablePageSizeCursorPaginationVeryLarge(ChangeablePageSizeCursorPagination):
    max_page_size = 3000


class IdCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = "-id"


class DateCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = "-date"


class DateReverseCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = "date"


class HistoricalCursorPagination(ChangeablePageSizeCursorPaginationLarge):
    ordering = ("id", "-history_date")


class HistoricalLargePagination(HistoricalCursorPagination):
    max_page_size = 10000


class UiNestedToimipaikkaNameOrderingCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = "nimi"


class UiHenkiloBasicNameOrderingCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("sukunimi", "etunimet")


class UiHenkiloNameOrderingCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("henkilo_sukunimi", "henkilo_etunimet", "id")


class UiYksiloimattomatChangeablePageSizeCursorPaginationLarge(ChangeablePageSizeCursorPagination):
    max_page_size = 500
    ordering = ("lapsi__vakatoimija__organisaatio_oid", "tyontekijat__vakajarjestaja__organisaatio_oid")


class TransferOutageCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("last_successful_max", "last_unsuccessful_max")


class RequestSummaryCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("-ratio", "-unsuccessful_count", "-summary_date", "id")


class RequestSummaryGroupCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("-ratio", "-unsuccessful_count", "id")


class ChangeablePageSizePagination(PageNumberPagination):
    max_page_size = 100
    page_size_query_param = "page_size"


class ChangeableReportingPageSizePagination(PageNumberPagination):
    max_page_size = 3000
    page_size_query_param = "page_size"


# Testing
class TestMaksutietoOrderCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = ("perheen_koko", "id")
