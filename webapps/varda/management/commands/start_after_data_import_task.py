from django.conf import settings
from django.core.management.base import BaseCommand

from varda.tasks import after_data_import_task


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        if not settings.QA_ENV:
            print('Error: The task must be run in QA.')
            return None

        after_data_import_task.delay()
