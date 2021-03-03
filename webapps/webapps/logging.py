import logging

from django.conf import settings


class ProductionFilter(logging.Filter):
    def filter(self, record):
        return settings.PRODUCTION_ENV
