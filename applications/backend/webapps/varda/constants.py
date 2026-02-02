import re

from django.conf import settings

from rest_framework import status

JARJESTAMISMUODOT_KUNTA = ["jm01"]
JARJESTAMISMUODOT_YKSITYINEN = ["jm04", "jm05"]
JARJESTAMISMUODOT_PAOS = ["jm02", "jm03"]

YRITYSMUOTO_KUNTA = ["41", "42"]

SUCCESSFUL_STATUS_CODE_LIST = [status.HTTP_200_OK, status.HTTP_201_CREATED, status.HTTP_204_NO_CONTENT]

OPINTOPOLKU_HEADERS = {"Caller-Id": "csc.varda", "CSRF": "csc.varda", "Cookie": "CSRF=csc.varda"}

SWAGGER_DESCRIPTION = """
    This page contains an interactive documentation of Varda REST API.

    Dates (e.g. alkamis_pvm, paattymis_pvm) must be in the following format: YYYY-MM-DD
    Some fields (e.g. *_koodi) are validated against related list of codes: https://virkailija.opintopolku.fi/varda/julkinen/koodistot
    Error codes returned from the API are listed here: https://virkailija.opintopolku.fi/varda/julkinen/koodistot/vardavirheviestit
"""

HETU_REGEX = re.compile(r"(\d{6})([A+\-])(\d{3}[0-9A-FHJ-NPR-Y])")

ALIVE_BOOT_TIME_CACHE_KEY = "alive_boot_time"
ALIVE_SEQ_CACHE_KEY = "alive_seq"

TEHTAVANIMIKE_KOODI_VAKA_AVUSTAJA = "81787"

MAXIMUM_ASIAKASMAKSU = 311  # eur

# Backend counts are managed by REPLICAS in aws-infrastructure/cdk-pipelines/lib/configuration.py
CELERY_WORKER_COUNT = 6 if settings.PRODUCTION_ENV else 4  # 'else' means QA

YHTEENVETO_TUEN_TIEDOT_DATE_FORMAT = "%d.%m.%Y"
