import base64
import json
import logging
import os
import requests
import sys
import time

from rest_framework import status
from varda.misc import get_http_header, update_pulssi
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


def get_request(api_endpoint, auth_token):
    """
    :param api_endpoint:
    :param auth_token:
    :return: {"ok": True: "data": data} if success and {"ok": False, "data": None} if request failed
    """
    url = f"https://{VARDA_HOSTNAME}{api_endpoint}"
    max_retries = 8  # Max 1 + 2 + 4 + 8 + 16 + 32 + 64 + 128 = 255 seconds = 4 minutes 15 seconds

    for i in range(max_retries):
        try:
            r = requests.get(url, headers=get_http_header(auth_token))
            status_code = r.status_code

            if status_code == status.HTTP_200_OK:
                return _handle_success(r)
            elif status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                if i < max_retries - 1:
                    wait_time = _get_wait_time(r, i)
                    time.sleep(wait_time)
                    logger.warning(f"Received 429, retrying after {wait_time} seconds.")
                    continue
                else:
                    logger.error(f"Request failed after {max_retries} retries due to HTTP 429.")
                    return {"ok": False, "data": None}
            else:
                return _handle_error(r, url)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {e}")
            return {"ok": False, "data": None}

    return {"ok": False, "data": None}  # Final fallback (just in case)


def _handle_success(response):
    """Handles a successful 200 OK response."""
    try:
        data = response.json()
        return {"ok": True, "data": data}
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error on 200 response: {e}")
        return {"ok": False, "data": None}


def _handle_error(response, url):
    """Handles a non-429, non-200 HTTP error."""
    logger.error(f"Error! HTTP status code: {response.status_code}. Url: {url}")
    logger.error(response.headers)
    logger.error(response.content)
    return {"ok": False, "data": None}


def _get_wait_time(response, retry_count, initial_delay=1):
    """Determines the appropriate wait time for a 429 response."""
    try:
        error_data = response.json()
        error_description = error_data.get("errors", [{}])[0].get("description")

        if error_description and "Try again in" in error_description:
            # DY008 - application-level rate limit
            try:
                delay = int(error_description.split("in ")[1].split(" ")[0])
                return delay
            except (ValueError, IndexError):
                # Fallback to exponential backoff if description format is unexpected
                logger.warning("Could not parse delay from description. Using exponential backoff.")
                return initial_delay * (2**retry_count)
        else:
            # GE027 - AWS WAF rate limit
            return initial_delay * (2**retry_count)

    except json.JSONDecodeError:
        # If the 429 response is not JSON
        logger.warning("429 response was not valid JSON. Using exponential backoff.")
        return initial_delay * (2**retry_count)


def set_organisaatio_active_errors():
    update_pulssi()  # This will send Slack-alerts if there are big drops in the counts.

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
