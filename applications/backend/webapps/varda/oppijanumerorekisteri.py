import datetime
import logging

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from pytz import timezone
from requests import RequestException
from rest_framework.exceptions import NotFound, APIException

from varda.clients.oppijanumerorekisteri_client import (
    fetch_yhteystiedot,
    get_henkilo_data_by_oid,
    fetch_changed_henkilot,
    get_huoltajuussuhde_changed_child_oids,
)
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.batcherror_type import BatchErrorType
from varda.enums.yhteystieto import Yhteystietoryhmatyyppi, YhteystietoAlkupera, YhteystietoTyyppi
from varda.misc import CustomServerErrorException, encrypt_string, get_json_from_external_service, hash_string, list_to_chunks
from varda.models import Henkilo, Huoltaja, Huoltajuussuhde, Lapsi, Aikaleima, BatchError


logger = logging.getLogger(__name__)


SERVICE_NAME = "oppijanumerorekisteri-service"


def batch_error_decorator(batch_error_type):
    def decorator(function):
        def wrap_decorator(*args):
            henkilo_oid = args[0]
            henkilo = Henkilo.objects.filter(henkilo_oid=henkilo_oid).first()
            try:
                with transaction.atomic():
                    function(*args)
                    if henkilo:
                        BatchError.objects.filter(henkilo=henkilo, type=batch_error_type.name).delete()
            except Exception as e:
                logger.exception("BatchError caught exception")
                if not henkilo:
                    logger.error("Could not create BatchError. Missing henkilo.")
                elif batch_error_type in (BatchErrorType.LAPSI_HUOLTAJUUSSUHDE_UPDATE, BatchErrorType.HENKILOTIETO_UPDATE):
                    _create_or_update_henkilo_obj_batch_error(henkilo, e, batch_error_type)
                else:
                    logger.error("Could not create BatchError. Unkown batcherror type {}".format(batch_error_type))

        return wrap_decorator

    return decorator


def save_henkilo_to_db(henkilo_id, henkilo_json):
    henkilo = Henkilo.objects.get(id=henkilo_id)

    # Field mapping: first field is Oppijanumerorekisteri - second attribute-name in Varda
    henkilo_fields = {
        "syntymaaika": "syntyma_pvm",
        "oidHenkilo": "henkilo_oid",
        "etunimet": "etunimet",
        "kutsumanimi": "kutsumanimi",
        "sukunimi": "sukunimi",
        "sukupuoli": "sukupuoli_koodi",
        "kotikunta": "kotikunta_koodi",
        "turvakielto": "turvakielto",
        "yksiloityVTJ": "vtj_yksiloity",
        "yksilointiYritetty": "vtj_yksilointi_yritetty",
    }

    for key, field_name in henkilo_fields.items():
        if henkilo_json.get(key, None) is not None:
            setattr(henkilo, field_name, henkilo_json[key])

    if "hetu" in henkilo_json and henkilo_json["hetu"]:
        henkilo.henkilotunnus = encrypt_string(henkilo_json["hetu"])
        henkilo.henkilotunnus_unique_hash = hash_string(henkilo_json["hetu"])
    else:
        henkilo.henkilotunnus = ""
        henkilo.henkilotunnus_unique_hash = ""

    aidinkieli = henkilo_json.get("aidinkieli", None)
    if aidinkieli is not None and "kieliKoodi" in aidinkieli:
        henkilo.aidinkieli_koodi = aidinkieli["kieliKoodi"]

    if henkilo.tyontekijat.exists() and not hasattr(henkilo, "huoltaja") and not henkilo.lapsi.exists():
        # Remove address information if Henkilo is only related to Tyontekijat
        henkilo.remove_address_information()
    else:
        if hasattr(henkilo, "huoltaja") and not henkilo.tyontekijat.exists() and not henkilo.lapsi.exists():
            # Remove birthdate if Henkilo is only related to Huoltaja
            henkilo.syntyma_pvm = None
        _set_address_to_henkilo(henkilo_json, henkilo)

    henkilo.save()


def _set_address_to_henkilo(henkilo_json, henkilo):
    """
    Finds address groups that varda requires and updates first one to henkilo object
    :param henkilo_json: Henkilo data from ONR
    :param henkilo: Henkilo object
    :return: None
    """
    address_fields = {
        YhteystietoTyyppi.YHTEYSTIETO_KATUOSOITE.value: "katuosoite",
        YhteystietoTyyppi.YHTEYSTIETO_POSTINUMERO.value: "postinumero",
        YhteystietoTyyppi.YHTEYSTIETO_KAUPUNKI.value: "postitoimipaikka",
    }
    address_group_list = henkilo_json.get("yhteystiedotRyhma", [])
    address_groups = [
        address_group
        for address_group in address_group_list
        if Yhteystietoryhmatyyppi.VTJ_VAKINAINEN_KOTIMAINEN_OSOITE.value == address_group.get("ryhmaKuvaus", None)
        and YhteystietoAlkupera.VTJ.value == address_group.get("ryhmaAlkuperaTieto", None)
        and any(
            yhteystieto.get("yhteystietoArvo", False)  # Empty string evaluates falsy
            for yhteystieto in address_group.get("yhteystieto", [])
            if yhteystieto.get("yhteystietoTyyppi", None) in address_fields.keys()
        )
    ]
    address_list = next(iter(address_groups), {}).get("yhteystieto", [])
    [
        setattr(henkilo, address_fields[address["yhteystietoTyyppi"]], address.get("yhteystietoArvo", ""))
        for address in address_list
        if address.get("yhteystietoTyyppi", None) in address_fields.keys()
    ]


@batch_error_decorator(BatchErrorType.HENKILOTIETO_UPDATE)
def fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id):
    _fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id)


def _fetch_henkilo_data_by_oid(henkilo_oid, henkilo_id, henkilo_data=None):
    """
    Update henkilo master data from oppijanumerorekisteri by henkilo oid and save to database
    :param henkilo_id: ID of existing henkilo
    :param henkilo_oid: Henkilo OID to query oppijanumerorekisteri with
    :param henkilo_data: Prefetched henkilo data
    :return: None
    """
    if not henkilo_data:
        henkilo_data = get_henkilo_data_by_oid(henkilo_oid)
    if henkilo_data:
        save_henkilo_to_db(henkilo_id, henkilo_data)
    else:
        raise RequestException("Could not get data from oppijanumerorekisteri for henkilo {} {}".format(henkilo_id, henkilo_oid))


def fetch_henkilot_with_oid():
    """
    Warning: This fetches almost all the henkilot in DB. Use only if you need to.
    TODO: Add warning to admin-view so that he/she knows what is about to do.
    """

    """
    Import here to avoid circular references.
    """
    from varda.tasks import update_henkilo_data_by_oid

    henkilo_id_oid_tuples = Henkilo.objects.exclude(henkilo_oid="").values_list("id", "henkilo_oid")
    for henkilo_id, henkilo_oid in henkilo_id_oid_tuples:
        update_henkilo_data_by_oid.apply_async(
            args=[henkilo_oid, henkilo_id], kwargs={"is_fetch_huoltajat": True}, queue="low_prio_queue"
        )


def fetch_henkilo_with_oid(henkilo_oid):
    """
    Admin functionality
    :param henkilo_oid: Current henkilö oid in database
    :return: None
    """
    try:
        henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
    except Henkilo.DoesNotExist:
        raise NotFound(detail="Henkilo was not found.", code=404)
    except Henkilo.MultipleObjectsReturned:  # This should never be possible
        logger.error("Multiple of henkilot was found with henkilo_oid: " + henkilo_oid)
        raise CustomServerErrorException
    _fetch_henkilo_data_by_oid(henkilo_oid, henkilo.id)


def fetch_and_update_modified_henkilot():
    """
    Updates changes in henkilot.
    :return: None
    """

    """
    Import here to avoid circular references.
    """
    from varda.tasks import update_henkilo_data_by_oid

    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.HENKILOMUUTOS_LAST_UPDATE.name)

    # Oppijanumerorekisteri uses Finland's timezone. We use UTC internally.
    helsinki = timezone("Europe/Helsinki")
    start_datetime = aikaleima.aikaleima.astimezone(helsinki).strftime("%Y-%m-%dT%H:%M:%S%z")  # e.g. 2020-02-18T18:23:11+0200
    end_datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    changed_henkilo_oids = fetch_changed_henkilot(start_datetime)
    retry_henkilo_oids = BatchError.objects.filter(
        type=BatchErrorType.HENKILOTIETO_UPDATE.name, retry_time__lte=datetime.datetime.now(datetime.timezone.utc)
    ).values_list("henkilo__henkilo_oid", flat=True)

    if changed_henkilo_oids["is_ok"]:
        for oppijanumero in changed_henkilo_oids["json_msg"] + list(retry_henkilo_oids):
            try:
                henkilo = Henkilo.objects.get(henkilo_oid=oppijanumero)
            except Henkilo.DoesNotExist:
                continue  # This is ok. No further actions needed.
            except Henkilo.MultipleObjectsReturned as e:  # This should never be possible
                logger.error("Multiple of henkilot was found with henkilo_oid: " + oppijanumero)
                [
                    _create_or_update_henkilo_obj_batch_error(henkilo, e, BatchErrorType.HENKILOTIETO_UPDATE)
                    for henkilo in Henkilo.objects.filter(henkilo_oid=oppijanumero)
                ]
                continue

            """
            We have a match. Finally update henkilo-data using the oppijanumero.
            """
            update_henkilo_data_by_oid.apply_async(args=[oppijanumero, henkilo.id], queue="low_prio_queue")

        aikaleima.aikaleima = end_datetime
        aikaleima.save()
    else:
        pass  # We need to fetch the henkilot again later. Do not save the aikaleima.


def update_huoltajuussuhteet():
    """
    Updates changes in huoltajuussuhde.
    :return: None
    """
    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.HUOLTAJASUHDEMUUTOS_LAST_UPDATE.name)

    # Oppijanumerorekisteri uses Finland's timezone. We use UTC internally.
    helsinki = timezone("Europe/Helsinki")
    # e.g. 2020-02-18T18:23:11+0200
    start_datetime = aikaleima.aikaleima.astimezone(helsinki).strftime("%Y-%m-%dT%H:%M:%S%z")
    datetime_end = datetime.datetime.now(tz=datetime.timezone.utc)

    # With zero we fetch items 0-4999, offset 5000 -> items 5000 - 9999.
    offset = 0
    # This is how many lapsi_oids are fetched with one GET-request (max).
    amount = 5000
    loop_index = 1
    while True:
        response_dict = get_huoltajuussuhde_changed_child_oids(start_datetime, offset, amount=amount)
        if not response_dict["is_ok"]:
            # Something went wrong, return and do not update Aikaleima
            logger.error(f"Could not fetch the changed huoltajuussuhteet, {start_datetime}, {offset}, {amount}.")
            return None

        changed_lapsi_oid_list = response_dict["json_msg"]
        for changed_lapsi_oid in changed_lapsi_oid_list:
            update_huoltajuussuhde(changed_lapsi_oid)

        offset += amount
        loop_index += 1
        if loop_index % 20 == 0:
            logger.warning(f"Very large queries to changed huoltajuussuhteet. Current amount: {loop_index * amount}")

        if len(changed_lapsi_oid_list) < amount:
            # We got everything, break from loop
            break

    # Retry previously failed updates
    oids_to_retry = BatchError.objects.filter(
        retry_time__lte=datetime.datetime.now(datetime.timezone.utc), type=BatchErrorType.LAPSI_HUOLTAJUUSSUHDE_UPDATE.name
    ).values_list("henkilo__henkilo_oid", flat=True)
    for lapsi_oid in oids_to_retry:
        update_huoltajuussuhde(lapsi_oid)

    # Update Aikaleima
    aikaleima.aikaleima = datetime_end
    aikaleima.save()


def _create_or_update_henkilo_obj_batch_error(henkilo_obj, error, batch_error_type):
    batch_error, is_new = BatchError.objects.get_or_create(henkilo=henkilo_obj, type=batch_error_type.name)
    batch_error.update_next_retry()
    batch_error.error_message = str(error)

    if duplicate_identifier := getattr(error, "duplicate_identifier", None):
        batch_error.henkilo_duplicate = Henkilo.objects.filter(
            Q(henkilotunnus_unique_hash=duplicate_identifier) | Q(henkilo_oid=duplicate_identifier)
        ).first()

    batch_error.save()


@batch_error_decorator(BatchErrorType.LAPSI_HUOLTAJUUSSUHDE_UPDATE)
def update_huoltajuussuhde(henkilo_oid):
    """
    Update huoltajasuhteet for lapsi
    :param henkilo_oid: Henkilo oid of the child
    :return: None
    """
    try:
        with transaction.atomic():
            henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
            _fetch_lapsen_huoltajat(henkilo.id)
    except Henkilo.DoesNotExist:
        logger.info(f"Skipped huoltajuussuhde update for child with OID {henkilo_oid} since he was not added to Varda")


def _get_huoltajat_from_onr(henkilo_id):
    """
    We can run this in test environment only with a few selected oppijanumerot.
    """
    test_lapsi_oids = [
        "1.2.246.562.24.68159811823",
        "1.2.246.562.24.49084901393",
        "1.2.246.562.24.65027773627",
        "1.2.246.562.24.86721655046",
        "1.2.246.562.24.70363612932",
        "1.2.246.562.24.87620484650",
        "1.2.246.562.24.33058618961",
        "1.2.246.562.24.56063622440",
        "1.2.246.562.24.6815981182311",
        "1.2.246.562.24.88057101673",
        "1.2.246.562.24.86012997950",
        "1.2.246.562.24.96722959126",
        "1.2.246.562.24.55720536061",
        "1.2.246.562.24.69162613635",
        "1.2.246.562.24.62217952604",
        "1.2.246.562.24.34854926047",
        "1.2.246.562.24.19040767420",
        "1.2.246.562.24.99564982497",
        "1.2.246.562.24.31646567853",
        "1.2.246.562.24.65811558391",
        "1.2.246.562.24.64889113617",
        "1.2.246.562.24.66624978714",
        "1.2.246.562.24.75379654523",
        "1.2.246.562.24.30468313134",
        "1.2.246.562.24.68116330800",
        "1.2.246.562.24.27514703229",
    ]
    henkilo_lapsi_obj = Henkilo.objects.get(id=henkilo_id)
    if henkilo_lapsi_obj.henkilo_oid == "" or (
        not settings.PRODUCTION_ENV and henkilo_lapsi_obj.henkilo_oid not in test_lapsi_oids
    ):
        return []

    huoltajat_url = "/henkilo/" + henkilo_lapsi_obj.henkilo_oid + "/huoltajat"
    reply_msg = get_json_from_external_service(SERVICE_NAME, huoltajat_url)
    if not reply_msg["is_ok"]:
        raise APIException("Could not fetch huoltajat from oppijanumerorekisteri for henkilo {}".format(henkilo_id))
    return reply_msg["json_msg"]


def fetch_huoltajat():
    """
    Fetch missing huoltajat.
    """
    lapset_without_huoltajuussuhteet = Henkilo.objects.filter(lapsi__huoltajuussuhteet__isnull=True).exclude(lapsi=None)
    no_of_lapset_without_huoltajuussuhteet = lapset_without_huoltajuussuhteet.count()
    logger.info(f"Number of lapset without huoltajuussuhteet: {no_of_lapset_without_huoltajuussuhteet}.")
    for henkilo_obj in lapset_without_huoltajuussuhteet:
        if henkilo_obj.henkilo_oid != "":
            try:
                _fetch_lapsen_huoltajat(henkilo_obj.id)
            except IntegrityError as ie:
                logger.error(
                    "Could not create or update huoltajuussuhde with henkilo-id {} and cause {}".format(
                        henkilo_obj.id, ie.__cause__
                    )
                )
            except Exception:
                logger.exception("Could not update huoltajuussuhteet with henkilo-id {}".format(henkilo_obj.id))


def _fetch_lapsen_huoltajat(henkilo_id):
    """
    Create or update huoltajat for all lapsi objects henkilo has. Throws exception on error.
    :param henkilo_id: Henkilo object id
    :return: None
    """
    lapsi_id_list = Henkilo.objects.filter(id=henkilo_id).exclude(lapsi=None).values_list("lapsi__id", flat=True)
    huoltajat = _get_huoltajat_from_onr(henkilo_id)
    huoltajat_master_data = [get_henkilo_data_by_oid(huoltaja["oidHenkilo"]) for huoltaja in huoltajat]
    with transaction.atomic():
        # Invalidate all current huoltajuussuhde and set ones returned valid
        [Lapsi.objects.get(id=lapsi_id).huoltajuussuhteet.update(voimassa_kytkin=False) for lapsi_id in lapsi_id_list]
        [_update_lapsi_huoltaja(lapsi_id, huoltaja) for lapsi_id in lapsi_id_list for huoltaja in huoltajat_master_data]


@transaction.atomic
def _update_lapsi_huoltaja(lapsi_id, huoltaja_master_data):
    lapsi_obj = Lapsi.objects.get(id=lapsi_id)
    # Oid should be used alone as unique identifier in query since hetu can change
    oid = huoltaja_master_data["oidHenkilo"]
    default_henkilo = {"henkilo_oid": oid}
    # Create henkilo stub for updating if not already exist
    henkilo_huoltaja_obj, henkilo_huoltaja_created = (
        Henkilo.objects.select_for_update(nowait=True).filter(henkilo_oid=oid).get_or_create(defaults=default_henkilo)
    )
    # Update henkilo
    _fetch_henkilo_data_by_oid(oid, henkilo_huoltaja_obj.id, huoltaja_master_data)

    huoltaja_obj, huoltaja_created = Huoltaja.objects.get_or_create(henkilo=henkilo_huoltaja_obj)

    Huoltajuussuhde.objects.update_or_create(
        lapsi=lapsi_obj,
        huoltaja=huoltaja_obj,
        # ONR returns only valid huoltaja
        defaults={"voimassa_kytkin": True},
    )


def get_user_data(henkilo_oid):
    # Default user data
    user_data = {"asiointikieli": "fi", "sahkoposti": ""}

    henkilo_data_response = get_henkilo_data_by_oid(henkilo_oid)
    if henkilo_data_response:
        if (asiointikieli := henkilo_data_response.get("asiointiKieli", None)) and (
            kielikoodi := asiointikieli.get("kieliKoodi", None)
        ):
            user_data["asiointikieli"] = kielikoodi
        user_data["sahkoposti"] = get_user_sahkoposti(henkilo_data_response)

    return user_data


def get_user_sahkoposti(response_data):
    """
    Get email from Oppijanumerorekisteri user data. Varda only wants to handle work email addresses
    (ryhmaKuvaus == yhteystietotyyppi2), and the one that has been marked as primary in Opintopolku (ID is the largest).
    ryhmaKuvaus values are from koodisto yhteystietotyypit:
    https://virkailija.opintopolku.fi/koodisto-service/rest/json/yhteystietotyypit/koodi
    :param response_data: response data
    :return: email if it is available, or empty string
    """
    email = ""
    email_priority = -1
    for yhteystieto_ryhma in response_data.get("yhteystiedotRyhma", []):
        yhteystieto_ryhma_tyyppi = yhteystieto_ryhma.get("ryhmaKuvaus", None)
        yhteystieto_id = yhteystieto_ryhma.get("id", 0)
        if yhteystieto_ryhma_tyyppi == Yhteystietoryhmatyyppi.TYOOSOITE.value:
            # Is work contact information
            for yhteystieto in yhteystieto_ryhma.get("yhteystieto", []):
                yhteystieto_tyyppi = yhteystieto.get("yhteystietoTyyppi", None)
                if yhteystieto_tyyppi == YhteystietoTyyppi.YHTEYSTIETO_SAHKOPOSTI.value and yhteystieto_id > email_priority:
                    # Is email address, and has higher priority than the last one
                    email_priority = yhteystieto_id
                    email = yhteystieto.get("yhteystietoArvo", "")
    return email


def fetch_yhteystieto_data_for_henkilo_oid_list(henkilo_oid_list):
    """
    Get yhteystieto data for henkilo_oid_list
    :param henkilo_oid_list: list of henkilo_oid values
    :return: {'oid': {'email': 'test@example.com', 'language', 'fi'}} if request is successful, else None
    """
    yhteystieto_data_dict = {}

    # Fetch yhteystiedot in 1000 henkilo_oid chunks
    henkilo_oid_nested_list = list_to_chunks(henkilo_oid_list, 1000)
    for henkilo_oid_sublist in henkilo_oid_nested_list:
        response = fetch_yhteystiedot(henkilo_oid_sublist)
        if response is None:
            # Error fetching yhteystiedot
            return None

        for henkilo_data in response:
            henkilo_oid = henkilo_data["oidHenkilo"]
            language = henkilo_data["asiointikieli"]
            email = get_user_sahkoposti(henkilo_data)
            yhteystieto_data_dict[henkilo_oid] = {"email": email, "language": language}

    return yhteystieto_data_dict
