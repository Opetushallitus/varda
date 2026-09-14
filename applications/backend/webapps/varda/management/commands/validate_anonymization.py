import logging

from anonymizer.python.validate_anonymization import validate_anonymization
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        validate_anonymization()
