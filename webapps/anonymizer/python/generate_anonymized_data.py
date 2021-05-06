import json
import logging
import os
import random
import zipfile
import datetime

from calendar import monthrange
from django.db.models import Max
from timeit import default_timer as timer
from varda.models import Henkilo
from varda.misc import encrypt_string, hash_string


logger = logging.getLogger(__name__)

DB_ANONYMIZER_ZIP_FILE_PATH = 'anonymizer/python/anonymized_names.zip'
KUNTAKOODI_FILE = 'anonymizer/python/kuntakoodit.zip'
DB_ANONYMIZED_JSON_FILE = '/tmp/anonymized_data.json'
DB_ANONYMIZED_ZIP_FILE_PATH = 'anonymizer/python/anonymized_data.zip'
CHECK_KEYS = '0123456789ABCDEFHJKLMNPRSTUVWXY'
CENTURIES = {'18': '+', '19': '-', '20': 'A'}


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

    check_number = '%02d%02d%s%03d' % (day, month, str(year)[2:4],
                                       order_num)

    check_number_index = int(check_number) % 31
    key = CHECK_KEYS[check_number_index]

    return '%02d%02d%s%s%03d%s' % (day, month, str(year)[2:4],
                                   century_sep, order_num, key)


def get_syntymaaika(henkilotunnus):
    """
    Get birthdate from Hetu string.
    """
    day = henkilotunnus[:2]
    month = henkilotunnus[2:4]
    year = henkilotunnus[4:6]
    century = henkilotunnus[6]
    if century == '-':
        cent = '19'
    else:
        cent = '20'
    return cent + year + '-' + month + '-' + day


def read_lines_file(zip_ref, file):
    """
    Read lines from file and return them.
    """
    with zip_ref.open(file) as f:
        lines = f.readlines()
    f.close()
    return lines


def create_henkilo(henkilo, henkilotunnus_unique_hash_set, file, etunimet_miehet, etunimet_naiset, sukunimet):
    from anonymizer.python.db_anonymizer import get_random_string
    # Gender
    sukupuoli_koodi = henkilo['sukupuoli_koodi'] or random.randint(1, 2)
    syntyma_pvm = henkilo['syntyma_pvm'] or datetime.date(random.randint(1990, 2019), random.randint(1, 12), random.randint(1, 28))

    # Henkilotunnus
    henkilotunnus = create_hetu_from_birthday(syntyma_pvm, sukupuoli_koodi)
    encrypted_henkilotunnus = encrypt_string(henkilotunnus)
    henkilotunnus_unique_hash = hash_string(henkilotunnus)

    # counter is to prevent infinite loop if there are duplicates in the data the max amount could be adjusted
    counter = 0
    while henkilotunnus_unique_hash in henkilotunnus_unique_hash_set and counter <= 100:
        henkilotunnus = create_hetu_from_birthday(syntyma_pvm, sukupuoli_koodi)
        encrypted_henkilotunnus = encrypt_string(henkilotunnus)
        henkilotunnus_unique_hash = hash_string(henkilotunnus)
        counter += 1

    if counter > 10:
        logger.info(f'Counter value for looping through duplicates: {counter}.')

    # Henkilo oid
    henkilo_oid_suffix = henkilo['id'] + 10000000000
    henkilo_oid = f'1.2.246.562.24.{henkilo_oid_suffix}'

    # Names
    if sukupuoli_koodi == '1':
        etunimi = random.choice(etunimet_miehet).decode('utf-8').rstrip('\n\r')
    else:  # sukupuoli_koodi == '2'
        etunimi = random.choice(etunimet_naiset).decode('utf-8').rstrip('\n\r')

    kutsumanimi = etunimi.split('-')[0]
    sukunimi = random.choice(sukunimet).decode('utf-8').rstrip('\n\r')

    # Get new syntyma_pvm from randomized hetu
    syntyma_pvm = get_syntymaaika(henkilotunnus)

    # Street address
    katuosoite = get_random_string(length=15, special_characters=False)
    postinumero = random.randrange(10000, 99999)

    data = {
        'id': henkilo['id'],
        'henkilotunnus': encrypted_henkilotunnus,
        'henkilotunnus_unique_hash': henkilotunnus_unique_hash,
        'henkilo_oid': henkilo_oid,
        'etunimet': etunimi,
        'kutsumanimi': kutsumanimi,
        'sukunimi': sukunimi,
        'syntyma_pvm': syntyma_pvm,
        'sukupuoli_koodi': sukupuoli_koodi,
        'kotikunta_koodi': henkilo['kotikunta_koodi'],
        'katuosoite': katuosoite,
        'postinumero': postinumero
    }
    json.dump(data, file)
    file.write(',\n')
    henkilotunnus_unique_hash_set.add(henkilotunnus_unique_hash)


def create_anonymized_data_dump():
    start = timer()
    henkilotunnus_unique_hash_set = set()
    logger.info('Creating the anonymized datadump...')
    # Unzip the dummy data and read the files
    with zipfile.ZipFile(DB_ANONYMIZER_ZIP_FILE_PATH, 'r') as zip_ref:
        etunimet_miehet = read_lines_file(zip_ref, 'etunimet_miehet.txt')
        etunimet_naiset = read_lines_file(zip_ref, 'etunimet_naiset.txt')
        sukunimet = read_lines_file(zip_ref, 'sukunimet.txt')

    with zipfile.ZipFile(KUNTAKOODI_FILE, 'r') as kuntakoodi_ref:
        kuntakoodit = read_lines_file(kuntakoodi_ref, 'kuntakoodit.txt')

    with open(DB_ANONYMIZED_JSON_FILE, 'w+') as f:
        f.write('[')

    with open(DB_ANONYMIZED_JSON_FILE, 'a+', encoding='utf-8') as f:
        henkilot = (Henkilo
                    .objects
                    .all()
                    .order_by('id')
                    .values('syntyma_pvm', 'id', 'sukupuoli_koodi', 'kotikunta_koodi'))
        max_id = Henkilo.objects.all().aggregate(Max('id'))['id__max']
        for henkilo in henkilot:
            create_henkilo(henkilo, henkilotunnus_unique_hash_set, f, etunimet_miehet, etunimet_naiset, sukunimet)
        counter = 1
        while counter < 100000:  # The amount of extra person info added to the dataset -1
            imaginary_henkilo = henkilo
            imaginary_henkilo['sukupuoli_koodi'] = random.randint(1, 2)
            imaginary_henkilo['syntyma_pvm'] = datetime.date(random.randint(2010, 2019), random.randint(1, 12), random.randint(1, 28))
            imaginary_henkilo['id'] = max_id + counter
            imaginary_henkilo['kotikunta_koodi'] = random.choice(kuntakoodit).decode('utf-8').rstrip('\n\r')
            create_henkilo(imaginary_henkilo, henkilotunnus_unique_hash_set, f, etunimet_miehet, etunimet_naiset, sukunimet)
            counter += 1

    with open(DB_ANONYMIZED_JSON_FILE, 'rb+') as f:
        """
        Remove two last chars in the file: ', '
        """
        if os.name == 'nt':
            f.seek(-3, os.SEEK_END)
        else:
            f.seek(-2, os.SEEK_END)
        f.truncate()

    with open(DB_ANONYMIZED_JSON_FILE, 'a') as f:
        f.write(']')

    # Finally create a new zip-file with the new content, and remove the temp-json
    with zipfile.ZipFile(DB_ANONYMIZED_ZIP_FILE_PATH, 'w') as zip_obj:
        zip_obj.write(DB_ANONYMIZED_JSON_FILE, 'anonymized_data.json')

    os.remove(DB_ANONYMIZED_JSON_FILE)

    end = timer()
    logger.info('Creation finished in {} seconds'.format(end - start))
