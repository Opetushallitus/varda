import base64
import datetime
import hashlib
import json
import logging
import os
import random
import requests
import string
import sys
import time
import zipfile

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.db import connection
from django.db.models import Max
from django_pg_bulk_update import bulk_update
from json.decoder import JSONDecodeError
from pathlib import Path
from timeit import default_timer as timer

from varda.models import (Henkilo, Toimipaikka, Organisaatio, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet,
                          Z5_AuditLog, Z6_RequestLog, Z7_AdditionalUserFields, Z8_ExcelReport, Z8_ExcelReportLog)


logger = logging.getLogger(__name__)

BATCH_SIZE = 50000
DB_ANONYMIZER_SQL_FILE_PATH_SETUP = 'anonymizer/sql/anonymizer_setup.sql'
DB_ANONYMIZER_SQL_FILE_PATH_HENKILO = 'anonymizer/sql/anonymizer_henkilo.sql'
DB_ANONYMIZER_SQL_FILE_PATH_TOIMIJA = 'anonymizer/sql/anonymizer_vakatoimija.sql'
DB_ANONYMIZER_SQL_FILE_PATH_VAKATIEDOT = 'anonymizer/sql/anonymizer_vakatiedot.sql'
DB_ANONYMIZER_SQL_FILE_PATH_HENKILOSTO = 'anonymizer/sql/anonymizer_henkilosto.sql'
DB_ANONYMIZER_SQL_FILE_PATH_CLEANUP = 'anonymizer/sql/anonymizer_cleanup.sql'
DB_ANONYMIZER_ZIP_FILE_PATH = 'anonymizer/python/anonymized_data.zip'
SAFETY_MARGIN_HENKILOT = 10
ARTIFACTORY_DOMAIN = settings.ARTIFACTORY_DOMAIN
ARTIFACTORY_GENERIC_REPO_KEY = 'varda-generic-python-local'
ANONYMIZED_DATA_FILE_PATH = 'anonymized_data.zip'
SLEEP_SECONDS_BETWEEN_FAILED_ATTEMPTS = 10


def anonymize_data():
    # SQL part
    operation_type = 'sql'
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_SETUP, 'Setup')
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_HENKILO, 'Henkilo')
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_TOIMIJA, 'Toimija')
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_VAKATIEDOT, 'Vakatiedot')
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_HENKILOSTO, 'Henkilosto')
    run_and_time_operation(operation_type, DB_ANONYMIZER_SQL_FILE_PATH_CLEANUP, 'Cleanup')

    # Python part (Henkilot)
    operation_type = 'python'
    run_and_time_operation(operation_type, anonymize_henkilot, 'Henkilo')
    run_and_time_operation(operation_type, finalize_data_dump, 'Finalize')


def base64_encoding(string_to_be_encoded):
    return base64.b64encode(bytes(string_to_be_encoded, "utf-8")).decode("utf-8")


def get_authentication_headers_artifactory():
    username = os.getenv("ARTIFACTORY_USERNAME")
    password = os.getenv("ARTIFACTORY_PASSWORD")
    credentials = username + ":" + password
    b64_credentials = base64_encoding(credentials)
    reqheaders = {}
    reqheaders['Authorization'] = 'Basic %s' % b64_credentials
    return reqheaders


def get_md5sum(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def run_and_time_operation(operation_type, operation, operation_name):
    start = timer()
    if operation_type == 'sql':
        logger.info('Running anonymizer SQL {}...'.format(operation_name))
        with open(Path(operation), encoding='utf-8') as f:
            with connection.cursor() as c:
                c.execute(f.read())
        end = timer()
        logger.info('{} SQL part successfully executed in {} seconds'.format(operation_name, end - start))
    elif operation_type == 'python':
        operation()
        end = timer()
        logger.info('{} python successfully executed in {} seconds'.format(operation_name, end - start))
    else:
        logger.warning('Unknown operation, nothing executed')


def get_test_accounts():
    """
    :return: Test accounts dict
    """
    test_accounts_json = '/tmp/anonymization/test_accounts.json'
    try:
        data_file = open(test_accounts_json, encoding='utf-8')
        with data_file:
            try:
                return json.loads(data_file.read())
            except JSONDecodeError as e:
                logger.warning(f'Could not load json: {test_accounts_json}.')
                logger.warning(f'Error: {e}')
    except OSError:
        logger.warning(f'Could not open: {test_accounts_json}')

    empty_test_accounts = {
        'admin_users': [],
        'local_staff_users': [],
        'oph_superusers': []
    }
    return empty_test_accounts


def add_admin_users(admin_users):
    for admin_user in admin_users:
        username = admin_user['username']
        user = User.objects.get_or_create(username=username)[0]
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.set_password(admin_user['password'])
        user.save()


def add_local_staff(local_staff_users):
    for local_staff_user in local_staff_users:
        username = local_staff_user['username']
        user = User.objects.get_or_create(username=username)[0]
        user.is_staff = True
        user.is_active = True
        user.set_password(local_staff_user['password'])
        user.save()


def add_oph_staff(oph_superusers):
    for oph_superuser in oph_superusers:
        user_id = oph_superuser['user_id']
        user = User.objects.get(id=user_id)
        user.username = oph_superuser['username']
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.save()
        user.set_unusable_password()


def finalize_data_dump():
    """
    - Remove historical-henkilot
    - Remove Z3, Z4, Z5, Z6, Z7, Z8
    - Remove users 3 & 4, plus references to Organisaatio + Toimipaikka
    - Load testdata (fixtures), huoltajat etc.
    """
    logger.info('Finalizing the data dump.')

    logger.info('Removing unnecessary data.')

    Session.objects.all().delete()
    Henkilo.history.all().delete()
    Z3_AdditionalCasUserFields.objects.all().delete()
    Z4_CasKayttoOikeudet.objects.all().delete()
    Z5_AuditLog.objects.all().delete()
    Z6_RequestLog.objects.all().delete()
    Z7_AdditionalUserFields.objects.all().delete()
    Z8_ExcelReport.objects.all().delete()
    Z8_ExcelReportLog.objects.all().delete()

    vakajarjestaja_1 = Organisaatio.objects.get(id=1)
    vakajarjestaja_1.save()
    toimipaikka_1 = Toimipaikka.objects.get(id=1)
    toimipaikka_1.save()

    logger.info('Anonymize the users.')
    user_qs = User.objects.all().exclude(username__in=('anonymous', 'varda_system'))
    anonymize_users(user_qs)
    logger.info('Add test-accounts.')
    test_accounts = get_test_accounts()
    add_admin_users(test_accounts['admin_users'])
    add_local_staff(test_accounts['local_staff_users'])
    add_oph_staff(test_accounts['oph_superusers'])


def fetch_generated_data_and_verify_checksum():
    """
    First check if the anonymized_data is found locally. If not, fetch it.
    In case of problems, sleep for a while, and try once again.

    :return: True if zip-file is ok, else False
    """
    for x in range(2):
        try:
            with open(DB_ANONYMIZER_ZIP_FILE_PATH):
                logger.info('Anonymized data was found locally.')
        except IOError:
            logger.info('Anonymized data was not found locally. Lets fetch it.')

            file_url = f'{ARTIFACTORY_DOMAIN}/artifactory/{ARTIFACTORY_GENERIC_REPO_KEY}/{ANONYMIZED_DATA_FILE_PATH}'
            r = requests.get(file_url, headers=get_authentication_headers_artifactory())

            if r.status_code == 200:
                logger.info('Fetching the zip-file finished.')
            else:
                logger.warning(f'Failed to download the anonymized_data. Status code: {r.status_code}')
                if x == 0:
                    time.sleep(SLEEP_SECONDS_BETWEEN_FAILED_ATTEMPTS)
                    continue
                else:
                    return False

            with open(DB_ANONYMIZER_ZIP_FILE_PATH, 'wb') as f:
                f.write(r.content)

        # Verify the zip-file checksum
        file_info_url = f'{ARTIFACTORY_DOMAIN}/artifactory/api/storage/' \
                        f'{ARTIFACTORY_GENERIC_REPO_KEY}/{ANONYMIZED_DATA_FILE_PATH}'
        r = requests.get(file_info_url, headers=get_authentication_headers_artifactory())

        if r.status_code == 200:
            correct_md5sum_of_zip_file = r.json()['checksums']['md5']
        else:
            logger.warning(f'Failed to fetch checksum. Status code: {r.status_code}')
            if x == 0:
                time.sleep(SLEEP_SECONDS_BETWEEN_FAILED_ATTEMPTS)
                continue
            else:
                return False

        md5sum_of_zip_file = get_md5sum(DB_ANONYMIZER_ZIP_FILE_PATH)
        if md5sum_of_zip_file == correct_md5sum_of_zip_file:
            logger.info('Zip-file checksum OK.')
            break
        else:
            logger.warning('Error: Downloaded zip-file is corrupted, checksum doesnt match.')
            if x == 0:
                os.remove(DB_ANONYMIZER_ZIP_FILE_PATH)
                logger.info('Removed the corrupted zip-file.')
                time.sleep(SLEEP_SECONDS_BETWEEN_FAILED_ATTEMPTS)
                continue
            else:
                return False

    return True


def anonymize_henkilot():
    zip_file_is_ok = fetch_generated_data_and_verify_checksum()
    if not zip_file_is_ok:
        sys.exit(1)

    # Unzip the dummy Hetu / sukunimi files and read them
    try:
        with zipfile.ZipFile(DB_ANONYMIZER_ZIP_FILE_PATH, 'r') as zip_ref:
            anonymized_data = read_lines_file(zip_ref, 'anonymized_data.json')
    except zipfile.BadZipFile:
        logger.error('Error: Bad zip-file.')
        return None

    if anonymized_data is None:
        logger.error('Error: Could not unzip the anonymized_data.zip properly.')
        return None

    last_henkilo_id = Henkilo.objects.all().aggregate(Max('id'))['id__max']
    if len(anonymized_data) < last_henkilo_id + SAFETY_MARGIN_HENKILOT:
        logger.warning(f'Not enough anonymized_data. Create more. Last henkilo-id is: {last_henkilo_id}')
        return None

    """
    Let's slice the anonymized_data list. No need for more anonymized_data than what we have henkilot in DB.
    """
    logger.info('Loading the preset in memory...')
    list_of_anonymized_data = json.loads(anonymized_data)[:last_henkilo_id + SAFETY_MARGIN_HENKILOT]

    """
    Using https://github.com/M1hacka/django-pg-bulk-update
    Maybe could use Django's own bulk_update when this is fixed: https://code.djangoproject.com/ticket/31202
    """
    logger.info('Starting to update henkilot...')
    updated = bulk_update(Henkilo, list_of_anonymized_data, key_fields='id', batch_size=BATCH_SIZE)
    logger.info(f'This is how many were actually updated: {updated}')


def read_lines_file(zip_ref, file):
    """
    Read lines from file and return them.
    """
    with zip_ref.open(file) as f:
        content = f.read()
    return content


def anonymize_users(user_qs):
    for user in user_qs:
        # Get random username and make sure it doesn't exist
        random_username = get_random_string(10)
        while User.objects.filter(username=random_username).exists():
            random_username = get_random_string(10)

        user.username = random_username

        # Set password unusable
        user.set_unusable_password()

        # Remove personal information
        user.first_name = ''
        user.last_name = ''
        user.email = ''
        user.last_login = None
        user.date_joined = datetime.datetime.now(tz=datetime.timezone.utc)

        # Remove superuser and staff status and set users as inactive
        user.is_superuser = False
        user.is_staff = False
        user.is_active = False
        user.save()


def get_random_string(length, special_characters=True):
    if special_characters:
        characters = string.ascii_letters + string.digits + '_@+.-'
    else:
        characters = string.ascii_letters + string.digits
    random_string = ''
    for i in range(length):
        random_string += random.choice(characters)

    return random_string
