import datetime
import json
import logging
import math
import re
from functools import wraps

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection, IntegrityError, transaction
from django.db.models import Case, Count, DateField, F, Func, IntegerField, Q, Value, When
from django.db.models.functions import Cast
from django.utils import timezone
from guardian.models import GroupObjectPermission, UserObjectPermission
from knox.models import AuthToken

from varda import koodistopalvelu, oppijanumerorekisteri
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.cache import delete_paattymis_pvm_cache, invalidate_cache, set_paattymis_pvm_cache
from varda.clients.oppijanumerorekisteri_client import fetch_henkilo_data_for_oid_list
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.excel_export import delete_excel_reports_earlier_than
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat
from varda.misc import hash_string, list_to_chunks, memory_efficient_queryset_iterator
from varda.misc_operations import set_paattymis_pvm_for_vakajarjestaja_data
from varda.models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, Lapsi, Maksutieto,
                          MaksutietoHuoltajuussuhde, Palvelussuhde, Taydennyskoulutus, TaydennyskoulutusTyontekija,
                          Toimipaikka, Tyontekija, Organisaatio, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          YearlyReportSummary,
                          Z10_KelaVarhaiskasvatussuhde, Z2_CodeTranslation, Z4_CasKayttoOikeudet, Z5_AuditLog,
                          Z6_LastRequest, Z6_RequestCount, Z6_RequestLog, Z6_RequestSummary, Z9_RelatedObjectChanged)
from varda.permission_groups import assign_object_permissions_to_taydennyskoulutus_groups, get_oph_yllapitaja_group_name
from varda.permissions import assign_object_level_permissions_for_instance, delete_object_permissions_explicitly


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
                    result = func(*args, **kwargs)
                finally:
                    cache.delete(lock_id)
                return result
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


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def run_management_commands():
    """
    To be run periodically, e.g. to clean out expired sessions
    """
    call_command('clearsessions', verbosity=0)
    call_command('django_cas_ng_clean_sessions', verbosity=0)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def remove_all_auth_tokens():
    """
    Delete all API tokens periodically so that users are forced to re-login and permission updates are fetched from
    Opintopolku.
    """
    AuthToken.objects.all().delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_oph_staff_to_vakajarjestaja_groups(user_id=None, organisaatio_oid=None):
    permission_groups.add_oph_staff_to_vakajarjestaja_katselija_groups(user_id=user_id,
                                                                       organisaatio_oid=organisaatio_oid)


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


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def update_henkilot_with_oid():
    oppijanumerorekisteri.fetch_henkilot_with_oid()


@shared_task
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


@shared_task
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


@shared_task
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


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_taydennyskoulutus_permissions_for_all_toimipaikat_task(vakajarjestaja_oid, taydennyskoulutus_id):
    taydennyskoulutus = Taydennyskoulutus.objects.get(id=taydennyskoulutus_id)
    toimipaikka_oid_list = (Toimipaikka.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                            .values_list('organisaatio_oid', flat=True))
    [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
     for toimipaikka_oid in toimipaikka_oid_list]

    invalidate_cache(Taydennyskoulutus.get_name(), taydennyskoulutus_id)


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
        BatchError.objects.filter(henkilo=henkilo).delete()
        henkilo.delete()


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
            # PostgreSQL specific functionality (regexp_replace)
            request_log_qs = (Z6_RequestLog.objects
                              .values(*values, 'timestamp__date')
                              .annotate(request_url_simple=Case(When(request_url__regex=r'^.*\/(\d*(:.*)?|[\d.]*)\/.*$',
                                                                     then=Func(
                                                                         F('request_url'), Value(r'\/(\d*(:.*)?|[\d.]*)\/'),
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

                MaksutietoHuoltajuussuhde.objects.filter(huoltajuussuhde__lapsi=old_lapsi).delete()
                old_lapsi.huoltajuussuhteet.all().delete()
                old_lapsi.delete()
                merged_lapsi_counter += 1

        except IntegrityError:
            logger.warning(f'IntegrityError for lapsi {lapsi}')

    logger.info(f'Merged {merged_lapsi_counter} lapsi objects')


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def general_monitoring_task():
    """
    This task is used to perform various monitoring tasks
    """
    # Check that number of super/staff users does not exceed limit
    if User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count() > settings.STAFF_USER_LIMIT:
        logger.error('There are too many users with is_staff=True or is_superuser=True.')

    # Check that number of OPH users does not exceed limit
    oph_yllapitaja_group = Group.objects.filter(name=get_oph_yllapitaja_group_name()).first()
    if oph_yllapitaja_group and oph_yllapitaja_group.user_set.count() > settings.OPH_USER_LIMIT:
        logger.error('There are too many OPH staff users.')

    # Check that an API is not systematically browsed through using the page-parameter
    # This task is run every hour so check the last 2 hours
    # Exclude LUOVUTUSPALVELU users
    # Exclude error-report-x paths
    two_hours_ago = timezone.now() - datetime.timedelta(hours=2)
    # PostgreSQL specific functionality (regexp_replace)
    page_queryset = (Z5_AuditLog.objects
                     .exclude(user__groups__name__icontains=Z4_CasKayttoOikeudet.LUOVUTUSPALVELU)
                     .exclude(successful_get_request_path__icontains='error-report-')
                     .filter(time_of_event__gte=two_hours_ago, query_params__icontains='page=')
                     .values('user', 'successful_get_request_path')
                     .annotate(page_number_count=Count(Func(
                         F('query_params'), Value(r'.*page=(\d*).*'), Value('\\1'), function='regexp_replace'),
                         distinct=True))
                     .values('user', 'successful_get_request_path', 'page_number_count')
                     .filter(page_number_count__gt=20))
    if page_queryset.exists():
        logger.error(f'The following APIs are browsed through: {page_queryset}')


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def init_related_object_changed_table_task():
    related_change_tuple = (
        (
            Organisaatio.get_name(), 'id', Organisaatio.get_name(), 'id', None, None,
        ),
        (
            Toimipaikka.get_name(), 'id', Toimipaikka.get_name(), 'id',
            Organisaatio.get_name(), 'vakajarjestaja_id',
        ),
        (
            Lapsi.get_name(), 'id', Lapsi.get_name(), 'id', None, None,
        ),
        (
            Varhaiskasvatuspaatos.get_name(), 'id', Varhaiskasvatuspaatos.get_name(), 'id',
            Lapsi.get_name(), 'lapsi_id',
        ),
        (
            Tyontekija.get_name(), 'id', Tyontekija.get_name(), 'id', None, None,
        ),
        (
            Palvelussuhde.get_name(), 'id', Palvelussuhde.get_name(), 'id',
            Tyontekija.get_name(), 'tyontekija_id',
        ),
        (
            Huoltajuussuhde.get_name(), 'id', Lapsi.get_name(), 'lapsi_id', None, None,
        ),
        (
            TaydennyskoulutusTyontekija.get_name(), 'id', Tyontekija.get_name(), 'tyontekija_id',
            Taydennyskoulutus.get_name(), 'taydennyskoulutus_id',
        ),
    )

    with transaction.atomic():
        for related_change in related_change_tuple:
            trigger_class = related_change[0]
            trigger_id_field = related_change[1]
            model_class = related_change[2]
            model_id_field = related_change[3]
            parent_class = related_change[4]
            parent_id_field = related_change[5]

            with connection.cursor() as cursor:
                if parent_class and parent_id_field:
                    cursor.execute(f'''
                        INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                            instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                        SELECT %s, {trigger_id_field}, %s, {model_id_field}, %s, {parent_id_field}, luonti_pvm, '+'
                        FROM varda_{trigger_class};
                    ''', [trigger_class, model_class, parent_class])
                else:
                    cursor.execute(f'''
                        INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                            instance_id, changed_timestamp, history_type)
                        SELECT %s, {trigger_id_field}, %s, {model_id_field}, luonti_pvm, '+'
                        FROM varda_{trigger_class};
                    ''', [trigger_class, model_class])

        # MaksutietoHuoltajuussuhde requires different logic
        with connection.cursor() as cursor:
            cursor.execute('''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'maksutietohuoltajuussuhde', mhs.id, 'lapsi', hs.lapsi_id, 'maksutieto', mhs.maksutieto_id,
                    mhs.luonti_pvm, '+'
                FROM varda_maksutietohuoltajuussuhde mhs
                LEFT JOIN varda_huoltajuussuhde hs ON hs.id = mhs.huoltajuussuhde_id;
            ''')


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def init_related_object_changed_table_complete_history_task(datetime_param=None):
    until_datetime = timezone.now()
    if datetime_param:
        until_datetime = datetime.datetime.strptime(datetime_param, '%Y-%m-%dT%H:%M:%S%z')

    query_list = [
        [
            'varda_historicalorganisaatio',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'organisaatio', org.id, 'organisaatio', org.id, null, null, org.history_date, org.history_type
                FROM varda_historicalorganisaatio org
                WHERE org.history_date <= %s AND org.id > %s AND org.id <= %s
                ORDER BY org.id;
            '''
        ],
        [
            'varda_historicaltoimipaikka',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'toimipaikka', tp.id, unnest(ARRAY['toimipaikka', 'organisaatio']),
                    unnest(ARRAY[tp.id, tp.vakajarjestaja_id]), unnest(ARRAY['organisaatio', null]),
                    unnest(ARRAY[tp.vakajarjestaja_id, null]), tp.history_date, tp.history_type
                FROM varda_historicaltoimipaikka tp
                WHERE tp.history_date <= %s AND tp.id > %s AND tp.id <= %s
                ORDER BY tp.id;
            '''
        ],
        [
            'varda_historicalkielipainotus',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'kielipainotus', pa.id, unnest(ARRAY['toimipaikka', 'organisaatio']),
                    unnest(ARRAY[tp.id, tp.vakajarjestaja_id]), unnest(ARRAY['organisaatio', null]),
                    unnest(ARRAY[tp.vakajarjestaja_id, null]), pa.history_date, pa.history_type
                FROM varda_historicalkielipainotus pa
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                     WHERE id = pa.toimipaikka_id AND history_date <= pa.history_date + interval '30 seconds'
                     ORDER BY id, history_date DESC) tp ON true
                WHERE pa.history_date <= %s AND pa.id > %s AND pa.id <= %s
                ORDER BY pa.id;
            '''
        ],
        [
            'varda_historicaltoiminnallinenpainotus',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'toiminnallinenpainotus', pa.id, unnest(ARRAY['toimipaikka', 'organisaatio']),
                    unnest(ARRAY[tp.id, tp.vakajarjestaja_id]), unnest(ARRAY['organisaatio', null]),
                    unnest(ARRAY[tp.vakajarjestaja_id, null]), pa.history_date, pa.history_type
                FROM varda_historicaltoiminnallinenpainotus pa
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicaltoimipaikka
                     WHERE id = pa.toimipaikka_id AND history_date <= pa.history_date + interval '30 seconds'
                     ORDER BY id, history_date DESC) tp ON true
                WHERE pa.history_date <= %s AND pa.id > %s AND pa.id <= %s
                ORDER BY pa.id;
            '''
        ],
        [
            'varda_historicallapsi',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'lapsi', la.id, 'lapsi', la.id, null, null, la.history_date, la.history_type
                FROM varda_historicallapsi la
                WHERE la.history_date <= %s AND la.id > %s AND la.id <= %s
                ORDER BY la.id;
            '''
        ],
        [
            'varda_historicalvarhaiskasvatuspaatos',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'varhaiskasvatuspaatos', pa.id, unnest(ARRAY['varhaiskasvatuspaatos', 'lapsi']),
                    unnest(ARRAY[pa.id, pa.lapsi_id]), unnest(ARRAY['lapsi', null]),
                    unnest(ARRAY[pa.lapsi_id, null]), pa.history_date, pa.history_type
                FROM varda_historicalvarhaiskasvatuspaatos pa
                WHERE pa.history_date <= %s AND pa.id > %s AND pa.id <= %s
                ORDER BY pa.id;
            '''
        ],
        [
            'varda_historicalvarhaiskasvatussuhde',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'varhaiskasvatussuhde', su.id, unnest(ARRAY['varhaiskasvatuspaatos', 'lapsi']),
                    unnest(ARRAY[pa.id, pa.lapsi_id]), unnest(ARRAY['lapsi', null]),
                    unnest(ARRAY[pa.lapsi_id, null]), su.history_date, su.history_type
                FROM varda_historicalvarhaiskasvatussuhde su
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalvarhaiskasvatuspaatos
                     WHERE id = su.varhaiskasvatuspaatos_id AND history_date <= su.history_date + interval '30 seconds'
                     ORDER BY id, history_date DESC) pa ON true
                WHERE su.history_date <= %s AND su.id > %s AND su.id <= %s
                ORDER BY su.id;
            '''
        ],
        # Maksutieto, Lapsi can be determined only for ~ events
        # (for + and - events MaksutietoHuoltajuussuhde objects do not exist)
        # MaksutietoHuoltajuussuhde history is incomplete so exclude rows which have NULL lapsi_id
        [
            'varda_historicalmaksutieto',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'maksutietohuoltajuussuhde', mahu.id, 'lapsi', hu.lapsi_id, 'maksutieto', ma.id,
                    ma.history_date, ma.history_type
                FROM varda_historicalmaksutieto ma
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalmaksutietohuoltajuussuhde
                     WHERE maksutieto_id = ma.id AND history_date <= ma.history_date
                     ORDER BY id, history_date DESC) mahu ON true
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalhuoltajuussuhde
                     WHERE id = mahu.huoltajuussuhde_id AND history_date <= ma.history_date
                     ORDER BY id, history_date DESC) hu ON true
                WHERE ma.history_type = '~' AND ma.history_date <= %s AND hu.lapsi_id IS NOT NULL
                    AND mahu.history_type != '-' AND ma.id > %s AND ma.id <= %s
                ORDER BY ma.id;
            '''
        ],
        # Huoltajuussuhde, no history_date filtering for varda_historicalhuoltajuussuhde as dates are out of sync
        # with varda_historicalmaksutietohuoltajuussuhde, and lapsi_id cannot change for Huoltajuussuhde object
        [
            'varda_historicalmaksutietohuoltajuussuhde',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'maksutietohuoltajuussuhde', mahu.id, 'lapsi', hu.lapsi_id, 'maksutieto', mahu.maksutieto_id,
                    mahu.history_date, mahu.history_type
                FROM varda_historicalmaksutietohuoltajuussuhde mahu
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalhuoltajuussuhde
                     WHERE id = mahu.huoltajuussuhde_id
                     ORDER BY id) hu ON true
                WHERE mahu.history_date <= %s AND mahu.id > %s AND mahu.id <= %s
                ORDER BY mahu.id;
            '''
        ],
        [
            'varda_historicalhuoltajuussuhde',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'huoltajuussuhde', hu.id, 'lapsi', hu.lapsi_id, null, null, hu.history_date, hu.history_type
                FROM varda_historicalhuoltajuussuhde hu
                WHERE hu.history_date <= %s AND hu.id > %s AND hu.id <= %s
                ORDER BY hu.id;
            '''
        ],
        [
            'varda_historicaltyontekija',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'tyontekija', ty.id, 'tyontekija', ty.id, null, null, ty.history_date, ty.history_type
                FROM varda_historicaltyontekija ty
                WHERE ty.history_date <= %s AND ty.id > %s AND ty.id <= %s
                ORDER BY ty.id;
            '''
        ],
        # Tutkinto, longer time frame since when transferring Toimipaikka objects from one Organisaatio to another,
        # Tutkinto objects are modified first, before Tyontekija objects
        [
            'varda_historicaltutkinto',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'tutkinto', tu.id, 'tyontekija', ty.id, null, null, tu.history_date, tu.history_type
                FROM varda_historicaltutkinto tu
                LEFT JOIN LATERAL
                    (SELECT * FROM varda_historicaltyontekija
                     WHERE vakajarjestaja_id = tu.vakajarjestaja_id AND henkilo_id = tu.henkilo_id
                        AND history_date <= tu.history_date + interval '5 minutes'
                     ORDER BY id, history_date DESC LIMIT 1) ty ON true
                WHERE tu.history_date <= %s AND tu.id > %s AND tu.id <= %s
                ORDER BY tu.id;
            '''
        ],
        [
            'varda_historicalpalvelussuhde',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'palvelussuhde', pa.id, unnest(ARRAY['palvelussuhde', 'tyontekija']),
                    unnest(ARRAY[pa.id, pa.tyontekija_id]), unnest(ARRAY['tyontekija', null]),
                    unnest(ARRAY[pa.tyontekija_id, null]), pa.history_date, pa.history_type
                FROM varda_historicalpalvelussuhde pa
                WHERE pa.history_date <= %s AND pa.id > %s AND pa.id <= %s
                ORDER BY pa.id;
            '''
        ],
        [
            'varda_historicaltyoskentelypaikka',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'tyoskentelypaikka', typ.id, unnest(ARRAY['palvelussuhde', 'tyontekija']),
                    unnest(ARRAY[pa.id, pa.tyontekija_id]), unnest(ARRAY['tyontekija', null]),
                    unnest(ARRAY[pa.tyontekija_id, null]), typ.history_date, typ.history_type
                FROM varda_historicaltyoskentelypaikka typ
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                     WHERE id = typ.palvelussuhde_id AND history_date <= typ.history_date + interval '30 seconds'
                     ORDER BY id, history_date DESC) pa ON true
                WHERE typ.history_date <= %s AND typ.id > %s AND typ.id <= %s
                ORDER BY typ.id;
            '''
        ],
        [
            'varda_historicalpidempipoissaolo',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'pidempipoissaolo', pi.id, unnest(ARRAY['palvelussuhde', 'tyontekija']),
                    unnest(ARRAY[pa.id, pa.tyontekija_id]), unnest(ARRAY['tyontekija', null]),
                    unnest(ARRAY[pa.tyontekija_id, null]), pi.history_date, pi.history_type
                FROM varda_historicalpidempipoissaolo pi
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalpalvelussuhde
                     WHERE id = pi.palvelussuhde_id AND history_date <= pi.history_date + interval '30 seconds'
                     ORDER BY id, history_date DESC) pa ON true
                WHERE pi.history_date <= %s AND pi.id > %s AND pi.id <= %s
                ORDER BY pi.id;
            '''
        ],
        # Taydennyskoulutus, Tyontekijat can be determined only for ~ events
        # (for + and - events TaydennyskoulutusTyontekija objects do not exist)
        [
            'varda_historicaltaydennyskoulutus',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'taydennyskoulutustyontekija', taty.id, 'tyontekija', taty.tyontekija_id,
                    'taydennyskoulutus', ta.id, ta.history_date, ta.history_type
                FROM varda_historicaltaydennyskoulutus ta
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicaltaydennyskoulutustyontekija
                     WHERE taydennyskoulutus_id = ta.id AND history_date <= ta.history_date
                     ORDER BY id, history_date DESC) taty ON true
                WHERE ta.history_type = '~' AND ta.history_date <= %s AND taty.history_type != '-'
                     AND ta.id > %s AND ta.id <= %s
                ORDER BY ta.id;
            '''
        ],
        [
            'varda_historicaltaydennyskoulutustyontekija',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'taydennyskoulutustyontekija', taty.id, 'tyontekija', taty.tyontekija_id, 'taydennyskoulutus',
                    taty.taydennyskoulutus_id, taty.history_date, taty.history_type
                FROM varda_historicaltaydennyskoulutustyontekija taty
                WHERE taty.history_date <= %s AND taty.id > %s AND taty.id <= %s
                ORDER BY taty.id;
            '''
        ],
        [
            'varda_historicaltilapainenhenkilosto',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'tilapainenhenkilosto', ti.id, 'organisaatio', ti.vakajarjestaja_id, null, null,
                    ti.history_date, ti.history_type
                FROM varda_historicaltilapainenhenkilosto ti
                WHERE ti.history_date <= %s AND ti.id > %s AND ti.id <= %s
                ORDER BY ti.id;
            '''
        ],
        [
            'varda_historicalhenkilo',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'lapsi', la.id, 'lapsi', la.id, null, null, he.history_date, he.history_type
                FROM varda_historicalhenkilo he
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicallapsi
                     WHERE henkilo_id = he.id AND history_date <= he.history_date
                     ORDER BY id, history_date DESC) la ON true
                WHERE he.history_type = '~' AND he.history_date <= %s AND la.id IS NOT NULL
                    AND la.history_type != '-' AND he.id > %s AND he.id <= %s
                ORDER BY he.id;
            '''
        ],
        [
            'varda_historicalhenkilo',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'huoltajuussuhde', hu.id, 'lapsi', hu.lapsi_id, null, null, he.history_date, he.history_type
                FROM varda_historicalhenkilo he
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalhuoltaja
                     WHERE henkilo_id = he.id AND history_date <= he.history_date
                     ORDER BY id, history_date DESC) huo ON true
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicalhuoltajuussuhde
                     WHERE huoltaja_id = huo.id AND history_date <= he.history_date
                     ORDER BY id, history_date DESC) hu ON TRUE
                WHERE he.history_type = '~' AND he.history_date <= %s AND hu.lapsi_id IS NOT NULL
                    AND huo.history_type != '-' AND hu.history_type != '-' AND he.id > %s AND he.id <= %s
                ORDER BY he.id;
            '''
        ],
        [
            'varda_historicalhenkilo',
            '''
                INSERT INTO varda_z9_relatedobjectchanged (trigger_model_name, trigger_instance_id, model_name,
                    instance_id, parent_model_name, parent_instance_id, changed_timestamp, history_type)
                SELECT 'tyontekija', ty.id, 'tyontekija', ty.id, null, null, he.history_date, he.history_type
                FROM varda_historicalhenkilo he
                LEFT JOIN LATERAL
                    (SELECT DISTINCT ON (id) * FROM varda_historicaltyontekija
                     WHERE henkilo_id = he.id AND history_date <= he.history_date
                     ORDER BY id, history_date DESC) ty ON true
                WHERE he.history_type = '~' AND he.history_date <= %s AND ty.id IS NOT NULL
                    AND ty.history_type != '-' AND he.id > %s AND he.id <= %s
                ORDER BY he.id;
            '''
        ]
    ]

    # Delete old RelatedObjectChanged events as they are rebuilt
    Z9_RelatedObjectChanged.objects.filter(changed_timestamp__lte=until_datetime).delete()

    with connection.cursor() as cursor:
        for query in query_list:
            table = query[0]
            raw_query = query[1]

            # These queries are very expensive in production, so process 100 000 objects at a time
            # Get the highest ID number and round it up to the next 100 000
            cursor.execute(f'SELECT MAX(id) FROM {table};')
            max_object_id = cursor.fetchone()[0]
            object_limit = int(math.ceil(max_object_id / 100000.0)) * 100000 + 1

            last_index = 0
            for index in range(100000, object_limit, 100000):
                cursor.execute(raw_query, [until_datetime, last_index, index])
                logger.info(f'Z9_RelatedObjectChanged table: {table}, id range: {last_index} - {index}, rowcount: {cursor.rowcount}')
                last_index = index


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def create_yearly_reporting_summary(vakajarjestaja_id, tilasto_pvm, poiminta_pvm, full_query, history_q):
    from varda.misc_queries import (get_vakajarjestaja_is_active, get_toimipaikat, get_kielipainotukset, get_toiminnalliset_painotukset,
                                    get_vakasuhteet, get_omat_vakasuhteet, get_paos_vakasuhteet, get_vakapaatokset,
                                    get_omat_vakapaatokset, get_paos_vakapaatokset, get_vuorohoito_vakapaatokset,
                                    get_omat_vuorohoito_vakapaatokset, get_paos_vuorohoito_vakapaatokset, get_lapset,
                                    get_omat_lapset, get_paos_lapset, get_henkilot, get_maksutiedot)

    tilasto_pvm = datetime.datetime.strptime(tilasto_pvm, '%Y-%m-%dT%H:%M:%S').date()

    if full_query:
        vakajarjestaja_obj = None
        with connection.cursor() as cursor:
            filters = [poiminta_pvm, tilasto_pvm, tilasto_pvm]
            base_query = """select count(distinct(hvj.id)) from varda_historicalorganisaatio hvj
                            join (select distinct on (id) id, history_type from varda_historicalorganisaatio
                            where history_date <= %s order by id, history_date desc) last_hvj
                            on hvj.id = last_hvj.id where last_hvj.history_type <> '-' and
                            hvj.alkamis_pvm <= %s and (hvj.paattymis_pvm >= %s or hvj.paattymis_pvm is Null)
                            """
            cursor.execute(base_query + ';', filters)
            row = cursor.fetchone()
            vakajarjestaja_count = row[0]
    else:
        vakajarjestaja_obj = Organisaatio.objects.get(id=vakajarjestaja_id)
        vakajarjestaja_count = 1

    vakajarjestaja_active = get_vakajarjestaja_is_active(vakajarjestaja_obj, tilasto_pvm, full_query)
    toimipaikat = get_toimipaikat(vakajarjestaja_obj, poiminta_pvm, tilasto_pvm, full_query, history_q)
    kielipainotukset = get_kielipainotukset(toimipaikat, poiminta_pvm, tilasto_pvm, history_q)
    toimintapainotukset = get_toiminnalliset_painotukset(toimipaikat, poiminta_pvm, tilasto_pvm, history_q)

    vakasuhteet = get_vakasuhteet(vakajarjestaja_obj, poiminta_pvm, tilasto_pvm, full_query, history_q)
    omat_vakasuhteet = get_omat_vakasuhteet(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)
    paos_vakasuhteet = get_paos_vakasuhteet(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)

    vakapaatokset = get_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)
    omat_vakapaatokset = get_omat_vakapaatokset(omat_vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)
    paos_vakapaatokset = get_paos_vakapaatokset(paos_vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)

    vuorohoito = get_vuorohoito_vakapaatokset(vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)
    omat_vuorohoito = get_omat_vuorohoito_vakapaatokset(omat_vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)
    paos_vuorohoito = get_paos_vuorohoito_vakapaatokset(paos_vakasuhteet, poiminta_pvm, tilasto_pvm, history_q)

    lapset = get_lapset(vakapaatokset, poiminta_pvm, Q(), history_q)
    omat_lapset = get_omat_lapset(vakajarjestaja_obj, vakapaatokset, poiminta_pvm, full_query, history_q)
    paos_lapset = get_paos_lapset(vakajarjestaja_obj, vakapaatokset, poiminta_pvm, full_query, history_q)

    henkilot = get_henkilot(lapset, poiminta_pvm, history_q)
    omat_henkilot = get_henkilot(omat_lapset, poiminta_pvm, history_q)
    paos_henkilot = get_henkilot(paos_lapset, poiminta_pvm, history_q)

    maksutiedot_yhteensa = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, None, None)
    maksutiedot_yhteensa_mp1 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, None, 'MP01')
    maksutiedot_yhteensa_mp2 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, None, 'MP02')
    maksutiedot_yhteensa_mp3 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, None, 'MP03')

    omat_maksutiedot_yhteensa = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, False, None)
    omat_maksutiedot_yhteensa_mp1 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, False, 'MP01')
    omat_maksutiedot_yhteensa_mp2 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, False, 'MP02')
    omat_maksutiedot_yhteensa_mp3 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, False, 'MP03')

    paos_maksutiedot_yhteensa = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, True, None)
    paos_maksutiedot_yhteensa_mp1 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, True, 'MP01')
    paos_maksutiedot_yhteensa_mp2 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, True, 'MP02')
    paos_maksutiedot_yhteensa_mp3 = get_maksutiedot(vakajarjestaja_obj, full_query, poiminta_pvm, tilasto_pvm, True, 'MP03')

    updated_values = {
        'status': ReportStatus.FINISHED.value,
        'vakajarjestaja_count': vakajarjestaja_count,
        'vakajarjestaja_is_active': vakajarjestaja_active,
        'poiminta_pvm': poiminta_pvm,
        'toimipaikka_count': len(toimipaikat),
        'kielipainotus_count': len(kielipainotukset),
        'toimintapainotus_count': len(toimintapainotukset),
        'yhteensa_henkilo_count': len(henkilot),
        'yhteensa_lapsi_count': len(lapset),
        'yhteensa_varhaiskasvatussuhde_count': len(vakasuhteet),
        'yhteensa_varhaiskasvatuspaatos_count': len(vakapaatokset),
        'yhteensa_vuorohoito_count': len(vuorohoito),
        'oma_henkilo_count': len(omat_henkilot),
        'oma_lapsi_count': len(omat_lapset),
        'oma_varhaiskasvatussuhde_count': len(omat_vakasuhteet),
        'oma_varhaiskasvatuspaatos_count': len(omat_vakapaatokset),
        'oma_vuorohoito_count': len(omat_vuorohoito),
        'paos_henkilo_count': len(paos_henkilot),
        'paos_lapsi_count': len(paos_lapset),
        'paos_varhaiskasvatussuhde_count': len(paos_vakasuhteet),
        'paos_varhaiskasvatuspaatos_count': len(paos_vakapaatokset),
        'paos_vuorohoito_count': len(paos_vuorohoito),
        'yhteensa_maksutieto_count': maksutiedot_yhteensa,
        'yhteensa_maksutieto_mp01_count': maksutiedot_yhteensa_mp1,
        'yhteensa_maksutieto_mp02_count': maksutiedot_yhteensa_mp2,
        'yhteensa_maksutieto_mp03_count': maksutiedot_yhteensa_mp3,
        'oma_maksutieto_count': omat_maksutiedot_yhteensa,
        'oma_maksutieto_mp01_count': omat_maksutiedot_yhteensa_mp1,
        'oma_maksutieto_mp02_count': omat_maksutiedot_yhteensa_mp2,
        'oma_maksutieto_mp03_count': omat_maksutiedot_yhteensa_mp3,
        'paos_maksutieto_count': paos_maksutiedot_yhteensa,
        'paos_maksutieto_mp01_count': paos_maksutiedot_yhteensa_mp1,
        'paos_maksutieto_mp02_count': paos_maksutiedot_yhteensa_mp2,
        'paos_maksutieto_mp03_count': paos_maksutiedot_yhteensa_mp3
    }

    YearlyReportSummary.objects.update_or_create(vakajarjestaja=vakajarjestaja_obj, tilasto_pvm=tilasto_pvm, defaults=updated_values)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def reset_superuser_permissions_task():
    """
    Sets is_superuser and is_staff fields False for CAS users that have either field as True.
    """
    for user in User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)):
        if hasattr(user, 'additional_cas_user_fields'):
            user.is_superuser = False
            user.is_staff = False
            user.save()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def create_oph_yllapitaja_group():
    """
    TEMPORARY FUNCTION
    """
    Group.objects.get_or_create(name=get_oph_yllapitaja_group_name())
    # Delete old oph_staff group
    Group.objects.filter(name='oph_staff').delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def hash_cas_oppija_usernames():
    """
    TEMPORARY FUNCTION
    """
    for user in User.objects.filter(username__regex=r'^.*(\d{6})([A+\-])(\d{3}[0-9A-FHJ-NPR-Y]).*$').iterator():
        try:
            user.username = f'cas#{hash_string(user.username)}'
            user.save()
        except IntegrityError as error:
            logger.error(f'Error hashing user {user.id}: {error}')


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def set_paattymis_pvm_for_vakajarjestaja_data_task(vakajarjestaja_id, paattymis_pvm, identifier):
    try:
        paattymis_pvm = datetime.datetime.strptime(paattymis_pvm, '%Y-%m-%d').date()
    except ValueError:
        logger.error(f'Could not parse paattymis_pvm: {paattymis_pvm}')
        return None

    vakajarjestaja = Organisaatio.objects.filter(id=vakajarjestaja_id).first()
    if not vakajarjestaja:
        logger.error(f'Could not find vakajarjestaja with id: {vakajarjestaja_id}')
        return None

    try:
        result = set_paattymis_pvm_for_vakajarjestaja_data(vakajarjestaja, paattymis_pvm)
        result['status'] = ReportStatus.FINISHED.value
        set_paattymis_pvm_cache(identifier, result)
        logger.info(f'Set paattymis_pvm {paattymis_pvm} for data of vakajarjestaja with ID '
                    f'{vakajarjestaja_id}: {json.dumps(result)}')
    except Exception as exception:
        delete_paattymis_pvm_cache(identifier)
        raise exception


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def get_ukranian_child_statistics(active_since='2022-02-24'):
    """
    Get number of Ukranian children per each municipality that started in vaka after active_since parameter
    TEMPORARY FUNCTION
    """
    try:
        active_since = datetime.datetime.strptime(active_since, '%Y-%m-%d').date()
    except ValueError:
        logger.error(f'Could not parse active_since: {active_since}')
        return None

    # Get list of henkilo_oid that have active Varhaiskasvatuspaatos and Varhaiskasvatussuhde after active since
    # and no previous Varhaiskasvatuspaatos objects
    today = datetime.datetime.today()
    oid_list = (Henkilo.objects
                .filter(Q(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__gte=active_since) &
                        (Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__isnull=True) |
                         Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__gt=today)) &
                        Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__gte=active_since) &
                        (Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                         Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gt=today)))
                .exclude(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__lt=active_since)
                .distinct('henkilo_oid').values_list('henkilo_oid', flat=True))
    oid_chunk_list = list_to_chunks(oid_list, 5000)

    valid_oid_list = []
    for oid_chunk in oid_chunk_list:
        result = fetch_henkilo_data_for_oid_list(oid_chunk)
        for henkilo_data in result:
            for kansalaisuus in henkilo_data.get('kansalaisuus', []):
                # https://koodistot.suomi.fi/codescheme;registryCode=jhs;schemeCode=valtio_1_20120101
                if kansalaisuus['kansalaisuusKoodi'] == '804':
                    valid_oid_list.append(henkilo_data['oidHenkilo'])
                    break

    kunta_dict = {'total': {'amount': len(valid_oid_list)}}
    for henkilo_oid in valid_oid_list:
        kunta_code_list = (Toimipaikka.objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid=henkilo_oid)
                           .distinct('kunta_koodi').values_list('kunta_koodi', flat=True))
        for kunta_code in kunta_code_list:
            kunta_translation = getattr(Z2_CodeTranslation.objects
                                        .filter(language__iexact='fi', code__code_value=kunta_code,
                                                code__koodisto__name=Koodistot.kunta_koodit.value).first(),
                                        'name', None)
            kunta_dict[kunta_code] = {'name': kunta_translation,
                                      'amount': kunta_dict.get(kunta_code, {}).get('amount', 0) + 1}

    result_str = 'kunta_koodi,kunta_nimi,lapsi_lkm'
    for key, value in kunta_dict.items():
        name = value.get('name', '')
        amount = value.get('amount', '')
        result_str += f';{key},{name},{amount}'

    return result_str


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def init_kela_varhaiskasvatussuhde_table_task(datetime_param=None):
    history_date_limit = timezone.now()
    if datetime_param:
        history_date_limit = datetime.datetime.strptime(datetime_param, '%Y-%m-%dT%H:%M:%S%z')

    # Delete old KelaVarhaiskasvatussuhde instances as they are rebuilt
    Z10_KelaVarhaiskasvatussuhde.objects.filter(history_date__lte=history_date_limit).delete()

    with connection.cursor() as cursor:
        # This query is very expensive in production, so process 100 000 objects at a time
        # Get the highest ID number and round it up to the next 100 000
        max_object_id = Varhaiskasvatussuhde.history.all().order_by('id').last().id
        object_limit = int(math.ceil(max_object_id / 100000.0)) * 100000 + 1

        last_index = 0
        for index in range(100000, object_limit, 100000):
            cursor.execute(
                '''
                    INSERT INTO varda_z10_kelavarhaiskasvatussuhde (varhaiskasvatussuhde_id, suhde_luonti_pvm,
                        suhde_alkamis_pvm, suhde_paattymis_pvm, varhaiskasvatuspaatos_id, paatos_luonti_pvm,
                        jarjestamismuoto_koodi, tilapainen_vaka_kytkin, lapsi_id, henkilo_id, has_hetu, history_type,
                        history_date)
                    SELECT DISTINCT ON (su.history_id) su.id, su.luonti_pvm, su.alkamis_pvm, su.paattymis_pvm, pa.id,
                        pa.luonti_pvm, pa.jarjestamismuoto_koodi, pa.tilapainen_vaka_kytkin, la.id, la.henkilo_id,
                        CASE WHEN he.henkilotunnus = '' OR he.henkilotunnus IS NULL THEN false ELSE true END,
                        su.history_type, su.history_date
                    FROM varda_historicalvarhaiskasvatussuhde su
                    LEFT JOIN varda_historicalvarhaiskasvatuspaatos pa on pa.id = su.varhaiskasvatuspaatos_id AND
                        pa.history_date <= su.history_date + interval '30 seconds'
                    LEFT JOIN varda_historicallapsi la on la.id = pa.lapsi_id AND
                        la.history_date <= su.history_date + interval '30 seconds'
                    LEFT JOIN varda_historicalhenkilo he on he.id = la.henkilo_id AND
                        he.history_date <= su.history_date + interval '30 seconds'
                    WHERE su.history_date <= %s AND su.id > %s AND su.id <= %s
                    ORDER BY su.history_id, pa.history_date DESC, la.history_date DESC, he.history_date DESC;
                ''', [history_date_limit, last_index, index])
            logger.info(f'Z10_KelaVarhaiskasvatussuhde id range: {last_index} - {index}, rowcount: {cursor.rowcount}')
            last_index = index
