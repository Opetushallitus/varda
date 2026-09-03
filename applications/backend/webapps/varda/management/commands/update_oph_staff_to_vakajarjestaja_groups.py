from django.core.management.base import BaseCommand

from varda.tasks import update_oph_staff_to_vakajarjestaja_groups


class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        update_oph_staff_to_vakajarjestaja_groups.delay()
