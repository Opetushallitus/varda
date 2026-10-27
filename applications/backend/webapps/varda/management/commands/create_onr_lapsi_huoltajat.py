import logging

from django.core.management.base import BaseCommand

from varda.tasks import create_onr_lapsi_huoltajat_task

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        logger.info("Starting to create ONR-lapsi-huoltajat.")
        create_onr_lapsi_huoltajat_task.delay()
