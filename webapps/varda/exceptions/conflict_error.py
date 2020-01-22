from django.utils.translation import ugettext_lazy as _

from rest_framework.exceptions import APIException
from rest_framework import status


class ConflictError(APIException):
    default_detail = _('Conflict error.')
    default_code = 'conflict'

    def __init__(self, detail=None, code=None, status_code=status.HTTP_409_CONFLICT):
        if detail is None:
            detail = self.default_detail

        if code is None:
            code = self.default_code

        self.detail = detail
        self.code = code
        self.status_code = status_code
