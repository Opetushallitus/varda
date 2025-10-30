import logging
import os
import requests

from django.conf import settings
from time import sleep
from urllib.parse import urlencode

from varda.constants import OPINTOPOLKU_HEADERS
from varda.models import Z1_OphAuthentication


logger = logging.getLogger(__name__)

"""
Example taken from: https://github.com/Opetushallitus/tarjonta-api-dokumentaatio/blob/master/lib/authenticate.js
"""


def get_new_ticketing_granting_ticket(username, password, external_request):
    """
    Ticketing granting ticket should be long lasting, therefore we save it to DB:
    https://confluence.csc.fi/display/oppija/Rajapintojen+autentikaatio
    Note: Saving to DB for only varda-application itself. For external users (palvelukayttajat) we do not save tgt.
    """
    if username is None or password is None:
        username = os.getenv("OPINTOPOLKU_USERNAME", "username")
        password = os.getenv("OPINTOPOLKU_PASSWORD", "password")

    credentials = urlencode({"username": username, "password": password})

    headers = {"Content-Type": "application/x-www-form-urlencoded", **OPINTOPOLKU_HEADERS}

    try:
        r = requests.post(settings.OPINTOPOLKU_DOMAIN + "/cas/v1/tickets", data=credentials, headers=headers)
    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException for /cas/v1/tickets. Error: {e}.")
        return None

    if r.status_code == 201:  # successful
        ticket = r.headers["Location"]
        if not external_request:  # internal request -> save to DB
            tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={"ticketing_granting_ticket": ""})[0]
            tgt.ticketing_granting_ticket = ticket
            tgt.save()
        return ticket
    else:
        if username is None:
            username = "None"  # For printing
        logger.warning(f"Error fetching tgt for user: {username}, status code: {r.status_code}. {r.content}")
        return None


def get_service_ticket(service_suffix, username, password, external_request, force_new_tgt):
    service_ticket_url = "service=" + settings.OPINTOPOLKU_DOMAIN + "/" + service_suffix

    # Try to fetch a service ticket 4 times
    for index in range(4):
        headers = {"Content-Type": "application/x-www-form-urlencoded", **OPINTOPOLKU_HEADERS}
        if external_request:
            ticket_granting_ticket_location = get_new_ticketing_granting_ticket(username, password, external_request)
        else:
            tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={"ticketing_granting_ticket": ""})[0]
            ticket_granting_ticket_location = tgt.ticketing_granting_ticket
            if force_new_tgt or not ticket_granting_ticket_location.startswith("http"):
                ticket_granting_ticket_location = get_new_ticketing_granting_ticket(username, password, external_request)

        if ticket_granting_ticket_location is None or not ticket_granting_ticket_location.startswith("http"):
            logger.warning(f"Did not get a service ticket for user: {username}. TGT: {ticket_granting_ticket_location}")
            # Exit loop, most likely username and/or password is incorrect
            break

        try:
            r = requests.post(ticket_granting_ticket_location, data=service_ticket_url, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.error(f"RequestException for ticket_granting_ticket_location. Error: {e}.")
            sleep(2)
            continue

        if r.status_code == 200:  # successful
            return r.content
        elif r.status_code != 404:  # something else than wrong or expired
            logger.error(f"Could not get a TGT. Status: {r.status_code}. {r.content}.")

        # Probably TGT is invalid. Clear the one in DB, and fetch a new one.
        tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={"ticketing_granting_ticket": ""})[0]
        tgt.ticketing_granting_ticket = ""
        tgt.save()
        continue

    return ""


def get_authentication_header(service_name, username=None, password=None, external_request=True, force_new_tgt=False):
    service_ticket_url = get_service_ticket(
        service_name + "/j_spring_cas_security_check", username, password, external_request, force_new_tgt
    )
    # Add 'clientSubSystemCode' rajapintakutsuihin: https://confluence.csc.fi/pages/viewpage.action?pageId=50858064
    # https://github.com/Opetushallitus/dokumentaatio/blob/master/http.md
    return {"CasSecurityTicket": service_ticket_url, "Content-Type": "application/json", **OPINTOPOLKU_HEADERS}


def get_contenttype_header():
    return {"Content-Type": "application/json", **OPINTOPOLKU_HEADERS}
