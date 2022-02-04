import datetime
import logging
import re
from functools import wraps

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import StringAgg
from django.core.cache import cache
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import Case, Count, DateField, F, Func, IntegerField, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Cast
from django.db.models.signals import post_save
from django.utils import timezone
from guardian.models import GroupObjectPermission, UserObjectPermission

from varda import koodistopalvelu, oppijanumerorekisteri
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.excel_export import delete_excel_reports_earlier_than
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat
from varda.misc import memory_efficient_queryset_iterator
from varda.models import (Aikaleima, BatchError, Henkilo, Huoltaja, Huoltajuussuhde, Lapsi, Maksutieto,
                          MaksutietoHuoltajuussuhde, Palvelussuhde, Taydennyskoulutus, TaydennyskoulutusTyontekija,
                          Toimipaikka, Tyontekija, VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          Z3_AdditionalCasUserFields, Z6_LastRequest, Z6_RequestCount, Z6_RequestLog, Z6_RequestSummary)
from varda.permission_groups import assign_object_permissions_to_taydennyskoulutus_groups
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
    # Check that number of OPH users does not exceed limit
    if Z3_AdditionalCasUserFields.objects.filter(approved_oph_staff=True).count() > 5:
        logger.error('There are too many users with approved_oph_staff=True.')


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def init_related_object_changed_table_task():
    related_change_tuple = (
        (
            VakaJarjestaja.get_name(), 'id', VakaJarjestaja.get_name(), 'id', None, None,
        ),
        (
            Toimipaikka.get_name(), 'id', Toimipaikka.get_name(), 'id',
            VakaJarjestaja.get_name(), 'vakajarjestaja_id',
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
def delete_toimipaikka_paakayttaja_groups():
    """
    TEMPORARY FUNCTION
    """
    with transaction.atomic():
        toimipaikka_oid_qs = Toimipaikka.objects.exclude(organisaatio_oid='').values('organisaatio_oid')
        group_qs = (Group.objects
                    .annotate(oid=Func(F('name'), Value(r'.*_(\d.*)'), Value(r'\1'), function='regexp_replace'))
                    .filter(oid__in=Subquery(toimipaikka_oid_qs), name__contains='PAAKAYTTAJA'))
        logger.info(f'Deleting {group_qs.count()} toimipaikka PAAKAYTTAJA groups')
        group_qs.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def create_missing_delete_events():
    """
    TEMPORARY FUNCTION
    """
    now = timezone.now()
    for model in (Henkilo, Lapsi, Huoltaja, Huoltajuussuhde, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Toimipaikka):
        # Gets list of object IDs that are missing a delete-event
        with transaction.atomic():
            qs = (model.history.values('id')
                  .annotate(history_type_list=StringAgg('history_type', ','),
                            live_id=Subquery(model.objects.filter(id=OuterRef('id')).values('id')))
                  .filter(~(Q(history_type_list__contains='+') & Q(history_type_list__contains='-')) &
                          Q(live_id__isnull=True))
                  .values_list('id', flat=True))

            for object_id in qs:
                # Get the last history record
                history_object = model.history.filter(id=object_id).order_by('-history_date').first()
                # Create delete event
                history_object.history_id = None
                history_object.history_date = now
                history_object.history_type = '-'
                history_object.save()

            logger.info(f'Created missing delete events for {qs.count()} {model.get_name()} objects.')
