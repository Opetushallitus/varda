import datetime
import logging
import re

from functools import wraps
from celery import shared_task

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.db.models import Q, IntegerField, Count, Case, When, DateField, Func, F, Value
from django.db.models.functions import Cast
from django.db.models.signals import post_save
from django.utils import timezone
from guardian.models import UserObjectPermission, GroupObjectPermission

from varda import oppijanumerorekisteri, koodistopalvelu
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.excel_export import delete_excel_reports_earlier_than
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat
from varda.misc import memory_efficient_queryset_iterator, get_user_vakajarjestaja
from varda.models import (Henkilo, Taydennyskoulutus, Toimipaikka, Z6_RequestLog, Lapsi, Varhaiskasvatuspaatos,
                          Huoltaja, Huoltajuussuhde, Maksutieto, PidempiPoissaolo, Z6_LastRequest,
                          Z6_RequestSummary, Z6_RequestCount, Aikaleima)
from varda.permissions import (assign_object_level_permissions_for_instance, assign_lapsi_henkilo_permissions,
                               delete_object_permissions_explicitly, delete_permissions_from_object_instance_by_oid)
from varda.permission_groups import (assign_object_permissions_to_taydennyskoulutus_groups,
                                     assign_object_level_permissions, assign_object_permissions_to_tyontekija_groups,
                                     get_all_permission_groups_for_organization, assign_permissions_for_toimipaikka)

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
def create_onr_lapsi_huoltajat_task():
    create_onr_lapsi_huoltajat(create_all_vakajarjestajat=True)


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
def send_alive_log_to_aws_task():
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        audit_log.send_alive_log_to_aws()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def guardian_clean_orphan_object_permissions():
    """
    Delete orphan permission instances that were not deleted for some reason when object was deleted
    """
    for permission_model in (UserObjectPermission, GroupObjectPermission,):
        permission_qs = (permission_model.objects
                         .distinct('object_pk', 'content_type')
                         .order_by('object_pk', 'content_type'))
        for permission in memory_efficient_queryset_iterator(permission_qs, chunk_size=2000):
            model_class = permission.content_type.model_class()
            if not model_class.objects.filter(id=permission.object_pk).exists():
                delete_object_permissions_explicitly(model_class, permission.object_pk)


@shared_task(acks_late=True)
@single_instance_task(timeout_in_minutes=8 * 60)
def change_paos_tallentaja_organization_task(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                             tallentaja_organisaatio_id, voimassa_kytkin):
    permissions.change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id,
                                                    tallentaja_organisaatio_id, voimassa_kytkin)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_koodistot_task():
    koodistopalvelu.update_koodistot()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def remove_address_information_from_tyontekijat_only_task():
    henkilot = Henkilo.objects.filter(~Q(kotikunta_koodi='') | ~Q(katuosoite='') |
                                      ~Q(postinumero='') | ~Q(postitoimipaikka=''),
                                      huoltaja__isnull=True, lapsi__isnull=True, tyontekijat__isnull=False).distinct()

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
            assign_object_level_permissions_for_instance(lapsi, (lapsi.vakatoimija.organisaatio_oid,))

    vakapaatos_content_type_id = ContentType.objects.get_for_model(Varhaiskasvatuspaatos).id
    orphan_vakapaatos_id_list = (UserObjectPermission.objects.filter(content_type=vakapaatos_content_type_id)
                                 .annotate(object_id=Cast('object_pk', IntegerField()))
                                 .distinct('object_id').values_list('object_id', flat=True))
    vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(lapsi__vakatoimija__isnull=False,
                                                         id__in=orphan_vakapaatos_id_list).distinct()
    for vakapaatos in vakapaatos_qs:
        with transaction.atomic():
            UserObjectPermission.objects.filter(content_type=vakapaatos_content_type_id, object_pk=vakapaatos.id).delete()
            assign_object_level_permissions_for_instance(vakapaatos, (vakapaatos.lapsi.vakatoimija.organisaatio_oid,))


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_excel_reports_older_than_arg_hours_task(hours):
    timestamp_lower_limit = datetime.datetime.now() - datetime.timedelta(hours=hours)
    timestamp_lower_limit = timestamp_lower_limit.replace(tzinfo=datetime.timezone.utc)
    delete_excel_reports_earlier_than(timestamp_lower_limit)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_toimipaikka_in_organisaatiopalvelu_by_id_task(toimipaikka_id):
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu(toimipaikka_filter=Q(pk=toimipaikka_id))


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def force_update_toimipaikat_in_organisaatiopalvelu_task():
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def remove_birthdate_from_huoltajat_only_task():
    henkilo_qs = Henkilo.objects.filter(syntyma_pvm__isnull=False, huoltaja__isnull=False,
                                        tyontekijat__isnull=True, lapsi__isnull=True).distinct()

    # Loop through each Henkilo so that save signals are processed correctly
    for henkilo in memory_efficient_queryset_iterator(henkilo_qs):
        henkilo.syntyma_pvm = None
        henkilo.save()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_huoltajat_without_relations_task():
    """
    Task that deletes Huoltaja objects that have no relations to Lapsi (Lapsi has been deleted).
    """
    huoltaja_qs = Huoltaja.objects.filter(huoltajuussuhteet__isnull=True)
    huoltaja_qs.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_henkilot_without_relations_task():
    """
    Task that deletes Henkilo objects without relations to Lapsi, Huoltaja or Tyontekija objects. Henkilo object must
    be older than certain limit, so recently created objects are not deleted.
    """
    created_datetime_limit = timezone.now() - datetime.timedelta(days=90)
    henkilo_qs = Henkilo.objects.filter(lapsi__isnull=True, tyontekijat__isnull=True, huoltaja__isnull=True,
                                        luonti_pvm__lt=created_datetime_limit)
    for henkilo in henkilo_qs:
        henkilo.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_lapsi_objects_without_vakatoimija():
    """
    Delete non-PAOS Lapsi objects that do not have vakatoimija and have not related Varhaiskasvatuspaatos,
    Varhaiskasvatussuhde or Maksutieto objects.

    TEMPORARY FUNCTION
    """
    lapsi_qs = Lapsi.objects.filter(vakatoimija__isnull=True, oma_organisaatio__isnull=True,
                                    paos_organisaatio__isnull=True, varhaiskasvatuspaatokset__isnull=True,
                                    huoltajuussuhteet__maksutiedot__isnull=True).distinct('id')
    for lapsi in memory_efficient_queryset_iterator(lapsi_qs):
        Huoltajuussuhde.objects.filter(lapsi=lapsi).delete()
        lapsi.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def delete_lapsi_huoltaja_lapsi_objects():
    """
    Deletes Lapsi objects that do not have any related information if Henkilo is also huoltaja

    TEMPORARY FUNCTION
    """
    henkilo_qs = Henkilo.objects.filter(lapsi__isnull=False, huoltaja__isnull=False).order_by('id')
    for henkilo in memory_efficient_queryset_iterator(henkilo_qs):
        for lapsi in henkilo.lapsi.filter(varhaiskasvatuspaatokset__isnull=True,
                                          huoltajuussuhteet__maksutiedot__isnull=True).distinct('id'):
            Huoltajuussuhde.objects.filter(lapsi=lapsi).delete()
            lapsi.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_henkilo_information_for_lapsi_huoltaja():
    """
    Some Henkilo objects are related to Lapsi and Huoltaja objects, and syntyma_pvm has previously been removed from
    Huoltaja objects even if Henkilo also has Lapsi object.

    TEMPORARY FUNCTION
    """
    henkilo_qs = Henkilo.objects.filter(lapsi__isnull=False, syntyma_pvm__isnull=True)
    for henkilo in memory_efficient_queryset_iterator(henkilo_qs):
        update_henkilo_data_by_oid(henkilo.henkilo_oid, henkilo.id)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_toimipaikka_maksutieto_permissions():
    """
    Reassign permissions for Maksutieto objects of non-PAOS lapset on Toimipaikka level. Toimipaikka may not have
    permissions to Maksutieto if Varhaiskasvatussuhde was created after Maksutieto.

    TEMPORARY FUNCTION
    """
    maksutieto_qs = (Maksutieto.objects.filter(huoltajuussuhteet__lapsi__oma_organisaatio__isnull=True)
                     .distinct('id').order_by('id'))
    for maksutieto in memory_efficient_queryset_iterator(maksutieto_qs):
        lapsi_id_set = set(maksutieto.huoltajuussuhteet.values_list('lapsi', flat=True))

        if len(lapsi_id_set) != 1:
            logger.error(f'Maksutieto {maksutieto.id} is not related to only 1 Lapsi object')
            continue

        lapsi = Lapsi.objects.get(id=lapsi_id_set.pop())
        if not lapsi.oma_organisaatio:
            # PAOS-lapset should not have issues with Maksutieto permissions
            oid_set = set(lapsi.varhaiskasvatuspaatokset
                          .values_list('varhaiskasvatussuhteet__toimipaikka__organisaatio_oid', flat=True))
            oid_set.discard(None)
            for oid in oid_set:
                assign_object_level_permissions(oid, Maksutieto, maksutieto)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_last_request_table_task(init=False):
    """
    Updates Z6_LastRequest table by going through existing Z6_RequestLog objects. By default goes through requests
    from the last 24 hours.

    :param init: True if table is initialized and all Z6_RequestLog objects are considered
    """
    timestamp_filter = Q() if init else Q(timestamp__gte=timezone.now() - datetime.timedelta(days=1))

    successful_request_log_qs = (Z6_RequestLog.objects.filter(timestamp_filter &
                                                              Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST))
                                 .distinct('user', 'vakajarjestaja', 'lahdejarjestelma')
                                 .order_by('user', 'vakajarjestaja', 'lahdejarjestelma', '-timestamp')
                                 .values_list('user', 'vakajarjestaja', 'lahdejarjestelma', 'timestamp'))
    unsuccessful_request_log_qs = (Z6_RequestLog.objects.filter(timestamp_filter &
                                                                ~Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST))
                                   .distinct('user', 'vakajarjestaja', 'lahdejarjestelma')
                                   .order_by('user', 'vakajarjestaja', 'lahdejarjestelma', '-timestamp')
                                   .values_list('user', 'vakajarjestaja', 'lahdejarjestelma', 'timestamp'))

    for index, request_log_qs in enumerate((successful_request_log_qs, unsuccessful_request_log_qs,)):
        is_successful = True if index == 0 else False
        for request_log in request_log_qs:
            user_id = request_log[0]
            vakajarjestaja_id = request_log[1]
            lahdejarjestelma = request_log[2]
            timestamp = request_log[3]

            last_request_defaults = ({'last_successful': timestamp} if is_successful else
                                     {'last_unsuccessful': timestamp})
            Z6_LastRequest.objects.update_or_create(user_id=user_id, vakajarjestaja_id=vakajarjestaja_id,
                                                    lahdejarjestelma=lahdejarjestelma,
                                                    defaults=last_request_defaults)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_missing_vakatoimija_field():
    """
    Assigns vakatoimija-field for Lapsi objects that do not have it already based on user's permission groups. Also
    assign permissions for Lapsi related objects.

    TEMPORARY FUNCTION
    """
    lapsi_qs = Lapsi.objects.filter(vakatoimija__isnull=True, oma_organisaatio__isnull=True,
                                    paos_organisaatio__isnull=True).distinct('id').order_by('id')
    for lapsi in lapsi_qs:
        user = lapsi.changed_by
        vakajarjestaja = get_user_vakajarjestaja(user)

        if not vakajarjestaja:
            # Could not determine vakatoimija of this Lapsi object
            continue

        with transaction.atomic():
            lapsi.vakatoimija = vakajarjestaja
            lapsi.save()

            assign_object_level_permissions_for_instance(lapsi, (vakajarjestaja.organisaatio_oid,))
            assign_lapsi_henkilo_permissions(lapsi, user=user)

            for vakapaatos in lapsi.varhaiskasvatuspaatokset.all():
                assign_object_level_permissions_for_instance(vakapaatos, (vakajarjestaja.organisaatio_oid,))

            for maksutieto in Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).distinct('id').order_by('id'):
                assign_object_level_permissions_for_instance(maksutieto, (vakajarjestaja.organisaatio_oid,))


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_toimipaikka_pidempi_poissaolo_permissions():
    """
    Assigns Toimipaikka level permissions for PidempiPoissaolo objects.

    TEMPORARY FUNCTION
    """
    for pidempi_poissaolo in memory_efficient_queryset_iterator(PidempiPoissaolo.objects.all().order_by('id')):
        palvelussuhde = pidempi_poissaolo.palvelussuhde
        toimipaikka_oid_set = set(palvelussuhde.tyoskentelypaikat
                                  .values_list('toimipaikka__organisaatio_oid', flat=True))
        toimipaikka_oid_set.discard(None)
        for toimipaikka_oid in toimipaikka_oid_set:
            assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempi_poissaolo)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_request_summary_table_task():
    """
    Updates Z6_RequestSummary table by going through existing Z6_RequestLog objects.
    """
    now = timezone.now()
    aikaleima, created_aikaleima = (Aikaleima.objects
                                    .get_or_create(avain=AikaleimaAvain.REQUEST_SUMMARY_LAST_UPDATE.value,
                                                   defaults={'aikaleima': now}))
    if created_aikaleima:
        # If Aikaleima was created, e.g. we are initializing Z6_RequestSummary, go through last 100 days
        start_timestamp = now - datetime.timedelta(days=100)
    else:
        start_timestamp = aikaleima.aikaleima
    current_date = start_timestamp.date()
    today = now.date()

    # Format: [[field, filters], [field, filters],]
    group_by_list = [
        ['user_id', {}],
        ['vakajarjestaja_id', {'vakajarjestaja__isnull': False}],
        ['lahdejarjestelma', {'lahdejarjestelma__isnull': False}],
        ['request_url_simple', {}],
    ]
    # Start going through Z6_RequestLog instances day by day until we reach today
    # Summaries are always updated for past days
    while current_date < today:
        # Go through group_by rules, currently summaries are grouped by user, vakajarjestaja, lahdejarjestelma and URL
        for group_by_value in group_by_list:
            value_field = group_by_value[0]
            filters = group_by_value[1]

            values = ['request_method', 'response_code']
            if value_field != 'request_url_simple':
                values.append(value_field)

            # QuerySet that groups Z6_RequestLog instances by defined fields and a simplified URL
            # e.g. /api/v1/varhaiskasvatuspaatokset/123/ -> /api/v1/varhaiskasvatuspaatokset/*/
            request_log_qs = (Z6_RequestLog.objects
                              .values(*values, 'timestamp__date')
                              .annotate(request_url_simple=Case(When(request_url__regex=r'^.*\/(\d.*)\/$',
                                                                     then=Func(
                                                                         F('request_url'), Value(r'\/(\d.*)\/$'),
                                                                         Value('/*/'),
                                                                         function='regexp_replace')
                                                                     ),
                                                                default=F('request_url')),
                                        date=Cast('timestamp', DateField()),
                                        count=Count('id'))
                              .values(*values, 'count', 'date', 'request_url_simple')
                              .filter(timestamp__date=current_date, **filters)
                              .order_by(value_field))

            current_group = None
            request_summary = None
            # Start going through grouped Z6_RequestLog instances and create Z6_RequestSummary and Z6_RequestCount
            # instances
            for request_log in request_log_qs:
                if request_log.get(value_field) != current_group:
                    current_group = request_log.get(value_field)
                    request_summary, created_summary = (Z6_RequestSummary.objects
                                                        .update_or_create(summary_date=current_date,
                                                                          **{value_field: current_group},
                                                                          defaults={'successful_count': 0,
                                                                                    'unsuccessful_count': 0}))
                    if not created_summary:
                        # If summary already existed, delete existing Z6_RequestCount instances
                        request_summary.request_counts.all().delete()

                # Each Z6_RequestCount instance has related Z6_RequestCount instances which provide additional
                # information on requests that succeeded or failed
                Z6_RequestCount.objects.create(request_summary=request_summary,
                                               request_url_simple=request_log.get('request_url_simple'),
                                               request_method=request_log.get('request_method'),
                                               response_code=request_log.get('response_code'),
                                               count=request_log.get('count'))

                # Update the _count field of Z6_RequestSummary instance
                if request_log.get('response_code') in SUCCESSFUL_STATUS_CODE_LIST:
                    request_summary.successful_count += request_log.get('count')
                else:
                    request_summary.unsuccessful_count += request_log.get('count')
                request_summary.save()

        current_date += datetime.timedelta(days=1)

    # Update Aikaleima instance
    aikaleima.aikaleima = now
    aikaleima.save()


@shared_task
def merge_duplicate_child(merge_list):
    """
    Merges duplicate child-objects

    Pre-requisite: Get a list of ID:s that are supposed to be merged and confirm the list with end-user

    Usage: to merge for example child 1 (old_lapsi) into child 2 (new_lapsi) use input [[2,1]]
           for multiple merges use a list of lists eg [[2,1], [3,4], [5,10]]

    merge_list: list of lists of lapsi_id to be merged

    :return:
    """
    from varda.validators import validate_merge_duplicate_child_list, validate_merge_duplicate_child_lapsi_objs
    from varda.misc import merge_lapsi_maksutiedot
    from django.db import IntegrityError

    validate_merge_duplicate_child_list(merge_list)

    merged_lapsi_counter = 0

    for lapsi in merge_list:
        try:
            with transaction.atomic():
                try:
                    new_lapsi = Lapsi.objects.get(id=lapsi[0])
                    old_lapsi = Lapsi.objects.get(id=lapsi[1])
                except Lapsi.DoesNotExist:
                    logger.warning(f'No child with id {lapsi[0]} or {lapsi[1]}')
                    raise IntegrityError

                validate_lapsi = validate_merge_duplicate_child_lapsi_objs(new_lapsi, old_lapsi)

                if not validate_lapsi['is_ok']:
                    logger.warning(validate_lapsi['error_msg'])
                    continue

                old_vakapaatokset = Varhaiskasvatuspaatos.objects.filter(lapsi_id=old_lapsi.id)

                for old_vakapaatos in old_vakapaatokset:
                    old_vakapaatos.lapsi = new_lapsi
                    old_vakapaatos.save()

                merged_lapsi_toimipaikat = (Toimipaikka.objects
                                                       .filter(Q(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=old_lapsi) |
                                                               Q(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=new_lapsi))
                                                       .exclude(organisaatio_oid__exact='')
                                                       .values_list('organisaatio_oid', flat=True)
                                                       .distinct())

                old_maksutiedot = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=old_lapsi).distinct('id')
                new_huoltajuussuhteet = Huoltajuussuhde.objects.filter(lapsi=new_lapsi)

                merge_lapsi_maksutiedot(new_lapsi, old_maksutiedot, new_huoltajuussuhteet, merged_lapsi_toimipaikat)

                old_lapsi.huoltajuussuhteet.all().delete()
                old_lapsi.delete()
                merged_lapsi_counter += 1

        except IntegrityError:
            logger.warning(f'IntegrityError for lapsi {lapsi}')

    logger.info(f'Merged {merged_lapsi_counter} lapsi objects')


@shared_task
def transfer_lapsi_objects_to_correct_vakajarjestaja(lapsi_id_list):
    """
    TEMPORARY FUNCTION
    """
    for lapsi_id in lapsi_id_list:
        with transaction.atomic():
            lapsi_obj = Lapsi.objects.filter(id=lapsi_id).first()
            if not lapsi_obj:
                logger.error(f'Lapsi object {lapsi_id} does not exist')
                continue
            if lapsi_obj.vakatoimija is None:
                logger.error(f'Lapsi object {lapsi_id} is PAOS')
                continue
            if lapsi_obj.varhaiskasvatuspaatokset.count() > 0:
                logger.error(f'Lapsi object {lapsi_id} has related varhaiskasvatuspaatos objects')
                continue
            if Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi_obj).distinct().count() > 0:
                logger.error(f'Lapsi object {lapsi_id} has related maksutieto objects')
                continue

            old_vakajarjestaja = lapsi_obj.vakatoimija
            vakajarjestaja = get_user_vakajarjestaja(lapsi_obj.changed_by)
            if not vakajarjestaja:
                logger.error(f'Could not determine vakajarjestaja for user {lapsi_obj.changed_by_id}')
                continue
            if old_vakajarjestaja == vakajarjestaja:
                logger.error(f'Lapsi object {lapsi_id} already belongs to vakajarjestaja {vakajarjestaja.id}')
                continue
            if Lapsi.objects.filter(vakatoimija=vakajarjestaja, henkilo=lapsi_obj.henkilo).exists():
                logger.error(f'Lapsi object {lapsi_id} already exists for vakajarjestaja {vakajarjestaja.id}')
                continue

            # Change vakatoimija of Lapsi object
            lapsi_obj.vakatoimija = vakajarjestaja
            lapsi_obj.save()

            # Delete Henkilo permissions, only from old_vakajarjestaja, if old_vakajarjestaja does not have PAOS-lapsi that remains
            if not Lapsi.objects.filter(oma_organisaatio=old_vakajarjestaja, henkilo=lapsi_obj.henkilo).exists():
                delete_permissions_from_object_instance_by_oid(lapsi_obj.henkilo, old_vakajarjestaja.organisaatio_oid)

            # Assign Henkilo permissions, only for new_vakajarjestaja
            assign_lapsi_henkilo_permissions(lapsi_obj)

            # Delete Lapsi permissions
            delete_object_permissions_explicitly(Lapsi, lapsi_id)

            # Assign Lapsi permissions
            assign_object_level_permissions_for_instance(lapsi_obj, (vakajarjestaja.organisaatio_oid,))


@shared_task
def transfer_toimipaikka_objects_to_correct_vakajarjestaja(toimipaikka_id_list):
    """
    TEMPORARY FUNCTION
    """
    for toimipaikka_id in toimipaikka_id_list:
        with transaction.atomic():
            toimipaikka_obj = Toimipaikka.objects.filter(id=toimipaikka_id).first()
            if not toimipaikka_obj:
                logger.error(f'Toimipaikka object {toimipaikka_id} does not exist')
                continue
            if toimipaikka_obj.varhaiskasvatussuhteet.count() > 0:
                logger.error(f'Toimipaikka object {toimipaikka_id} has related varhaiskasvatussuhde objects')
                continue
            if toimipaikka_obj.tyoskentelypaikat.count() > 0:
                logger.error(f'Toimipaikka object {toimipaikka_id} has related tyoskentelypaikka objects')
                continue
            if toimipaikka_obj.kielipainotukset.count() > 0:
                logger.error(f'Toimipaikka object {toimipaikka_id} has related kielipainotus objects')
                continue
            if toimipaikka_obj.toiminnallisetpainotukset.count() > 0:
                logger.error(f'Toimipaikka object {toimipaikka_id} has related toiminnallinen painotus objects')
                continue

            old_vakajarjestaja = toimipaikka_obj.vakajarjestaja
            vakajarjestaja = get_user_vakajarjestaja(toimipaikka_obj.changed_by)
            if not vakajarjestaja:
                logger.error(f'Could not determine vakajarjestaja for user {toimipaikka_obj.changed_by_id}')
                continue
            if old_vakajarjestaja == vakajarjestaja:
                logger.error(f'Toimipaikka object {toimipaikka_id} already belongs to vakajarjestaja {vakajarjestaja.id}')
                continue

            # Disassociate all users from Toimipaikka specific permission groups
            for group in get_all_permission_groups_for_organization(toimipaikka_obj.organisaatio_oid):
                group.user_set.clear()

            # Delete permissions
            delete_object_permissions_explicitly(Toimipaikka, toimipaikka_obj.id)

            # Chance VakaJarjestaja reference of Toimipaikka
            toimipaikka_obj.vakajarjestaja = vakajarjestaja
            toimipaikka_obj.save()

            # Assign permissions
            assign_permissions_for_toimipaikka(toimipaikka_obj, vakajarjestaja.organisaatio_oid)
