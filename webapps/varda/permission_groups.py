import logging

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from guardian.shortcuts import assign_perm, remove_perm
from time import sleep
from varda.misc import get_json_from_external_service
from varda.models import Toimipaikka, VakaJarjestaja, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet


# Get an instance of a logger
logger = logging.getLogger(__name__)


def assign_permissions_to_vakajarjestaja_obj(vakajarjestaja_organisaatio_oid):
    vakajarjestaja_query = VakaJarjestaja.objects.filter(organisaatio_oid=vakajarjestaja_organisaatio_oid)
    if len(vakajarjestaja_query) == 1:
        vakajarjestaja_obj = vakajarjestaja_query[0]
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, VakaJarjestaja, vakajarjestaja_obj)
    else:
        logger.error('VakaJarjestaja: Could not assign obj-level permissions to: ' + vakajarjestaja_organisaatio_oid)


def assign_permissions_to_toimipaikka_obj(toimipaikka_organisaatio_oid, vakajarjestaja_organisaatio_oid):
    toimipaikka_query = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_organisaatio_oid)
    if len(toimipaikka_query) == 1:
        toimipaikka_obj = toimipaikka_query[0]
        assign_object_level_permissions(toimipaikka_organisaatio_oid, Toimipaikka, toimipaikka_obj)
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Toimipaikka, toimipaikka_obj)  # Remember also vakajarjestaja-level
    else:
        logger.error('Toimipaikka: Could not assign obj-level permissions to: ' + toimipaikka_organisaatio_oid)


def get_organization_type(organisaatio_oid):
    """
    We know that organization is vaka-organization but we want to know which type.
    """
    service_name = "organisaatio-service"
    organisaatio_url = "/rest/organisaatio/v4/hae?aktiiviset=true&oid=" + organisaatio_oid
    reply_msg = get_json_from_external_service(service_name, organisaatio_url)
    if not reply_msg["is_ok"]:
        return True

    reply_json = reply_msg["json_msg"]

    if "numHits" not in reply_json or ("numHits" in reply_json and reply_json["numHits"] != 1):
        logger.warning('No organization hit for: /' + service_name + organisaatio_url)
        return True

    try:
        organization_data = reply_json["organisaatiot"][0]
    except IndexError:
        logger.error('Problem with organization: /' + service_name + organisaatio_url)
        return None

    if "organisaatiotyypit" not in organization_data:
        logger.error('Organisaatio missing rquired data: /' + service_name + organisaatio_url)
        return True

    if "organisaatiotyyppi_07" in organization_data["organisaatiotyypit"]:
        return "organisaatiotyyppi_07"
    else:  # "organisaatiotyyppi_08" in organization_data["organisaatiotyypit"]:
        return "organisaatiotyyppi_08"


def create_permission_groups_for_organisaatio(organisaatio_oid, vakajarjestaja=True):
    PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA
    KATSELIJA = Z4_CasKayttoOikeudet.KATSELIJA
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA

    HUOLTAJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    HUOLTAJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    roles_vakajarjestaja = [PALVELUKAYTTAJA, PAAKAYTTAJA, TALLENTAJA, KATSELIJA,
                            HUOLTAJATIEDOT_TALLENTAJA, HUOLTAJATIEDOT_KATSELIJA]

    if vakajarjestaja:
        roles = roles_vakajarjestaja
    else:  # toimipaikka -> drop PALVELUKAYTTAJA + PAAKAYTTAJA
        roles = roles_vakajarjestaja.copy()
        del roles[0:2]  # remove indexes 0-1 -> palvelukayttaja & paakayttaja

    organization_type = get_organization_type(organisaatio_oid)

    for role in roles:
        group_name = role + "_" + organisaatio_oid
        try:
            Group.objects.get(name=group_name)  # group's name is unique
        except Group.DoesNotExist:
            create_permission_group(role, organisaatio_oid, organization_type)


def get_permission_group(role, organisaatio_oid):
    """
    Sometimes group is not ready yet (creation happening asynchronously).
    Let's wait then a few seconds.
    """
    group_name = role + "_" + organisaatio_oid
    MAX_LOOPS = 5
    loop_number = 0
    while True:
        loop_number += 1
        try:
            permission_group = Group.objects.get(name=group_name)  # group's name is unique
            break
        except Group.DoesNotExist:
            logger.error('Did not find permission_group with name: ' + group_name)
            if loop_number < MAX_LOOPS:
                sleep(2)
            else:
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

    group_templates_vakajarjestaja = {
        PAAKAYTTAJA: 'vakajarjestaja_paakayttaja',
        TALLENTAJA: 'vakajarjestaja_tallentaja',
        KATSELIJA: 'vakajarjestaja_katselija',
        PALVELUKAYTTAJA: 'vakajarjestaja_palvelukayttaja',
        HUOLTAJATIEDOT_TALLENTAJA: 'vakajarjestaja_huoltajatiedot_tallentaja',
        HUOLTAJATIEDOT_KATSELIJA: 'vakajarjestaja_huoltajatiedot_katselija'
    }

    group_templates_toimipaikka = {
        PAAKAYTTAJA: 'toimipaikka_katselija',
        TALLENTAJA: 'toimipaikka_tallentaja',
        KATSELIJA: 'toimipaikka_katselija',
        HUOLTAJATIEDOT_TALLENTAJA: 'toimipaikka_huoltajatiedot_tallentaja',
        HUOLTAJATIEDOT_KATSELIJA: 'toimipaikka_huoltajatiedot_katselija'
    }

    """
    organisaatiotyyppi_07 == "Varhaiskasvatuksen jarjestaja"
    organisaatiotyyppi_08 == "Varhaiskasvatuksen toimipaikka"
    Ref: https://github.com/Opetushallitus/organisaatio/blob/master/organisaatio-service/src/main/resources/db/migration/V084__organisaatio_tyypit.sql
    """
    if organization_type == "organisaatiotyyppi_07":
        group_template_name = group_templates_vakajarjestaja[role]
    else:  # organization_type == "organisaatiotyyppi_08":
        group_template_name = group_templates_toimipaikka[role]

    """
    Finally copy the template and create a new permission_group.
    """
    new_name_of_permission_group = role + "_" + organisaatio_oid

    group_template = Group.objects.get(name=group_template_name)
    group_template_permissions = group_template.permissions.all()

    group_new = group_template
    group_new.pk = None  # This is required when a new instance is wanted
    group_new.name = new_name_of_permission_group

    with transaction.atomic():
        group_new.save()  # This creates a permission_group with a new id

        for permission in group_template_permissions:
            group_new.permissions.add(permission)


def assign_organisation_group_permissions(model, instance, vakajarjestaja_oid, toimipaikka_oid=None):
    """
    Assings varhaiskasvatuksen jarjestaja and toimipaikka group permissions to object instance
    :param model: Model of the instance
    :param instance: Object instance of the model
    :param vakajarjestaja_oid: Organisation oid of varhaiskasvatuksen jarjestaja over given toimipaikka
    :param toimipaikka_oid: organisaatio oid of toimipaikka under given varhaiskasvatuksen jarjestaja
    :return: None
    """
    assign_object_level_permissions(vakajarjestaja_oid, model, instance)
    if toimipaikka_oid is not None:
        assign_object_level_permissions(toimipaikka_oid, model, instance)


def assign_or_remove_object_level_permissions(organisaatio_oid, model_name, model_obj, paos_kytkin, assign):
    content_type_obj = ContentType.objects.get_for_model(model_name)
    all_organization_permission_groups = get_permission_groups_for_organization(organisaatio_oid)

    for permission_group in all_organization_permission_groups:
        model_specific_permissions_for_group = permission_group.permissions.filter(content_type=content_type_obj.id)
        for permission in model_specific_permissions_for_group:
            if paos_kytkin and permission.codename != 'view_' + model_name._meta.model.__name__.lower():
                continue
            if assign:
                assign_perm(permission, permission_group, model_obj)
            else:
                remove_perm(permission, permission_group, model_obj)


def assign_object_level_permissions(organisaatio_oid, model_name, model_obj, paos_kytkin=False):
    assign_or_remove_object_level_permissions(organisaatio_oid, model_name, model_obj, paos_kytkin, assign=True)


def remove_object_level_permissions(organisaatio_oid, model_name, model_obj, paos_kytkin=False):
    assign_or_remove_object_level_permissions(organisaatio_oid, model_name, model_obj, paos_kytkin, assign=False)


def get_permission_groups_for_organization(organisaatio_oid):
    """
    Let's find all the groups for organization, where group_name has one of the roles in it.
    We do not want to include possibly other groups in this search.

    First, if organisaatio_oid is empty, return no permissions.
    """
    permission_groups = []
    if organisaatio_oid is None or organisaatio_oid == "":
        return permission_groups

    PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA
    KATSELIJA = Z4_CasKayttoOikeudet.KATSELIJA
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA

    HUOLTAJATIEDOT_TALLENTAJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    HUOLTAJATIEDOT_KATSELIJA = Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    roles = [PAAKAYTTAJA, TALLENTAJA, KATSELIJA, PALVELUKAYTTAJA,
             HUOLTAJATIEDOT_TALLENTAJA, HUOLTAJATIEDOT_KATSELIJA]

    all_organization_groups = Group.objects.filter(name__contains=organisaatio_oid)
    for group in all_organization_groups:
        if any(x in group.name for x in roles):
            permission_groups.append(group)

    return permission_groups


def add_oph_staff_to_vakajarjestaja_katselija_groups():
    """
    Select users with "approved_oph_staff:True" -> Add them KATSELIJA-permissions to every vakajarjestaja.
    I.e. exclude toimipaikka_oid-groups below.
    """
    approved_oph_staff_query = Z3_AdditionalCasUserFields.objects.filter(approved_oph_staff=True)
    vakajarjestaja_oids = VakaJarjestaja.objects.values_list('organisaatio_oid', flat=True).exclude(organisaatio_oid=None)
    org_oid_query = Q()
    for organisaatio_oid in vakajarjestaja_oids:
        org_oid_query |= Q(name__endswith=organisaatio_oid)

    katselija_groups = (Group
                        .objects
                        .filter((Q(name__startswith='VARDA-KATSELIJA') |
                                 Q(name__startswith='HUOLTAJATIETO_KATSELU')),
                                org_oid_query))

    for katselija_group in katselija_groups:
        for approved_oph_staff_member_obj in approved_oph_staff_query:
            if not approved_oph_staff_member_obj.user.is_superuser:  # Superuser has permissions anyhow
                katselija_group.user_set.add(approved_oph_staff_member_obj.user)
