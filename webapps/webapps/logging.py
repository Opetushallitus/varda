import logging

from django.conf import settings

from varda.helper_functions import hide_hetu


class ProductionFilter(logging.Filter):
    def filter(self, record):
        return settings.PRODUCTION_ENV


class SensitiveFormatter(logging.Formatter):
    def format(self, record):
        formatted_record = super(SensitiveFormatter, self).format(record)
        return hide_hetu(formatted_record, hide_date=False)
