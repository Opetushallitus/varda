import logging

from django.conf import settings
from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import ValidationError

from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.misc import get_json_from_external_service
from varda.models import Organisaatio, Z4_CasKayttoOikeudet


logger = logging.getLogger(__name__)


def get_organization_type(organisaatio_oid):
    """
    We know that organization is vaka-organization but we want to know which type.
    """
    service_name = "organisaatio-service"
    organisaatio_url = "/api/hae?aktiiviset=true&suunnitellut=true&lakkautetut=true&oid=" + organisaatio_oid
    reply_msg = get_json_from_external_service(service_name, organisaatio_url)
    if not reply_msg["is_ok"]:
        return True

    reply_json = reply_msg["json_msg"]

    if "numHits" not in reply_json or ("numHits" in reply_json and reply_json["numHits"] != 1):
        logger.warning("No organization hit for: /" + service_name + organisaatio_url)
        return True

    try:
        organization_data = reply_json["organisaatiot"][0]
    except IndexError:
        logger.error("Problem with organization: /" + service_name + organisaatio_url)
        return None

    if "organisaatiotyypit" not in organization_data:
        logger.error("Organisaatio missing rquired data: /" + service_name + organisaatio_url)
        return True

    if "organisaatiotyyppi_07" in organization_data["organisaatiotyypit"]:
        return "organisaatiotyyppi_07"
    else:  # 'organisaatiotyyppi_08' in organization_data['organisaatiotyypit']:
        return "organisaatiotyyppi_08"


def create_permission_groups_for_organisaatio(organisaatio_oid, organisaatiotyyppi):
    PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA
    KATSELIJA = Z4_CasKayttoOikeudet.KATSELIJA
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA

    HUOLTAJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    HUOLTAJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    HENKILOSTO_TYONTEKIJA_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA
    HENKILOSTO_TYONTEKIJA_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA

    HENKILOSTO_VUOKRATTU_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_TALLENTAJA
    HENKILOSTO_VUOKRATTU_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_KATSELIJA

    TUEN_TIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.TUEN_TIEDOT_TALLENTAJA
    TUEN_TIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.TUEN_TIEDOT_KATSELIJA

    HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA
    HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA

    TOIMIJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.TOIMIJATIEDOT_KATSELIJA
    TOIMIJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA

    RAPORTTIEN_KATSELIJA = Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA

    roles_vakajarjestaja = [
        PALVELUKAYTTAJA,
        PAAKAYTTAJA,
        TALLENTAJA,
        KATSELIJA,
        HUOLTAJATIEDOT_TALLENTAJA,
        HUOLTAJATIEDOT_KATSELIJA,
        HENKILOSTO_TYONTEKIJA_TALLENTAJA,
        HENKILOSTO_TYONTEKIJA_KATSELIJA,
        HENKILOSTO_VUOKRATTU_TALLENTAJA,
        HENKILOSTO_VUOKRATTU_KATSELIJA,
        TUEN_TIEDOT_TALLENTAJA,
        TUEN_TIEDOT_KATSELIJA,
        HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
        HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
        TOIMIJATIEDOT_KATSELIJA,
        TOIMIJATIEDOT_TALLENTAJA,
        RAPORTTIEN_KATSELIJA,
    ]

    roles = []

    if organisaatiotyyppi == Organisaatiotyyppi.VAKAJARJESTAJA.value:
        roles = roles_vakajarjestaja
    elif organisaatiotyyppi == Organisaatiotyyppi.TOIMIPAIKKA.value:
        # toimipaikka -> drop PALVELUKAYTTAJA, PAAKAYTTAJA, HENKILOSTO_VUOKRATTU, TUEN_TIEDOT, TOIMIJATIEDOT, RAPORTIT
        excluded_roles = [
            PALVELUKAYTTAJA,
            PAAKAYTTAJA,
            HENKILOSTO_VUOKRATTU_TALLENTAJA,
            HENKILOSTO_VUOKRATTU_KATSELIJA,
            TUEN_TIEDOT_TALLENTAJA,
            TUEN_TIEDOT_KATSELIJA,
            TOIMIJATIEDOT_TALLENTAJA,
            TOIMIJATIEDOT_KATSELIJA,
            RAPORTTIEN_KATSELIJA,
        ]
        roles = [role for role in roles_vakajarjestaja if role not in excluded_roles]
    elif organisaatiotyyppi == Organisaatiotyyppi.MUU.value:
        # muu (OPH, Kela...) -> LUOVUTUSPALVELU
        roles = [Z4_CasKayttoOikeudet.LUOVUTUSPALVELU]
        if organisaatio_oid == settings.OPETUSHALLITUS_ORGANISAATIO_OID:
            roles.append(Z4_CasKayttoOikeudet.YLLAPITAJA)

    for role in roles:
        group_name = f"{role}_{organisaatio_oid}"
        try:
            Group.objects.get(name=group_name)  # group's name is unique
        except Group.DoesNotExist:
            if organisaatiotyyppi in [
                Organisaatiotyyppi.VAKAJARJESTAJA.value,
                Organisaatiotyyppi.TOIMIPAIKKA.value,
                Organisaatiotyyppi.MUU.value,
            ]:
                create_permission_group(role, organisaatio_oid, organisaatiotyyppi)
            else:
                logger.warning(
                    "User tried to login to non-valid organisation {}. Not creating permission group {}.".format(
                        organisaatio_oid, group_name
                    )
                )


def get_permission_group(role, organisaatio_oid):
    """
    Return permission group
    :param role: permission group role eg. VARDA-PAAKAYTTAJA
    :param organisaatio_oid: organisation where permission group is in
    :return: Group object or None
    """
    group_name = role + "_" + organisaatio_oid
    try:
        permission_group = Group.objects.get(name=group_name)  # group's name is unique
    except Group.DoesNotExist:
        logger.error("Did not find permission_group with name: " + group_name)
        return None

    return permission_group


def create_permission_group(role, organisaatio_oid, organization_type):
    """
    We have permission_group-templates available. Let's create a new permission_group and use the existing templates as a base.
    This will create a new group, and assign it pre-defined model-permissions from the template.
    """
    PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA
    KATSELIJA = Z4_CasKayttoOikeudet.KATSELIJA
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA
    HUOLTAJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    HUOLTAJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    HENKILOSTO_TYONTEKIJA_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA
    HENKILOSTO_TYONTEKIJA_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA

    HENKILOSTO_VUOKRATTU_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_TALLENTAJA
    HENKILOSTO_VUOKRATTU_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_KATSELIJA

    TUEN_TIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.TUEN_TIEDOT_TALLENTAJA
    TUEN_TIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.TUEN_TIEDOT_KATSELIJA

    HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA = Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA
    HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA = Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA

    TOIMIJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.TOIMIJATIEDOT_KATSELIJA
    TOIMIJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA

    RAPORTTIEN_KATSELIJA = Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA

    group_templates_vakajarjestaja = {
        PAAKAYTTAJA: "vakajarjestaja_paakayttaja",
        TALLENTAJA: "vakajarjestaja_tallentaja",
        KATSELIJA: "vakajarjestaja_katselija",
        PALVELUKAYTTAJA: "vakajarjestaja_palvelukayttaja",
        HUOLTAJATIEDOT_TALLENTAJA: "vakajarjestaja_huoltajatiedot_tallentaja",
        HUOLTAJATIEDOT_KATSELIJA: "vakajarjestaja_huoltajatiedot_katselija",
        HENKILOSTO_TYONTEKIJA_TALLENTAJA: "vakajarjestaja_henkilosto_tyontekija_tallentaja",
        HENKILOSTO_TYONTEKIJA_KATSELIJA: "vakajarjestaja_henkilosto_tyontekija_katselija",
        HENKILOSTO_VUOKRATTU_TALLENTAJA: "vakajarjestaja_henkilosto_vuokrattu_tallentaja",
        HENKILOSTO_VUOKRATTU_KATSELIJA: "vakajarjestaja_henkilosto_vuokrattu_katselija",
        TUEN_TIEDOT_TALLENTAJA: "vakajarjestaja_tuen_tiedot_tallentaja",
        TUEN_TIEDOT_KATSELIJA: "vakajarjestaja_tuen_tiedot_katselija",
        HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA: "vakajarjestaja_henkilosto_taydennyskoulutus_tallentaja",
        HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA: "vakajarjestaja_henkilosto_taydennyskoulutus_katselija",
        TOIMIJATIEDOT_KATSELIJA: "vakajarjestaja_toimijatiedot_katselija",
        TOIMIJATIEDOT_TALLENTAJA: "vakajarjestaja_toimijatiedot_tallentaja",
        RAPORTTIEN_KATSELIJA: "vakajarjestaja_raporttien_katselija",
    }

    group_templates_toimipaikka = {
        PAAKAYTTAJA: "toimipaikka_katselija",
        TALLENTAJA: "toimipaikka_tallentaja",
        KATSELIJA: "toimipaikka_katselija",
        HUOLTAJATIEDOT_TALLENTAJA: "toimipaikka_huoltajatiedot_tallentaja",
        HUOLTAJATIEDOT_KATSELIJA: "toimipaikka_huoltajatiedot_katselija",
        HENKILOSTO_TYONTEKIJA_TALLENTAJA: "toimipaikka_henkilosto_tyontekija_tallentaja",
        HENKILOSTO_TYONTEKIJA_KATSELIJA: "toimipaikka_henkilosto_tyontekija_katselija",
        HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA: "toimipaikka_henkilosto_taydennyskoulutus_tallentaja",
        HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA: "toimipaikka_henkilosto_taydennyskoulutus_katselija",
    }

    group_templates_muu = {Z4_CasKayttoOikeudet.YLLAPITAJA: "yllapitaja", Z4_CasKayttoOikeudet.LUOVUTUSPALVELU: "luovutuspalvelu"}

    """
    organisaatiotyyppi_05 == 'Muu organisaatio'
    organisaatiotyyppi_07 == 'Varhaiskasvatuksen jarjestaja'
    organisaatiotyyppi_08 == 'Varhaiskasvatuksen toimipaikka'
    Ref: https://github.com/Opetushallitus/organisaatio/blob/master/organisaatio-service/src/main/resources/db/migration/V084__organisaatio_tyypit.sql
    """
    if organization_type == Organisaatiotyyppi.VAKAJARJESTAJA.value:
        group_template_name = group_templates_vakajarjestaja[role]
    elif organization_type == Organisaatiotyyppi.TOIMIPAIKKA.value:
        group_template_name = group_templates_toimipaikka[role]
    elif organization_type == Organisaatiotyyppi.MUU.value:
        group_template_name = group_templates_muu[role]
    else:
        logger.error(f"Creating permission group for {organization_type} is not allowed.")
        return None

    """
    Finally copy the template and create a new permission_group.
    """
    new_name_of_permission_group = f"{role}_{organisaatio_oid}"

    group_template = Group.objects.get(name=group_template_name)
    group_template_permissions = group_template.permissions.all()

    group_new = group_template
    group_new.pk = None  # This is required when a new instance is wanted
    group_new.name = new_name_of_permission_group

    with transaction.atomic():
        group_new.save()  # This creates a permission_group with a new id

        for permission in group_template_permissions:
            group_new.permissions.add(permission)


def get_all_permission_groups_for_organization(organisaatio_oid):
    if not organisaatio_oid:
        return Group.objects.none()
    return Group.objects.filter(name__endswith=organisaatio_oid)


def add_oph_staff_to_vakajarjestaja_katselija_groups(user_id=None, organisaatio_oid=None):
    """
    Select users belonging to VARDA-YLLAPITAJA group -> Add them KATSELIJA-permissions to every vakajarjestaja.
    I.e. exclude toimipaikka_oid-groups below.
    """
    group_obj = Group.objects.filter(name=get_oph_yllapitaja_group_name()).first()
    if not group_obj:
        logger.error("OPH staff group does not exist.")
        return None
    user_qs = group_obj.user_set.all()

    if user_qs.count() > settings.OPH_USER_LIMIT:
        # Check that number of OPH users does not exceed limit
        error_msg = "There are too many OPH staff users."
        logger.error(error_msg)
        raise ValidationError(error_msg)

    if user_id:
        user_qs = user_qs.filter(id=user_id)

    vakajarjestaja_oids = (
        [organisaatio_oid]
        if organisaatio_oid
        else Organisaatio.objects.values_list("organisaatio_oid", flat=True).exclude(
            Q(organisaatio_oid=None) | Q(organisaatio_oid="")
        )
    )
    org_oid_query = Q()
    for org_oid in vakajarjestaja_oids:
        org_oid_query |= Q(name__endswith=org_oid)

    katselija_condition = (
        Q(name__startswith="VARDA-KATSELIJA")
        | Q(name__startswith="HUOLTAJATIETO_KATSELU")
        | Q(name__startswith="HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA")
        | Q(name__startswith="HENKILOSTO_VUOKRATTU_KATSELIJA")
        | Q(name__startswith="HENKILOSTO_TYONTEKIJA_KATSELIJA")
        | Q(name__startswith="VARDA_TOIMIJATIEDOT_KATSELIJA")
        | Q(name__startswith="VARDA_RAPORTTIEN_KATSELIJA")
    )
    katselija_groups_query = Group.objects.filter(katselija_condition, org_oid_query)

    for user in user_qs:
        if not user.is_superuser:  # Superuser has permissions anyhow
            for katselija_group in katselija_groups_query:
                katselija_group.user_set.add(user)


def get_oph_yllapitaja_group_name():
    return f"{Z4_CasKayttoOikeudet.YLLAPITAJA}_{settings.OPETUSHALLITUS_ORGANISAATIO_OID}"
