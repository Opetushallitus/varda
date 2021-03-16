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
        username = os.getenv('OPINTOPOLKU_USERNAME', 'username')
        password = os.getenv('OPINTOPOLKU_PASSWORD', 'password')

    credentials = urlencode({
        'username': username,
        'password': password
    })

    headers = {'Content-Type': 'application/x-www-form-urlencoded', **OPINTOPOLKU_HEADERS}

    try:
        r = requests.post(settings.OPINTOPOLKU_DOMAIN + '/cas/v1/tickets', data=credentials, headers=headers)
    except requests.exceptions.RequestException as e:
        logger.error('RequestException for /cas/v1/tickets. Error: {}.'.format(e))
        return None

    if r.status_code == 201:  # successful
        ticket = r.headers['Location']
        if not external_request:  # internal request -> save to DB
            tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={'ticketing_granting_ticket': ''})[0]
            tgt.ticketing_granting_ticket = ticket
            tgt.save()
        return ticket
    else:
        if username is None:
            username = 'None'  # For printing
        logger.warning('Error fetching tgt for user: ' + username + ', status code: ' + str(r.status_code) + '. ' + str(r.content))
        return None


def get_service_ticket(service_suffix, username, password, external_request):
    service_ticket_url = 'service=' + settings.OPINTOPOLKU_DOMAIN + '/' + service_suffix

    LOOP_NUMBER = 0
    MAX_NO_OF_LOOPS = 4

    while LOOP_NUMBER < MAX_NO_OF_LOOPS:
        LOOP_NUMBER += 1
        headers = {'Content-Type': 'application/x-www-form-urlencoded', **OPINTOPOLKU_HEADERS}
        if external_request:
            ticket_granting_ticket_location = get_new_ticketing_granting_ticket(username, password, external_request)
        else:
            tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={'ticketing_granting_ticket': ''})[0]
            ticket_granting_ticket_location = tgt.ticketing_granting_ticket
            if not ticket_granting_ticket_location.startswith('http'):
                ticket_granting_ticket_location = get_new_ticketing_granting_ticket(username, password, external_request)

        if ticket_granting_ticket_location is None or not ticket_granting_ticket_location.startswith('http'):
            break  # exit loop

        try:
            r = requests.post(ticket_granting_ticket_location, data=service_ticket_url, headers=headers)
        except requests.exceptions.RequestException as e:
            logger.error('RequestException for ticket_granting_ticket_location. Error: {}.'.format(e))
            sleep(2)
            continue

        if r.status_code == 200:  # successful
            return r.content
        elif r.status_code != 404:  # something else than wrong or expired
            logger.error('Could not get a TGT. Status: {}. {}.'.format(r.status_code, r.content))

        """
        Probably TGT is unvalid. Clear the one in DB, and fetch a new one.
        """
        tgt = Z1_OphAuthentication.objects.get_or_create(id=1, defaults={'ticketing_granting_ticket': ''})[0]
        tgt.ticketing_granting_ticket = ''
        tgt.save()
        continue

    logger.error('Error: Did not get a service ticket for user: ' + str(username) + '. TGT: ' + str(ticket_granting_ticket_location))
    return ''


def get_authentication_header(service_name, username=None, password=None, external_request=True):
    service_ticket_url = get_service_ticket(service_name + '/j_spring_cas_security_check', username, password, external_request)
    # Add 'clientSubSystemCode' rajapintakutsuihin: https://confluence.csc.fi/pages/viewpage.action?pageId=50858064
    # https://github.com/Opetushallitus/dokumentaatio/blob/master/http.md
    return {'CasSecurityTicket': service_ticket_url, 'Content-Type': 'application/json', **OPINTOPOLKU_HEADERS}


def get_contenttype_header():
    return {'Content-Type': 'application/json', **OPINTOPOLKU_HEADERS}
