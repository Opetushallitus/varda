import re

from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.exceptions import NotFound


def get_full_path_without_page_number(request_full_path):
    path_without_page = re.sub('page=[0-9]+', '', request_full_path)
    path_without_page_and_double_chars = re.sub('&&', '&', path_without_page)
    return re.sub(r'[?&]*$', '', path_without_page_and_double_chars)  # also remove these characters from the end


def get_requested_page_and_query_params(request_query_params):
    requested_page = 1
    query_params = request_query_params.copy()  # otherwise immutable querydict
    try:
        requested_page = query_params['page']
        if not requested_page.isdigit() or int(requested_page) < 1:
            raise NotFound(detail='Invalid page.')
        query_params.pop('page')
        query_params.pop('ordering')
    except KeyError:
        pass

    query_param_dict = query_params.dict()
    query_param_dict_has_values = dict(filter(lambda x: x[1] != '', query_param_dict.items()))

    return {'requested_page': int(requested_page), 'query_params': query_param_dict_has_values}


class CustomDjangoPaginator(DjangoPaginator):
    def __init__(self, object_list, per_page, total_count):
        super().__init__(object_list, per_page, orphans=0,
                         allow_empty_first_page=True)
        self.total_count = total_count

    def validate_number(self, number):
        """
        Page number validation is done already earlier.
        Check get_requested_page() above.
        """
        return number

    def page(self, number):
        """Return a Page object for the given 1-based page number."""
        number = self.validate_number(number)
        bottom = 0  # Custom value: sliced queryset has per_page items in total (or less)
        top = self.per_page  # Custom value: sliced queryset has per_page items in total (or less)
        if top + self.orphans >= self.count:
            top = self.count
        return self._get_page(self.object_list[bottom:top], number, self)

    @cached_property
    def count(self):
        return self.total_count


class CustomPagination(PageNumberPagination):
    django_paginator_class = CustomDjangoPaginator
    invalid_page_message = 'Invalid page.'

    def paginate_queryset(self, queryset, request, view=None, queryset_total_count=0, page_size=20, page_number=1):
        paginator = self.django_paginator_class(queryset, page_size, queryset_total_count)
        try:
            self.page = paginator.page(page_number)
        except Exception as exc:
            msg = self.invalid_page_message.format(
                page_number=page_number, message=str(exc)
            )
            raise NotFound(msg)

        self.display_page_controls = True
        self.request = request
        return list(self.page)


class ChangeablePageSizePagination(PageNumberPagination):
    max_page_size = 100
    page_size_query_param = 'page_size'


class ChangeableReportingPageSizePagination(PageNumberPagination):
    max_page_size = 3000
    page_size_query_param = 'page_size'


class ChangeablePageSizePaginationLarge(ChangeablePageSizePagination):
    max_page_size = 500


class ChangeablePageSizeCursorPagination(CursorPagination):
    max_page_size = 100
    page_size_query_param = 'page_size'


class TimestampCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = '-timestamp'


class TimestampReverseCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = 'timestamp'


class DateCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = '-date'


class DateReverseCursorPagination(ChangeablePageSizeCursorPagination):
    ordering = 'date'
