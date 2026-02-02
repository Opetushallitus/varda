import datetime
import json
import logging

from collections import defaultdict
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.db import connection, transaction
from django.db.models import Case, Count, DateField, F, Func, Max, Q, Value, When, OuterRef, Exists

from django.db.models.functions import Cast
from django.utils import timezone
from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.shortcuts import get_objects_for_group
from knox.models import AuthToken
from psycopg import sql

from varda import koodistopalvelu, lokalisointipalvelu, oppijanumerorekisteri
from varda import organisaatiopalvelu
from varda import permission_groups
from varda import permissions
from varda.audit_log import audit_log
from varda.cache import delete_paattymis_pvm_cache, set_paattymis_pvm_cache
from varda.clients.oppijanumerorekisteri_client import fetch_henkilo_data_for_oid_list, get_henkilo_by_henkilotunnus
from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.custom_celery import custom_shared_task
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.data_category import DataCategory
from varda.enums.koodistot import Koodistot
from varda.enums.lokalisointi import Lokalisointi
from varda.enums.reporting import ReportStatus
from varda.excel_export import delete_excel_reports_earlier_than
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat, get_onr_lapset
from varda.misc import (
    encrypt_string,
    hash_string,
    list_to_chunks,
    memory_efficient_queryset_iterator,
    get_person_count_per_kunta_dict,
)
from varda.misc_operations import set_paattymis_pvm_for_vakajarjestaja_data
from varda.models import (
    Aikaleima,
    BatchError,
    Henkilo,
    Huoltaja,
    Lapsi,
    Toimipaikka,
    Tutkinto,
    Organisaatio,
    ToiminnallinenPainotus,
    KieliPainotus,
    Palvelussuhde,
    Varhaiskasvatussuhde,
    Varhaiskasvatuspaatos,
    Tukipaatos,
    TukipaatosAikavali,
    PidempiPoissaolo,
    Z2_Code,
    Z2_CodeTranslation,
    Z2_Koodisto,
    Z4_CasKayttoOikeudet,
    Z5_AuditLog,
    Z6_LastRequest,
    Z6_RequestCount,
    Z6_RequestLog,
    Z6_RequestSummary,
)
from varda.permission_groups import get_oph_yllapitaja_group_name
from varda.permissions import reassign_all_lapsi_permissions, assign_lapsi_permissions
from varda.viestintapalvelu import (
    send_no_paakayttaja_message,
    send_no_transfers_message,
    send_puutteelliset_tiedot_message,
    update_message_targets_and_paakayttaja_status,
)


logger = logging.getLogger(__name__)


@custom_shared_task()
def add(x, y):
    """
    This is currently only needed for testing, don't remove!
    """
    return x + y


@custom_shared_task(single_instance=True)
def run_management_commands():
    """
    To be run periodically, e.g. to clean out expired sessions
    """
    call_command("clearsessions", verbosity=0)
    call_command("django_cas_ng_clean_sessions", verbosity=0)


@custom_shared_task(single_instance=True)
def remove_all_auth_tokens():
    """
    Delete all API tokens periodically so that users are forced to re-login and permission updates are fetched from
    Opintopolku.
    """
    AuthToken.objects.all().delete()


@custom_shared_task(single_instance=True)
def update_oph_staff_to_vakajarjestaja_groups(user_id=None, organisaatio_oid=None):
    permission_groups.add_oph_staff_to_vakajarjestaja_katselija_groups(user_id=user_id, organisaatio_oid=organisaatio_oid)


@custom_shared_task(single_instance=True)
def update_vakajarjestajat():
    organisaatiopalvelu.fetch_organisaatio_info()


@custom_shared_task(single_instance=True)
def check_henkilot_without_vtj_yksilointi():
    oppijanumerorekisteri.check_henkilot_without_vtj_yksilointi()


@custom_shared_task(single_instance=True)
def update_modified_henkilot():
    oppijanumerorekisteri.fetch_and_update_modified_henkilot()


@custom_shared_task(single_instance=True)
def update_toimipaikat_in_organisaatiopalvelu_task():
    organisaatiopalvelu.update_toimipaikat_in_organisaatiopalvelu()


@custom_shared_task(single_instance=True)
def fetch_huoltajat_task():
    oppijanumerorekisteri.fetch_huoltajat()


@custom_shared_task(single_instance=True)
def create_onr_lapsi_huoltajat_task():
    create_onr_lapsi_huoltajat(create_all_vakajarjestajat=True)


@custom_shared_task(single_instance=True)
def update_all_organisaatio_service_originated_organisations_task():
    """
    Updates all organisations which data is managed by organisaatio service
    :return: None
    """
    organisaatiopalvelu.update_all_organisaatio_service_organisations()


@custom_shared_task(single_instance=True)
def update_henkilot_with_oid():
    oppijanumerorekisteri.fetch_henkilot_with_oid()


@custom_shared_task(single_instance=True)
def update_henkilo_data_by_oid(henkilo_oid, henkilo_id, is_fetch_huoltajat=False):
    oppijanumerorekisteri.fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id)
    if is_fetch_huoltajat:
        oppijanumerorekisteri.update_huoltajuussuhde(henkilo_oid)


@custom_shared_task(single_instance=True)
def update_huoltajasuhteet_task():
    """
    Updates huoltajasuhde changes from oppijanumerorekisteri
    :return: None
    """
    oppijanumerorekisteri.update_huoltajuussuhteet()


@custom_shared_task(single_instance=True)
def send_audit_log_to_aws_task():
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        audit_log.collect_audit_log_and_send_to_aws()


@custom_shared_task(single_instance=True)
def send_alive_log_to_aws_task():
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        audit_log.send_alive_log_to_aws()


@custom_shared_task(single_instance=True)
def send_data_access_log_to_aws_task():
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        audit_log.send_data_access_log()


@custom_shared_task(single_instance=True)
def guardian_clean_orphan_object_permissions():
    """
    Delete orphan permission instances that were not deleted for some reason when object was deleted
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    for permission_model in (
        UserObjectPermission,
        GroupObjectPermission,
    ):
        permission_qs = permission_model.objects.distinct("object_pk", "content_type").order_by("object_pk", "content_type")
        for permission in permission_qs.iterator():
            model_class = permission.content_type.model_class()
            if not model_class.objects.filter(id=permission.object_pk).exists():
                permission.delete()


@custom_shared_task(single_instance=True)
def change_paos_tallentaja_organization_task(jarjestaja_organisaatio_id, tuottaja_organisaatio_id):
    permissions.reassign_paos_permissions(jarjestaja_organisaatio_id, tuottaja_organisaatio_id)


@custom_shared_task(single_instance=True)
def update_koodistot_task():
    with transaction.atomic():
        # Check if there is any data that should not be stored anymore
        old_koodisto_qs = Z2_Koodisto.objects.filter(~Q(name__in=Koodistot.list() + Lokalisointi.list()))
        if old_koodisto_qs.exists():
            Z2_CodeTranslation.objects.filter(code__koodisto__in=old_koodisto_qs).delete()
            Z2_Code.objects.filter(koodisto__in=old_koodisto_qs).delete()
            old_koodisto_qs.delete()

    koodistopalvelu.update_koodistot()
    lokalisointipalvelu.update_lokalisointi_data()


@custom_shared_task(single_instance=True)
def remove_address_information_from_tyontekijat_only_task():
    henkilot = Henkilo.objects.filter(
        ~Q(kotikunta_koodi="") | ~Q(katuosoite="") | ~Q(postinumero="") | ~Q(postitoimipaikka=""),
        huoltaja__isnull=True,
        lapsi__isnull=True,
        tyontekijat__isnull=False,
    ).distinct()

    # Loop through each Henkilo so that save signals are processed correctly
    for henkilo in henkilot:
        henkilo.remove_address_information()
        henkilo.save()


@custom_shared_task(single_instance=True)
def after_data_import_task():
    """
    Task that is run in QA environment after data import.
    Currently updates the anonymized toimipaikat to organisaatiopalvelu, and fetches the henkilo-data for "ONR-lapset".
    """
    if settings.PRODUCTION_ENV:
        logger.error("Running this task in production is not allowed!")
        return None

    # Push anonymized toimipaikat to organisaatiopalvelu
    toimipaikka_filter = Q(toimintamuoto_koodi__iexact="tm02") | Q(toimintamuoto_koodi__iexact="tm03")
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu(toimipaikka_filter=toimipaikka_filter)

    # Add "ONR-lapset"
    for henkilo in get_onr_lapset():
        henkilo_result = get_henkilo_by_henkilotunnus(**henkilo)
        henkilo_data = henkilo_result["result"]
        try:
            henkilo_obj = Henkilo.objects.create(
                etunimet=henkilo_data.get("etunimet", henkilo["etunimet"]),
                kutsumanimi=henkilo_data.get("kutsumanimi", henkilo["kutsumanimi"]),
                sukunimi=henkilo_data.get("sukunimi", henkilo["sukunimi"]),
                syntyma_pvm=henkilo_data.get("syntymaaika", None),
                henkilo_oid=henkilo_data.get("oidHenkilo", None),
                henkilotunnus=encrypt_string(henkilo["henkilotunnus"]),
                henkilotunnus_unique_hash=hash_string(henkilo["henkilotunnus"]),
            )
            Lapsi.objects.create(henkilo=henkilo_obj)
        except Exception as e:
            logger.error(e)

    fetch_huoltajat_task.delay()
    set_all_vaka_avustajat_kelpoisuus_true_to_false.delay()


@custom_shared_task(single_instance=True)
def delete_request_log_older_than_arg_days_task(days):
    timestamp_lower_limit = datetime.datetime.now() - datetime.timedelta(days=days)
    timestamp_lower_limit = timestamp_lower_limit.replace(tzinfo=datetime.timezone.utc)

    Z6_RequestLog.objects.filter(timestamp__lt=timestamp_lower_limit).delete()


@custom_shared_task(single_instance=True)
def delete_excel_reports_older_than_arg_hours_task(hours):
    timestamp_lower_limit = datetime.datetime.now() - datetime.timedelta(hours=hours)
    timestamp_lower_limit = timestamp_lower_limit.replace(tzinfo=datetime.timezone.utc)
    delete_excel_reports_earlier_than(timestamp_lower_limit)


@custom_shared_task(single_instance=True)
def update_toimipaikka_in_organisaatiopalvelu_by_id_task(toimipaikka_id):
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu(toimipaikka_filter=Q(pk=toimipaikka_id))


@custom_shared_task(single_instance=True)
def force_update_toimipaikat_in_organisaatiopalvelu_task():
    organisaatiopalvelu.update_all_toimipaikat_in_organisaatiopalvelu()


@custom_shared_task(single_instance=True)
def remove_birthdate_from_huoltajat_only_task():
    henkilo_qs = Henkilo.objects.filter(
        syntyma_pvm__isnull=False, huoltaja__isnull=False, tyontekijat__isnull=True, lapsi__isnull=True
    ).distinct()

    # Loop through each Henkilo so that save signals are processed correctly
    for henkilo in memory_efficient_queryset_iterator(henkilo_qs):
        henkilo.syntyma_pvm = None
        henkilo.save()


@custom_shared_task(single_instance=True)
def delete_huoltajat_without_relations_task():
    """
    Task that deletes Huoltaja objects that have no relations to Lapsi (Lapsi has been deleted).
    """
    huoltaja_qs = Huoltaja.objects.filter(huoltajuussuhteet__isnull=True)
    huoltaja_qs.delete()


@custom_shared_task(single_instance=True)
def delete_henkilot_without_relations_task():
    """
    Task that deletes Henkilo objects without relations to Lapsi, Huoltaja or Tyontekija objects. Henkilo object must
    be older than certain limit, so recently created objects are not deleted.
    """
    created_datetime_limit = timezone.now() - datetime.timedelta(days=settings.DELETE_HENKILO_WITHOUT_ROLE_IN_DAYS)
    henkilo_qs = Henkilo.objects.filter(
        lapsi__isnull=True, tyontekijat__isnull=True, huoltaja__isnull=True, luonti_pvm__lt=created_datetime_limit
    )
    for henkilo in henkilo_qs:
        BatchError.objects.filter(henkilo=henkilo).delete()
        BatchError.objects.filter(henkilo_duplicate=henkilo).delete()
        Tutkinto.objects.filter(henkilo=henkilo).delete()
        henkilo.delete()

    cleanup_Z10_KelaVarhaiskasvatussuhde_task.delay()


@custom_shared_task(single_instance=True)
def update_last_request_table_task(init=False):
    """
    Updates Z6_LastRequest table by going through existing Z6_RequestLog objects. By default goes through requests
    from the last 24 hours.

    :param init: True if table is initialized and all Z6_RequestLog objects are considered
    """
    timestamp_filter = Q() if init else Q(timestamp__gte=timezone.now() - datetime.timedelta(days=1))
    successful_options = [
        (Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST), True),
        (~Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST), False),
    ]

    for response_code_filter, is_successful in successful_options:
        request_log_qs = (
            Z6_RequestLog.objects.filter(timestamp_filter & response_code_filter)
            .distinct("user", "vakajarjestaja", "lahdejarjestelma", "data_category")
            .order_by("user", "vakajarjestaja", "lahdejarjestelma", "data_category", "-timestamp")
            .values("user", "vakajarjestaja", "lahdejarjestelma", "data_category", "timestamp")
        )

        for request_log in request_log_qs:
            last_request_defaults = (
                {"last_successful": request_log["timestamp"]}
                if is_successful
                else {"last_unsuccessful": request_log["timestamp"]}
            )
            Z6_LastRequest.objects.update_or_create(
                user_id=request_log["user"],
                vakajarjestaja_id=request_log["vakajarjestaja"],
                lahdejarjestelma=request_log["lahdejarjestelma"],
                data_category=request_log["data_category"],
                defaults=last_request_defaults,
            )


@custom_shared_task(single_instance=True)
def update_request_summary_table_task():
    """
    Updates Z6_RequestSummary table by going through existing Z6_RequestLog objects.
    """
    now = timezone.now()
    aikaleima, created_aikaleima = Aikaleima.objects.get_or_create(
        avain=AikaleimaAvain.REQUEST_SUMMARY_LAST_UPDATE.value, defaults={"aikaleima": now}
    )
    if created_aikaleima:
        # If Aikaleima was created, e.g. we are initializing Z6_RequestSummary, go through last 100 days
        start_timestamp = now - datetime.timedelta(days=100)
    else:
        start_timestamp = aikaleima.aikaleima
    current_date = start_timestamp.date()
    today = now.date()

    # Format: [[field, filters], [field, filters],]
    group_by_list = [
        ["user_id", {"user__isnull": False}],
        ["vakajarjestaja_id", {"vakajarjestaja__isnull": False}],
        ["lahdejarjestelma", {"lahdejarjestelma__isnull": False}],
        ["request_url_simple", {}],
    ]
    # Start going through Z6_RequestLog instances day by day until we reach today
    # Summaries are always updated for past days
    while current_date < today:
        # Go through group_by rules, currently summaries are grouped by user, vakajarjestaja, lahdejarjestelma and URL
        for group_by_value in group_by_list:
            value_field = group_by_value[0]
            filters = group_by_value[1]

            values = ["request_method", "response_code"]
            if value_field != "request_url_simple":
                values.append(value_field)

            # QuerySet that groups Z6_RequestLog instances by defined fields and a simplified URL
            # e.g. /api/v1/varhaiskasvatuspaatokset/123/ -> /api/v1/varhaiskasvatuspaatokset/*/
            # PostgreSQL specific functionality (regexp_replace)
            request_log_qs = (
                Z6_RequestLog.objects.values(*values, "timestamp__date")
                .annotate(
                    request_url_simple=Case(
                        When(
                            request_url__regex=r"^.*\/(\d*(:.*)?|[\d.]*)\/.*$",
                            then=Func(
                                F("request_url"), Value(r"\/(\d*(:.*)?|[\d.]*)\/"), Value("/*/"), function="regexp_replace"
                            ),
                        ),
                        default=F("request_url"),
                    ),
                    date=Cast("timestamp", DateField()),
                    count=Count("id"),
                )
                .values(*values, "count", "date", "request_url_simple")
                .filter(timestamp__date=current_date, **filters)
                .order_by(value_field)
            )

            current_group = None
            request_summary = None
            # Start going through grouped Z6_RequestLog instances and create Z6_RequestSummary and Z6_RequestCount
            # instances
            for request_log in request_log_qs:
                if request_log.get(value_field) != current_group:
                    current_group = request_log.get(value_field)
                    request_summary, created_summary = Z6_RequestSummary.objects.update_or_create(
                        summary_date=current_date,
                        **{value_field: current_group},
                        defaults={"successful_count": 0, "unsuccessful_count": 0},
                    )
                    if not created_summary:
                        # If summary already existed, delete existing Z6_RequestCount instances
                        request_summary.request_counts.all().delete()

                # Each Z6_RequestCount instance has related Z6_RequestCount instances which provide additional
                # information on requests that succeeded or failed
                Z6_RequestCount.objects.create(
                    request_summary=request_summary,
                    request_url_simple=request_log.get("request_url_simple"),
                    request_method=request_log.get("request_method"),
                    response_code=request_log.get("response_code"),
                    count=request_log.get("count"),
                )

                # Update the _count field of Z6_RequestSummary instance
                if request_log.get("response_code") in SUCCESSFUL_STATUS_CODE_LIST:
                    request_summary.successful_count += request_log.get("count")
                else:
                    request_summary.unsuccessful_count += request_log.get("count")
                request_summary.save()

        current_date += datetime.timedelta(days=1)

    # Update Aikaleima instance
    aikaleima.aikaleima = now
    aikaleima.save()


@custom_shared_task()
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
                    logger.warning(f"No Lapsi object with ID {item[0]} or no Henkilo object with ID {item[1]}")
                    raise IntegrityError

                # Validate that new Henkilo is not Tyontekija or Huoltaja
                if henkilo.tyontekijat.exists() or hasattr(henkilo, "huoltaja"):
                    logger.warning(f"Henkilo {henkilo.id} cannot be Tyontekija or Huoltaja")
                    raise IntegrityError

                # Validate that new Henkilo does not have identical Lapsi object already
                if henkilo.lapsi.filter(
                    vakatoimija=lapsi.vakatoimija,
                    oma_organisaatio=lapsi.oma_organisaatio,
                    paos_organisaatio=lapsi.paos_organisaatio,
                ).exists():
                    logger.warning(f"Henkilo {henkilo.id} cannot have identical Lapsi as {lapsi.id}")
                    raise IntegrityError

                lapsi.henkilo = henkilo
                lapsi.save()

                reassign_all_lapsi_permissions(lapsi)
                counter += 1
        except IntegrityError:
            logger.warning(f"IntegrityError for item {item}")
            continue
    logger.info(f"Modified {counter} Lapsi objects")


@custom_shared_task(single_instance=True)
def general_monitoring_task():
    """
    This task is used to perform various monitoring tasks
    """
    # Check that number of super/staff users does not exceed limit
    if User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count() > settings.STAFF_USER_LIMIT:
        logger.error("There are too many users with is_staff=True or is_superuser=True.")

    # Check that number of OPH users does not exceed limit
    oph_yllapitaja_group = Group.objects.filter(name=get_oph_yllapitaja_group_name()).first()
    if oph_yllapitaja_group and oph_yllapitaja_group.user_set.count() > settings.OPH_USER_LIMIT:
        logger.error("There are too many OPH staff users.")

    # Check that an API is not systematically browsed through using the page-parameter
    # This task is run every hour so check the last 2 hours
    # Exclude LUOVUTUSPALVELU users
    # Exclude error-report-x paths
    two_hours_ago = timezone.now() - datetime.timedelta(hours=2)
    # PostgreSQL specific functionality (regexp_replace)
    page_queryset = (
        Z5_AuditLog.objects.exclude(user__groups__name__icontains=Z4_CasKayttoOikeudet.LUOVUTUSPALVELU)
        .exclude(successful_get_request_path__icontains="error-report-")
        .filter(time_of_event__gte=two_hours_ago, query_params__icontains="page=")
        .values("user", "successful_get_request_path")
        .annotate(
            page_number_count=Count(
                Func(F("query_params"), Value(r".*page=(\d*).*"), Value("\\1"), function="regexp_replace"), distinct=True
            )
        )
        .values("user", "successful_get_request_path", "page_number_count")
        .filter(page_number_count__gt=20)
    )
    if page_queryset.exists():
        logger.error(f"The following APIs are browsed through: {page_queryset}")


@custom_shared_task(single_instance=True)
def reset_superuser_permissions_task():
    """
    Sets is_superuser and is_staff fields False for CAS users that have either field as True.
    """
    for user in User.objects.filter(Q(is_superuser=True) | Q(is_staff=True)):
        if hasattr(user, "additional_cas_user_fields"):
            user.is_superuser = False
            user.is_staff = False
            user.save()


@custom_shared_task(single_instance=True)
def set_paattymis_pvm_for_vakajarjestaja_data_task(vakajarjestaja_id, paattymis_pvm, identifier):
    try:
        paattymis_pvm = datetime.datetime.strptime(paattymis_pvm, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Could not parse paattymis_pvm: {paattymis_pvm}")
        return None

    vakajarjestaja = Organisaatio.objects.filter(id=vakajarjestaja_id).first()
    if not vakajarjestaja:
        logger.error(f"Could not find vakajarjestaja with id: {vakajarjestaja_id}")
        return None

    try:
        result = set_paattymis_pvm_for_vakajarjestaja_data(vakajarjestaja, paattymis_pvm)
        result["status"] = ReportStatus.FINISHED.value
        set_paattymis_pvm_cache(identifier, result)
        logger.info(
            f"Set paattymis_pvm {paattymis_pvm} for data of vakajarjestaja with ID {vakajarjestaja_id}: {json.dumps(result)}"
        )
    except Exception as exception:
        delete_paattymis_pvm_cache(identifier)
        raise exception


@custom_shared_task(single_instance=True)
def get_ukranian_child_statistics(active_since="2022-02-24", swedish=False, has_kotikunta=False):
    """
    Get number of Ukranian children per each municipality that started in vaka after active_since parameter
    TEMPORARY FUNCTION
    """
    try:
        active_since = datetime.datetime.strptime(active_since, "%Y-%m-%d").date()
    except ValueError:
        logger.error(f"Could not parse active_since: {active_since}")
        return None

    toimintakieli_filter = (
        Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__toimintakieli_koodi__icontains="sv")
        if swedish
        else Q()
    )
    kotikunta_filter = (
        Q(kotikunta_koodi__isnull=False) & ~Q(kotikunta_koodi="") & ~Q(kotikunta_koodi__in=["198", "199", "200", "999"])
        if has_kotikunta
        else Q()
    )

    # Get list of henkilo_oid that have active Varhaiskasvatuspaatos and Varhaiskasvatussuhde after active since
    # and no previous Varhaiskasvatuspaatos objects
    today = datetime.datetime.today()
    oid_list = (
        Henkilo.objects.filter(
            Q(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__gte=active_since)
            & (
                Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__isnull=True)
                | Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__gt=today)
            )
            & Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__gte=active_since)
            & (
                Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True)
                | Q(lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gt=today)
            )
            & toimintakieli_filter
            & kotikunta_filter
        )
        .exclude(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__lt=active_since)
        .distinct("henkilo_oid")
        .values_list("henkilo_oid", flat=True)
    )
    oid_chunk_list = list_to_chunks(oid_list, 5000)

    valid_oid_list = []
    for oid_chunk in oid_chunk_list:
        result = fetch_henkilo_data_for_oid_list(oid_chunk)
        for henkilo_data in result:
            for kansalaisuus in henkilo_data.get("kansalaisuus", []):
                # https://koodistot.suomi.fi/codescheme;registryCode=jhs;schemeCode=valtio_1_20120101
                if kansalaisuus["kansalaisuusKoodi"] == "804":
                    valid_oid_list.append(henkilo_data["oidHenkilo"])
                    break

    code_language = "sv" if swedish else "fi"
    kunta_dict = get_person_count_per_kunta_dict(valid_oid_list, code_language)

    result_str = "kunta_koodi,kunta_nimi,lapsi_lkm,lapsi_lkm_ika_0_3,lapsi_lkm_ika_yli_3"
    for key, value in kunta_dict.items():
        name = value.get("name", "")
        amount = value.get("amount", "")
        amount_age_lte_3 = value.get("amount_age_lte_3", "")
        amount_age_gt_3 = value.get("amount_age_gt_3", "")
        result_str += f";{key},{name},{amount},{amount_age_lte_3},{amount_age_gt_3}"

    return result_str


@custom_shared_task(single_instance=True)
def vacuum_database_task(table_name=None):
    table_list = []
    if table_name:
        table_list.append(table_name)
    else:
        # If table_name is not defined, vacuum and analyze all model tables from all apps
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                table_list.append(model._meta.db_table)

    with connection.cursor() as cursor:
        for table in table_list:
            cursor.execute(sql.SQL("VACUUM ANALYZE {};").format(sql.Identifier(table)))


@custom_shared_task(single_instance=True)
def update_message_targets_and_paakayttaja_status_task():
    update_message_targets_and_paakayttaja_status()


@custom_shared_task(single_instance=True)
def send_no_paakayttaja_message_task():
    send_no_paakayttaja_message()


@custom_shared_task(single_instance=True)
def send_puutteelliset_tiedot_message_task():
    send_puutteelliset_tiedot_message()


@custom_shared_task(single_instance=True)
def send_no_transfers_message_task():
    send_no_transfers_message()


@custom_shared_task(single_instance=True)
def init_last_request_data_category():
    """
    TEMPORARY TASK
    """
    last_request_qs = (
        Z6_LastRequest.objects.values("vakajarjestaja")
        .filter(vakajarjestaja__isnull=False)
        .annotate(
            last_successful_max=Max("last_successful"),
            last_unsuccessful_max=Max("last_unsuccessful"),
            user_instance_id=Max("user_id"),
        )
        .values("vakajarjestaja", "last_successful_max", "last_unsuccessful_max", "user_instance_id")
    )
    for last_request in last_request_qs:
        for data_category in [DataCategory.VARHAISKASVATUS.value, DataCategory.HENKILOSTO.value]:
            Z6_LastRequest.objects.update_or_create(
                vakajarjestaja_id=last_request["vakajarjestaja"],
                user_id=last_request["user_instance_id"],
                data_category=data_category,
                defaults={
                    "last_successful": last_request["last_successful_max"],
                    "last_unsuccessful": last_request["last_unsuccessful_max"],
                },
            )


@custom_shared_task(single_instance=True)
def set_all_vaka_avustajat_kelpoisuus_true_to_false():
    """
    DO NOT REMOVE!, this task in run after anonymization
    """
    from varda.models import Tyoskentelypaikka
    from varda.constants import TEHTAVANIMIKE_KOODI_VAKA_AVUSTAJA

    tyoskentelypaikat = Tyoskentelypaikka.objects.filter(
        tehtavanimike_koodi=TEHTAVANIMIKE_KOODI_VAKA_AVUSTAJA, kelpoisuus_kytkin=True
    )
    update_count = tyoskentelypaikat.update(kelpoisuus_kytkin=False, muutos_pvm=timezone.now())
    logger.info(f"Tyoskentelypaikat (vaka-avustaja) kelpoisuus updated. count={update_count}")


@custom_shared_task(single_instance=True)
def set_toimipaikkas_inactive_painotus_kytkin_to_false():
    """
    set varda_toimipaikka [toiminnallinen/kieli]painotus_kytkin to false
    if toimipaikka is not found in varda_[toiminnallinen/kieli]painotus table
    """
    # Update Toimipaikka toiminnallinenpainotus_kytkin
    toiminnallinenpainotus_toimipaikka_ids = ToiminnallinenPainotus.objects.values_list("toimipaikka__id", flat=True).distinct()
    update_count_toiminnallinenpainotus = (
        Toimipaikka.objects.filter(toiminnallinenpainotus_kytkin=True)
        .exclude(pk__in=toiminnallinenpainotus_toimipaikka_ids)
        .update(toiminnallinenpainotus_kytkin=False, muutos_pvm=timezone.now())
    )

    # Update Toimipaikka kielipainotus_kytkin
    kielipainotus_toimipaikka_ids = KieliPainotus.objects.values_list("toimipaikka__id", flat=True).distinct()
    update_count_kielipainotus = (
        Toimipaikka.objects.filter(kielipainotus_kytkin=True)
        .exclude(pk__in=kielipainotus_toimipaikka_ids)
        .update(kielipainotus_kytkin=False, muutos_pvm=timezone.now())
    )

    if update_count_toiminnallinenpainotus or update_count_kielipainotus:
        logger.info(
            f"Toimipaikka toiminnallinenpainotus_kytkin updated (count={update_count_toiminnallinenpainotus}). "
            f"Toimipaikka kielipainotus_kytkin updated (count={update_count_kielipainotus})."
        )
    else:
        logger.info("Toimipaikka toiminnallinenpainotus_kytkin and kielipainotus_kytkin activity-statuses checked.")


@custom_shared_task(single_instance=True)
def transfer_toimipaikat_to_another_vakajarjestaja():
    """
    DO NOT REMOVE!, task can be used for another transfer
    """
    from varda.organisation_transformations import transfer_toimipaikat_to_vakajarjestaja

    new_vakajarjestaja = dict(y_tunnus="0191866-5", organisaatio_oid="1.2.246.562.10.414627898710")

    old_vakajarjestajas = [
        dict(y_tunnus="", organisaatio_oid="1.2.246.562.10.57107331241"),
    ]

    new_organisaatio = Organisaatio.objects.get(**new_vakajarjestaja)

    for old_vakajarjestaja in old_vakajarjestajas:
        old_organisaatio = Organisaatio.objects.get(**old_vakajarjestaja)

        transfer_toimipaikat_to_vakajarjestaja(new_organisaatio, old_organisaatio)

        logger.info(
            f"Toimipaikat transfer from {old_organisaatio.nimi} ({old_organisaatio.organisaatio_oid}) "
            f"to {new_organisaatio.nimi} ({new_organisaatio.organisaatio_oid}) ready."
        )


@custom_shared_task(single_instance=True)
def cleanup_Z10_KelaVarhaiskasvatussuhde_task():
    """
    Periodic cleanups
    - Delete all rows in varda_z10_kelavarhaiskasvatussuhde where henkilo_id points to a non-existent henkilo
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM varda_z10_kelavarhaiskasvatussuhde WHERE henkilo_id IN (
              SELECT DISTINCT henkilo_id
              FROM varda_z10_kelavarhaiskasvatussuhde
                LEFT JOIN varda_henkilo ON varda_z10_kelavarhaiskasvatussuhde.henkilo_id = varda_henkilo.id
                WHERE varda_z10_kelavarhaiskasvatussuhde.history_type = '-' AND varda_henkilo.id IS NULL
            );
        """
        )

        result = cursor.rowcount
        if not result:
            result = 0
        logger.info(f"Deleted {result} rows from varda_z10_kelavarhaiskasvatussuhde.")


@custom_shared_task(single_instance=True)
def add_missing_vakasuhde_vakapaatos_permissions():
    """
    add missing Varhaiskasvatussuhde/Varhaiskasvatuspaatos permissions
    """
    # If KATSELIJA-permission is missing then other permissions are also missing.
    katselija_groups = Group.objects.filter(name__startswith=f"{Z4_CasKayttoOikeudet.KATSELIJA}_")
    katselija_groups_dict = {group.name: group for group in katselija_groups}

    no_vakasuhde_perm_count = 0
    no_vakapaatos_perm_count = 0
    vakasuhde_organisaatiot = Varhaiskasvatussuhde.objects.values_list("toimipaikka__organisaatio_oid", flat=True).distinct()
    for org_oid in list(vakasuhde_organisaatiot):
        if not org_oid:
            continue

        group = katselija_groups_dict.get(f"{Z4_CasKayttoOikeudet.KATSELIJA}_{org_oid}")
        if not group:
            logger.error(f"{Z4_CasKayttoOikeudet.KATSELIJA}_{org_oid} group not found.")
            continue

        # Phase 1: Add missing Varhaiskasvatussuhde+Varhaiskasvatuspaatos permissions
        # (This fixes also most of missing Varhaiskasvatuspaatos permissions)
        current_permission_vakasuhde_objs = get_objects_for_group(
            group, "varda.view_varhaiskasvatussuhde", accept_global_perms=False
        )
        no_permission_vakasuhde_objs = Varhaiskasvatussuhde.objects.filter(toimipaikka__organisaatio_oid=org_oid).exclude(
            id__in=current_permission_vakasuhde_objs
        )
        no_vakasuhde_perm_count += no_permission_vakasuhde_objs.count()
        for vakasuhde in no_permission_vakasuhde_objs:
            # Reassign Varhaiskasvatussuhde (and Varhaiskasvatuspaatos) permissions
            assign_lapsi_permissions(
                vakasuhde.varhaiskasvatuspaatos.lapsi, toimipaikka_oid=vakasuhde.toimipaikka.organisaatio_oid, reassign=True
            )

        # Phase 2: Add missing Varhaiskasvatuspaatos permissions
        # (This fixes rest Varhaiskasvatuspaatos permissions which are not fixed in Phase 1)
        current_permission_vakapaatos_objs = get_objects_for_group(
            group, "varda.view_varhaiskasvatuspaatos", accept_global_perms=False
        )
        no_permission_vakapaatos_objs = Varhaiskasvatuspaatos.objects.filter(
            varhaiskasvatussuhteet__toimipaikka__organisaatio_oid=org_oid
        ).exclude(id__in=current_permission_vakapaatos_objs)
        no_vakapaatos_perm_count += no_permission_vakapaatos_objs.count()
        for vakapaatos in no_permission_vakapaatos_objs:
            # Reassign Varhaiskasvatuspaatos (and Varhaiskasvatussuhde) permissions
            assign_lapsi_permissions(
                vakapaatos.lapsi,
                toimipaikka_oid=vakapaatos.varhaiskasvatussuhteet.first().toimipaikka.organisaatio_oid,
                reassign=True,
            )

    logger.info(
        "Missing Vakasuhde/-paatos permissions checked and added. "
        f"(Count {no_vakasuhde_perm_count}/{no_vakapaatos_perm_count})"
    )


@custom_shared_task(single_instance=True)
def remove_inactive_tutkintos(timeout_minutes=5):
    """
    delete every Tutkinto which are not found in any Palvelussuhde,
    exclude tyontekijas which don't have any palvelussuhde,
    exclude Tutkintos created within last 90 days
    """
    task_start_time = timezone.now()

    datetime_90d_ago = timezone.now() - datetime.timedelta(days=90)
    henkilo_ids_have_palvelussuhde = set(Palvelussuhde.objects.values_list("tyontekija__henkilo_id", flat=True).distinct())
    tutkinto_koodis = Palvelussuhde.objects.values_list("tutkinto_koodi", flat=True).distinct()
    deleted_count_all = 0
    for tutkinto_koodi in list(tutkinto_koodis):
        logger.info(f"Inactive Tutkinto objects checking started. tutkinto_koodi={tutkinto_koodi}")

        active_henkilo_tutkintos = set()
        palvelussuhde_objs_ids = (
            Palvelussuhde.objects.filter(tutkinto_koodi=tutkinto_koodi).order_by("id").values_list("id", flat=True)
        )

        # Split the list of id:s into batches
        BATCH_SIZE = 5000
        for i in range(0, len(palvelussuhde_objs_ids), BATCH_SIZE):
            batch_ids = palvelussuhde_objs_ids[i : i + BATCH_SIZE]
            palvelussuhde_objs = (
                Palvelussuhde.objects.filter(id__in=batch_ids)
                .select_related("tyontekija")
                .only("tyontekija__henkilo_id", "tutkinto_koodi")
            )
            active_henkilo_tutkintos |= {f"{obj.tyontekija.henkilo_id}-{obj.tutkinto_koodi}" for obj in palvelussuhde_objs}

        tutkinto_objs = Tutkinto.objects.filter(tutkinto_koodi=tutkinto_koodi, luonti_pvm__lt=datetime_90d_ago).select_related(
            "henkilo"
        )
        tutkinto_ids_to_delete = {
            obj.id
            for obj in tutkinto_objs
            if (
                f"{obj.henkilo.id}-{obj.tutkinto_koodi}" not in active_henkilo_tutkintos
                and obj.henkilo.id in henkilo_ids_have_palvelussuhde
            )
        }
        tutkinto_ids_to_delete = list(tutkinto_ids_to_delete)

        # Split the list of id:s into batches
        BATCH_SIZE = 20
        for i in range(0, len(tutkinto_ids_to_delete), BATCH_SIZE):
            batch_ids = tutkinto_ids_to_delete[i : i + BATCH_SIZE]
            deleted_count, _ = Tutkinto.objects.filter(id__in=batch_ids).delete()
            deleted_count_all += deleted_count
            logger.info(f"Inactive Tutkinto objects batch deleted. tutkinto_koodi={tutkinto_koodi} count={deleted_count}")

        logger.info(f"Inactive Tutkinto objects checked. tutkinto_koodi={tutkinto_koodi}")

        if timezone.now() > task_start_time + datetime.timedelta(minutes=timeout_minutes):
            logger.error(f"Inactive Tutkinto objects checking timeout. Timeout {timeout_minutes} minutes exceeded.")
            break

    logger.info(f"Inactive Tutkinto objects checked and deleted. count={deleted_count_all}")


@custom_shared_task(single_instance=True)
def add_missing_tukipaatos_paatosmaaras():
    """
    Task is used to add missing Tukipaatos/paatosmaara 0 values.

    If: (in Tukipaatos table) >=1 value is added for combinations:
    --tilastointi_pvm
    --vakajarjestaja_id

    Then: all missing values are added for combinations:
    --yksityinen_jarjestaja (true/false)
    --IKARYHMA_CODES (5 values)
    --TUENTASO_CODES (3 values)
    Total: 30 values (2*5*3=30) for every.
    """

    tukipaatos_objs = Tukipaatos.objects.all().select_related("vakajarjestaja").order_by("-tilastointi_pvm")

    latest_tukipaatos = tukipaatos_objs.first()
    TUENTASO_CODES = list(
        Z2_Code.objects.filter(
            Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=latest_tukipaatos.tilastointi_pvm),
            alkamis_pvm__lte=latest_tukipaatos.tilastointi_pvm,
            koodisto__name=Koodistot.tuentaso_koodit.value,
        )
        .order_by("code_value")
        .values_list("code_value", flat=True)
    )

    IKARYHMA_CODES = list(
        Z2_Code.objects.filter(
            Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=latest_tukipaatos.tilastointi_pvm),
            alkamis_pvm__lte=latest_tukipaatos.tilastointi_pvm,
            koodisto__name=Koodistot.ikaryhma_koodit.value,
        )
        .order_by("code_value")
        .values_list("code_value", flat=True)
    )

    tukipaatoses_dict = defaultdict(dict)
    for tukipaatos in tukipaatos_objs:
        vakajarjestaja_id = tukipaatos.vakajarjestaja.id
        date_str = tukipaatos.tilastointi_pvm.strftime("%Y-%m-%d")
        vakajarjestaja_tilastointipvm = f"{vakajarjestaja_id}_{date_str}"

        yksityinen = tukipaatos.yksityinen_jarjestaja
        ikaryhma_code = tukipaatos.ikaryhma_koodi
        tuentaso_code = tukipaatos.tuentaso_koodi
        yksityinen_ikaryhma_tuentaso = f"{yksityinen}-{ikaryhma_code}-{tuentaso_code}"

        tukipaatoses_dict[vakajarjestaja_tilastointipvm][yksityinen_ikaryhma_tuentaso] = tukipaatos

    created_count = 0
    for tukipaatoses_key in tukipaatoses_dict.keys():
        vakajarjestaja_tilastointipvm_dict = tukipaatoses_dict.get(tukipaatoses_key)

        # Get one Tukipaatos from dict to use its values when creating new objects
        tukipaatos_key = list(vakajarjestaja_tilastointipvm_dict.keys())[0]
        tukipaatos = vakajarjestaja_tilastointipvm_dict.get(tukipaatos_key)
        for yksityinen in [True, False]:
            for ikaryhma_code in IKARYHMA_CODES:
                for tuentaso_code in TUENTASO_CODES:
                    yksityinen_ikaryhma_tuentaso = f"{yksityinen}-{ikaryhma_code}-{tuentaso_code}"
                    # Add missing Tukipaatos
                    if yksityinen_ikaryhma_tuentaso not in vakajarjestaja_tilastointipvm_dict:
                        Tukipaatos.objects.create(
                            vakajarjestaja=tukipaatos.vakajarjestaja,
                            paatosmaara=0,
                            yksityinen_jarjestaja=yksityinen,
                            ikaryhma_koodi=ikaryhma_code,
                            tuentaso_koodi=tuentaso_code,
                            tilastointi_pvm=tukipaatos.tilastointi_pvm,
                            lahdejarjestelma=tukipaatos.lahdejarjestelma,
                        )
                        created_count += 1

    logger.info(f"Missing Tukipaatoses created. count={created_count}")


@custom_shared_task(single_instance=True)
def set_organisaatio_active_errors_task():
    from varda.reporting import set_organisaatio_active_errors

    set_organisaatio_active_errors()


@custom_shared_task(single_instance=True)
def generate_active_lapsi_excel_by_date_task(date_str: str = None, password: str = None) -> None:
    """
    Task generates an Excel file containing Lapsi data (hetu and oppijanumero)
    that are active on the given date.

    Lapsi is considered active if they have both an active Varhaiskasvatuspaatos
    and Varhaiskasvatussuhde on the specified date.

    :param date_str: The date in format: YYYY-MM-DD
    :param password: Password to open the Excel-file
    """
    from django.contrib.auth.models import User
    from varda.enums.reporting import ReportStatus
    from varda.enums.supported_language import SupportedLanguage
    from varda.excel_export import ExcelReportGenerator, ExcelReportType
    from varda.models import Z8_ExcelReport

    if not date_str:
        logger.warning("Generating active lapsi excel failed: Date is missing")
        return None

    if not password:
        logger.warning("Generating active lapsi excel failed: Password is missing")
        return None

    try:
        date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except Exception:
        logger.warning("Generating active lapsi excel failed: Faulty date")
        return None

    """
    User is required but not needed. Let's just assign the first admin-user.
    We could provide the user-id as an argument but probably no need.
    """
    user = User.objects.filter(is_superuser=True).first()
    language = SupportedLanguage.FI.value
    excel_report = Z8_ExcelReport.objects.create(
        user=user,
        password=encrypt_string(password),
        status=ReportStatus.PENDING.value,
        language=language,
        target_date=date,
        admin_user_all_organizations=True,
        report_type=ExcelReportType.VAKATIEDOT_VOIMASSA.value,
    )
    report_generator = ExcelReportGenerator(excel_report)
    report_generator.generate()

    return None


@custom_shared_task(single_instance=True)
def remove_tutkintos_003_if_multiple_tutkinto_koodi():
    """
    Removes Tutkinto objects with tutkinto_koodi=003 if the same henkilo + vakajarjestaja
    have another tutkinto_koodi.
    """

    # Subquery to check if another tutkinto_koodi exists for the same henkilo + vakajarjestaja
    other_tutkinto_exists = Tutkinto.objects.filter(
        henkilo=OuterRef("henkilo"), vakajarjestaja=OuterRef("vakajarjestaja")
    ).exclude(tutkinto_koodi="003")

    # Main query to get the matching '003' objects
    tutkintos_to_delete = Tutkinto.objects.filter(tutkinto_koodi="003").filter(Exists(other_tutkinto_exists)).order_by("id")

    if tutkintos_to_delete:
        deleted_count, _ = Tutkinto.objects.filter(id__in=tutkintos_to_delete).delete()
        logger.info(f"Remove Tutkinto objects with tutkinto_koodi=003. Count: {deleted_count}")
    else:
        logger.info("Remove Tutkinto objects with tutkinto_koodi=003: No objects to remove.")


@custom_shared_task(single_instance=True)
def create_new_tukipaatos_aikavali(year=None):
    """
    Creates a new TukipaatosAikavali.

    This task is run once a year via a periodic task scheduler.
    It sets:
      - alkamis_pvm to December 1st of the given year (default: current year)
      - paattymis_pvm to the last day of January of the next year
      - tilastointi_pvm to December 31st of the given year (default: current year)

    Ensures none of these dates are already used in existing records.
    If any of the dates already exist, logs an error and skips creation.
    """

    # Use current year if year is not given
    if year is None:
        today = datetime.date.today()
        year = today.year

    next_year = year + 1

    # Next TukipaatosAikavali dates
    alkamis_pvm = datetime.date(year, 12, 1)  # First day of December
    paattymis_pvm = datetime.date(next_year, 1, 31)  # Last day of January
    tilastointi_pvm = datetime.date(year, 12, 31)  # Last day of December

    with transaction.atomic():
        # Check if any of these dates already exist
        conflict_exists = TukipaatosAikavali.objects.filter(
            Q(alkamis_pvm=alkamis_pvm) | Q(paattymis_pvm=paattymis_pvm) | Q(tilastointi_pvm=tilastointi_pvm)
        ).exists()

        if conflict_exists:
            logger.error("Conflict with dates creating new TukipaatosAikavali.")
        else:
            TukipaatosAikavali.objects.create(
                alkamis_pvm=alkamis_pvm, paattymis_pvm=paattymis_pvm, tilastointi_pvm=tilastointi_pvm
            )
            logger.info(f"Successfully created new TukipaatosAikavali. (tilastointi_pvm={tilastointi_pvm})")


@custom_shared_task(single_instance=True)
def remove_helsinki_ehijat_palvelussuhteet_without_tyoskentelypaikka():
    """
    Removes Palvelussuhde objects with
    - lahdejarjestelma='7' (eHijat)
    - oid='1.2.246.562.10.346830761110' (Helsingin kaupunki)
    - no related Tyoskentelypaikka
    """
    HELSINGIN_KAUPUNKI = "1.2.246.562.10.346830761110"
    LAHDEJARJESTELMA = "7"

    with transaction.atomic():
        poissaolot_deleted_count, _ = PidempiPoissaolo.objects.filter(
            palvelussuhde__tyontekija__vakajarjestaja__organisaatio_oid=HELSINGIN_KAUPUNKI,
            palvelussuhde__lahdejarjestelma=LAHDEJARJESTELMA,
            palvelussuhde__tyoskentelypaikat__isnull=True,
        ).delete()

        palvelussuhteet_deleted_count, _ = Palvelussuhde.objects.filter(
            tyontekija__vakajarjestaja__organisaatio_oid=HELSINGIN_KAUPUNKI,
            lahdejarjestelma=LAHDEJARJESTELMA,
            tyoskentelypaikat__isnull=True,
        ).delete()

        logger.info(
            "Palvelussuhde (Helsinki, eHijat, without related Tyoskentelypaikka) objects deleted. "
            f"count={palvelussuhteet_deleted_count}. "
            f"PidempiPoissaolo objects deleted. count={poissaolot_deleted_count}."
        )
