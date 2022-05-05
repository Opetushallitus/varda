import json
import logging

from rest_framework import status

from varda.misc import get_json_from_external_service, get_reply_json, hash_string, post_json_to_external_service
from varda.models import Henkilo


logger = logging.getLogger(__name__)

SERVICE_NAME = 'oppijanumerorekisteri-service'


def get_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi):
    return get_or_create_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi, create_new=False)


def get_or_create_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi, create_new=True):
    """
    Example of return-JSON:
    {
      "id": 64660804,
      "etunimet": "Mt-Testi",
      "syntymaaika": "1998-01-02",
      "kuolinpaiva": null,
      "hetu": "020198-9567",
      "kutsumanimi": "Mt-Testi",
      "oidHenkilo": "1.2.246.562.24.33698282553",
      "oppijanumero": null,
      "sukunimi": "Omatsivut-Testaaja",
      "sukupuoli": "2",
      "turvakielto": false,
      "henkiloTyyppi": "OPPIJA",
      "eiSuomalaistaHetua": false,
      "passivoitu": false,
      "yksiloity": false,
      "yksiloityVTJ": false,
      "yksilointiYritetty": false,
      "duplicate": false,
      "created": 1514905831026,
      "modified": 1516627104532,
      "vtjsynced": null,
      "kasittelijaOid": "1.2.246.562.24.11272665615",
      "asiointiKieli": null,
      "aidinkieli": {
        "id": 1,
        "kieliKoodi": "fi",
        "kieliTyyppi": "suomi"
      },
      "huoltaja": null,
      "kielisyys": [],
      "kansalaisuus": [
        {
          "id": 1,
          "kansalaisuusKoodi": "246"
        }
      ],
      "yhteystiedotRyhma": [
        {
          "id": 71514267,
          "ryhmaKuvaus": "yhteystietotyyppi2",
          "ryhmaAlkuperaTieto": "alkupera2",
          "readOnly": false,
          "yhteystieto": [
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_SAHKOPOSTI",
              "yhteystietoArvo": "arpa-kuutio@example.com"
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_PUHELINNUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_MATKAPUHELINNUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_POSTINUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_KUNTA",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_KATUOSOITE",
              "yhteystietoArvo": null
            }
          ]
        }
      ],
    }
    """
    reply_msg = get_json_from_external_service(SERVICE_NAME, '/henkilo/hetu={}'.format(henkilotunnus), auth=True)
    default_henkilo_query_error_result = {'new_henkilo': False, 'result': None}

    if reply_msg['is_ok']:
        return {'new_henkilo': False, 'result': reply_msg['json_msg']}
    else:
        """
        Henkilo was not found by henkilotunnus. Let's add it to Oppijanumerorekisteri.
        """
        if create_new:
            return add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=henkilotunnus)
        else:
            return default_henkilo_query_error_result


def add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=None):
    default_henkilo_query_error_result = {'new_henkilo': False, 'result': None}
    if henkilotunnus:
        new_henkilo_oid_in_oppijanumerorekisteri = _add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=henkilotunnus)
    else:
        new_henkilo_oid_in_oppijanumerorekisteri = _add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi)
    if new_henkilo_oid_in_oppijanumerorekisteri is None:
        return default_henkilo_query_error_result
    else:
        return {'new_henkilo': True, 'result': get_henkilo_data_by_oid(new_henkilo_oid_in_oppijanumerorekisteri)}


def _add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=None):
    """
    Create new henkilo to ONR
    :param etunimet: First names
    :param kutsumanimi: Nick name
    :param sukunimi: Last name
    :param henkilotunnus: SSN
    :return: Oid of created henkilo or None
    """
    new_henkilo = {
        'etunimet': etunimet,
        'kutsumanimi': kutsumanimi,
        'sukunimi': sukunimi
    }
    if henkilotunnus:
        new_henkilo['hetu'] = henkilotunnus

    reply_msg = post_json_to_external_service(SERVICE_NAME, '/henkilo/', json.dumps(new_henkilo), status.HTTP_201_CREATED, auth=True, reply_type='text')
    if reply_msg['is_ok']:
        return reply_msg['json_msg']
    elif henkilotunnus:
        henkilo = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string(henkilotunnus))
        henkilo_id = henkilo.id
        added_by = henkilo.history.last().history_user.username
        henkilotunnus_prefix_hided = henkilotunnus and 'DDMMYY' + henkilotunnus[-5:]
        logger.error('Couldn\'t add a new henkilo to Oppijanumerorekisteri. Henkilotunnus: {}. Id: {}. Added by: {}'
                     .format(henkilotunnus_prefix_hided, henkilo_id, added_by))
        return None


def get_henkilo_data_by_oid(oid):
    """
    Fetch henkilo's master henkilo data from oppijanumerorekisteri.
    Example of return-JSON:
    {
      "id": 68394254,
      "etunimet": "Airi Testi",
      "syntymaaika": "2013-01-01",
      "kuolinpaiva": null,
      "hetu": "010113A9127",
      "kutsumanimi": "Airi",
      "oidHenkilo": "1.2.246.562.24.87081324139",
      "oppijanumero": "1.2.246.562.24.87081324139",
      "sukunimi": "Stenberg-Testi",
      "sukupuoli": "2",
      "kotikunta": null,
      "turvakielto": false,
      "eiSuomalaistaHetua": false,
      "passivoitu": false,
      "yksiloity": false,
      "yksiloityVTJ": true,
      "yksilointiYritetty": true,
      "duplicate": false,
      "created": 1518592887587,
      "modified": 1538146363041,
      "vtjsynced": null,
      "kasittelijaOid": "1.2.246.562.24.66631583590",
      "asiointiKieli": null,
      "aidinkieli": {
        "id": 1,
        "kieliKoodi": "fi",
        "kieliTyyppi": "suomi"
      },
      "huoltaja": null,
      "kielisyys": [],
      "kansalaisuus": [],
      "yhteystiedotRyhma": [],
      "henkiloTyyppi": "OPPIJA",
      "yhteystiedotRyhma": [
        {
          "id": 71514267,
          "ryhmaKuvaus": "yhteystietotyyppi2",
          "ryhmaAlkuperaTieto": "alkupera2",
          "readOnly": false,
          "yhteystieto": [
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_SAHKOPOSTI",
              "yhteystietoArvo": "arpa-kuutio@example.com"
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_PUHELINNUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_MATKAPUHELINNUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_POSTINUMERO",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_KUNTA",
              "yhteystietoArvo": null
            },
            {
              "yhteystietoTyyppi": "YHTEYSTIETO_KATUOSOITE",
              "yhteystietoArvo": null
            }
          ]
        }
      ],
    }
    """
    reply_msg = get_json_from_external_service(SERVICE_NAME, '/henkilo/{}/master'.format(oid), auth=True)

    if reply_msg['is_ok']:
        return reply_msg['json_msg']
    else:
        logger.error('Couldn\'t fetch henkilo with oid: {}'.format(oid))
        return None


def get_henkilot_changed_since(start_datetime, offset, amount=5000):
    """
    Fetch changed henkilot from oppijanumerorekisteri.
    :param start_datetime: Date time (in ISO 8601) since when we fetch changes
    :param offset: position of the paginated (and ordered) dataset
    :param amount: How many (max) are fetched
    :return: Reply-json: ok and list of henkilo oids or not ok and None
    """
    url = '/s2s/changedSince/{}?amount={}&offset={}'.format(start_datetime, amount, offset)
    response = get_json_from_external_service(SERVICE_NAME, url, large_query=True)
    return get_reply_json(is_ok=response['is_ok'], json_msg=response['json_msg'])


def get_huoltajasuhde_changed_child_oids(start_datetime, offset, amount=5000):
    """
    Fetch changed huoltajasuhteet from oppijanumerorekisteri.
    :param start_datetime: Date time (in ISO 8601) since when we fetch changes
    :param offset: position of the paginated (and ordered) dataset
    :param amount: How many (max) are fetched
    :return: Reply-json: ok and list of lapsi oids or not ok and None
    """
    url = '/henkilo/huoltajasuhdemuutokset/alkaen/{}?amount={}&offset={}'.format(start_datetime, amount, offset)
    response = get_json_from_external_service(SERVICE_NAME, url, large_query=True)
    return get_reply_json(is_ok=response['is_ok'], json_msg=response['json_msg'])


def fetch_changed_huoltajuussuhteet(start_datetime):
    """
    Fetch changes in huoltajuussuhde.
    :return: Reply-json: ok and list of lapsi oids or not ok and None
    """
    list_of_changed_lapsi_oids = []

    amount = 5000  # This is how many lapsi_oids are fetched with one GET-request (max).
    offset = 0     # With zero we fetch items 0-4999, offset 5000 -> items 5000 - 9999.
    loop_number = 1
    while True:
        changed_lapsi_oids_msg = get_huoltajasuhde_changed_child_oids(start_datetime, offset, amount)
        if not changed_lapsi_oids_msg['is_ok']:
            """
            Something went wrong. Cancel fetching, and return is_ok=False.
            """
            logger.error('Could not fetch the changed huoltajuussuhteet, {}, {}, {}.'
                         .format(start_datetime, offset, amount))
            return get_reply_json(is_ok=False, json_msg=None)

        list_of_changed_lapsi_oids += changed_lapsi_oids_msg['json_msg']
        len_of_fetched_lapsi_oids = len(changed_lapsi_oids_msg['json_msg'])

        if len_of_fetched_lapsi_oids < amount:  # We got everything. Return the list of all changed lapsi oids
            return get_reply_json(is_ok=True, json_msg=list_of_changed_lapsi_oids)
        elif len_of_fetched_lapsi_oids == amount:
            offset += amount
            loop_number += 1
            if loop_number % 20 == 0:
                logger.warning('Very large queries to changed huoltajuussuhteet. Current amount: {}'
                               .format(loop_number * amount))
            continue  # We (probably) didn't get everything yet. Fetch another batch.
        else:
            logger.error('Changed huoltajuussuhteet: We got more than we requested. Received: {}, Requested: {}'
                         .format(len_of_fetched_lapsi_oids, amount))
            return get_reply_json(is_ok=False, json_msg=None)


def fetch_changed_henkilot(start_datetime):
    """
    Fetch changes in henkilot.
    :return: Reply-json: ok and list of henkilo oids or not ok and None
    """
    list_of_all_changed_oppijanumerot = []

    amount = 5000  # This is how many henkilo_oids are fetched with one GET-request (max).
    offset = 0     # With zero we fetch items 0-4999, offset 5000 -> items 5000 - 9999.
    loop_number = 1
    while True:
        changed_henkilo_oids_msg = get_henkilot_changed_since(start_datetime, offset, amount)
        if not changed_henkilo_oids_msg['is_ok']:
            """
            Something went wrong. Cancel fetching, and return is_ok=False.
            """
            logger.error('Could not fetch the changed henkilot, {}, {}, {}.'
                         .format(start_datetime, offset, amount))
            return get_reply_json(is_ok=False, json_msg=None)

        list_of_all_changed_oppijanumerot += changed_henkilo_oids_msg['json_msg']
        len_of_fetched_henkilo_oids = len(changed_henkilo_oids_msg['json_msg'])

        if len_of_fetched_henkilo_oids < amount:  # We got everything. Return the list of all changed henkilo oids
            return get_reply_json(is_ok=True, json_msg=list_of_all_changed_oppijanumerot)
        elif len_of_fetched_henkilo_oids == amount:
            offset += amount
            loop_number += 1
            if loop_number % 20 == 0:
                logger.warning('Very large queries to changed henkilot. Current amount: {}'
                               .format(loop_number * amount))
            continue  # We (probably) didn't get everything yet. Fetch another batch.
        else:
            logger.error('Changed henkilot: We got more than we requested. Received: {}, Requested: {}'
                         .format(len_of_fetched_henkilo_oids, amount))
            return get_reply_json(is_ok=False, json_msg=None)


def fetch_henkilo_data_for_oid_list(oid_list):
    """
    Returns list of henkilo data for list of OIDs
    Example of return JSON:
    [
        {
            "oidHenkilo": "1.2.246.562.24.40599396777",
            "hetu": "010113A9072",
            "kaikkiHetut": [],
            "passivoitu": false,
            "etunimet": "Jan-Olof Testi",
            "kutsumanimi": "Jan-Olof",
            "sukunimi": "Vuori-Testi",
            "aidinkieli": {
                "kieliKoodi": "fi",
                "kieliTyyppi": "suomi"
            },
            "asiointiKieli": null,
            "kansalaisuus": [
                {
                    "kansalaisuusKoodi": "246"
                }
            ],
            "kasittelijaOid": "1.2.246.562.24.66631583590",
            "syntymaaika": "2013-01-01",
            "sukupuoli": "1",
            "kotikunta": null,
            "oppijanumero": "1.2.246.562.24.40599396777",
            "turvakielto": false,
            "eiSuomalaistaHetua": false,
            "yksiloity": false,
            "yksiloityVTJ": true,
            "yksilointiYritetty": true,
            "duplicate": false,
            "created": 1542376370546,
            "modified": 1584058500126,
            "vtjsynced": null,
            "yhteystiedotRyhma": [],
            "yksilointivirheet": [],
            "kielisyys": [],
            "henkiloTyyppi": "OPPIJA"
        }
    ]
    :param oid_list: list of OID identifiers
    :return: list of henkilo data
    """

    reply_msg = post_json_to_external_service(SERVICE_NAME, '/henkilo/henkilotByHenkiloOidList', json.dumps(oid_list),
                                              status.HTTP_200_OK, large_query=True)
    json_msg = reply_msg['json_msg']
    if reply_msg['is_ok']:
        return json_msg
    else:
        logger.error(f'Error fetching henkilo data for OID list: {json_msg}')
        return []
