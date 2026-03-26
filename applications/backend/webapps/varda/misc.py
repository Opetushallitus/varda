import csv
import datetime
import hashlib
import importlib
import json
import logging
import operator
import os
import random
import requests
import secrets
import sys
import time

from calendar import monthrange
from collections import Counter
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from functools import reduce
from io import StringIO
from requests.exceptions import ConnectionError, RequestException, Timeout
from rest_framework import status
from rest_framework.exceptions import APIException
from time import sleep
from urllib.parse import urlparse

from varda.clients.allas_s3_client import Client as S3Client
from varda.clients.lampi_s3_client import Client as LampiS3Client
from varda.constants import CELERY_WORKER_COUNT
from varda.custom_celery import custom_shared_task
from varda.enums.error_messages import ErrorMessages
from varda.enums.koodistot import Koodistot
from varda.helper_functions import hide_hetu
from varda.models import Henkilo, Toimipaikka, Z2_CodeTranslation, Tukipaatos
from varda.oph_yhteiskayttopalvelu_autentikaatio import get_authentication_header, get_contenttype_header
from webapps.celery import app as celery_app


logger = logging.getLogger(__name__)

CHECK_KEYS = "0123456789ABCDEFHJKLMNPRSTUVWXY"
CENTURIES = {"18": "+", "19": "-", "20": "A"}


class CustomServerErrorException(APIException):
    default_detail = {"errors": [ErrorMessages.MI016.value]}


def get_iso_datetime_object(date_string: str) -> datetime:
    """
    Converts ISO 8601 date string to datetime-object.
    :param date_string: e.g. 2024-02-02T06:01:06.119091Z
    :return: datetime
    """
    format_string = "%Y-%m-%dT%H:%M:%S.%fZ"
    return datetime.datetime.strptime(date_string, format_string)


def get_year_n_years_ago(n: int) -> int:
    current_year = datetime.datetime.now().year
    target_year = current_year - n
    return target_year


def sleep_if_not_test(x_seconds):
    if not settings.TESTING:
        sleep(x_seconds)


def hash_string(string):
    """
    Return a SHA-256 hash of the given string
    """
    return hashlib.sha256(string.encode("utf-8")).hexdigest()


def create_hetu_from_birthday(syntyma_pvm, sukupuoli_koodi):
    """
    Taken from: https://gist.github.com/puumuki/11172310
    """
    now = datetime.datetime.now()
    current_year = now.year
    current_month = now.month
    current_day = now.day

    year = syntyma_pvm.year

    # make sure people are not born in the future or are not too old either
    if year >= current_year or year < 1800:
        year = current_year
        month = random.randint(1, current_month)
    else:
        month = random.randint(1, 12)

    if month == current_month and year == current_year:
        day = random.randint(1, current_day)
    else:
        day = random.randint(1, monthrange(year, month)[1])

    century_sep = CENTURIES[str(year)[0:2]]

    if int(sukupuoli_koodi) == 1:
        order_num = random.randrange(3, 1000, 2)
    else:
        order_num = random.randrange(2, 1000, 2)

    check_number = "%02d%02d%s%03d" % (day, month, str(year)[2:4], order_num)

    check_number_index = int(check_number) % 31
    key = CHECK_KEYS[check_number_index]

    return "%02d%02d%s%s%03d%s" % (day, month, str(year)[2:4], century_sep, order_num, key)


def decrypt_henkilotunnus(encrypted_henkilotunnus, henkilo_id=None, raise_error=True):
    """
    This is needed when updating henkilo-data from Oppijanumerorekisteri.

    Original key generated with: Fernet.generate_key().decode('utf-8')
    Details: https://cryptography.io/en/latest/fernet/
    """
    if not encrypted_henkilotunnus:
        return None

    henkilo_id = henkilo_id or getattr(Henkilo.objects.filter(henkilotunnus=encrypted_henkilotunnus).first(), "id", None)

    f = _get_fernet()
    try:
        resolved_token = f.decrypt(encrypted_henkilotunnus.encode("utf-8"))
    except TypeError:
        if raise_error:
            logger.error(f"Decrypt henkilotunnus: Fernet token is not bytes. Henkilo.id: {henkilo_id}")
            raise CustomServerErrorException
        else:
            return None
    except InvalidToken:
        if raise_error:
            logger.error(f"Decrypt henkilotunnus: Invalid token. Henkilo.id: {henkilo_id}")
            raise CustomServerErrorException
        else:
            return None
    return resolved_token.decode("utf-8")  # convert bytes -> string


def _get_fernet():
    decoded_key = settings.FERNET_SECRET_KEY
    key = decoded_key.encode("utf-8")
    if not key:
        logger.error("Fernet error. No secret key available.")
        raise CustomServerErrorException
    return Fernet(key)


def encrypt_string(original_string):
    f = _get_fernet()

    try:
        token = f.encrypt(original_string.encode("utf-8"))
    except TypeError:
        logger.error("Encryption error: Data is not bytes.")
        raise CustomServerErrorException
    return token.decode("utf-8")  # convert bytes -> string


def decrypt_excel_report_password(encrypted_password, report_id):
    f = _get_fernet()
    try:
        resolved_token = f.decrypt(encrypted_password.encode("utf-8"))
    except (TypeError, InvalidToken) as decryptException:
        logger.error(f"Failed to decrypt Excel password with id {report_id}: {decryptException}")
        raise CustomServerErrorException
    return resolved_token.decode("utf-8")


@transaction.atomic
def rotate_henkilotunnus(henkilo_id, f=None):
    henkilo = Henkilo.objects.get(id=henkilo_id)
    try:
        henkilotunnus_encrypted = henkilo.henkilotunnus.encode("utf-8")
        if henkilotunnus_encrypted != b"":
            if not f:
                f = _get_fernet()
            henkilo.henkilotunnus = f.rotate(henkilotunnus_encrypted).decode("utf-8")
            henkilo.save()
    except TypeError:
        logger.error("Hetu invalid format. Expecting bytes.")


def get_http_header(auth_token):
    return {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Token {auth_token}"}


def get_reply_json(is_ok, json_msg=None):
    return {"is_ok": is_ok, "json_msg": json_msg}


def decode_json_msg(reply_type, response, service_name):
    try:
        if reply_type == "json":
            json_msg = json.loads(response.content)
        elif reply_type == "text":
            json_msg = response.text
        else:
            raise ValueError("Illegal argument {}".format(reply_type))
    except json.JSONDecodeError:
        logger.error(service_name + ": Could not decode json. Invalid reply.")
        return None
    return json_msg


def send_request_get_response(service_name, http_url_suffix, headers, request_type, data_json, large_query):
    """
    Request timeout: https://requests.readthedocs.io/en/master/user/advanced/#timeouts
    """
    DEFAULT_CONNECT_TIMEOUT = 7  # seconds
    DEFAULT_READ_TIMEOUT = 60  # seconds
    DEFAULT_READ_TIMEOUT_LARGE_QUERY = 3600  # seconds
    if large_query:
        DEFAULT_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT_LARGE_QUERY)
    else:
        DEFAULT_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)
    response = None

    try:
        http_complete_url = settings.OPINTOPOLKU_DOMAIN + "/" + service_name + http_url_suffix
        if request_type == "get":
            response = requests.get(http_complete_url, headers=headers, timeout=DEFAULT_TIMEOUT_TUPLE)
        elif request_type == "post":
            response = requests.post(http_complete_url, headers=headers, data=data_json, timeout=DEFAULT_TIMEOUT_TUPLE)
        else:  # put
            response = requests.put(http_complete_url, headers=headers, data=data_json, timeout=DEFAULT_TIMEOUT_TUPLE)
    except (RequestException, ConnectionError, Timeout) as e:
        logger.error("Failed to make a request. Url: {}, Error: {}".format(http_complete_url, e))

    return response


def _log_failed_request_hide_hetu(service_name, http_url_suffix, headers, response):
    url_possible_hetu_hidden = hide_hetu(service_name + http_url_suffix)
    logger.error(
        "{}: Authentication issue. Status_code: {}. Url: {}. Service-ticket: {}.".format(
            service_name, response.status_code, url_possible_hetu_hidden, headers["CasSecurityTicket"]
        )
    )


def send_request_to_external_service(
    request_type, service_name, http_url_suffix, expected_status_code, auth, reply_type="json", data_json=None, large_query=False
):
    """
    Response.close():
    https://github.com/psf/requests/blob/a9ee0eef5a70acb9ed35622b3675574b11f92cb4/requests/models.py#L963
    """
    force_new_tgt = False
    MAX_NO_OF_ATTEMPS = 3
    number_of_attempt = 0
    while number_of_attempt < MAX_NO_OF_ATTEMPS:
        number_of_attempt += 1
        headers = (
            get_authentication_header(service_name, external_request=False, force_new_tgt=force_new_tgt)
            if auth
            else get_contenttype_header()
        )
        response = send_request_get_response(service_name, http_url_suffix, headers, request_type, data_json, large_query)
        if response is None:
            logger.error("Could not get a response: {}, {}, {}".format(request_type, service_name, http_url_suffix))
            sleep_if_not_test(2)
            continue

        if response.status_code == expected_status_code:
            pass
        elif response.status_code == status.HTTP_403_FORBIDDEN:
            _log_failed_request_hide_hetu(service_name, http_url_suffix, headers, response)
            response.close()
            sleep_if_not_test(2)
            continue
        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            if number_of_attempt == MAX_NO_OF_ATTEMPS:
                _log_failed_request_hide_hetu(service_name, http_url_suffix, headers, response)
            response.close()
            sleep_if_not_test(2)
            force_new_tgt = True
            continue
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            break
        else:
            logger.error(
                "{0}: {1}-request ({0}{2}) returned status_code: {3}, {4}".format(
                    service_name, request_type, http_url_suffix, response.status_code, response.content
                )
            )
            response.close()
            sleep_if_not_test(2)
            continue

        json_msg = decode_json_msg(reply_type, response, service_name)
        if json_msg is None:
            logger.error("Could not get a valid json_msg: {}, {}, {}".format(request_type, service_name, http_url_suffix))
            response.close()
            sleep_if_not_test(2)
            continue

        return get_reply_json(is_ok=True, json_msg=json_msg)
    return get_reply_json(is_ok=False)


def get_json_from_external_service(service_name, http_url_suffix, auth=True, large_query=False):
    request_type = "get"
    expected_status_code = status.HTTP_200_OK
    return send_request_to_external_service(
        request_type, service_name, http_url_suffix, expected_status_code, auth, large_query=large_query
    )


def post_json_to_external_service(
    service_name, http_url_suffix, data_json, expected_status_code, auth=True, reply_type="json", large_query=False
):
    request_type = "post"
    return send_request_to_external_service(
        request_type,
        service_name,
        http_url_suffix,
        expected_status_code,
        auth,
        reply_type=reply_type,
        data_json=data_json,
        large_query=large_query,
    )


def put_json_to_external_service(service_name, http_url_suffix, data_json, expected_status_code):
    request_type = "put"
    auth = True
    return send_request_to_external_service(
        request_type, service_name, http_url_suffix, expected_status_code, auth, data_json=data_json
    )


def path_parse(request_full_path):
    """
    :param request_full_path: either string or bytes
    :return request_full_path: string
    """
    parsed_url = urlparse(request_full_path)
    request_full_path = parsed_url.path
    query_params = parsed_url.query
    try:
        request_full_path = request_full_path.decode()
        query_params = query_params.decode()
    except AttributeError:
        pass  # request_full_path is already type:string
    except ValueError:
        logger.error(f"Failed to parse url: {request_full_path}, {query_params}")
        raise CustomServerErrorException
    return request_full_path, query_params


def single_line_with_linebreaks_parse(single_line_input: str) -> str:
    """
    :param single_line_input: Single line with explicit linebreaks \n
    :return: Multi-line string

    https://stackoverflow.com/a/54760909/8689704
    """
    return single_line_input.replace("\\r\\n", "")


def list_to_chunks(list_, size):
    return [list_[i : i + size] for i in range(0, len(list_), size)]


def intersection(lst1, lst2):
    """
    TODO: Perfect place for C-extension (=speedup!)
    """
    return sorted(list(set(lst1) & set(lst2)))


def list_of_dicts_has_duplicate_values(searchable_list, key_name):
    """
    https://www.robjwells.com/2015/08/python-counter-gotcha-with-max/
    """
    c = Counter()
    for item in searchable_list:
        if key_name in item:
            c[item[key_name]] += 1

    highest_occurrence = c.most_common(1)[0][1] if c else None
    if highest_occurrence is not None and highest_occurrence > 1:
        return True
    return False


def test_decrypt_all_hetus():
    """
    Validate all hetus in db are decryptable. Meant to be run after after fernet key rotation.
    """
    logger.info("Starting decrypting all hetus in db")
    [
        decrypt_henkilotunnus(henkilo_data[0], henkilo_id=henkilo_data[1])
        for henkilo_data in Henkilo.objects.exclude(henkilotunnus="").values_list("henkilotunnus", "id")
    ]
    logger.info("Finished decrypting all hetus in db succesfully")


@custom_shared_task()
def update_all_vakajarjestaja_permissiongroups():
    """
    Creates all organisaatio permission groups and assign permissions according the premission template matching the
    permission group.
    Needs to be run after permission template changes.
    :return: None
    """
    from varda.clients.organisaatio_client import get_multiple_organisaatio, get_organization_type
    from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
    from varda.models import Toimipaikka, Organisaatio
    from varda.permissions import assign_organisaatio_permissions, assign_toimipaikka_permissions
    from varda.permission_groups import create_permission_groups_for_organisaatio

    logger.info("Starting setting vakajarjestaja permissions")
    all_vakajarjestaja_oids = Organisaatio.objects.exclude(organisaatio_oid__exact="").values_list("organisaatio_oid", flat=True)
    vakajarjestaja_oid_chunks = list_to_chunks(all_vakajarjestaja_oids, 100)
    for vakajarjestaja_oid_chunk in vakajarjestaja_oid_chunks:
        vakajarjestaja_data_list = {
            organisaatio["oid"]: organisaatio for organisaatio in get_multiple_organisaatio(vakajarjestaja_oid_chunk)
        }
        for vakajarjestaja_oid in vakajarjestaja_oid_chunk:
            organisaatiotyyppi = get_organization_type(vakajarjestaja_data_list.get(vakajarjestaja_oid))
            create_permission_groups_for_organisaatio(vakajarjestaja_oid, organisaatiotyyppi)
            assign_organisaatio_permissions(Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid))
    logger.info("Finished setting vakajarjestaja permissions.")
    logger.info("Setting toimipaikka permissions.")
    toimipaikka_oid_list = Toimipaikka.objects.exclude(organisaatio_oid__exact="").values_list("organisaatio_oid", flat=True)
    toimipaikka_oid_chunks = list_to_chunks(toimipaikka_oid_list, 100)
    for toimipaikka_oid_chunk in toimipaikka_oid_chunks:
        for toimipaikka_oid in toimipaikka_oid_chunk:
            create_permission_groups_for_organisaatio(toimipaikka_oid, Organisaatiotyyppi.TOIMIPAIKKA.value)
            assign_toimipaikka_permissions(Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid))
    logger.info("Finished setting toimipaikka permissions")


def update_painotus_kytkin(toimipaikka, related_painotus_attribute, kytkin_name):
    """
    Automatically update toimipaikka.(kieli/toiminnallinen)painotus_kytkin when painotus is created, updated or deleted
    :param toimipaikka: Toimipaikka instance
    :param related_painotus_attribute: name of the related field attribute (toiminnallisetpainotukset/kielipainotukset)
    :param kytkin_name: name of the kytkin attribute (toiminnallinenpainotus_kytkin/kielipainotus_kytkin)
    """
    current_kytkin_value = getattr(toimipaikka, kytkin_name)
    new_kytkin_value = getattr(toimipaikka, related_painotus_attribute).exists()

    if current_kytkin_value != new_kytkin_value:
        setattr(toimipaikka, kytkin_name, new_kytkin_value)
        toimipaikka.save()


def flatten_nested_list(nested_list):
    return reduce(operator.iconcat, nested_list, [])


def memory_efficient_queryset_iterator(queryset, chunk_size=1000):
    """
    When iterating large querysets (e.g. Henkilo.objects.all()) Django caches the results and uses a lot of memory.
    Using a built in paginator helps with memory usage, but decreases performance.
    :param queryset: QuerySet, must be ordered (e.g. Henkilo.objects.order_by('id))
    :param chunk_size: default size of a single page
    :return: returns a generator that can be iterated over (e.g. for instance in memory_efficient_queryset_iterator(..))
    """
    paginator = Paginator(queryset, chunk_size)
    for page_number in paginator.page_range:
        page = paginator.get_page(page_number)
        for instance in page.object_list:
            yield instance


def get_queryset_in_chunks(queryset, chunk_size=10000):
    """
    Split QuerySet result into chunks to help with memory usage efficiency
    :param queryset: QuerySet
    :param chunk_size: size of the chunk
    :return: chunk of results
    """
    if not queryset:
        # If QuerySet is empty, yield nothing so that e.g. for loop is not triggered
        yield from []
    else:
        chunk = []
        for result in queryset.iterator():
            chunk.append(result)

            if len(chunk) == chunk_size:
                yield chunk
                # Start a new chunk
                chunk = []

        # Return the remaining chunk
        yield chunk


class TemporaryObject(object):
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def get_nested_value(instance, field_list):
    for field in field_list:
        instance = getattr(instance, field)
    return instance


def load_in_new_module(library_name, name):
    spec = importlib.util.find_spec(library_name)
    library_copy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(library_copy)
    sys.modules[name] = library_copy
    del spec
    return library_copy


def is_date_within_timeframe(today, start_date, end_date):
    return start_date <= today <= end_date


def find_timeframe_for_current_date(today, timeframes):
    for timeframe in timeframes:
        is_within_timeframe = is_date_within_timeframe(today, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        if is_within_timeframe:
            return timeframe
    return None


def find_active_timeframe(today, timeframes):
    errors = []

    if not timeframes.exists():
        # Add error if no active timeframes found
        errors.append(ErrorMessages.TT002.value)

    found_timeframe = find_timeframe_for_current_date(today, timeframes)
    if not found_timeframe:
        errors.append(ErrorMessages.TT001.value)

    return errors, found_timeframe


def find_next_timeframe(today, timeframes):
    _, timeframe = find_active_timeframe(today, timeframes)
    if timeframe:  # There is currently an active timeframe
        return timeframe

    # If there is no active timeframe, find the next one
    for timeframe in timeframes:
        if today < timeframe.alkamis_pvm:
            return timeframe

    return None


def get_tilastointi_pvm(today, timeframes):
    timeframe = find_next_timeframe(today, timeframes)
    if not timeframe:
        return None

    return timeframe.tilastointi_pvm


def get_next_timeframe(today, timeframes):
    if not timeframes:
        return None, None, None

    next_timeframe = find_next_timeframe(today, timeframes)
    if not next_timeframe:
        return None, None, None

    return next_timeframe.alkamis_pvm, next_timeframe.paattymis_pvm, next_timeframe.tilastointi_pvm


def get_latest_tilastointi_pvm_before_date(organisaatio, before_date):
    latest_tukipaatos = (
        Tukipaatos.objects.filter(vakajarjestaja=organisaatio, tilastointi_pvm__lte=before_date)
        .order_by("tilastointi_pvm")
        .last()
    )

    return latest_tukipaatos.tilastointi_pvm if latest_tukipaatos else None


def get_latest_tilastointi_pvm(vakajarjestaja):
    latest_tukipaatos = Tukipaatos.objects.filter(vakajarjestaja=vakajarjestaja).order_by("tilastointi_pvm").last()

    return latest_tukipaatos.tilastointi_pvm if latest_tukipaatos else None


def get_tuen_tiedot_tuen_taso_paatosmaaras(organisaatio, tilastointi_pvm):
    paatosmaaras_dict = dict()
    for tuentaso_code in ["TT01", "TT02", "TT03"]:
        paatosmaaras_dict[tuentaso_code] = Tukipaatos.objects.filter(
            vakajarjestaja=organisaatio, tuentaso_koodi=tuentaso_code, tilastointi_pvm=tilastointi_pvm
        ).aggregate(Sum("paatosmaara"))["paatosmaara__sum"]

    paatosmaaras_dict["total"] = Tukipaatos.objects.filter(
        vakajarjestaja=organisaatio, tilastointi_pvm=tilastointi_pvm
    ).aggregate(Sum("paatosmaara"))["paatosmaara__sum"]

    return paatosmaaras_dict


def create_muistutus_report_csv(msg_logs):
    data = [[msg_log.organisaatio.nimi, msg_log.message_type] for msg_log in msg_logs]

    col_names = ["organisaatio", "message_type"]

    # Create a StringIO object to store CSV data
    csv_buffer = StringIO()

    writer = csv.writer(csv_buffer, delimiter=";")
    writer.writerow(col_names)
    writer.writerows(data)
    csv_data = csv_buffer.getvalue()
    csv_buffer.close()

    return csv_data


def upload_backup_to_allas(file_path):
    """
    :param file_path: Which file to be uploaded. E.g. /var/backups/allas_backup-2024-05-17T10:10:00.gz.enc
    :return:
    """
    if settings.PRODUCTION_ENV or settings.QA_ENV:
        s3_client = S3Client()
        filename = file_path.split("/")[-1]
        for index in range(0, 5):
            # Try to upload max five times
            logger.info("Starting to upload file to Allas.")
            result = s3_client.upload_file(file_path, filename)
            if result:
                logger.info("Upload to Allas finished successfully.")
                return None

        logger.error("Failed to upload backup to Allas.")


def is_within_date_range(date, start_date, end_date):
    """
    Check if the given date is within the given date range
    :param date: Date to check
    :param start_date: Start date of the range
    :param end_date: End date of the range
    """
    if date is None:
        return False
    if start_date is None and end_date is None:
        return True
    if start_date is None:
        return date <= end_date
    if end_date is None:
        return date >= start_date
    return start_date <= date <= end_date


def get_person_count_per_kunta_dict(henkilo_oid_list, code_language):
    # Calculate ages in year
    current_date = datetime.datetime.now().date()
    henkilo_ages_dict = dict()
    henkilos = Henkilo.objects.filter(henkilo_oid__in=henkilo_oid_list)
    henkilo_age_lte_3y_count = 0
    henkilo_age_gt_3y_count = 0
    for henkilo in henkilos:
        age = (current_date - henkilo.syntyma_pvm).days / 365.25  # Considering leap years
        henkilo_ages_dict[henkilo.henkilo_oid] = age
        if age > 3.0:
            henkilo_age_gt_3y_count += 1
        else:
            henkilo_age_lte_3y_count += 1

    kunta_dict = dict(
        total=dict(
            amount=len(henkilo_oid_list), amount_age_lte_3=henkilo_age_lte_3y_count, amount_age_gt_3=henkilo_age_gt_3y_count
        )
    )
    for henkilo_oid in henkilo_oid_list:
        henkilo_age = henkilo_ages_dict.get(henkilo_oid, None)
        kunta_code_list = (
            Toimipaikka.objects.filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid=henkilo_oid)
            .distinct("kunta_koodi")
            .values_list("kunta_koodi", flat=True)
        )
        for kunta_code in kunta_code_list:
            if kunta_code not in kunta_dict:
                kunta_translation = getattr(
                    Z2_CodeTranslation.objects.filter(
                        language__iexact=code_language,
                        code__code_value=kunta_code,
                        code__koodisto__name=Koodistot.kunta_koodit.value,
                    ).first(),
                    "name",
                    None,
                )
                kunta_dict[kunta_code] = dict(name=kunta_translation, amount=0, amount_age_lte_3=0, amount_age_gt_3=0)
            kunta_dict[kunta_code]["amount"] += 1
            if henkilo_age and henkilo_age <= 3.0:
                kunta_dict[kunta_code]["amount_age_lte_3"] += 1
            elif henkilo_age and henkilo_age > 3.0:
                kunta_dict[kunta_code]["amount_age_gt_3"] += 1

    return kunta_dict


def make_random_password(length=10, allowed_chars="abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"):
    """
    https://stackoverflow.com/a/77444566

    :param length:
    :param allowed_chars:
    :return:
    """
    return "".join(secrets.choice(allowed_chars) for i in range(length))


def upload_lampi_export(files: [str]):
    """
    param: files: list of files to upload
    E.g. [
      '/var/exports/varda_lapsi.csv.gz', '/var/exports/varda_lapsi_schema.sql.gz',
      '/var/exports/varda_varhaiskasvatus.csv.gz' '/var/exports/varda_varhaiskasvatus_schema.sql.gz',
    ]

    Database tables to be uploaded are specified at: lib/eks/apps/integrations/lampi/database_tables.py

    More info: https://jira.eduuni.fi/browse/OPHVARDA-2879
    """
    varda_lampi_schema_version = settings.LAMPI_SCHEMA_VERSION
    s3_client = LampiS3Client()
    manifest_json = {"tables": [], "schema": {}}
    for file in files:
        logger.info(f"Uploading to Lampi: {file}")
        filename = file.split("/")[-1]
        object_path = f"fulldump/varda/{varda_lampi_schema_version}/{filename}"
        upload_fileobj_response = s3_client.upload_file(file, object_path)
        if upload_fileobj_response:
            try:
                version_id = upload_fileobj_response["VersionId"]
                key_s3_version = {
                    "key": object_path,
                    "s3Version": version_id,
                }
                if "csv" in filename:
                    manifest_json["tables"].append(key_s3_version)
                else:
                    manifest_json["schema"] = key_s3_version
            except KeyError:
                logger.error(f"Lampi upload {object_path} failed! Version-id missing from response.")
                return None
            logger.info(f"Lampi upload {object_path} successful.")
        else:
            logger.error(f"Lampi upload {object_path} failed!")

    # Finally upload manifest.json
    key = f"fulldump/varda/{varda_lampi_schema_version}/manifest.json"
    response = s3_client.upload_json_file(key, manifest_json)
    if response and response["ResponseMetadata"]["HTTPStatusCode"] == 200:
        logger.info("Complete Lampi upload successful.")
    else:
        logger.error("Complete Lampi upload failed! Please try again.")


def check_active_celery_workers() -> (bool, int):
    MAX_NO_OF_LOOPS = 3
    SLEEPS = [1, 1, 0]  # No sleep after last fail
    for i in range(MAX_NO_OF_LOOPS):
        try:
            active_workers = celery_app.control.ping()
            if active_workers and len(active_workers) >= CELERY_WORKER_COUNT:
                return True, len(active_workers)
            return False, len(active_workers)
        except Exception:
            pass
        time.sleep(SLEEPS[i])

    return False, 0


def send_slack_message(text: str, channel: str = "varda"):
    url_prefix = "https://hooks.slack.com/services/"

    if channel == "varda":
        url_suffix = os.getenv("SLACK_CHANNEL_VARDA_WEBHOOK_PATH")
    else:
        logging.error(f"Slack-channel {channel} not supported.")
        return None

    if not url_suffix:
        return None

    payload = {"text": text}

    try:
        requests.post(url_prefix + url_suffix, json=payload, timeout=10).raise_for_status()
    except requests.exceptions.RequestException:
        logging.error(f"Slack webhook failed. Text: {text}")


def update_pulssi():
    url = "https://opintopolku.fi/varda/pulssi/"
    try:
        logging.info("Update Pulssi view in production.")
        requests.get(url).raise_for_status()
    except requests.exceptions.RequestException:
        logging.error("Updating Pulssi failed.")
