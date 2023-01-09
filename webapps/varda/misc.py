import functools
import hashlib
import importlib
import json
import logging
import operator
import re
import sys
from collections import Counter
from time import sleep
from urllib.parse import urlparse

import requests
from celery import shared_task
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from requests.exceptions import ConnectionError, RequestException, Timeout
from rest_framework import status
from rest_framework.exceptions import APIException

from varda.enums.error_messages import ErrorMessages
from varda.helper_functions import hide_hetu
from varda.models import Henkilo, Organisaatio
from varda.oph_yhteiskayttopalvelu_autentikaatio import get_authentication_header, get_contenttype_header


logger = logging.getLogger(__name__)


class CustomServerErrorException(APIException):
    default_detail = {'errors': [ErrorMessages.MI016.value]}


def sleep_if_not_test(x_seconds):
    if not settings.TESTING:
        sleep(x_seconds)


def hash_string(string):
    """
    Return a SHA-256 hash of the given string
    """
    return hashlib.sha256(string.encode('utf-8')).hexdigest()


def decrypt_henkilotunnus(encrypted_henkilotunnus, henkilo_id=None, raise_error=True):
    """
    This is needed when updating henkilo-data from Oppijanumerorekisteri.

    Original key generated with: Fernet.generate_key().decode('utf-8')
    Details: https://cryptography.io/en/latest/fernet/
    """
    if not encrypted_henkilotunnus:
        return None

    henkilo_id = henkilo_id or getattr(Henkilo.objects.filter(henkilotunnus=encrypted_henkilotunnus).first(), 'id', None)

    f = _get_fernet()
    try:
        resolved_token = f.decrypt(encrypted_henkilotunnus.encode('utf-8'))
    except TypeError:
        if raise_error:
            logger.error(f'Decrypt henkilotunnus: Fernet token is not bytes. Henkilo.id: {henkilo_id}')
            raise CustomServerErrorException
        else:
            return None
    except InvalidToken:
        if raise_error:
            logger.error(f'Decrypt henkilotunnus: Invalid token. Henkilo.id: {henkilo_id}')
            raise CustomServerErrorException
        else:
            return None
    return resolved_token.decode('utf-8')  # convert bytes -> string


def _get_fernet():
    decoded_key = settings.FERNET_SECRET_KEY
    key = decoded_key.encode('utf-8')
    if not key:
        logger.error('Fernet error. No secret key available.')
        raise CustomServerErrorException
    return Fernet(key)


def encrypt_string(original_string):
    f = _get_fernet()

    try:
        token = f.encrypt(original_string.encode('utf-8'))
    except TypeError:
        logger.error('Encryption error: Data is not bytes.')
        raise CustomServerErrorException
    return token.decode('utf-8')  # convert bytes -> string


def decrypt_excel_report_password(encrypted_password, report_id):
    f = _get_fernet()
    try:
        resolved_token = f.decrypt(encrypted_password.encode('utf-8'))
    except (TypeError, InvalidToken) as decryptException:
        logger.error(f'Failed to decrypt Excel password with id {report_id}: {decryptException}')
        raise CustomServerErrorException
    return resolved_token.decode('utf-8')


@transaction.atomic
def rotate_henkilotunnus(henkilo_id, f=None):
    henkilo = Henkilo.objects.get(id=henkilo_id)
    try:
        henkilotunnus_encrypted = henkilo.henkilotunnus.encode('utf-8')
        if henkilotunnus_encrypted != b'':
            if not f:
                f = _get_fernet()
            henkilo.henkilotunnus = f.rotate(henkilotunnus_encrypted).decode('utf-8')
            henkilo.save()
    except TypeError:
        logger.error('Hetu invalid format. Expecting bytes.')


def get_reply_json(is_ok, json_msg=None):
    return {'is_ok': is_ok, 'json_msg': json_msg}


def decode_json_msg(reply_type, response, service_name):
    try:
        if reply_type == 'json':
            json_msg = json.loads(response.content)
        elif reply_type == 'text':
            json_msg = response.text
        else:
            raise ValueError('Illegal argument {}'.format(reply_type))
    except json.JSONDecodeError:
        logger.error(service_name + ': Could not decode json. Invalid reply.')
        return None
    return json_msg


def send_request_get_response(service_name, http_url_suffix, headers, request_type, data_json, large_query):
    """
    Request timeout: https://requests.readthedocs.io/en/master/user/advanced/#timeouts
    """
    DEFAULT_CONNECT_TIMEOUT = 7  # seconds
    DEFAULT_READ_TIMEOUT = 60    # seconds
    DEFAULT_READ_TIMEOUT_LARGE_QUERY = 3600  # seconds
    if large_query:
        DEFAULT_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT_LARGE_QUERY)
    else:
        DEFAULT_TIMEOUT_TUPLE = (DEFAULT_CONNECT_TIMEOUT, DEFAULT_READ_TIMEOUT)
    response = None

    try:
        http_complete_url = settings.OPINTOPOLKU_DOMAIN + '/' + service_name + http_url_suffix
        if request_type == 'get':
            response = requests.get(http_complete_url, headers=headers, timeout=DEFAULT_TIMEOUT_TUPLE)
        elif request_type == 'post':
            response = requests.post(http_complete_url, headers=headers, data=data_json, timeout=DEFAULT_TIMEOUT_TUPLE)
        else:  # put
            response = requests.put(http_complete_url, headers=headers, data=data_json, timeout=DEFAULT_TIMEOUT_TUPLE)
    except (RequestException, ConnectionError, Timeout) as e:
        logger.error('Failed to make a request. Url: {}, Error: {}'.format(http_complete_url, e))

    return response


def send_request_to_external_service(request_type, service_name, http_url_suffix, expected_status_code, auth,
                                     reply_type='json', data_json=None, large_query=False):
    """
    Response.close():
    https://github.com/psf/requests/blob/a9ee0eef5a70acb9ed35622b3675574b11f92cb4/requests/models.py#L963
    """
    MAX_NO_OF_ATTEMPS = 3
    number_of_attempt = 0
    while number_of_attempt < MAX_NO_OF_ATTEMPS:
        number_of_attempt += 1
        headers = get_authentication_header(service_name, external_request=False) if auth else get_contenttype_header()
        response = send_request_get_response(service_name, http_url_suffix, headers, request_type, data_json, large_query)
        if response is None:
            logger.error('Could not get a response: {}, {}, {}'.format(request_type, service_name, http_url_suffix))
            sleep_if_not_test(2)
            continue

        if response.status_code == expected_status_code:
            pass
        elif response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
            url_possible_hetu_hidden = hide_hetu(service_name + http_url_suffix)
            logger.error('{}: Authentication issue. Status_code: {}. Url: {}. Service-ticket: {}.'
                         .format(service_name, response.status_code, url_possible_hetu_hidden, headers['CasSecurityTicket']))
            response.close()
            sleep_if_not_test(2)
            continue
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            break
        else:
            logger.error('{0}: {1}-request ({0}{2}) returned status_code: {3}, {4}'
                         .format(service_name, request_type, http_url_suffix, response.status_code, response.content))
            response.close()
            sleep_if_not_test(2)
            continue

        json_msg = decode_json_msg(reply_type, response, service_name)
        if json_msg is None:
            logger.error('Could not get a valid json_msg: {}, {}, {}'.format(request_type, service_name, http_url_suffix))
            response.close()
            sleep_if_not_test(2)
            continue

        return get_reply_json(is_ok=True, json_msg=json_msg)
    return get_reply_json(is_ok=False)


def get_json_from_external_service(service_name, http_url_suffix, auth=True, large_query=False):
    request_type = 'get'
    expected_status_code = status.HTTP_200_OK
    return send_request_to_external_service(request_type, service_name, http_url_suffix, expected_status_code, auth,
                                            large_query=large_query)


def post_json_to_external_service(service_name, http_url_suffix, data_json, expected_status_code, auth=True,
                                  reply_type='json', large_query=False):
    request_type = 'post'
    return send_request_to_external_service(request_type, service_name, http_url_suffix, expected_status_code, auth,
                                            reply_type=reply_type, data_json=data_json, large_query=large_query)


def put_json_to_external_service(service_name, http_url_suffix, data_json, expected_status_code):
    request_type = 'put'
    auth = True
    return send_request_to_external_service(request_type, service_name, http_url_suffix, expected_status_code, auth,
                                            data_json=data_json)


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
        logger.error(f'Failed to parse url: {request_full_path}, {query_params}')
        raise CustomServerErrorException
    return request_full_path, query_params


def list_to_chunks(list_, size):
    return [list_[i:i + size] for i in range(0, len(list_), size)]


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
    logger.info('Starting decrypting all hetus in db')
    [decrypt_henkilotunnus(henkilo_data[0], henkilo_id=henkilo_data[1])
     for henkilo_data in Henkilo.objects.exclude(henkilotunnus='').values_list('henkilotunnus', 'id')]
    logger.info('Finished decrypting all hetus in db succesfully')


@shared_task
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

    logger.info('Starting setting vakajarjestaja permissions')
    all_vakajarjestaja_oids = (Organisaatio.objects.exclude(organisaatio_oid__exact='')
                               .values_list('organisaatio_oid', flat=True))
    vakajarjestaja_oid_chunks = list_to_chunks(all_vakajarjestaja_oids, 100)
    for vakajarjestaja_oid_chunk in vakajarjestaja_oid_chunks:
        vakajarjestaja_data_list = {organisaatio['oid']: organisaatio
                                    for organisaatio in get_multiple_organisaatio(vakajarjestaja_oid_chunk)}
        for vakajarjestaja_oid in vakajarjestaja_oid_chunk:
            organisaatiotyyppi = get_organization_type(vakajarjestaja_data_list.get(vakajarjestaja_oid))
            create_permission_groups_for_organisaatio(vakajarjestaja_oid, organisaatiotyyppi)
            assign_organisaatio_permissions(Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid))
    logger.info('Finished setting vakajarjestaja permissions.')
    logger.info('Setting toimipaikka permissions.')
    toimipaikka_oid_list = (Toimipaikka.objects.exclude(organisaatio_oid__exact='')
                            .values_list('organisaatio_oid', flat=True))
    toimipaikka_oid_chunks = list_to_chunks(toimipaikka_oid_list, 100)
    for toimipaikka_oid_chunk in toimipaikka_oid_chunks:
        for toimipaikka_oid in toimipaikka_oid_chunk:
            create_permission_groups_for_organisaatio(toimipaikka_oid, Organisaatiotyyppi.TOIMIPAIKKA.value)
            assign_toimipaikka_permissions(Toimipaikka.objects.get(organisaatio_oid=toimipaikka_oid))
    logger.info('Finished setting toimipaikka permissions')


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
    return functools.reduce(operator.iconcat, nested_list, [])


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


class TemporaryObject(object):
    def __init__(self, *args, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def get_user_vakajarjestaja(user):
    """
    Determine which Vakajarjestaja user has permissions to and return it
    :param user: User object
    :return: Vakajarjestaja object if user has permissions to only one Vakajarjestaja, otherwise None
    """
    user_group_names = user.groups.values_list('name', flat=True)

    regex_pattern = re.compile(r'.*_([\d\.]*)')
    organisaatio_oid_set = {match.group(1) for group_name in user_group_names
                            if (match := regex_pattern.fullmatch(group_name)) and match.group(1)}

    # organisaatio_oid might be that of Vakajarjestaja or Toimipaikka
    vakajarjestaja_qs = Organisaatio.objects.filter(Q(organisaatio_oid__in=organisaatio_oid_set) |
                                                    Q(toimipaikat__organisaatio_oid__in=organisaatio_oid_set)).distinct()
    if not vakajarjestaja_qs.exists() or vakajarjestaja_qs.count() > 1:
        # User has permissions to multiple Vakajarjestaja or has no permissions at all
        logger.warning(f'Could not determine Vakajarjestaja for user: {user}')
        return None

    return vakajarjestaja_qs.first()


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
        @functools.wraps(func)  # preserves func.__name__
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
