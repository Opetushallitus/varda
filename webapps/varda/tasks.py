import datetime
import json
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import transaction
from django.db.models import Case, Count, DateField, F, Func, Q, Value, When
from django.db.models.functions import Cast
from django.utils import timezone
from guardian.models import GroupObjectPermission, UserObjectPermission
from knox.models import AuthToken

from varda import koodistopalvelu, oppijanumerorekisteri
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.cache import delete_paattymis_pvm_cache, set_paattymis_pvm_cache
from varda.clients.oppijanumerorekisteri_client import fetch_henkilo_data_for_oid_list
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.koodistot import Koodistot
from varda.enums.reporting import ReportStatus
from varda.excel_export import delete_excel_reports_earlier_than
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat
from varda.misc import list_to_chunks, memory_efficient_queryset_iterator, single_instance_task
from varda.misc_operations import set_paattymis_pvm_for_vakajarjestaja_data
from varda.models import (Aikaleima, BatchError, Henkilo, Huoltaja, Lapsi, MaksutietoHuoltajuussuhde, Toimipaikka,
                          Organisaatio, YearlyReportSummary, Z2_CodeTranslation, Z4_CasKayttoOikeudet, Z5_AuditLog,
                          Z6_LastRequest, Z6_RequestCount, Z6_RequestLog, Z6_RequestSummary,)
from varda.organisation_transformations import transfer_vaka_data_to_different_lapsi
from varda.permission_groups import get_oph_yllapitaja_group_name
from varda.permissions import reassign_all_lapsi_permissions


logger = logging.getLogger(__name__)


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
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    for permission_model in (UserObjectPermission, GroupObjectPermission,):
        permission_qs = (permission_model.objects
                         .distinct('object_pk', 'content_type')
                         .order_by('object_pk', 'content_type'))
        for permission in permission_qs.iterator():
            model_class = permission.content_type.model_class()
            if not model_class.objects.filter(id=permission.object_pk).exists():
                permission.delete()


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def change_paos_tallentaja_organization_task(jarjestaja_organisaatio_id, tuottaja_organisaatio_id):
    permissions.reassign_paos_permissions(jarjestaja_organisaatio_id, tuottaja_organisaatio_id)


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
def merge_duplicate_child_task(merge_list):
    """
    Merges duplicate Lapsi objects. Transfers Varhaiskasvatuspaatos, Varhaiskasvatussuhde and Maksutieto objects from
    old_lapsi to new_lapsi and deletes old_lapsi.

    Pre-requisite: Get a list of ID:s that are supposed to be merged and confirm the list with end-user

    :param merge_list: list of lists of Lapsi object IDs to be merged [[new_lapsi_id, old_lapsi_id], [...]]
    """
    from django.db import IntegrityError
    from varda.validators import validate_nested_list_with_two_ints

    validate_nested_list_with_two_ints(merge_list)
    counter = 0

    for item in merge_list:
        try:
            with transaction.atomic():
                try:
                    new_lapsi = Lapsi.objects.get(id=item[0])
                    old_lapsi = Lapsi.objects.get(id=item[1])
                except Lapsi.DoesNotExist:
                    logger.warning(f'No Lapsi object with ID {item[0]} or ID {item[1]}')
                    raise IntegrityError

                # Validate that Lapsi objects belong to the same Organisaatio
                if (new_lapsi.vakatoimija_id != old_lapsi.vakatoimija_id or
                        new_lapsi.oma_organisaatio_id != old_lapsi.oma_organisaatio_id or
                        new_lapsi.paos_organisaatio_id != old_lapsi.paos_organisaatio_id):
                    logger.warning(f'Cannot merge Lapsi objects {item} with different Organisaatio relation')
                    raise IntegrityError
                # Validate that Lapsi objects are not the same
                if new_lapsi.id == old_lapsi.id:
                    logger.warning(f'Cannot merge Lapsi with ID {new_lapsi.id} with itself')
                    raise IntegrityError

                # Transfer Varhaiskasvatuspaatos and Maksutieto objects
                transfer_vaka_data_to_different_lapsi(old_lapsi, new_lapsi)

                # Delete MaksutietoHuoltajuussuhde and Huoltajuussuhde objects before deleting Lapsi object
                MaksutietoHuoltajuussuhde.objects.filter(huoltajuussuhde__lapsi=old_lapsi).delete()
                old_lapsi.huoltajuussuhteet.all().delete()
                old_lapsi.delete()

                reassign_all_lapsi_permissions(new_lapsi)
                counter += 1
        except IntegrityError:
            logger.warning(f'IntegrityError for item {item}')
            continue
    logger.info(f'Merged {counter} Lapsi objects')


@shared_task
def change_lapsi_henkilo_task(change_list):
    """
    Modifies Henkilo relation of Lapsi object.

    Pre-requisite: Get a list of ID:s that are supposed to be changed and confirm the list with end-user

    :param change_list: list of lists of Lapsi and Henkilo IDs to be changed [[lapsi_id, henkilo_id], [...]]
    """
    from django.db import IntegrityError
    from varda.validators import validate_nested_list_with_two_ints

    validate_nested_list_with_two_ints(change_list)
    counter = 0

    for item in change_list:
        try:
            with transaction.atomic():
                try:
                    lapsi = Lapsi.objects.get(id=item[0])
                    henkilo = Henkilo.objects.get(id=item[1])
                except (Lapsi.DoesNotExist, Henkilo.DoesNotExist):
                    logger.warning(f'No Lapsi object with ID {item[0]} or no Henkilo object with ID {item[1]}')
                    raise IntegrityError

                # Validate that new Henkilo is not Tyontekija or Huoltaja
                if henkilo.tyontekijat.exists() or hasattr(henkilo, 'huoltaja'):
                    logger.warning(f'Henkilo {henkilo.id} cannot be Tyontekija or Huoltaja')
                    raise IntegrityError

                # Validate that new Henkilo does not have identical Lapsi object already
                if (henkilo.lapsi.filter(vakatoimija=lapsi.vakatoimija, oma_organisaatio=lapsi.oma_organisaatio,
                                         paos_organisaatio=lapsi.paos_organisaatio).exists()):
                    logger.warning(f'Henkilo {henkilo.id} cannot have identical Lapsi as {lapsi.id}')
                    raise IntegrityError

                lapsi.henkilo = henkilo
                lapsi.save()

                reassign_all_lapsi_permissions(lapsi)
                counter += 1
        except IntegrityError:
            logger.warning(f'IntegrityError for item {item}')
            continue
    logger.info(f'Modified {counter} Lapsi objects')


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
def create_yearly_reporting_summary(tilasto_pvm, poiminta_pvm, organisaatio_id):
    from varda.misc_queries import (get_yearly_report_organisaatio_count, get_yearly_report_toimipaikka_count,
                                    get_yearly_report_kielipainotus_count,
                                    get_yearly_report_toiminnallinen_painotus_count, get_yearly_report_vaka_data,
                                    get_yearly_report_maksutieto_data)

    tilasto_pvm = datetime.datetime.strptime(tilasto_pvm, '%Y-%m-%dT%H:%M:%S').date()

    if organisaatio_id:
        organisaatio_obj = Organisaatio.objects.get(id=organisaatio_id)
        vakajarjestaja_count = 1
    else:
        organisaatio_obj = None
        vakajarjestaja_count = get_yearly_report_organisaatio_count(poiminta_pvm, tilasto_pvm)

    vakajarjestaja_active = True
    if organisaatio_obj:
        if organisaatio_obj.paattymis_pvm is None:
            vakajarjestaja_active = organisaatio_obj.alkamis_pvm <= tilasto_pvm
        else:
            vakajarjestaja_active = organisaatio_obj.alkamis_pvm <= tilasto_pvm <= organisaatio_obj.paattymis_pvm

    toimipaikka_count = get_yearly_report_toimipaikka_count(poiminta_pvm, tilasto_pvm, organisaatio_id)
    kielipainotus_count = get_yearly_report_kielipainotus_count(poiminta_pvm, tilasto_pvm, organisaatio_id)
    toiminnallinen_painotus_count = get_yearly_report_toiminnallinen_painotus_count(poiminta_pvm, tilasto_pvm,
                                                                                    organisaatio_id)

    # Nested dict: {paos (None, True, False): {vuorohoito (None, True, False): {...}}}
    vaka_data = get_yearly_report_vaka_data(poiminta_pvm, tilasto_pvm, organisaatio_id)

    vakasuhde_count = vaka_data.get(None, {}).get(None, {}).get('suhde_count', 0)
    oma_vakasuhde_count = vaka_data.get(False, {}).get(None, {}).get('suhde_count', 0)
    paos_vakasuhde_count = vaka_data.get(True, {}).get(None, {}).get('suhde_count', 0)

    vakapaatos_count = vaka_data.get(None, {}).get(None, {}).get('paatos_count', 0)
    oma_vakapaatos_count = vaka_data.get(False, {}).get(None, {}).get('paatos_count', 0)
    paos_vakapaatos_count = vaka_data.get(True, {}).get(None, {}).get('paatos_count', 0)

    vuorohoito_vakapaatos_count = vaka_data.get(None, {}).get(True, {}).get('paatos_count', 0)
    oma_vuorohoito_vakapaatos_count = vaka_data.get(False, {}).get(True, {}).get('paatos_count', 0)
    paos_vuorohoito_vakapaatos_count = vaka_data.get(True, {}).get(True, {}).get('paatos_count', 0)

    lapsi_count = vaka_data.get(None, {}).get(None, {}).get('lapsi_count', 0)
    oma_lapsi_count = vaka_data.get(False, {}).get(None, {}).get('lapsi_count', 0)
    paos_lapsi_count = vaka_data.get(True, {}).get(None, {}).get('lapsi_count', 0)

    henkilo_count = vaka_data.get(None, {}).get(None, {}).get('henkilo_count', 0)
    oma_henkilo_count = vaka_data.get(False, {}).get(None, {}).get('henkilo_count', 0)
    paos_henkilo_count = vaka_data.get(True, {}).get(None, {}).get('henkilo_count', 0)

    # Nested dict: {paos (None, True, False): {maksun_peruste (None, 'mp01', 'mp02', 'mp03'): {...}}}
    maksutieto_data = get_yearly_report_maksutieto_data(poiminta_pvm, tilasto_pvm, organisaatio_id)

    maksutieto_count = maksutieto_data.get(None, {}).get(None, {}).get('maksutieto_count', 0)
    maksutieto_mp1_count = maksutieto_data.get(None, {}).get('mp01', {}).get('maksutieto_count', 0)
    maksutieto_mp2_count = maksutieto_data.get(None, {}).get('mp02', {}).get('maksutieto_count', 0)
    maksutieto_mp3_count = maksutieto_data.get(None, {}).get('mp03', {}).get('maksutieto_count', 0)

    oma_maksutieto_count = maksutieto_data.get(False, {}).get(None, {}).get('maksutieto_count', 0)
    oma_maksutieto_mp1_count = maksutieto_data.get(False, {}).get('mp01', {}).get('maksutieto_count', 0)
    oma_maksutieto_mp2_count = maksutieto_data.get(False, {}).get('mp02', {}).get('maksutieto_count', 0)
    oma_maksutieto_mp3_count = maksutieto_data.get(False, {}).get('mp03', {}).get('maksutieto_count', 0)

    paos_maksutieto_count = maksutieto_data.get(True, {}).get(None, {}).get('maksutieto_count', 0)
    paos_maksutieto_mp1_count = maksutieto_data.get(True, {}).get('mp01', {}).get('maksutieto_count', 0)
    paos_maksutieto_mp2_count = maksutieto_data.get(True, {}).get('mp02', {}).get('maksutieto_count', 0)
    paos_maksutieto_mp3_count = maksutieto_data.get(True, {}).get('mp03', {}).get('maksutieto_count', 0)

    updated_values = {
        'status': ReportStatus.FINISHED.value,
        'vakajarjestaja_count': vakajarjestaja_count,
        'vakajarjestaja_is_active': vakajarjestaja_active,
        'poiminta_pvm': poiminta_pvm,
        'toimipaikka_count': toimipaikka_count,
        'kielipainotus_count': kielipainotus_count,
        'toimintapainotus_count': toiminnallinen_painotus_count,
        'yhteensa_henkilo_count': henkilo_count,
        'yhteensa_lapsi_count': lapsi_count,
        'yhteensa_varhaiskasvatussuhde_count': vakasuhde_count,
        'yhteensa_varhaiskasvatuspaatos_count': vakapaatos_count,
        'yhteensa_vuorohoito_count': vuorohoito_vakapaatos_count,
        'oma_henkilo_count': oma_henkilo_count,
        'oma_lapsi_count': oma_lapsi_count,
        'oma_varhaiskasvatussuhde_count': oma_vakasuhde_count,
        'oma_varhaiskasvatuspaatos_count': oma_vakapaatos_count,
        'oma_vuorohoito_count': oma_vuorohoito_vakapaatos_count,
        'paos_henkilo_count': paos_henkilo_count,
        'paos_lapsi_count': paos_lapsi_count,
        'paos_varhaiskasvatussuhde_count': paos_vakasuhde_count,
        'paos_varhaiskasvatuspaatos_count': paos_vakapaatos_count,
        'paos_vuorohoito_count': paos_vuorohoito_vakapaatos_count,
        'yhteensa_maksutieto_count': maksutieto_count,
        'yhteensa_maksutieto_mp01_count': maksutieto_mp1_count,
        'yhteensa_maksutieto_mp02_count': maksutieto_mp2_count,
        'yhteensa_maksutieto_mp03_count': maksutieto_mp3_count,
        'oma_maksutieto_count': oma_maksutieto_count,
        'oma_maksutieto_mp01_count': oma_maksutieto_mp1_count,
        'oma_maksutieto_mp02_count': oma_maksutieto_mp2_count,
        'oma_maksutieto_mp03_count': oma_maksutieto_mp3_count,
        'paos_maksutieto_count': paos_maksutieto_count,
        'paos_maksutieto_mp01_count': paos_maksutieto_mp1_count,
        'paos_maksutieto_mp02_count': paos_maksutieto_mp2_count,
        'paos_maksutieto_mp03_count': paos_maksutieto_mp3_count
    }

    YearlyReportSummary.objects.update_or_create(vakajarjestaja_id=organisaatio_id, tilasto_pvm=tilasto_pvm,
                                                 defaults=updated_values)


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
def get_ukranian_child_statistics(active_since='2022-02-24', swedish=False):
    """
    Get number of Ukranian children per each municipality that started in vaka after active_since parameter
    TEMPORARY FUNCTION
    """
    try:
        active_since = datetime.datetime.strptime(active_since, '%Y-%m-%d').date()
    except ValueError:
        logger.error(f'Could not parse active_since: {active_since}')
        return None

    asiointikieli_filter = (Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__asiointikieli_koodi__icontains='sv')
                            if swedish else Q())

    # Get list of henkilo_oid that have active Varhaiskasvatuspaatos and Varhaiskasvatussuhde after active since
    # and no previous Varhaiskasvatuspaatos objects
    today = datetime.datetime.today()
    oid_list = (Henkilo.objects
                .filter(Q(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__gte=active_since) &
                        (Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__isnull=True) |
                         Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__gt=today)) &
                        Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__gte=active_since) &
                        (Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                         Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gt=today)) &
                        asiointikieli_filter)
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

    code_language = 'sv' if swedish else 'fi'
    kunta_dict = {'total': {'amount': len(valid_oid_list)}}
    for henkilo_oid in valid_oid_list:
        kunta_code_list = (Toimipaikka.objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid=henkilo_oid)
                           .distinct('kunta_koodi').values_list('kunta_koodi', flat=True))
        for kunta_code in kunta_code_list:
            kunta_translation = getattr(Z2_CodeTranslation.objects
                                        .filter(language__iexact=code_language, code__code_value=kunta_code,
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
