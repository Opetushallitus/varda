from django.core.management.base import BaseCommand
from varda.migrations.testing.setup import load_testing_data


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        load_testing_data()
