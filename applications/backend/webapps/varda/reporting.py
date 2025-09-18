import base64
import json
import logging
import os
import requests
import sys
import time

from rest_framework import status
from varda.misc_queries import get_active_vakajarjestajat
from varda.models import Organisaatio, ErrorReports

logger = logging.getLogger(__name__)


VARDA_HOSTNAME = os.getenv("VARDA_HOSTNAME")
VARDA_API_USERNAME = os.getenv("VARDA_API_USERNAME")
VARDA_API_PASSWORD = os.getenv("VARDA_API_PASSWORD")


def base64_encoding(string_to_be_encoded):
    return base64.b64encode(bytes(string_to_be_encoded, "utf-8")).decode("utf-8")


def get_basic_authentication_headers():
    credentials = VARDA_API_USERNAME + ":" + VARDA_API_PASSWORD
    b64_credentials = base64_encoding(credentials)
    return {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Basic {b64_credentials}"}


def get_access_token():
    api_token_endpoint = "/api/user/apikey/"
    try:
        r = requests.get(
            f"https://{VARDA_HOSTNAME}{api_token_endpoint}", headers=get_basic_authentication_headers(), allow_redirects=False
        )
    except requests.exceptions.RequestException as e:
        logger.error(e)
        sys.exit(1)

    status_code = r.status_code
    if status_code != status.HTTP_200_OK:
        logger.error(f"Error! HTTP status code: {status_code}")
        logger.error(r.headers)
        logger.error(r.content)
        sys.exit(1)

    try:
        data = json.loads(r.content)
    except ValueError as e:
        logger.error(e)
        sys.exit(1)
    return data["token"]


def get_http_header(auth_token):
    return {"Accept": "application/json", "Content-Type": "application/json", "Authorization": f"Token {auth_token}"}


def get_request(api_endpoint, auth_token):
    """
    :param api_endpoint:
    :param auth_token:
    :return: {"ok": True: "data": data} if success and {"ok": False, "data": None} if request failed
    """
    url = f"https://{VARDA_HOSTNAME}{api_endpoint}"
    for i in range(3):
        try:
            r = requests.get(url, headers=get_http_header(auth_token))
        except requests.exceptions.RequestException as e:
            logger.error(e)
            return {"ok": False, "data": None}

        status_code = r.status_code
        if status_code == status.HTTP_429_TOO_MANY_REQUESTS and i < 2:
            time.sleep(1 * (1 + i))  # First wait for 1s, then 2s, and finally 3s
            continue
        elif status_code != status.HTTP_200_OK:
            logger.error(f"Error! HTTP status code: {status_code}. Url: {url}")
            logger.error(r.headers)
            logger.error(r.content)
            return {"ok": False, "data": None}

        try:
            data = json.loads(r.content)
        except ValueError as e:
            logger.error(e)
            return {"ok": False, "data": None}
        return {"ok": True, "data": data}


def set_organisaatio_active_errors():
    auth_token = get_access_token()
    active_vakajarjestajat = get_active_vakajarjestajat()
    for vakajarjestaja in active_vakajarjestajat:
        vakajarjestaja_id = vakajarjestaja.id

        try:
            error_reports = vakajarjestaja.error_reports
        except Organisaatio.error_reports.RelatedObjectDoesNotExist:
            error_reports = ErrorReports.objects.create(organisaatio=vakajarjestaja)

        error_report_organisaatio = f"/api/v1/vakajarjestajat/{vakajarjestaja_id}/error-report-organisaatio/"
        error_report_toimipaikat = f"/api/v1/vakajarjestajat/{vakajarjestaja_id}/error-report-toimipaikat/"
        error_report_tyontekijat = f"/api/v1/vakajarjestajat/{vakajarjestaja_id}/error-report-tyontekijat/"
        error_report_lapset = f"/api/v1/vakajarjestajat/{vakajarjestaja_id}/error-report-lapset/"
        endpoints = [error_report_organisaatio, error_report_toimipaikat, error_report_tyontekijat, error_report_lapset]

        for endpoint in endpoints:
            result = get_request(endpoint, auth_token)
            if (result["ok"] and result["data"]["count"] > 0) or (not result["ok"]):
                """
                Include also not result['ok'] since there was an error, e.g. api-request timeout.
                """
                if not error_reports.active_errors:
                    error_reports.active_errors = True
                    error_reports.save()
                break
            elif endpoint == endpoints[-1] and error_reports.active_errors:  # Last one -> No active errors
                error_reports.active_errors = False
                error_reports.save()
