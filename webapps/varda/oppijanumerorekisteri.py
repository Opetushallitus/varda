import datetime
import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.db.models import Q
from guardian.shortcuts import assign_perm
from pytz import timezone
from rest_framework.exceptions import NotFound, APIException

from varda.clients.oppijanumerorekisteri_client import (get_or_create_henkilo_by_henkilotunnus, get_henkilo_data_by_oid,
                                                        fetch_changed_henkilot, fetch_changed_huoltajuussuhteet)
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.batcherror_type import BatchErrorType
from varda.enums.yhteystieto import Yhteystietoryhmatyyppi, YhteystietoAlkupera, YhteystietoTyyppi
from varda.misc import (CustomServerErrorException, decrypt_henkilotunnus, encrypt_henkilotunnus,
                        get_json_from_external_service, hash_string)
from varda.models import Henkilo, Huoltaja, Huoltajuussuhde, Lapsi, Aikaleima, BatchError

# Get an instance of a logger
logger = logging.getLogger(__name__)

SERVICE_NAME = "oppijanumerorekisteri-service"


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
        "yksilointiYritetty": "vtj_yksilointi_yritetty"
    }

    for key, field_name in henkilo_fields.items():
        if henkilo_json.get(key, None) is not None:
            setattr(henkilo, field_name, henkilo_json[key])

    if "hetu" in henkilo_json and henkilo_json["hetu"]:
        henkilo.henkilotunnus = encrypt_henkilotunnus(henkilo_json["hetu"])
        henkilo.henkilotunnus_unique_hash = hash_string(henkilo_json["hetu"])
    else:
        henkilo.henkilotunnus = ''
        henkilo.henkilotunnus_unique_hash = ''

    aidinkieli = henkilo_json.get("aidinkieli", None)
    if aidinkieli is not None and "kieliKoodi" in aidinkieli:
        henkilo.aidinkieli_koodi = aidinkieli["kieliKoodi"]

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
        YhteystietoTyyppi.YHTEYSTIETO_KAUPUNKI.value: "postitoimipaikka"
    }
    address_group_list = henkilo_json.get("yhteystiedotRyhma", [])
    address_groups = [address_group
                      for address_group
                      in address_group_list
                      if Yhteystietoryhmatyyppi.VTJ_VAKINAINEN_KOTIMAINEN_OSOITE.value == address_group.get("ryhmaKuvaus", None) and
                      YhteystietoAlkupera.VTJ.value == address_group.get("ryhmaAlkuperaTieto", None) and
                      any(yhteystieto.get("yhteystietoArvo", False)  # Empty string evaluates falsy
                          for yhteystieto
                          in address_group.get("yhteystieto", [])
                          if yhteystieto.get("yhteystietoTyyppi", None) in address_fields.keys())
                      ]
    address_list = next(iter(address_groups), {}).get("yhteystieto", [])
    [setattr(henkilo, address_fields[address["yhteystietoTyyppi"]], address.get("yhteystietoArvo", ''))
     for address
     in address_list
     if address.get("yhteystietoTyyppi", None) in address_fields.keys()
     ]


def _fetch_henkilo_data_by_henkilotunnus(henkilo_id, henkilotunnus, etunimet, kutsumanimi, sukunimi):
    """
    If henkilo is not found from Oppijanumerorekisteri, we add it there.
    """
    henkilo_query = get_or_create_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi)
    if henkilo_query and 'result' in henkilo_query:
        henkilo_data = henkilo_query['result']
        if henkilo_data is not None:
            save_henkilo_to_db(henkilo_id, henkilo_data)
    else:
        logger.error('Failed to fetch henkilo_data for henkilo_id: {}.'.format(henkilo_id))


def fetch_henkilo_data_by_oid(henkilo_id, henkilo_oid, henkilo_data=None):
    """
    Update henkilo master data from oppijanumerorekisteri by henkilo oid and save to database
    :param henkilo_id: ID of existing henkilo
    :param henkilo_oid: Henkilo OID to query oppijanumerorekisteri with
    :param henkilo_data: Prefetched henkilo data
    :return: None
    """
    if not henkilo_data:
        henkilo_data = get_henkilo_data_by_oid(henkilo_oid)
    if henkilo_data is not None:
        save_henkilo_to_db(henkilo_id, henkilo_data)


def fetch_henkilot_without_oid():
    """
    Schedule this method to be run once a day.
    """
    henkilot = Henkilo.objects.filter(henkilo_oid="")
    for henkilo in henkilot:
        henkilo_id = henkilo.id
        henkilotunnus = decrypt_henkilotunnus(henkilo.henkilotunnus)
        etunimet = henkilo.etunimet
        kutsumanimi = henkilo.kutsumanimi
        sukunimi = henkilo.sukunimi
        _fetch_henkilo_data_by_henkilotunnus(henkilo_id, henkilotunnus, etunimet, kutsumanimi, sukunimi)


def fetch_henkilot_with_oid():
    """
    Warning: This fetches almost all the henkilot in DB. Use only if you need to.
    TODO: Add warning to admin-view so that he/she knows what is about to do.
    """

    """
    Import here to avoid circular references.
    """
    from varda.tasks import update_henkilo_data_by_oid

    henkilot = Henkilo.objects.filter(~Q(henkilo_oid=""))  # TODO: Use values_list
    for henkilo in henkilot:
        henkilo_id = henkilo.id
        henkilo_oid = henkilo.henkilo_oid
        update_henkilo_data_by_oid.apply_async(args=[henkilo_id, henkilo_oid], queue='low_prio_queue')


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
    fetch_henkilo_data_by_oid(henkilo.id, henkilo_oid)


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
    helsinki = timezone('Europe/Helsinki')
    start_datetime = aikaleima.aikaleima.astimezone(helsinki).strftime('%Y-%m-%dT%H:%M:%S%z')  # e.g. 2020-02-18T18:23:11+0200
    end_datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    changed_henkilo_oids = fetch_changed_henkilot(start_datetime)

    if changed_henkilo_oids['is_ok']:
        for oppijanumero in changed_henkilo_oids['json_msg']:
            try:
                henkilo = Henkilo.objects.get(henkilo_oid=oppijanumero)
            except Henkilo.DoesNotExist:
                continue  # This is ok. No further actions needed.
            except Henkilo.MultipleObjectsReturned:  # This should never be possible
                logger.error("Multiple of henkilot was found with henkilo_oid: " + oppijanumero)
                continue

            """
            We have a match. Finally update henkilo-data using the oppijanumero.
            """
            update_henkilo_data_by_oid.apply_async(args=[henkilo.id, oppijanumero], queue='low_prio_queue')

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
    helsinki = timezone('Europe/Helsinki')
    start_datetime = aikaleima.aikaleima.astimezone(helsinki).strftime('%Y-%m-%dT%H:%M:%S%z')  # e.g. 2020-02-18T18:23:11+0200
    end_datetime = datetime.datetime.now(tz=datetime.timezone.utc)

    changed_lapsi_oids = fetch_changed_huoltajuussuhteet(start_datetime)
    oids_to_retry = (BatchError.objects
                     .filter(retry_time__lte=datetime.datetime.now(datetime.timezone.utc),
                             type=BatchErrorType.LAPSI_HUOLTAJUUSSUHDE_UPDATE.name)
                     .values_list('henkilo__henkilo_oid', flat=True)
                     )

    if changed_lapsi_oids['is_ok']:
        [update_huoltajuussuhde(lapsi_oid) for lapsi_oid in changed_lapsi_oids['json_msg'] + list(oids_to_retry)]

        aikaleima.aikaleima = end_datetime
        aikaleima.save()
    else:
        pass  # We need to fetch the huoltajuussuhteet again later. Do not save the aikaleima.


def lapsi_batch_error_decorator(batch_error_type):
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
                if henkilo:
                    _create_or_update_lapsi_batch_error(henkilo, e, batch_error_type)
                else:
                    logger.exception('Could not create batch error. Missing henkilo.')
        return wrap_decorator
    return decorator


def _create_or_update_lapsi_batch_error(henkilo_obj, error, batch_error_type):
    batch_error, is_new = BatchError.objects.get_or_create(henkilo=henkilo_obj, type=batch_error_type.name)
    batch_error.update_next_retry()
    batch_error.error_message = str(error)
    batch_error.save()


@lapsi_batch_error_decorator(BatchErrorType.LAPSI_HUOLTAJUUSSUHDE_UPDATE)
def update_huoltajuussuhde(henkilo_oid):
    """
    Update huoltajasuhteet for lapsi
    :param henkilo_oid: Henkilo oid of the child
    :return: None
    """
    try:
        with transaction.atomic():
            henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
            fetch_lapsen_huoltajat(henkilo.id)
    except Henkilo.DoesNotExist:
        logger.info("Skipped huoltajasuhde update for child with oid {} since he was not added to varda"
                    .format(henkilo_oid))


def _get_huoltajat_from_onr(henkilo_id):
    """
    We can run this in test environment only with a few selected oppijanumerot.
    """
    test_lapsi_oids = ['1.2.246.562.24.68159811823',
                       '1.2.246.562.24.49084901393',
                       '1.2.246.562.24.65027773627',
                       '1.2.246.562.24.86721655046',
                       '1.2.246.562.24.70363612932',
                       '1.2.246.562.24.87620484650',
                       '1.2.246.562.24.33058618961',
                       '1.2.246.562.24.56063622440',
                       '1.2.246.562.24.6815981182311',
                       '1.2.246.562.24.88057101673',
                       ]
    henkilo_lapsi_obj = Henkilo.objects.get(id=henkilo_id)
    if (henkilo_lapsi_obj.henkilo_oid == "" or
            (not settings.PRODUCTION_ENV and henkilo_lapsi_obj.henkilo_oid not in test_lapsi_oids)):
        return []

    huoltajat_url = "/henkilo/" + henkilo_lapsi_obj.henkilo_oid + "/huoltajat"
    reply_msg = get_json_from_external_service(SERVICE_NAME, huoltajat_url)
    if not reply_msg["is_ok"]:
        raise APIException('Could not fetch huoltajat from oppijanumerorekisteri for henkilo {}'.format(henkilo_id))
    return reply_msg["json_msg"]


def fetch_huoltajat():
    """
    Fetch missing huoltajat.
    """
    lapset_without_huoltajuussuhteet = Henkilo.objects.filter(lapsi__huoltajuussuhteet__isnull=True).exclude(lapsi=None)
    for henkilo_obj in lapset_without_huoltajuussuhteet:
        if henkilo_obj.henkilo_oid != "":
            try:
                fetch_lapsen_huoltajat(henkilo_obj.id)
            except IntegrityError as ie:
                logger.error('Could not create or update huoltajuussuhde with henkilo-id {} and cause {}'
                             .format(henkilo_obj.id, ie.__cause__))
            except Exception:
                logger.exception('Could not update huoltajuussuhteet with henkilo-id {}'.format(henkilo_obj.id))


def fetch_lapsen_huoltajat(henkilo_id):
    """
    Create or update huoltajat for all lapsi objects henkilo has. Throws exception on error.
    :param henkilo_id: Henkilo object id
    :return: None
    """
    lapsi_id_list = Henkilo.objects.filter(id=henkilo_id).exclude(lapsi=None).values_list('lapsi__id', flat=True)
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
    default_henkilo = {
        'henkilo_oid': oid,
        'changed_by': lapsi_obj.changed_by,
    }
    # Create henkilo stub for updating if not already exist
    henkilo_huoltaja_obj, henkilo_huoltaja_created = (Henkilo.objects.select_for_update(nowait=True)
                                                      .filter(henkilo_oid=oid)
                                                      .get_or_create(defaults=default_henkilo)
                                                      )
    # Update henkilo
    fetch_henkilo_data_by_oid(henkilo_huoltaja_obj.id, oid, huoltaja_master_data)
    if henkilo_huoltaja_created:
        group = Group.objects.get(name="vakajarjestaja_view_henkilo")
        assign_perm('view_henkilo', group, henkilo_huoltaja_obj)

    huoltaja_obj, huoltaja_created = (Huoltaja.objects
                                      .get_or_create(henkilo=henkilo_huoltaja_obj,
                                                     defaults={
                                                         'changed_by': lapsi_obj.changed_by,
                                                     })
                                      )

    Huoltajuussuhde.objects.update_or_create(lapsi=lapsi_obj,
                                             huoltaja=huoltaja_obj,
                                             defaults={
                                                 'changed_by': lapsi_obj.changed_by,
                                                 'voimassa_kytkin': True,  # ONR returns only valid huoltaja
                                             })
