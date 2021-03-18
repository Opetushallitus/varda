import datetime
import logging
import re

from functools import wraps
from celery import shared_task

from django.conf import settings
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q, IntegerField
from django.db.models.functions import Cast
from django.db.models.signals import post_save
from guardian.models import UserObjectPermission, GroupObjectPermission

from varda import oppijanumerorekisteri, koodistopalvelu
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.excel_export import delete_excel_reports_earlier_than
from varda.misc import flatten_nested_list, memory_efficient_queryset_iterator
from varda.models import (Henkilo, Taydennyskoulutus, Toimipaikka, Z6_RequestLog, Lapsi, Varhaiskasvatuspaatos,
                          Z4_CasKayttoOikeudet)
from varda.permissions import (assign_lapsi_permissions, assign_vakapaatos_vakasuhde_permissions,
                               assign_henkilo_permissions_for_vaka_groups,
                               assign_henkilo_permissions_for_tyontekija_groups)
from varda.permission_groups import assign_object_permissions_to_taydennyskoulutus_groups


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
    if settings.PRODUCTION_ENV or settings.QA_ENV:
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


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_taydennyskoulutus_permissions_for_all_toimipaikat_task(vakajarjestaja_oid, taydennyskoulutus_id):
    taydennyskoulutus = Taydennyskoulutus.objects.get(id=taydennyskoulutus_id)
    toimipaikka_oid_list = (Toimipaikka.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                            .values_list('organisaatio_oid', flat=True))
    [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
     for toimipaikka_oid in toimipaikka_oid_list]

    # Send post_save signal so that cache is updated
    post_save.send(Taydennyskoulutus, instance=taydennyskoulutus, created=True)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def after_data_import_task():
    """
    Task that is run in QA environment after data import.
    Currently updates the anonymized toimipaikat to organisaatiopalvelu.
    """
    if settings.PRODUCTION_ENV:
        logger.error('Running this task in production is not allowed!')
        return None

    # Push anonymized toimipaikat to organisaatiopalvelu
    toimipaikka_filter = Q(toimintamuoto_koodi__iexact='tm02') | Q(toimintamuoto_koodi__iexact='tm03')
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu(toimipaikka_filter=toimipaikka_filter)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_request_log_older_than_arg_days_task(days):
    timestamp_lower_limit = datetime.datetime.now() - datetime.timedelta(days=days)
    timestamp_lower_limit = timestamp_lower_limit.replace(tzinfo=datetime.timezone.utc)

    Z6_RequestLog.objects.filter(timestamp__lt=timestamp_lower_limit).delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def fix_orphan_vakatiedot_permissions():
    """
    Before Lapsi required vakatoimija-field, Vakajarjestaja-level permissions were set after first Varhaiskasvatussuhde
    was added for Lapsi (we got Vakajarjestaja via Toimipaikka). If Varhaiskasvatussuhde has not been created, there are
    Lapsi and Varhaiskasvatuspaatos objects that only users who created them have access to.

    Here we go through every such object and assign permissions for Vakajarjestaja groups if vakatoimija-field of Lapsi
    is filled.
    """
    lapsi_content_type_id = ContentType.objects.get_for_model(Lapsi).id
    orphan_lapsi_id_list = (UserObjectPermission.objects.filter(content_type=lapsi_content_type_id)
                            .annotate(object_id=Cast('object_pk', IntegerField()))
                            .distinct('object_id').values_list('object_id', flat=True))
    lapsi_qs = Lapsi.objects.filter(vakatoimija__isnull=False, id__in=orphan_lapsi_id_list).distinct()
    for lapsi in lapsi_qs:
        with transaction.atomic():
            UserObjectPermission.objects.filter(content_type=lapsi_content_type_id, object_pk=lapsi.id).delete()
            assign_lapsi_permissions(lapsi.vakatoimija.organisaatio_oid, lapsi)

    vakapaatos_content_type_id = ContentType.objects.get_for_model(Varhaiskasvatuspaatos).id
    orphan_vakapaatos_id_list = (UserObjectPermission.objects.filter(content_type=vakapaatos_content_type_id)
                                 .annotate(object_id=Cast('object_pk', IntegerField()))
                                 .distinct('object_id').values_list('object_id', flat=True))
    vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(lapsi__vakatoimija__isnull=False,
                                                         id__in=orphan_vakapaatos_id_list).distinct()
    for vakapaatos in vakapaatos_qs:
        with transaction.atomic():
            UserObjectPermission.objects.filter(content_type=vakapaatos_content_type_id, object_pk=vakapaatos.id).delete()
            assign_vakapaatos_vakasuhde_permissions(Varhaiskasvatuspaatos, vakapaatos.lapsi.vakatoimija.organisaatio_oid,
                                                    None, vakapaatos)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def modify_view_henkilo_permission():
    """
    Add view_henkilo permission to HUOLTAJATIETO_TALLENNUS and HUOLTAJATIETO_KATSELU groups
    Add object level permissions for Henkilo objects based on related Lapsi and Tyontekija objects
    """
    permission_name = 'view_henkilo'
    view_henkilo_permission = Permission.objects.get(codename=permission_name)

    # Add view_henkilo permission to huoltajatieto template groups
    huoltajatieto_template_group_names = ['vakajarjestaja_huoltajatiedot_tallentaja',
                                          'vakajarjestaja_huoltajatiedot_katselija',
                                          'toimipaikka_huoltajatiedot_tallentaja',
                                          'toimipaikka_huoltajatiedot_katselija']
    huoltajatieto_template_group_qs = Group.objects.filter(name__in=huoltajatieto_template_group_names)
    for huoltajatieto_template_group in huoltajatieto_template_group_qs:
        huoltajatieto_template_group.permissions.add(view_henkilo_permission)

    # Add view_henkilo permission to existing groups
    huoltajatieto_group_qs = Group.objects.filter(Q(name__startswith=Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA) |
                                                  Q(name__startswith=Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA))
    for huoltajatieto_group in huoltajatieto_group_qs:
        huoltajatieto_group.permissions.add(view_henkilo_permission)

    # Add object level permissions for existing Henkilo objects
    # Only assign permissions for those that have Lapsi and Tyontekija objects
    # (nobody has access to Henkilo of Huoltaja)
    henkilo_qs = Henkilo.objects.filter(Q(lapsi__isnull=False) | Q(tyontekijat__isnull=False)).order_by('id')
    for henkilo in memory_efficient_queryset_iterator(henkilo_qs):
        lapsi_nested_oid_list = henkilo.lapsi.values_list('vakatoimija__organisaatio_oid',
                                                          'oma_organisaatio__organisaatio_oid',
                                                          'paos_organisaatio__organisaatio_oid',
                                                          'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__organisaatio_oid',
                                                          'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid')
        lapsi_oid_list = flatten_nested_list(lapsi_nested_oid_list)
        lapsi_oid_set = set(lapsi_oid_list)
        lapsi_oid_set.discard(None)
        assign_henkilo_permissions_for_vaka_groups(lapsi_oid_set, henkilo)

        tyontekija_nested_oid_list = henkilo.tyontekijat.values_list('vakajarjestaja__organisaatio_oid',
                                                                     'palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid')
        tyontekija_oid_list = flatten_nested_list(tyontekija_nested_oid_list)
        tyontekija_oid_set = set(tyontekija_oid_list)
        tyontekija_oid_set.discard(None)
        assign_henkilo_permissions_for_tyontekija_groups(tyontekija_oid_set, henkilo)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_excel_reports_older_than_arg_hours_task(hours):
    timestamp_lower_limit = datetime.datetime.now() - datetime.timedelta(hours=hours)
    timestamp_lower_limit = timestamp_lower_limit.replace(tzinfo=datetime.timezone.utc)
    delete_excel_reports_earlier_than(timestamp_lower_limit)
