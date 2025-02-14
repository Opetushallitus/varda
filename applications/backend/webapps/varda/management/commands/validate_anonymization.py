import logging

from django.core.management.base import BaseCommand
from anonymizer.python.validate_anonymization import validate_anonymization


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        validate_anonymization()
