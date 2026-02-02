import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework.exceptions import AuthenticationFailed

from varda.cache import delete_object_ids_user_has_permissions
from varda.clients import organisaatio_client
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.enums.tietosisalto_ryhma import TietosisaltoRyhma
from varda.exceptions.invalid_koodi_uri_exception import InvalidKoodiUriException
from varda.misc import get_json_from_external_service, get_reply_json
from varda.models import Toimipaikka, Organisaatio, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, LoginCertificate
from varda.oppijanumerorekisteri import fetch_yhteystieto_data_for_henkilo_oid_list, get_user_data
from varda.organisaatiopalvelu import create_toimipaikka_using_oid, create_organization_using_oid
from varda.permission_groups import get_permission_group
from varda.permissions import delete_all_user_permissions, get_related_organisaatio_for_user, is_oph_staff


logger = logging.getLogger(__name__)
SERVICE_NAME = "kayttooikeus-service"


def set_permissions_for_cas_user(user_id):
    """
    Set virkailija CAS authenticated user privileges.
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # Cas library creates user on login so we should come here basically never
        return None

    # Cleared so service users can't find way to login through here as regular user.
    if settings.QA_ENV or settings.PRODUCTION_ENV:
        LoginCertificate.objects.filter(user=user).update(user=None)

    henkilo_oid, kayttajatyyppi = set_user_info_for_cas_user(user)
    if kayttajatyyppi == Kayttajatyyppi.PALVELU.value:
        set_service_user_permissions(user, henkilo_oid)
    else:
        set_user_kayttooikeudet(henkilo_oid, user)
    # After permissions have been fetched, modify groups so that user only has permissions to one organization at a time
    set_active_groups_for_user(user)


def set_user_info_for_cas_user(user):
    """
    Get basic information for CAS-user from kayttooikeus-service
    :param user: User instance
    :return: User henkilo_oid
    """
    user_info = get_user_info(user.username)
    if user_info["is_ok"]:
        henkilo_oid = user_info["json_msg"]["henkilo_oid"]
        henkilo_kayttajatyyppi = user_info["json_msg"]["henkilo_kayttajatyyppi"]
    else:
        # not ok
        return None

    additional_cas_user_fields, created = Z3_AdditionalCasUserFields.objects.update_or_create(
        user=user, defaults={"kayttajatyyppi": henkilo_kayttajatyyppi, "henkilo_oid": henkilo_oid, "toimintakieli_koodi": "fi"}
    )

    set_user_info_from_onr(additional_cas_user_fields)

    return henkilo_oid, henkilo_kayttajatyyppi


def set_user_info_from_onr(additional_cas_user_fields):
    """
    Get basic information for CAS-user from oppijanumerorekisteri-service, and update Z3_AdditionalCasUserFields
    :param additional_cas_user_fields: Z3_AdditionalCasUserFields instance
    """
    user = additional_cas_user_fields.user
    henkilo_oid = additional_cas_user_fields.henkilo_oid

    user_data = get_user_data(henkilo_oid)
    # sahkoposti field value can also be null, but null is not allowed for User.email field so default to empty string
    email = user_data.get("sahkoposti", "") or ""
    if user.email != email:
        user.email = email
        user.save()

    # toimintakieli_koodi is asiointikieli in ONR (term change OPHVARDA-2817)
    additional_cas_user_fields.toimintakieli_koodi = user_data.get("asiointikieli", "")
    additional_cas_user_fields.save()


def set_user_kayttooikeudet(henkilo_oid, user):
    from varda.tasks import update_oph_staff_to_vakajarjestaja_groups

    # Get current permissions
    permissions_by_organization_list = _get_organizations_and_perm_groups_of_user(henkilo_oid)

    # If user is still OPH-staff, let the permissions be as they are, and exit.
    is_oph_yllapitaja = False
    for permissions_by_organization in permissions_by_organization_list:
        organisaatio_oid = permissions_by_organization["organization_data"]["oid"]
        permissions = permissions_by_organization["permissions"]
        if organisaatio_oid == settings.OPETUSHALLITUS_ORGANISAATIO_OID and Z4_CasKayttoOikeudet.YLLAPITAJA in permissions:
            is_oph_yllapitaja = True
            break
    if is_oph_staff(user) and is_oph_yllapitaja:
        return None

    delete_all_user_permissions(user, delete_henkilo_permissions=False)

    # After removal, let's set the user permissions.
    for permissions_by_organization in permissions_by_organization_list:
        fetch_permissions_roles_for_organization(
            user.id, henkilo_oid, permissions_by_organization["organization_data"], permissions_by_organization["permissions"]
        )

    if is_oph_yllapitaja:
        update_oph_staff_to_vakajarjestaja_groups.delay(user_id=user.id)


def set_user_permissions(user, organisation, role):
    organization_oid = organisation["oid"]
    try:
        Z4_CasKayttoOikeudet.objects.create(user=user, organisaatio_oid=organization_oid, kayttooikeus=role)
    except IntegrityError:
        logger.warning("User with id: " + str(user.id) + " is hitting an IntegrityError.")
        return None  # Shouldn't ever come here unless several people are using the same credentials.

    organization_specific_permission_group = get_permission_group(role, organization_oid)
    if organization_specific_permission_group is not None:
        organization_specific_permission_group.user_set.add(user)  # Assign the user to this permission_group


def fetch_permissions_roles_for_organization(user_id, henkilo_oid, organisation, permission_group_list):
    user = User.objects.get(id=user_id)
    organization_oid = organisation["oid"]
    """
    User might have multiple of VARDA-permissions to one single organization. We take into account only the 'highest' permission the user has.
    Order from highest to lowest:
    - Z4_CasKayttoOikeudet.TALLENTAJA
    - Z4_CasKayttoOikeudet.KATSELIJA

    There is an exception to this rule: If organization is an 'integraatio-organisaatio',
    then the highest possible VARDA-permission for 'virkailija' is KATSELIJA.
    """
    role_vakatiedot = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.VAKATIEDOT,
        Z4_CasKayttoOikeudet.TALLENTAJA,
        Z4_CasKayttoOikeudet.KATSELIJA,
    )
    """
    User might have multiple of VARDA-permissions to one single organization. We take into account only the 'highest' permission the user has.
    Order from highest to lowest:
    - Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    - Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    There is an exception to this rule: If organization is an 'integraatio-organisaatio',
    then the highest possible VARDA-HUOLTAJA-permission for 'virkailija' is HUOLTAJATIEDOT_KATSELIJA.
    """
    role_huoltajatiedot = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.VAKATIEDOT,
        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
    )
    # Z4_CasKayttoOikeudet.PAAKAYTTAJA
    role_paakayttaja = select_highest_kayttooikeusrooli(
        permission_group_list, organization_oid, TietosisaltoRyhma.VAKATIEDOT, Z4_CasKayttoOikeudet.PAAKAYTTAJA
    )
    # Henkilosto
    role_tyontekija = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.TYONTEKIJATIEDOT,
        Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
    )

    role_taydennyskoulutus = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT,
        Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
    )

    role_vuokrattuhenkilosto = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.VUOKRATTUHENKILOSTOTIEDOT,
        Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_KATSELIJA,
    )

    role_tukipaatos = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.TUKIPAATOSTIEDOT,
        Z4_CasKayttoOikeudet.TUEN_TIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.TUEN_TIEDOT_KATSELIJA,
    )

    role_toimijatiedot = select_highest_kayttooikeusrooli(
        permission_group_list,
        organization_oid,
        TietosisaltoRyhma.TOIMIJATIEDOT,
        Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.TOIMIJATIEDOT_KATSELIJA,
    )

    role_raportit = select_highest_kayttooikeusrooli(
        permission_group_list, organization_oid, TietosisaltoRyhma.RAPORTIT, Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA
    )

    roles = [
        role_vakatiedot,
        role_huoltajatiedot,
        role_paakayttaja,
        role_tyontekija,
        role_taydennyskoulutus,
        role_vuokrattuhenkilosto,
        role_tukipaatos,
        role_toimijatiedot,
        role_raportit,
    ]

    # Check if user has VARDA-YLLAPITAJA permission
    if organization_oid == settings.OPETUSHALLITUS_ORGANISAATIO_OID and Z4_CasKayttoOikeudet.YLLAPITAJA in permission_group_list:
        roles.append(Z4_CasKayttoOikeudet.YLLAPITAJA)

    if all(role is None for role in roles):
        return None

    """
    We know the organization is either vakajarjestaja or vaka-toimipaikka,
    and user has some varda-permission role there.
    """
    try:
        create_organization_or_toimipaikka_if_needed(organisation)
    except (InvalidKoodiUriException, KeyError, StopIteration):
        logger.warning(
            "Organisaatio {0} creation failed for henkilo {1}. Skipping role creation.".format(organization_oid, henkilo_oid)
        )
        return None

    [set_user_permissions(user, organisation, role) for role in roles if role is not None]


def create_organization_or_toimipaikka_if_needed(organization):
    organisaatio_oid = organization["oid"]
    if organisaatio_client.is_of_type(organization, Organisaatiotyyppi.VAKAJARJESTAJA.value, Organisaatiotyyppi.MUU.value):
        if not Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid).exists():
            """
            Organization doesn't exist yet, let's create it.
            """
            organisaatiotyyppi = organisaatio_client.get_organization_type(organization)
            create_organization_using_oid(organisaatio_oid, organisaatiotyyppi)
    elif organisaatio_client.is_of_type(organization, Organisaatiotyyppi.TOIMIPAIKKA.value):
        if not Toimipaikka.objects.filter(organisaatio_oid=organisaatio_oid).exists():
            """
            Toimipaikka doesn't exist yet, let's create it.
            """
            create_toimipaikka_using_oid(organisaatio_oid)


def get_user_info(username):
    """
    Fetch henkilo_oid and kayttajaTyyppi, based on the username.
    """
    henkilo_url = "/henkilo/kayttajatunnus=" + username
    reply_msg = get_json_from_external_service(SERVICE_NAME, henkilo_url)
    if not reply_msg["is_ok"]:
        return get_reply_json(is_ok=False)

    reply_json = reply_msg["json_msg"]
    if "oid" not in reply_json or "kayttajaTyyppi" not in reply_json:
        logger.error("Missing info from /" + SERVICE_NAME + henkilo_url + " reply.")
        return get_reply_json(is_ok=False)

    henkilo_oid = reply_json["oid"]
    henkilo_kayttajatyyppi = reply_json["kayttajaTyyppi"]

    if henkilo_kayttajatyyppi:
        json_msg = {"henkilo_oid": henkilo_oid, "henkilo_kayttajatyyppi": henkilo_kayttajatyyppi}
        return get_reply_json(is_ok=True, json_msg=json_msg)  # kayttajatyyppi can be e.g. VIRKAILIJA, OPPIJA, '', ...
    else:
        return get_reply_json(is_ok=False)


def select_highest_kayttooikeusrooli(kayttooikeusrooli_list, organization_oid, tietosisalto_ryhma, *args):
    """
    Select highest role from user permissions and provided list. In case of integraatio_organisaatio selects lowest one.
    :param tietosisalto_ryhma: integraatio_organisaatio group which should be considered for read only user
    :type tietosisalto_ryhma: TietosisaltoRyhma
    :param kayttooikeusrooli_list: Roles user has
    :param organization_oid: Oid of organisation in order to make sure it's not (under) integration organisation
    :param args: Roles in order from highest to lowest
    :return: Most valuable kayttooikeus role user has or None
    """
    vakajarjestaja_obj = None

    try:
        vakajarjestaja_obj = Organisaatio.objects.get(organisaatio_oid=organization_oid)
    except Organisaatio.DoesNotExist:
        try:
            toimipaikka_obj = Toimipaikka.objects.get(organisaatio_oid=organization_oid)
            vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        except Toimipaikka.DoesNotExist:
            pass

    # Give integraatio organisaatio always the lowest privilege.
    if (
        vakajarjestaja_obj
        and tietosisalto_ryhma.value in vakajarjestaja_obj.integraatio_organisaatio
        and any(role in kayttooikeusrooli_list for role in args)
    ):
        # Lowest priority should be katselija
        return args[-1]

    return next(iter([role for role in args if role in kayttooikeusrooli_list]), None)


def _get_organizations_and_perm_groups_of_user(henkilo_oid):
    """
    Fetch user permissions and organisation data for organisations user has permissions to. Exclude organizations and
    permissions not related to Varda.
    :param henkilo_oid: user henkilo oid
    :return: [{organization_data: {}, permissions: []}, {...}]
    """
    permissions_by_organization_list = _get_permissions_by_organization(henkilo_oid)
    if permissions_by_organization_list is None:
        logger.error(f"Could not get user permissions for OID {henkilo_oid}")
        return []

    organisaatio_oid_list = []
    permissions_by_organisaatio_oid = {}
    for permissions_by_organization in permissions_by_organization_list:
        organisaatio_oid = permissions_by_organization["organisaatioOid"]
        # Exclude permissions not related to Varda
        permissions = [
            permission["oikeus"]
            for permission in permissions_by_organization["kayttooikeudet"]
            if permission["palvelu"] == "VARDA"
        ]
        if len(permissions) > 0:
            organisaatio_oid_list.append(organisaatio_oid)
            permissions_by_organisaatio_oid[organisaatio_oid] = permissions

    organization_data_list = organisaatio_client.get_multiple_organisaatio(organisaatio_oid_list)
    data_by_organisaatio_oid = {
        organization_data["oid"]: organization_data
        for organization_data in organization_data_list
        if organisaatio_client.is_valid_organization(organization_data)
    }

    return [
        {"organization_data": organization_data, "permissions": permissions_by_organisaatio_oid[organisaatio_oid]}
        for organisaatio_oid, organization_data in data_by_organisaatio_oid.items()
    ]


def _get_permissions_by_organization(henkilo_oid):
    url = f"/kayttooikeus/kayttaja?oidHenkilo={henkilo_oid}"
    result = get_json_from_external_service(SERVICE_NAME, url)
    if not result["is_ok"]:
        return None

    result_msg = result.get("json_msg", [])
    first_user = next(iter(result_msg), {})
    return first_user.get("organisaatiot", [])


def set_service_user_permissions(user, henkilo_oid):
    # Get current permissions from Käyttöoikeuspalvelu, delete existing permissions in any case (error or success)
    try:
        if not henkilo_oid:
            logger.error(f"Service user with id: {user.id} does not have an OID.")
            return None
        permissions_by_organization_list = _get_organizations_and_perm_groups_of_user(henkilo_oid)
    except Exception as exception:
        raise exception
    finally:
        # Delete existing permissions after getting current ones, so that time without any permissions is short
        # Service users can use multiple simultaneous instances, so we want user to have permissions at all times
        delete_all_user_permissions(user, delete_henkilo_permissions=False)

    if len(permissions_by_organization_list) != 1:
        # Decline access to Varda if the service user doesn't have correct permissions to VARDA-service
        # in one active organization.
        raise AuthenticationFailed({"errors": [ErrorMessages.PE008.value]})

    organization_data = permissions_by_organization_list[0]["organization_data"]
    permissions = permissions_by_organization_list[0]["permissions"]

    if not organisaatio_client.is_of_type(
        organization_data, Organisaatiotyyppi.VAKAJARJESTAJA.value, Organisaatiotyyppi.MUU.value
    ):
        logger.error(f"Service user with id: {user.id} does not have permissions to a top level organization.")
        return None

    permissions = _exclude_non_valid_permissions(permissions)
    organisaatio_oid = organization_data["oid"]

    _create_or_update_organization_for_service_user(permissions, organization_data, user)
    for permission in permissions:
        organization_specific_permission_group = get_permission_group(permission, organisaatio_oid)
        if organization_specific_permission_group is not None:
            # Assign the user to this permission group
            organization_specific_permission_group.user_set.add(user)


def _exclude_non_valid_permissions(permission_list):
    accepted_service_user_permissions = (
        Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
        Z4_CasKayttoOikeudet.TALLENTAJA,
        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
        Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_TALLENTAJA,
        Z4_CasKayttoOikeudet.TUEN_TIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA,
        Z4_CasKayttoOikeudet.LUOVUTUSPALVELU,
    )
    return [permission for permission in permission_list if permission in accepted_service_user_permissions]


def _create_or_update_organization_for_service_user(permission_list, organization_data, user):
    """
    Creates vakajarjestaja if one does not exist yet. Marks vakajarjestaja integraatio organisaatio if needed.
    :param permission_list: List of permission strings user has for accessing varda
    :param organization_data: Oid of the vakajarjestaja user has permissions to
    :param user: user logging in
    """
    # Having any of these permissions means that it is allowed to transfer that data only via integration
    integraatio_permissions = {
        Z4_CasKayttoOikeudet.PALVELUKAYTTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.TALLENTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA: TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA: TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_VUOKRATTU_TALLENTAJA: TietosisaltoRyhma.VUOKRATTUHENKILOSTOTIEDOT.value,
        Z4_CasKayttoOikeudet.TUEN_TIEDOT_TALLENTAJA: TietosisaltoRyhma.TUKIPAATOSTIEDOT.value,
        Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA: TietosisaltoRyhma.TOIMIJATIEDOT.value,
    }

    organisaatio_oid = organization_data["oid"]
    for permission in permission_list:
        k, created = Z4_CasKayttoOikeudet.objects.get_or_create(
            user=user, organisaatio_oid=organisaatio_oid, kayttooikeus=permission
        )
        if not created:
            logger.info(f"Already had permission {permission} for user: {user.username}, organisaatio_oid: {organisaatio_oid}")
    vakajarjestaja_obj = Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid).first()
    integration_flags_set = {
        integraatio_permissions.get(permission) for permission in permission_list if permission in integraatio_permissions
    }
    if vakajarjestaja_obj:
        # There is only one vakajarjestaja, organisaatio_oid is unique
        existing_integration_flags_set = set(vakajarjestaja_obj.integraatio_organisaatio)
        if not integration_flags_set.issubset(existing_integration_flags_set):
            # User has new permissions, so add integraatio flags for Vakajarjestaja
            vakajarjestaja_obj.integraatio_organisaatio = tuple(existing_integration_flags_set.union(integration_flags_set))
            vakajarjestaja_obj.save()
    else:
        # Organisaatio doesn't exist yet, let's create it.
        organisaatiotyyppi = organisaatio_client.get_organization_type(organization_data)
        create_organization_using_oid(organisaatio_oid, organisaatiotyyppi, integraatio_organisaatio=tuple(integration_flags_set))


@transaction.atomic
def set_active_groups_for_user(user, organisaatio_obj=None):
    """
    Modify User's permission groups so that User only has active permissions to one organization at a time.
    :param user: User object
    :param organisaatio_obj: Organisaatio object
    """
    if user.is_superuser or is_oph_staff(user):
        # Skip for admin and OPH users
        return None

    if not (cas_fields := user.additional_cas_user_fields):
        logger.error(f"User with ID {user.id} is missing related Z3_AdditionalCasUserFields object.")
        return None

    if cas_fields.all_groups.count() == 0:
        # all_groups has not been set yet, initialize groups
        cas_fields.all_groups.set(user.groups.all())

    organisaatio_qs = get_related_organisaatio_for_user(user, groups=cas_fields.all_groups)
    if organisaatio_qs.count() == 1:
        # User only has permissions to a single Organisaatio, no need to reset permission groups
        return None

    # Set default Organisaatio if one was not provided
    organisaatio_obj = organisaatio_obj or organisaatio_qs.first()
    if not organisaatio_obj:
        # Most likely user has tried to log in to Varda without any permissions to Varda
        logger.warning(f"Could not determine Organisaatio for User with ID {user.id}")
        return None

    group_filter = Q(name__endswith=organisaatio_obj.organisaatio_oid)
    toimipaikka_oid_list = (
        Toimipaikka.objects.filter(vakajarjestaja=organisaatio_obj)
        .exclude(organisaatio_oid="")
        .values_list("organisaatio_oid", flat=True)
    )
    for organisaatio_oid in toimipaikka_oid_list:
        group_filter |= Q(name__endswith=organisaatio_oid)

    # Get all permission groups that are related to selected or default Organisaatio and set them as active groups
    group_qs = cas_fields.all_groups.filter(group_filter)
    user.groups.set(group_qs)
    delete_object_ids_user_has_permissions(user.id)


def get_all_paakayttaja_users():
    """
    Get VARDA-PAAKAYTTAJA users and respective Organisaatio IDs
    :return: {'henkilo_oid': set(1, 2)} User with OID 'henkilo_oid' is VARDA-PAAKAYTTAJA in Organisaatio IDs 1 and 2
    if request is successful, else None
    """
    henkilo_oid_organisaatio_dict = {}

    # We can get 1000 users per request so continue fetching until empty list is returned
    # With offset = 0 we fetch items 0-999, offset = 1000 -> items 1000 - 1999 etc.
    chunk_size = 1000
    offset = 0
    while True:
        """
        Example response:
        [
            {
                "oidHenkilo": "1.2.246.562.24.10067105747",
                "username": "Testitestaaja_kouvola",
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": "1.2.246.562.10.16568914952",
                        "kayttooikeudet": [
                            {
                                "palvelu": "VARDA",
                                "oikeus": "VARDA-PAAKAYTTAJA"
                            },
                            {
                                "palvelu": "VARDA",
                                "oikeus": "HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA"
                            }
                        ]
                    },
                    {
                        "organisaatioOid": "1.2.246.562.10.88962782699",
                        "kayttooikeudet": [
                            {
                                "palvelu": "VARDA",
                                "oikeus": "VARDA-TALLENTAJA"
                            }
                        ]
                    }
                ]
            }
        ]
        """
        response = get_json_from_external_service(
            SERVICE_NAME, f"/kayttooikeus/kayttaja?palvelu=VARDA&offset={offset}", large_query=True
        )
        response_body = response["json_msg"]
        if not response["is_ok"]:
            logger.error(f"Could not get user permissions from kayttooikeus-service: {response_body}")
            return None

        for user_data in response_body:
            henkilo_oid = user_data["oidHenkilo"]
            for organisaatio in user_data["organisaatiot"]:
                organisaatio_qs = Organisaatio.vakajarjestajat.filter(organisaatio_oid=organisaatio["organisaatioOid"])
                for permission in organisaatio["kayttooikeudet"]:
                    if (
                        permission["palvelu"] == "VARDA"
                        and permission["oikeus"] == Z4_CasKayttoOikeudet.PAAKAYTTAJA
                        and (organisaatio_obj := organisaatio_qs.first())
                    ):
                        # User has VARDA-PAAKAYTTAJA permission in Organisaatio that exists in Varda
                        organisaatio_set = henkilo_oid_organisaatio_dict.get(henkilo_oid, set())
                        organisaatio_set.add(organisaatio_obj.id)
                        henkilo_oid_organisaatio_dict[henkilo_oid] = organisaatio_set

        if len(response_body) < chunk_size:
            # There were fewer results than chunk_size, fetch is complete
            break

        offset += chunk_size

    return henkilo_oid_organisaatio_dict


def get_paakayttaja_users_with_yhteystieto_data():
    henkilo_oid_organisaatio_dict = get_all_paakayttaja_users()
    if henkilo_oid_organisaatio_dict is None:
        # Error getting VARDA-PAAKAYTTAJA users
        return None

    # Form a list of henkilo_oid values
    henkilo_oid_list = [henkilo_oid for henkilo_oid in henkilo_oid_organisaatio_dict]

    # All users fetched, fetch email addresses
    yhteystieto_data_dict = fetch_yhteystieto_data_for_henkilo_oid_list(henkilo_oid_list)
    if yhteystieto_data_dict is None:
        # Error fetching yhteystieto data
        return None

    user_data_list = []
    for henkilo_oid, yhteystieto_data in yhteystieto_data_dict.items():
        user_data_list.append(
            {
                "henkilo_oid": henkilo_oid,
                "yhteystieto_data": yhteystieto_data,
                "organisaatio_id_set": henkilo_oid_organisaatio_dict[henkilo_oid],
            }
        )

    return user_data_list
