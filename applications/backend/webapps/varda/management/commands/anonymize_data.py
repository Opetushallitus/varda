import logging

from anonymizer.python.db_anonymizer import anonymize_data
from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if settings.PRODUCTION_ENV:
            logger.error("Anonymization is not allowed in production!")
            return None

        anonymize_data()
