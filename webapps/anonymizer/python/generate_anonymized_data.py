import json
import os
import random
import zipfile

from calendar import monthrange
from timeit import default_timer as timer
from varda.misc import encrypt_henkilotunnus, hash_string


DB_ANONYMIZER_ZIP_FILE_PATH = 'anonymizer/python/anonymized_names.zip'
CHECK_KEYS = '0123456789ABCDEFHJKLMNPRSTUVWXY'
CENTURIES = {'18': '+', '19': '-', '20': 'A'}


def create_hetu(start=2011, end=2019):
    """
    Taken from: https://gist.github.com/puumuki/11172310
    """
    year = random.randint(start, end)
    month = random.randint(1, 12)
    day = random.randint(1, monthrange(year, month)[1])

    century_sep = CENTURIES[str(year)[0:2]]

    order_num = random.randint(2, 889)

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


def get_sukupuoli(henkilotunnus):
    """
    Get gender from Hetu string.
    1: mies (man)
    2: nainen (woman)
    """
    number = henkilotunnus[7:10]
    return '1' if int(number) % 2 == 0 else '2'


def read_lines_file(zip_ref, file):
    """
    Read lines from file and return them.
    """
    with zip_ref.open(file) as f:
        lines = f.readlines()
    f.close()
    return lines


def create_anonymized_data_dump(no_of_anonymized_henkilo):
    start = timer()
    print('Creating the anonymized datadump...')
    # Unzip the dummy data and read the files
    with zipfile.ZipFile(DB_ANONYMIZER_ZIP_FILE_PATH, 'r') as zip_ref:
        etunimet_miehet = read_lines_file(zip_ref, 'etunimet_miehet.txt')
        etunimet_naiset = read_lines_file(zip_ref, 'etunimet_naiset.txt')
        sukunimet = read_lines_file(zip_ref, 'sukunimet.txt')

    with open('anonymized_data.json', 'w+') as f:
        f.write('[')

    with open('anonymized_data.json', 'a', encoding='utf-8') as f:
        for henkilo_id in range(no_of_anonymized_henkilo):
            # Henkilotunnus
            henkilotunnus = create_hetu()
            encrypted_henkilotunnus = encrypt_henkilotunnus(henkilotunnus)
            henkilotunnus_unique_hash = hash_string(henkilotunnus)

            # Gender
            sukupuoli_koodi = get_sukupuoli(henkilotunnus)

            # Names
            if sukupuoli_koodi == '1':
                etunimi = random.choice(etunimet_miehet).decode('utf-8').rstrip('\n\r')
            else:  # sukupuoli_koodi == '2'
                etunimi = random.choice(etunimet_naiset).decode('utf-8').rstrip('\n\r')

            kutsumanimi = etunimi.split('-')[0]
            sukunimi = random.choice(sukunimet).decode('utf-8').rstrip('\n\r')

            # Birthdate
            syntyma_pvm = get_syntymaaika(henkilotunnus)

            data = {
                'id': henkilo_id,
                'henkilotunnus': encrypted_henkilotunnus,
                'henkilotunnus_unique_hash': henkilotunnus_unique_hash,
                'etunimet': etunimi,
                'kutsumanimi': kutsumanimi,
                'sukunimi': sukunimi,
                'syntyma_pvm': syntyma_pvm,
                'sukupuoli_koodi': sukupuoli_koodi
            }
            json.dump(data, f)
            f.write(',\n')

    with open('anonymized_data.json', 'rb+') as f:
        """
        Remove two last chars in the file: ', '
        """
        f.seek(-2, os.SEEK_END)
        f.truncate()

    with open('anonymized_data.json', 'a') as f:
        f.write(']')

    # Finally create a new zip-file with the new content, and remove the temp-json
    with zipfile.ZipFile('anonymizer/python/anonymized_data.zip', 'w') as zip_obj:
        zip_obj.write('anonymized_data.json')

    os.remove('anonymized_data.json')

    end = timer()
    print('Creation finished in {} seconds'.format(end - start))
