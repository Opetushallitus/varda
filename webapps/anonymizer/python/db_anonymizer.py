import datetime
import random
import zipfile
from django.db import connection
from pathlib import Path
from timeit import default_timer as timer

DB_ANONYMIZER_SQL_FILE_PATH = 'anonymizer/sql/anonymizer.sql'
DB_ANONYMIZER_ZIP_FILE_PATH = 'anonymizer/anonymize.zip'


def anonymize_data():

    # SQL part
    start = timer()
    print("Anonymizing data (SQL part)...")
    with open(Path(DB_ANONYMIZER_SQL_FILE_PATH), encoding='utf-8') as f:
        with connection.cursor() as c:
            c.execute(f.read())
    f.close()
    end = timer()
    print("SQL part successfully executed in " + str(end - start) + " seconds")

    # Python part (Hetut)
    start = timer()
    print("Anonymizing data (Python part / Hetut and lastnames)...")
    anonymize_hetu()
    end = timer()
    print("Python part successfully executed in " + str(end - start) + " seconds")


def anonymize_hetu():
    from varda.misc import encrypt_henkilotunnus, hash_string
    from varda.models import Henkilo

    # Unzip the dummy Hetu / sukunimi files and read them
    with zipfile.ZipFile(DB_ANONYMIZER_ZIP_FILE_PATH, 'r') as zip_ref:
        hetut = read_lines_file(zip_ref, 'hetut_anonymize.txt')
        sukunimet = read_lines_file(zip_ref, 'sukunimet_anonymize.txt')

        henkilot = Henkilo.objects.all()

        for i, henkilo in enumerate(henkilot):
            # Hetu
            hetu = hetut[i].decode("utf-8").rstrip("\n\r")
            henkilo.henkilotunnus = encrypt_henkilotunnus(hetu)
            henkilo.henkilotunnus_unique_hash = hash_string(hetu)

            # Lastname
            henkilo.sukunimi = random.choice(sukunimet).decode("utf-8").rstrip("\n\r")

            # Birthdate and gender
            henkilo.syntyma_pvm = get_syntymaaika(hetu)
            henkilo.sukupuoli_koodi = get_sukupuoli(hetu)

            henkilo.save()


def read_lines_file(zip_ref, file):
    """
    Read lines from file and return them.
    """
    with zip_ref.open(file) as f:
        lines = f.readlines()
    f.close()
    return lines


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
    return datetime.date(int(cent + year), int(month), int(day))


def get_sukupuoli(henkilotunnus):
    """
    Get gender from Hetu string.
    """
    number = henkilotunnus[7:10]
    return '1' if int(number) % 2 == 0 else '2'
