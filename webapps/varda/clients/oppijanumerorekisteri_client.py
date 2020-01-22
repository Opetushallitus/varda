import json
import logging

from rest_framework import status

from varda.misc import hash_string, get_json_from_external_service, post_json_to_external_service
from varda.models import Henkilo

# Get an instance of a logger
logger = logging.getLogger(__name__)

SERVICE_NAME = "oppijanumerorekisteri-service"


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
    default_henkilo_query_error_result = {"new_henkilo": False, "result": None}

    if reply_msg["is_ok"]:
        return {"new_henkilo": False, "result": reply_msg["json_msg"]}
    else:
        """
        Henkilo was not found by henkilotunnus. Let's add it to Oppijanumerorekisteri.
        """
        if create_new:
            return add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=henkilotunnus)
        else:
            return default_henkilo_query_error_result


def add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=None):
    default_henkilo_query_error_result = {"new_henkilo": False, "result": None}
    if henkilotunnus:
        new_henkilo_oid_in_oppijanumerorekisteri = _add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=henkilotunnus)
    else:
        new_henkilo_oid_in_oppijanumerorekisteri = _add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi)
    if new_henkilo_oid_in_oppijanumerorekisteri is None:
        return default_henkilo_query_error_result
    else:
        return {"new_henkilo": True, "result": get_henkilo_data_by_oid(new_henkilo_oid_in_oppijanumerorekisteri)}


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
        "etunimet": etunimet,
        "kutsumanimi": kutsumanimi,
        "sukunimi": sukunimi
    }
    if henkilotunnus:
        new_henkilo["hetu"] = henkilotunnus

    reply_msg = post_json_to_external_service(SERVICE_NAME, '/henkilo/', json.dumps(new_henkilo), status.HTTP_201_CREATED, auth=True, reply_type='text')
    if reply_msg["is_ok"]:
        return reply_msg["json_msg"]
    elif henkilotunnus:
        henkilo = Henkilo.objects.get(henkilotunnus_unique_hash=hash_string(henkilotunnus))
        henkilo_id = henkilo.id
        added_by = henkilo.changed_by.username
        henkilotunnus_prefix_hided = henkilotunnus and 'DDMMYY' + henkilotunnus[-5:]
        logger.error("Couldn't add a new henkilo to Oppijanumerorekisteri. Henkilotunnus: {}. Id: {}. Added by: {}"
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

    if reply_msg["is_ok"]:
        return reply_msg["json_msg"]
    else:
        logger.error("Couldn't fetch henkilo with oid: {}".format(oid))
        return None
