from django.core.management.base import BaseCommand
from django.conf import settings
from varda.misc import upload_lampi_export


class Command(BaseCommand):
    help = "Upload export csvs to Lampi"

    def add_arguments(self, parser):
        parser.add_argument("--files", nargs="*", help="file list", default=[], type=str)

    def handle(self, *args, **kwargs):
        files = kwargs["files"]
        if settings.PRODUCTION_ENV or settings.QA_ENV:
            upload_lampi_export(files)
