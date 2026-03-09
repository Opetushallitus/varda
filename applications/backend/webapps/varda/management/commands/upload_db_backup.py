from django.core.management.base import BaseCommand
from varda.misc import upload_backup_to_allas


class Command(BaseCommand):
    help = "Upload DB backup to Allas bucket"

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="File path")

    def handle(self, *args, **kwargs):
        file_path = kwargs["file_path"]
        upload_backup_to_allas(file_path)
