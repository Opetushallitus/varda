import copy
import datetime
import json
import logging
import uuid

from django.db import transaction
from django.db.models import F, DurationField, ExpressionWrapper

from varda.clients.organisaatio_client import (
    get_organisaatiopalvelu_info,
    get_parent_oid,
    check_if_toimipaikka_exists_by_name,
    get_organisaatio,
    create_organisaatio,
    update_organisaatio,
    get_changed_since,
    get_multiple_organisaatio,
)
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.exceptions.invalid_koodi_uri_exception import InvalidKoodiUriException
from varda.misc import list_to_chunks
from varda.models import Toimipaikka, Organisaatio, KieliPainotus, ToiminnallinenPainotus, Aikaleima
from varda.permission_groups import create_permission_groups_for_organisaatio
from varda.permissions import (
    assign_kielipainotus_permissions,
    assign_organisaatio_permissions,
    assign_toiminnallinen_painotus_permissions,
    assign_toimipaikka_permissions,
)
from varda.related_object_validations import toimipaikka_is_valid_to_organisaatiopalvelu


logger = logging.getLogger(__name__)


def vakajarjestaja_changed(vakajarjestaja, vakajarjestaja_original):
    if (
        vakajarjestaja.nimi == vakajarjestaja_original.nimi
        and vakajarjestaja.organisaatio_oid == vakajarjestaja_original.organisaatio_oid
        and vakajarjestaja.kunta_koodi == vakajarjestaja_original.kunta_koodi
        and str(vakajarjestaja.alkamis_pvm) == str(vakajarjestaja_original.alkamis_pvm)
        and str(vakajarjestaja.paattymis_pvm) == str(vakajarjestaja_original.paattymis_pvm)
        and vakajarjestaja.postiosoite == vakajarjestaja_original.postiosoite
        and vakajarjestaja.postinumero == vakajarjestaja_original.postinumero
        and vakajarjestaja.postitoimipaikka == vakajarjestaja_original.postitoimipaikka
        and vakajarjestaja.kayntiosoite == vakajarjestaja_original.kayntiosoite
        and vakajarjestaja.kayntiosoite_postinumero == vakajarjestaja_original.kayntiosoite_postinumero
        and vakajarjestaja.kayntiosoite_postitoimipaikka == vakajarjestaja_original.kayntiosoite_postitoimipaikka
        and vakajarjestaja.yritysmuoto == vakajarjestaja_original.yritysmuoto
        and set(vakajarjestaja.organisaatiotyyppi) == set(vakajarjestaja_original.organisaatiotyyppi)
        and vakajarjestaja.ytjkieli == vakajarjestaja_original.ytjkieli
    ):
        return False  # no changes made
    return True


def update_vakajarjestaja(vakajarjestaja, result_organisaatiopalvelu):
    """
    This method saves the fetched data to VARDA database.
    Make a database transaction only if data is changed.
    """
    vakajarjestaja_original = copy.deepcopy(vakajarjestaja)

    vakajarjestaja.nimi = result_organisaatiopalvelu["nimi"]
    vakajarjestaja.y_tunnus = result_organisaatiopalvelu.get("ytunnus", "")
    vakajarjestaja.kunta_koodi = result_organisaatiopalvelu["kunta_koodi"]
    vakajarjestaja.postiosoite = result_organisaatiopalvelu["postiosoite"]
    vakajarjestaja.postinumero = result_organisaatiopalvelu["postinumero"]
    vakajarjestaja.postitoimipaikka = result_organisaatiopalvelu["postitoimipaikka"]
    vakajarjestaja.kayntiosoite = result_organisaatiopalvelu["kayntiosoite"]
    vakajarjestaja.kayntiosoite_postinumero = result_organisaatiopalvelu["kayntiosoite_postinumero"]
    vakajarjestaja.kayntiosoite_postitoimipaikka = result_organisaatiopalvelu["kayntiosoite_postitoimipaikka"]
    vakajarjestaja.ytjkieli = result_organisaatiopalvelu["ytjkieli"]
    vakajarjestaja.yritysmuoto = result_organisaatiopalvelu["yritysmuoto"]
    vakajarjestaja.alkamis_pvm = result_organisaatiopalvelu["alkamis_pvm"]
    vakajarjestaja.organisaatiotyyppi = result_organisaatiopalvelu["organisaatiotyyppi"]

    paattymis_pvm = result_organisaatiopalvelu["paattymis_pvm"]
    # paattymis_pvm can have a null-value in VARDA
    vakajarjestaja.paattymis_pvm = paattymis_pvm or None
    if vakajarjestaja_changed(vakajarjestaja, vakajarjestaja_original):
        vakajarjestaja.save()


def fetch_organisaatio_info(vakajarjestaja_id=None):
    """
    Organisaatiopalvelu-integraatio

    For each vakajarjestaja (they have a unique Y-tunnus) we fetch the following information from Organisaatiopalvelu:
    - nimi
    - organisaatio_oid
    - kunta_koodi
    - kayntiosoite (osoite, postinumero, postitoimipaikka)
    - postiosoite (osoite, postinumero, postitoimipaikka)
    - alkamis_pvm
    - ytjkieli
    - yritysmuoto

    We need to perform three queries to get all these info (marked above as Organisaatio/YTJ).

    This function can be used to fetch data for one organization (with vakajarjestaja_id) or for all organizations in db.
    """
    if vakajarjestaja_id is None:
        vakajarjestajat = Organisaatio.objects.all()
    else:
        vakajarjestajat = [Organisaatio.objects.get(id=vakajarjestaja_id)]

    for vakajarjestaja in vakajarjestajat:
        organisaatio_oid = vakajarjestaja.organisaatio_oid
        if not organisaatio_oid:
            logger.error(f"Organization with id {vakajarjestaja_id} does not have organisaatio_oid.")
            continue
        if result_organisaatiopalvelu := get_organisaatiopalvelu_info(organisaatio_oid):
            update_vakajarjestaja(vakajarjestaja, result_organisaatiopalvelu)


def create_organization_using_oid(organisaatio_oid, organisaatiotyyppi, integraatio_organisaatio=None):
    from varda.tasks import update_oph_staff_to_vakajarjestaja_groups

    if not integraatio_organisaatio:
        integraatio_organisaatio = []

    organization_tuple = Organisaatio.objects.get_or_create(
        organisaatio_oid=organisaatio_oid, defaults={"integraatio_organisaatio": integraatio_organisaatio}
    )
    organization_obj = organization_tuple[0]
    organization_created = organization_tuple[1]

    if organization_created:
        fetch_organisaatio_info(vakajarjestaja_id=organization_obj.id)
        # New organization, let's create pre-defined permission_groups for it
        create_permission_groups_for_organisaatio(organisaatio_oid, organisaatiotyyppi)
        assign_organisaatio_permissions(organization_obj)
        # Update permissions for OPH staff users
        update_oph_staff_to_vakajarjestaja_groups.delay(organisaatio_oid=organisaatio_oid)
    else:
        logger.warning("Vakajarjestaja was already created with organisaatio-oid: " + organisaatio_oid)


def get_vakajarjestaja(organisaatio_oid):
    parent_oid = get_parent_oid(organisaatio_oid)
    if parent_oid is None:
        logger.error("Did not get parent_oid for: " + organisaatio_oid)
    else:
        vakajarjestaja_query = Organisaatio.objects.filter(organisaatio_oid=parent_oid)
        if len(vakajarjestaja_query) == 0:
            create_organization_using_oid(parent_oid, Organisaatiotyyppi.VAKAJARJESTAJA.value)
            new_vakajarjestaja_query = Organisaatio.objects.filter(organisaatio_oid=parent_oid)
            if len(new_vakajarjestaja_query) == 1:
                return new_vakajarjestaja_query[0]
        elif len(vakajarjestaja_query) == 1:
            return vakajarjestaja_query[0]
        else:
            logger.error("More than one Vakajarjestaja was found with organisaatio-oid: " + parent_oid)


def fetch_and_save_toimipaikka_data(toimipaikka_obj):
    """
    Fetch and save toimipaikka data from organisaatio-service.
    """
    toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
    reply_json = get_organisaatio(toimipaikka_organisaatio_oid)
    try:
        _fill_toimipaikka_data(reply_json, toimipaikka_obj)
        toimipaikka_obj.save()
    except (KeyError, StopIteration):
        logger.error("Missing required field in organisation-service data with oid %s", toimipaikka_organisaatio_oid)
        raise
    except InvalidKoodiUriException as e:
        logger.error("Invalid koodi uri %s in organisation-service data with oid %s", e, toimipaikka_organisaatio_oid)
        raise


def _fill_toimipaikka_data(reply_json, toimipaikka_obj):
    if "fi" in reply_json["nimi"]:
        toimipaikan_nimi = reply_json["nimi"]["fi"]
    elif "sv" in reply_json["nimi"]:
        toimipaikan_nimi = reply_json["nimi"]["sv"]
    else:
        toimipaikan_nimi = None
    if toimipaikan_nimi is not None:
        toimipaikka_obj.nimi = toimipaikan_nimi
    toimipaikka_obj.nimi_sv = ""

    toimipaikka_obj.kunta_koodi = get_koodi_from_uri(reply_json["kotipaikkaUri"], required=False)
    toimipaikka_obj.alkamis_pvm = reply_json["alkuPvm"]
    toimipaikka_obj.paattymis_pvm = reply_json.get("lakkautusPvm", None)
    # toimipaikka_obj.toimintakieli_koodi defaulted to FI

    _fill_yhteystiedot(reply_json, toimipaikka_obj)

    _fill_varhaiskasvatustiedot(reply_json, toimipaikka_obj)

    # Managed on organisaatio-service if toimipaikka has other organisation types
    if len(reply_json["tyypit"]) > 1:
        toimipaikka_obj.hallinnointijarjestelma = Hallinnointijarjestelma.ORGANISAATIO


def get_koodi_from_uri(uri, required=True):
    split_uri = uri.split("_")
    if len(split_uri) <= 1:
        if required:
            raise InvalidKoodiUriException(uri)
        return None
    return split_uri[1]


def _fill_varhaiskasvatustiedot(reply_json, toimipaikka_obj):
    vaka_tiedot = reply_json["varhaiskasvatuksenToimipaikkaTiedot"]
    toimipaikka_obj.toimintamuoto_koodi = get_koodi_from_uri(vaka_tiedot["toimintamuoto"])
    toimipaikka_obj.kasvatusopillinen_jarjestelma_koodi = get_koodi_from_uri(vaka_tiedot["kasvatusopillinenJarjestelma"])
    toimipaikka_obj.jarjestamismuoto_koodi = list(
        map(lambda muoto: get_koodi_from_uri(muoto), vaka_tiedot["varhaiskasvatuksenJarjestamismuodot"])
    )
    toimipaikka_obj.varhaiskasvatuspaikat = vaka_tiedot["paikkojenLukumaara"]

    KieliPainotus.objects.filter(toimipaikka=toimipaikka_obj).delete()
    kielipainotukset_json = vaka_tiedot.get("varhaiskasvatuksenKielipainotukset", [])
    kielipainotukset = set(map(lambda kieli: create_kielipainotus(toimipaikka_obj.id, kieli), kielipainotukset_json))
    toimipaikka_obj.kielipainotus_kytkin = len(kielipainotukset) > 0

    ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka_obj).delete()
    toimintapainotukset_json = vaka_tiedot.get("varhaiskasvatuksenToiminnallinenpainotukset", [])
    toimintapainotukset = set(
        map(lambda toiminta: create_toiminnallinenpainotus(toimipaikka_obj.id, toiminta), toimintapainotukset_json)
    )
    toimipaikka_obj.toiminnallinenpainotus_kytkin = len(toimintapainotukset) > 0


def _fill_yhteystiedot(reply_json, toimipaikka_obj):
    # Organisaatio-service provided default values that might not be with expected language.
    # This info is not mandatory in organisaatio-service unlike our service so error might occur.
    kayntiosoite = reply_json["kayntiosoite"]
    toimipaikka_obj.kayntiosoite = kayntiosoite["osoite"]
    toimipaikka_obj.kayntiosoite_postinumero = get_koodi_from_uri(kayntiosoite["postinumeroUri"])
    toimipaikka_obj.kayntiosoite_postitoimipaikka = kayntiosoite["postitoimipaikka"]

    # Organisaatio-service provided default values that might not be with expected language.
    postiosoite = reply_json["postiosoite"]
    toimipaikka_obj.postiosoite = postiosoite["osoite"]
    toimipaikka_obj.postinumero = get_koodi_from_uri(postiosoite["postinumeroUri"])
    toimipaikka_obj.postitoimipaikka = postiosoite["postitoimipaikka"]

    # Choose the first ones. (there might be multiple same type with different languages)
    toimipaikka_obj.puhelinnumero = next(
        iter([y["numero"] for y in reply_json["yhteystiedot"] if "tyyppi" in y.keys() and y["tyyppi"] == "puhelin"])
    )
    toimipaikka_obj.sahkopostiosoite = next(iter([y["email"] for y in reply_json["yhteystiedot"] if "email" in y.keys()]))


def create_kielipainotus(toimipaikka_id, kieli):
    toimipaikka_obj = Toimipaikka.objects.select_related("vakajarjestaja").get(id=toimipaikka_id)
    kielipainotus = KieliPainotus.objects.create(
        toimipaikka=toimipaikka_obj,
        kielipainotus_koodi=get_koodi_from_uri(kieli["kielipainotus"]).upper(),
        alkamis_pvm=kieli["alkupvm"],
        paattymis_pvm=kieli.get("loppupvm", None),
    )
    assign_kielipainotus_permissions(kielipainotus)
    return kielipainotus


def create_toiminnallinenpainotus(toimipaikka_id, toiminnallinen):
    toimipaikka_obj = Toimipaikka.objects.select_related("vakajarjestaja").get(id=toimipaikka_id)
    alkupvm = toiminnallinen["alkupvm"]
    loppupvm = toiminnallinen.get("loppupvm", None)
    painotus = get_koodi_from_uri(toiminnallinen["toiminnallinenpainotus"])
    toiminnallinen_painotus = ToiminnallinenPainotus.objects.create(
        toimipaikka=toimipaikka_obj, toimintapainotus_koodi=painotus, alkamis_pvm=alkupvm, paattymis_pvm=loppupvm
    )
    assign_toiminnallinen_painotus_permissions(toiminnallinen_painotus)
    return toiminnallinen_painotus


def create_toimipaikka_using_oid(toimipaikka_organisaatio_oid):
    vakajarjestaja = get_vakajarjestaja(toimipaikka_organisaatio_oid)
    if vakajarjestaja is None:
        return

    """
    Use default-values here, which needs to be updated with Org.palvelu data
    Use random uuid for name. Otherwise we hit uniquness-error.
    """
    uuido = uuid.uuid4()
    uuids = str(uuido)
    uuids = uuids.replace("-", "")

    with transaction.atomic():
        toimipaikka_tuple = Toimipaikka.objects.get_or_create(
            organisaatio_oid=toimipaikka_organisaatio_oid,
            vakajarjestaja=vakajarjestaja,
            defaults={
                "nimi": uuids,
                "toimintakieli_koodi": ["FI"],
                "jarjestamismuoto_koodi": [""],
                "varhaiskasvatuspaikat": 1,
                "alkamis_pvm": "2018-12-01",
            },
        )
        toimipaikka_obj = toimipaikka_tuple[0]
        toimipaikka_created = toimipaikka_tuple[1]
        if toimipaikka_created:
            # New organization, let's create pre-defined permission groups for it
            # This needs to be done before fetch and save so Toimipaikka has permission groups to assign
            # for KieliPainotus and ToiminnallinenPainotus objects
            create_permission_groups_for_organisaatio(toimipaikka_organisaatio_oid, Organisaatiotyyppi.TOIMIPAIKKA.value)
            fetch_and_save_toimipaikka_data(toimipaikka_obj)
            assign_toimipaikka_permissions(toimipaikka_obj)
        else:
            logger.warning("Toimipaikka was already created with organisaatio-oid: " + toimipaikka_organisaatio_oid)


def check_if_toimipaikka_exists_in_organisaatiopalvelu(vakajarjestaja_id, toimipaikka_name):
    """
    If more than one toimipaikka found, let's return the first one. Send an alert to admins to debug more.

    :param vakajarjestaja_id:
    :param toimipaikka_name:
    :return: Organisaatio oid, empty string or None
    """
    vakajarjestaja_obj = Organisaatio.objects.get(id=vakajarjestaja_id)
    toimipaikka_exists_already, oids = check_if_toimipaikka_exists_by_name(toimipaikka_name, vakajarjestaja_obj.organisaatio_oid)
    if not toimipaikka_exists_already:
        return None
    else:
        if len(oids) == 0:
            return ""  # An error occured
        elif len(oids) > 1:
            logger.error(f"More than one toimipaikka found. Vakajarjestaja-id: {vakajarjestaja_id}, oids: {oids}.")
    return oids[0]


def get_toimipaikka_json(toimipaikka_validated_data, vakajarjestaja_id):
    vakajarjestaja = Organisaatio.objects.get(id=vakajarjestaja_id)
    parent_oid = vakajarjestaja.organisaatio_oid

    kayntiosoite_fi = {
        "osoiteTyyppi": "kaynti",
        "kieli": "kieli_fi#1",
        "osoite": toimipaikka_validated_data["kayntiosoite"],
        "postinumeroUri": "posti_" + toimipaikka_validated_data["kayntiosoite_postinumero"],
        "postitoimipaikka": toimipaikka_validated_data["kayntiosoite_postitoimipaikka"],
    }
    postiosoite_fi = {
        "osoiteTyyppi": "posti",
        "kieli": "kieli_fi#1",
        "osoite": toimipaikka_validated_data["postiosoite"],
        "postinumeroUri": "posti_" + toimipaikka_validated_data["postinumero"],
        "postitoimipaikka": toimipaikka_validated_data["postitoimipaikka"],
    }
    kayntiosoite_sv = {**kayntiosoite_fi, "kieli": "kieli_sv#1"}
    postiosoite_sv = {**postiosoite_fi, "kieli": "kieli_sv#1"}
    email_fi = {"email": toimipaikka_validated_data["sahkopostiosoite"], "kieli": "kieli_fi#1"}
    puhelin_fi = {"tyyppi": "puhelin", "kieli": "kieli_fi#1", "numero": toimipaikka_validated_data["puhelinnumero"]}
    email_sv = {**email_fi, "kieli": "kieli_sv#1"}
    puhelin_sv = {**puhelin_fi, "kieli": "kieli_sv#1"}
    email_en = {**email_fi, "kieli": "kieli_en#1"}
    puhelin_en = {**puhelin_fi, "kieli": "kieli_en#1"}

    kasvatusopillinen_jarjestelma = (
        "vardakasvatusopillinenjarjestelma_" + toimipaikka_validated_data["kasvatusopillinen_jarjestelma_koodi"].lower()
    )
    toimintamuoto = "vardatoimintamuoto_" + toimipaikka_validated_data["toimintamuoto_koodi"].lower()
    jarjestamismuoto = [
        "vardajarjestamismuoto_" + koodi.lower() for koodi in toimipaikka_validated_data["jarjestamismuoto_koodi"]
    ]
    varhaiskasvatuspaikat = toimipaikka_validated_data["varhaiskasvatuspaikat"]
    alkamis_pvm = str(toimipaikka_validated_data["alkamis_pvm"])
    paattymis_pvm = (
        str(toimipaikka_validated_data["paattymis_pvm"])
        if "paattymis_pvm" in toimipaikka_validated_data and toimipaikka_validated_data["paattymis_pvm"] is not None
        else None
    )
    kunta_koodi = "kunta_" + toimipaikka_validated_data["kunta_koodi"]

    piilotettu = toimipaikka_validated_data["toimintamuoto_koodi"].lower() in ["tm02", "tm03"]

    nimi = toimipaikka_validated_data["nimi"]
    nimi_group = {"fi": nimi, "sv": nimi, "en": nimi}

    toimipaikka_json = {
        "tyypit": [Organisaatiotyyppi.TOIMIPAIKKA.value],
        "nimi": nimi_group,
        "nimet": [{"nimi": nimi_group, "alkuPvm": alkamis_pvm}],
        "kieletUris": ["oppilaitoksenopetuskieli_1#1"],
        "yhteystiedot": [
            kayntiosoite_fi,
            postiosoite_fi,
            email_fi,
            puhelin_fi,
            {"www": None, "kieli": "kieli_fi#1"},
            {"tyyppi": "puhelin", "kieli": "kieli_fi#1"},
            kayntiosoite_sv,
            postiosoite_sv,
            email_sv,
            puhelin_sv,
            {"www": None, "kieli": "kieli_sv#1"},
            {"tyyppi": "puhelin", "kieli": "kieli_sv#1"},
            email_en,
            puhelin_en,
            {"www": None, "kieli": "kieli_en#1"},
            {"tyyppi": "puhelin", "kieli": "kieli_en#1"},
        ],
        "vuosiluokat": [],
        "lisatiedot": [],
        "maaUri": "maatjavaltiot1_fin",
        "parentOid": parent_oid,
        "metadata": {
            "yhteystiedot": [
                {"osoiteTyyppi": "kaynti", "kieli": "kieli_fi#1"},
                {"osoiteTyyppi": "posti", "kieli": "kieli_fi#1"},
                {"email": None, "kieli": "kieli_fi#1"},
                {"www": None, "kieli": "kieli_fi#1"},
                {"tyyppi": "puhelin", "kieli": "kieli_fi#1"},
                {"osoiteTyyppi": "kaynti", "kieli": "kieli_sv#1"},
                {"osoiteTyyppi": "posti", "kieli": "kieli_sv#1"},
                {"email": None, "kieli": "kieli_sv#1"},
                {"www": None, "kieli": "kieli_sv#1"},
                {"tyyppi": "puhelin", "kieli": "kieli_sv#1"},
                {"osoiteTyyppi": "kaynti", "kieli": "kieli_en#1"},
                {"osoiteTyyppi": "posti", "kieli": "kieli_en#1"},
                {"email": None, "kieli": "kieli_en#1"},
                {"www": None, "kieli": "kieli_en#1"},
                {"tyyppi": "puhelin", "kieli": "kieli_en#1"},
            ],
            "data": {
                "YLEISKUVAUS": {},
                "ESTEETOMYYS": {},
                "OPPIMISYMPARISTO": {},
                "VUOSIKELLO": {},
                "VASTUUHENKILOT": {},
                "VALINTAMENETTELY": {},
                "AIEMMIN_HANKITTU_OSAAMINEN": {},
                "KIELIOPINNOT": {},
                "TYOHARJOITTELU": {},
                "OPISKELIJALIIKKUVUUS": {},
                "KANSAINVALISET_KOULUTUSOHJELMAT": {},
                "KUSTANNUKSET": {},
                "TIETOA_ASUMISESTA": {},
                "RAHOITUS": {},
                "OPISKELIJARUOKAILU": {},
                "TERVEYDENHUOLTOPALVELUT": {},
                "VAKUUTUKSET": {},
                "OPISKELIJALIIKUNTA": {},
                "VAPAA_AIKA": {},
                "OPISKELIJA_JARJESTOT": {},
                "sosiaalinenmedia_4#1": {},
                "sosiaalinenmedia_1#1": {},
                "sosiaalinenmedia_7#1": {},
                "sosiaalinenmedia_3#1": {},
                "sosiaalinenmedia_2#1": {},
                "sosiaalinenmedia_6#1": {},
                "sosiaalinenmedia_5#1": {},
                "NIMI": {},
                "TEHTAVANIMIKE": {},
                "PUHELINNUMERO": {},
                "SAHKOPOSTIOSOITE": {},
            },
            "hakutoimistoEctsEmail": {},
            "hakutoimistoEctsPuhelin": {},
            "hakutoimistoEctsTehtavanimike": {},
            "hakutoimistoEctsNimi": {},
            "hakutoimistonNimi": {"kieli_fi#1": None, "kieli_sv#1": None, "kieli_en#1": None},
        },
        "yhteystietoArvos": [],
        "varhaiskasvatuksenToimipaikkaTiedot": {
            "toimintamuoto": toimintamuoto,
            "kasvatusopillinenJarjestelma": kasvatusopillinen_jarjestelma,
            "varhaiskasvatuksenToiminnallinenpainotukset": [
                {"toiminnallinenpainotus": "vardatoiminnallinenpainotus_tp98", "alkupvm": str(datetime.date.today())}
            ],
            "paikkojenLukumaara": varhaiskasvatuspaikat,
            "varhaiskasvatuksenJarjestamismuodot": jarjestamismuoto,
            "varhaiskasvatuksenKielipainotukset": [{"kielipainotus": "kieli_99", "alkupvm": str(datetime.date.today())}],
        },
        "piilotettu": piilotettu,
        "alkuPvm": alkamis_pvm,
        "lakkautusPvm": paattymis_pvm,
        "kotipaikkaUri": kunta_koodi,
    }
    return json.dumps(toimipaikka_json)


def get_toimipaikka_update_json(saved_toimipaikka_obj, old_toimipaikka):
    new_toimipaikka_json = copy.deepcopy(old_toimipaikka)

    alkamis_pvm = str(saved_toimipaikka_obj.alkamis_pvm)
    paattymis_pvm = str(saved_toimipaikka_obj.paattymis_pvm) if saved_toimipaikka_obj.paattymis_pvm is not None else None
    new_toimipaikka_json["kotipaikkaUri"] = "kunta_" + saved_toimipaikka_obj.kunta_koodi
    new_toimipaikka_json["alkuPvm"] = alkamis_pvm
    new_toimipaikka_json["lakkautusPvm"] = paattymis_pvm
    new_toimipaikka_json["piilotettu"] = saved_toimipaikka_obj.toimintamuoto_koodi.lower() in ["tm02", "tm03"]

    update_nimet(new_toimipaikka_json, saved_toimipaikka_obj)
    update_vakatieto(new_toimipaikka_json, saved_toimipaikka_obj)
    update_yhteystiedot(new_toimipaikka_json, saved_toimipaikka_obj)

    # Remove redundant parts
    new_toimipaikka_json.pop("kayntiosoite", None)
    new_toimipaikka_json.pop("postiosoite", None)
    new_toimipaikka_json.pop("luontiPvm", None)
    new_toimipaikka_json.pop("muokkausPvm", None)
    new_toimipaikka_json.get("metadata", {}).pop("luontiPvm", None)
    new_toimipaikka_json.get("metadata", {}).pop("muokkausPvm", None)

    # For example end result JSON see: test_organisaatio_update_json
    return json.dumps(new_toimipaikka_json)


def update_nimet(new_toimipaikka_json, toimipaikka_obj):
    # Nimi expected to be validated on higher level as unchanged
    nimi_to_update = next(
        iter(sorted(new_toimipaikka_json.get("nimet", []), key=lambda _nimi: _nimi["alkuPvm"], reverse=True)), {}
    )
    nimi = toimipaikka_obj.nimi
    nimi_group = {"fi": nimi, "sv": nimi, "en": nimi}
    nimi_to_update["nimi"] = nimi_group
    new_toimipaikka_json["nimi"] = nimi_group


def update_vakatieto(new_toimipaikka_json, toimipaikka_obj):
    toimipaikka_id = toimipaikka_obj.id
    vakatieto = new_toimipaikka_json.get("varhaiskasvatuksenToimipaikkaTiedot", {})
    vakatieto["kasvatusopillinenJarjestelma"] = (
        "vardakasvatusopillinenjarjestelma_" + toimipaikka_obj.kasvatusopillinen_jarjestelma_koodi.lower()
    )
    vakatieto["toimintamuoto"] = "vardatoimintamuoto_" + toimipaikka_obj.toimintamuoto_koodi.lower()
    vakatieto["varhaiskasvatuksenJarjestamismuodot"] = [
        "vardajarjestamismuoto_" + koodi.lower() for koodi in toimipaikka_obj.jarjestamismuoto_koodi
    ]
    vakatieto["paikkojenLukumaara"] = toimipaikka_obj.varhaiskasvatuspaikat
    # These have separate update api
    vakatieto["varhaiskasvatuksenKielipainotukset"] = get_kielipainotukset_in_toimipaikka(toimipaikka_id)
    vakatieto["varhaiskasvatuksenToiminnallinenpainotukset"] = get_toiminnallisetpainotukset_in_toimipaikka(toimipaikka_id)
    new_toimipaikka_json["varhaiskasvatuksenToimipaikkaTiedot"] = vakatieto


def update_yhteystiedot(new_toimipaikka_json, toimipaikka_obj):
    # Update existing or create new emails for each language
    yhteystiedot = new_toimipaikka_json.get("yhteystiedot", [])

    # Sähköposti
    email_template = {"email": toimipaikka_obj.sahkopostiosoite}
    upsert_yhteystieto(
        email_template, yhteystiedot, lambda _yhteystieto: "email" in _yhteystieto, ["kieli_fi#1", "kieli_sv#1", "kieli_en#1"]
    )
    # Puhelinnumero
    puhelinnumero_template = {"numero": toimipaikka_obj.puhelinnumero, "tyyppi": "puhelin"}
    upsert_yhteystieto(
        puhelinnumero_template,
        yhteystiedot,
        lambda _yhteystieto: "numero" in _yhteystieto,
        ["kieli_fi#1", "kieli_sv#1", "kieli_en#1"],
    )
    # Postiosoite
    posti_template = {
        "osoite": toimipaikka_obj.postiosoite,
        "postinumeroUri": "posti_" + toimipaikka_obj.postinumero,
        "postitoimipaikka": toimipaikka_obj.postitoimipaikka,
        "osoiteTyyppi": "posti",
    }
    upsert_yhteystieto(
        posti_template,
        yhteystiedot,
        lambda _yhteystieto: "osoiteTyyppi" in _yhteystieto and "posti" == _yhteystieto["osoiteTyyppi"],
        ["kieli_fi#1", "kieli_sv#1"],
    )
    # Käyntiosoite
    kaynti_template = {
        "osoite": toimipaikka_obj.kayntiosoite,
        "postinumeroUri": "posti_" + toimipaikka_obj.kayntiosoite_postinumero,
        "postitoimipaikka": toimipaikka_obj.kayntiosoite_postitoimipaikka,
        "osoiteTyyppi": "kaynti",
    }
    upsert_yhteystieto(
        kaynti_template,
        yhteystiedot,
        lambda _yhteystieto: "osoiteTyyppi" in _yhteystieto and "kaynti" == _yhteystieto["osoiteTyyppi"],
        ["kieli_fi#1", "kieli_sv#1"],
    )
    new_toimipaikka_json["yhteystiedot"] = yhteystiedot


def upsert_yhteystieto(yhteystieto_template, yhteystiedot, condition, lang_urls):
    """
    Create or update yhteystieto
    :param yhteystieto_template: dictionary containing update and create fields
    :param yhteystiedot: list to insert or update
    :param condition: function to identify correct yhteystieto elements
    :param lang_urls: list of kieli uris this handles
    :return: None
    """
    [yhteystieto.update(copy.copy(yhteystieto_template)) for yhteystieto in yhteystiedot if condition(yhteystieto)]
    existing_yhteystieto_lang_urls = [yhteystieto["kieli"] for yhteystieto in yhteystiedot if condition(yhteystieto)]
    new_emails = [
        create_yhteystieto(yhteystieto_template, lang_url)
        for lang_url in lang_urls
        if lang_url not in existing_yhteystieto_lang_urls
    ]
    yhteystiedot.extend(new_emails)


def create_yhteystieto(yhteystieto_to_copy, lang_url):
    """
    Copy and add kieli to new yhteystieto
    :param yhteystieto_to_copy: yhteystieto dictionary
    :param lang_url: lang url to include
    :return: yhteystieto
    """
    new_yhteystieto = copy.copy(yhteystieto_to_copy)
    new_yhteystieto.update({"kieli": lang_url})
    return new_yhteystieto


def get_kielipainotukset_in_toimipaikka(toimipaikka_id):
    queryset = KieliPainotus.objects.filter(toimipaikka=toimipaikka_id)
    kielipainotukset = []

    for kielipainotus in queryset:
        kielipainotus_koodi = kielipainotus.kielipainotus_koodi.lower()
        if kielipainotus_koodi.startswith("se"):
            # If kielipainotus_koodi is one of saame variants (se*), send just generic saame (se)
            # Organisaatiopalvelu does not support saame variants
            kielipainotus_koodi = "se"

        kielipainotukset.append(
            {
                "kielipainotus": "kieli_" + kielipainotus_koodi,
                "alkupvm": str(kielipainotus.alkamis_pvm),
                "loppupvm": str(kielipainotus.paattymis_pvm) if kielipainotus.paattymis_pvm else None,
            }
        )

    if not kielipainotukset:  # Add default
        kielipainotukset.append({"kielipainotus": "kieli_99", "alkupvm": str(datetime.date.today())})
    return kielipainotukset


def get_toiminnallisetpainotukset_in_toimipaikka(toimipaikka_id):
    queryset = ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka_id)
    toiminnallisetpainotukset = []

    for toiminnallinenpainotus in queryset:
        painotus = {}
        painotus["toiminnallinenpainotus"] = (
            "vardatoiminnallinenpainotus_" + toiminnallinenpainotus.toimintapainotus_koodi.lower()
        )
        painotus["alkupvm"] = str(toiminnallinenpainotus.alkamis_pvm)
        painotus["loppupvm"] = str(toiminnallinenpainotus.paattymis_pvm) if toiminnallinenpainotus.paattymis_pvm else None
        toiminnallisetpainotukset.append(painotus)

    if not toiminnallisetpainotukset:  # Add default
        toiminnallisetpainotukset.append(
            {"toiminnallinenpainotus": "vardatoiminnallinenpainotus_tp98", "alkupvm": str(datetime.date.today())}
        )
    return toiminnallisetpainotukset


def create_toimipaikka_in_organisaatiopalvelu(toimipaikka_validated_data):
    vakajarjestaja_id = toimipaikka_validated_data["vakajarjestaja"].id
    toimipaikka_json = get_toimipaikka_json(toimipaikka_validated_data, vakajarjestaja_id)

    return create_organisaatio(toimipaikka_json)


def update_toimipaikka_in_organisaatiopalvelu(toimipaikka_obj):
    toimipaikka_id = toimipaikka_obj.id
    toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
    old_toimipaikka = get_organisaatio(toimipaikka_organisaatio_oid, toimipaikka_id)

    if old_toimipaikka is not None:
        toimipaikka_update_json = get_toimipaikka_update_json(toimipaikka_obj, old_toimipaikka)
        update_organisaatio(toimipaikka_organisaatio_oid, toimipaikka_update_json, toimipaikka_id)


def update_toimipaikat_in_organisaatiopalvelu():
    """
    First, make a list of all the toimipaikka-objects which have been changed after the last aikaleima.
    Include also the changes (and removals via history) from relation of Kielipainotus and Toiminnallinenpainotus.
    """
    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.ORGANISAATIOS_VARDA_LAST_UPDATE.name)
    end_datetime = datetime.datetime.now(tz=datetime.timezone.utc)
    start_datetime = aikaleima.aikaleima

    """
    When a toimipaikka is created, the muutos_pvm and luonti_pvm are not the same.
    They have a very small time difference. See example below.



    # select nimi, luonti_pvm, muutos_pvm from varda_toimipaikka;
            nimi         |          luonti_pvm           |          muutos_pvm
    ---------------------+-------------------------------+-------------------------------
     Tester2 toimipaikka | 2019-05-08 11:53:53.491152+03 | 2019-05-08 11:53:53.491169+03
     Paivakoti kukkanen  | 2019-05-08 11:53:53.499696+03 | 2019-05-08 11:53:53.499715+03

    We do not want to include the ones having (almost) same creation/update time.
    Note: It would be better to use absolute (abs) function below, but couldn't get that working.
    However, seems like luonti_pvm is always before muutos_pvm, so we should be safe.
    https://stackoverflow.com/questions/47456867/how-to-get-absolute-value-of-interval-in-django-f-expression

    We need annotations only for the first Toimipaikka-query. But because we use union later,
    we need to add the same annotation to all toimipaikka-queries. Union requires that the
    querysets have exactly the same attributes (and same types).
    """
    # Do not update organisaatio service managed toimipaikkas (filter/exclude has no effect after union)
    toimipaikka_base_qs = Toimipaikka.objects.exclude(hallinnointijarjestelma=Hallinnointijarjestelma.ORGANISAATIO.name)

    toimipaikka_changed_qs = (
        toimipaikka_base_qs.filter(muutos_pvm__gt=start_datetime).annotate(
            update_time_difference=ExpressionWrapper(F("muutos_pvm") - F("luonti_pvm"), output_field=DurationField())
        )
        # greater than 100 mseconds difference
        .filter(update_time_difference__gt=datetime.timedelta(microseconds=100 * 1000))
    )

    toimipaikka_kielipainotus_changed_qs = toimipaikka_base_qs.filter(kielipainotukset__muutos_pvm__gt=start_datetime).annotate(
        update_time_difference=ExpressionWrapper(F("muutos_pvm") - F("luonti_pvm"), output_field=DurationField())
    )
    toimipaikka_toiminnallinenpainotus_changed_qs = toimipaikka_base_qs.filter(
        toiminnallisetpainotukset__muutos_pvm__gt=start_datetime
    ).annotate(update_time_difference=ExpressionWrapper(F("muutos_pvm") - F("luonti_pvm"), output_field=DurationField()))

    """
    Let's use the history-type to find the removals:
    '+' added
    '~' changed
    '-' deleted
    """
    history_kielipainotus_deleted_qs = (
        KieliPainotus.history.filter(history_date__gt=start_datetime)
        .filter(history_type="-")
        .values_list("toimipaikka_id", flat=True)
    )

    history_toiminnallinenpainotus_deleted_qs = (
        ToiminnallinenPainotus.history.filter(history_date__gt=start_datetime)
        .filter(history_type="-")
        .values_list("toimipaikka_id", flat=True)
    )

    history_deleted_painotukset_union = history_kielipainotus_deleted_qs.union(history_toiminnallinenpainotus_deleted_qs)

    toimipaikka_deleted_painotukset_qs = toimipaikka_base_qs.filter(id__in=history_deleted_painotukset_union).annotate(
        update_time_difference=ExpressionWrapper(F("muutos_pvm") - F("luonti_pvm"), output_field=DurationField())
    )

    result_qs = toimipaikka_changed_qs.union(
        toimipaikka_kielipainotus_changed_qs, toimipaikka_toiminnallinenpainotus_changed_qs, toimipaikka_deleted_painotukset_qs
    )
    for toimipaikka_obj in result_qs:
        if toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka_obj):
            update_toimipaikka_in_organisaatiopalvelu(toimipaikka_obj)

    aikaleima.aikaleima = end_datetime
    aikaleima.save()


def update_all_organisaatio_service_organisations():
    """
    Checks for updates for all organisaatio-service managed toimipaikkas using running timestamp.
    :return: None
    """
    chunk_size = 100
    # Playing it safe with new update timestamp (could be the time last request was made). Expecting
    # organisaatio-service to use same timezone as varda.
    aikaleima_now = datetime.datetime.now(tz=datetime.timezone.utc)
    aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.ORGANISAATIOS_LAST_UPDATE.name)
    changed_oids = get_changed_since(aikaleima.aikaleima)
    # List might be long so we split it to avoid big 'in' queries.
    for oid_chunk in list_to_chunks(changed_oids, chunk_size):
        _update_toimipaikka_chunk(oid_chunk)
    aikaleima.aikaleima = aikaleima_now
    aikaleima.save()


def _update_toimipaikka_chunk(oid_chunk):
    toimipaikka_objs = Toimipaikka.objects.filter(
        organisaatio_oid__in=oid_chunk, hallinnointijarjestelma=Hallinnointijarjestelma.ORGANISAATIO.name
    )
    oids_to_update = set(map(lambda org: org.organisaatio_oid, toimipaikka_objs))
    organisaatios_data = {org["oid"]: org for org in get_multiple_organisaatio(oids_to_update)}
    for toimipaikka in toimipaikka_objs:
        organisaatio = organisaatios_data.get(toimipaikka.organisaatio_oid, None)
        if organisaatio is None:
            logger.error(
                "Organisaatio-service managed toimipaikka not found from organisaatio-service with oid %s",
                toimipaikka.organisaatio_oid,
            )
        else:
            _fill_toimipaikka_data(organisaatio, toimipaikka)
            toimipaikka.save()


def update_all_toimipaikat_in_organisaatiopalvelu(toimipaikka_filter=None):
    """
    Update all toimipaikat in organisaatiopalvelu
    :param toimipaikka_filter: Q-object
    """
    # Exclude Organisaatiopalvelu-managed toimipaikat
    toimipaikka_qs = Toimipaikka.objects.exclude(hallinnointijarjestelma=Hallinnointijarjestelma.ORGANISAATIO.name)
    if toimipaikka_filter:
        toimipaikka_qs = toimipaikka_qs.filter(toimipaikka_filter)

    for toimipaikka in toimipaikka_qs:
        if toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka):
            update_toimipaikka_in_organisaatiopalvelu(toimipaikka)
