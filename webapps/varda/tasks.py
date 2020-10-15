import logging
import re
from functools import wraps

from django.core.cache import cache
from celery import shared_task
from django.contrib.contenttypes.models import ContentType
from django.core.management import call_command
from django.db.models import Q
from guardian.models import UserObjectPermission, GroupObjectPermission

from varda import oppijanumerorekisteri, koodistopalvelu
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.models import Henkilo, Taydennyskoulutus
from varda.permission_groups import assign_object_permissions_to_taydennyskoulutus_groups


# Get an instance of a logger
logger = logging.getLogger(__name__)


def single_instance_task(timeout_in_minutes=8 * 60):
    """
    Decorator for celery task lock. Does not allow executing same task again if it's already running with matching id.
    Note: Uses django memcached as non persistent storage which could be culled or crash losing all locks!
    Note: Relies that task execution time is less than given timeout
    Note: Args should be ids that contain no whitespaces since those will be parsed off
    :param timeout_in_minutes: Time in minutes when lock will be released at latest. Should be greater than maximum task run time.
    :return: Decorated function
    """
    def decorator(func):
        @wraps(func)  # preserves func.__name__
        def decorator_wrapper(*args, **kwargs):
            arg_values = '{}{}'.format(args, kwargs)
            cache_key_suffix = re.sub(r'\s+', '', arg_values)  # whitespaces are not allowed in cache keys
            lock_id = 'celery-single-instance-{}-{}'.format(func.__name__, cache_key_suffix)
            lock_timeout_in_seconds = timeout_in_minutes * 60
            if cache.add(lock_id, 'true', lock_timeout_in_seconds):  # 'true' is never used value for the key
                try:
                    func(*args, **kwargs)
                finally:
                    cache.delete(lock_id)
            else:
                logger.error('Task already running with lock_id {}'.format(lock_id))
        return decorator_wrapper
    return decorator


@shared_task
@single_instance_task(timeout_in_minutes=1)
def add(x, y):
    """
    This is currently only needed for testing, don't remove!
    """
    return x + y


"""
Use acks_late=True for the task-decoration, unless periodic task which always gets called with the same arguments.
"""


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def run_management_commands():
    """
    To be run periodically, e.g. to clean out expired sessions
    """
    call_command('clearsessions', verbosity=0)
    call_command('django_cas_ng_clean_sessions', verbosity=0)


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def remove_all_auth_tokens():
    from rest_framework.authtoken.models import Token
    Token.objects.all().delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_oph_staff_to_vakajarjestaja_groups():
    permission_groups.add_oph_staff_to_vakajarjestaja_katselija_groups()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_vakajarjestajat():
    organisaatiopalvelu.fetch_organisaatio_info()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_modified_henkilot():
    oppijanumerorekisteri.fetch_and_update_modified_henkilot()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_toimipaikat_in_organisaatiopalvelu_task():
    organisaatiopalvelu.update_toimipaikat_in_organisaatiopalvelu()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def fetch_huoltajat_task():
    oppijanumerorekisteri.fetch_huoltajat()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_all_organisaatio_service_originated_organisations_task():
    """
    Updates all organisations which data is managed by organisaatio service
    :return: None
    """
    organisaatiopalvelu.update_all_organisaatio_service_organisations()


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def update_henkilot_with_oid():
    oppijanumerorekisteri.fetch_henkilot_with_oid()


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def update_henkilo_data_by_oid(henkilo_oid, henkilo_id, is_fetch_huoltajat=False):
    oppijanumerorekisteri.fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id)
    if is_fetch_huoltajat:
        oppijanumerorekisteri.update_huoltajuussuhde(henkilo_oid)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_huoltajasuhteet_task():
    """
    Updates huoltajasuhde changes from oppijanumerorekisteri
    :return: None
    """
    oppijanumerorekisteri.update_huoltajuussuhteet()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def send_audit_log_to_aws_task():
    audit_log.collect_audit_log_and_send_to_aws()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def guardian_clean_orphan_objects():
    # from guardian.utils import clean_orphan_obj_perms
    # clean_orphan_obj_perms() - We do not want to run this currently.
    pass


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def change_paos_tallentaja_organization_task(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                             tallentaja_organisaatio_id, voimassa_kytkin):
    permissions.change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                                    tallentaja_organisaatio_id, voimassa_kytkin)


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_object_permissions_explicitly_task(content_type_id, instance_id):
    """
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    content_type = ContentType.objects.get(id=content_type_id)
    filters = Q(content_type=content_type, object_pk=str(instance_id))
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_koodistot_task():
    koodistopalvelu.update_koodistot()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def remove_address_information_from_tyontekijat_only_task():
    henkilot = Henkilo.objects.filter(~Q(kotikunta_koodi='') | ~Q(katuosoite='') |
                                      ~Q(postinumero='') | ~Q(postitoimipaikka=''),
                                      huoltaja__isnull=True, tyontekijat__isnull=False).distinct()

    # Loop through each Henkilo so that save signals are processed correctly
    for henkilo in henkilot:
        henkilo.remove_address_information()
        henkilo.save()


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_taydennyskoulutus_permissions_for_toimipaikka_task(vakajarjestaja_oid, toimipaikka_oid):
    """
    Assign object level permissions to all taydennyskoulutukset of given vakajarjestaja for toimipaikka level groups
    :param vakajarjestaja_oid: OID of vakajarjestaja
    :param toimipaikka_oid: OID of toimipaikka
    """
    taydennyskoulutukset = Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
    [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
     for taydennyskoulutus in taydennyskoulutukset
     ]
