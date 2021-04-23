import os

from django.conf import settings
from django.core.management.base import BaseCommand
from anonymizer.python.db_anonymizer import anonymize_data


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if settings.PRODUCTION_ENV:
            print('Anonymization is not allowed in production!')
            return None

        opintopolku_username = os.getenv('OPINTOPOLKU_USERNAME', None)
        opintopolku_password = os.getenv('OPINTOPOLKU_PASSWORD', None)
        if opintopolku_username is None or opintopolku_password is None:
            print('Env variables OPINTOPOLKU_USERNAME and OPINTOPOLKU_PASSWORD are needed.')
            return None

        anonymize_data()
