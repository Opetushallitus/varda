from django.conf import settings
from django.core.management.base import BaseCommand
from anonymizer.python.generate_anonymized_data import create_anonymized_data_dump


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-n", "--number_of_henkilot", type=int)

    def handle(self, *args, **options):
        if settings.PRODUCTION_ENV:
            print("Creating anonymized data in production is not allowed!")
            return None

        create_anonymized_data_dump()
