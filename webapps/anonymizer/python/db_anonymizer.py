import base64
import hashlib
import json
import os
import random
import string
import requests
import zipfile
import datetime

from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from django.db.models import Max
from django_pg_bulk_update import bulk_update
from pathlib import Path
from timeit import default_timer as timer
from varda.migrations.testing.setup import create_onr_lapsi_huoltajat
from varda.models import (Henkilo, HistoricalHenkilo, Toimipaikka, VakaJarjestaja,
                          Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Z5_AuditLog)


BATCH_SIZE = 50000
DB_ANONYMIZER_SQL_FILE_PATH = 'anonymizer/sql/anonymizer.sql'
DB_ANONYMIZER_ZIP_FILE_PATH = 'anonymizer/python/anonymized_data.zip'
CORRECT_MD5SUM_OF_ZIP_FILE = '7fceecbc4bdc2021ea8c9a18816018ab'
SAFETY_MARGIN_HENKILOT = 10


def anonymize_data():

    # SQL part
    start = timer()
    print('Anonymizing data (SQL part)...')
    with open(Path(DB_ANONYMIZER_SQL_FILE_PATH), encoding='utf-8') as f:
        with connection.cursor() as c:
            c.execute(f.read())
    end = timer()
    print('SQL part successfully executed in {} seconds'.format(end - start))

    # Python part (Henkilot)
    start = timer()
    print('Anonymizing data (Python part / Hetut and lastnames)...')
    anonymize_henkilot()
    end = timer()
    print('Python part successfully executed in {} seconds'.format(end - start))

    start = timer()
    print('Finalizing the dump.')
    finalize_data_dump()
    end = timer()
    print('Finalizing the dump executed in {} seconds'.format(end - start))


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


def finalize_data_dump():
    """
    - Remove historical-henkilot
    - Remove Z3, Z4, Z5
    - Remove users 3 & 4, plus references to VakaJarjestaja + Toimipaikka
    - Load testdata (fixtures), huoltajat etc.
    """
    HistoricalHenkilo.objects.all().delete()

    Z3_AdditionalCasUserFields.objects.all().delete()
    Z4_CasKayttoOikeudet.objects.all().delete()
    Z5_AuditLog.objects.all().delete()

    user = User.objects.get(id=2)
    vakajarjestaja_1 = VakaJarjestaja.objects.get(id=1)
    vakajarjestaja_1.changed_by = user
    vakajarjestaja_1.save()
    toimipaikka_1 = Toimipaikka.objects.get(id=1)
    toimipaikka_1.changed_by = user
    toimipaikka_1.save()

    user_qs = User.objects.all()
    anonymize_users(user_qs)

    call_command('loaddata', 'varda/unit_tests/fixture_qa_only.json')

    create_onr_lapsi_huoltajat(create_all_vakajarjestajat=True)


def anonymize_henkilot():
    """
    Using https://github.com/M1hacka/django-pg-bulk-update
    Maybe could use Django's own bulk_update when this is fixed: https://code.djangoproject.com/ticket/31202
    """

    # First check if the anonymized_data is found locally. If not fetch it.
    try:
        with open(DB_ANONYMIZER_ZIP_FILE_PATH):
            print('Anonymized data was found locally.')
    except IOError:
        print('Anonymized data was not found locally. Lets fetch it.')

        url = os.getenv('ANONYMIZED_DATA_LOCATION_URL')
        r = requests.get(url, headers=get_authentication_headers_artifactory())
        if r.status_code != 200:
            print('Failed to download the anonymized_data. Status_code: {}'.format(r.status_code))
            return None
        with open(DB_ANONYMIZER_ZIP_FILE_PATH, 'wb') as f:
            f.write(r.content)

    zipfile_info = zipfile.ZipInfo.from_file(DB_ANONYMIZER_ZIP_FILE_PATH)
    if (zipfile_info.date_time[0] == datetime.datetime.now().year and
            zipfile_info.date_time[1] == datetime.datetime.now().month and
            zipfile_info.date_time[2] == datetime.datetime.now().day):
        pass
    else:
        md5sum_of_zip_file = get_md5sum(DB_ANONYMIZER_ZIP_FILE_PATH)
        if md5sum_of_zip_file != CORRECT_MD5SUM_OF_ZIP_FILE:
            print('Error: Downloaded file is corrupted, md5sum doesnt match.')
            return None

    # Unzip the dummy Hetu / sukunimi files and read them
    try:
        with zipfile.ZipFile(DB_ANONYMIZER_ZIP_FILE_PATH, 'r') as zip_ref:
            anonymized_data = read_lines_file(zip_ref, 'anonymized_data.json')
    except zipfile.BadZipFile:
        print('Error: Bad zip-file.')
        return None

    if anonymized_data is None:
        print('Error: Could not unzip the anonymized_data.zip properly.')
        return None

    last_henkilo_id = Henkilo.objects.all().aggregate(Max('id'))['id__max']
    if len(anonymized_data) < last_henkilo_id + SAFETY_MARGIN_HENKILOT:
        print('Not enough anonymized_data. Create more. Last henkilo-id is: {}'.format(last_henkilo_id))
        return None

    """
    Let's slice the anonymized_data list. No need for more anonymized_data than what we have henkilot in DB.
    """
    list_of_anonymized_data = json.loads(anonymized_data)[:last_henkilo_id + SAFETY_MARGIN_HENKILOT]
    updated = bulk_update(Henkilo, list_of_anonymized_data, key_fields='id', batch_size=BATCH_SIZE)
    print('This is how many were actually updated: {}'.format(updated))


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


def get_random_string(length):
    characters = string.ascii_letters + string.digits + '_@+.-'

    random_string = ''
    for i in range(length):
        random_string += random.choice(characters)

    return random_string
