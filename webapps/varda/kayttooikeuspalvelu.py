import logging

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError
from django.db.models import Q
from guardian.models import UserObjectPermission
from rest_framework.exceptions import AuthenticationFailed

from varda.cache import delete_cached_user_permissions_for_model
from varda.clients import organisaatio_client
from varda.clients.organisaatio_client import is_not_valid_vaka_organization_in_organisaatiopalvelu
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.tietosisalto_ryhma import TietosisaltoRyhma
from varda.exceptions.invalid_koodi_uri_exception import InvalidKoodiUriException
from varda.misc import get_json_from_external_service, get_reply_json
from varda.models import Toimipaikka, VakaJarjestaja, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, LoginCertificate
from varda.organisaatiopalvelu import create_toimipaikka_using_oid, create_vakajarjestaja_using_oid
from varda.permission_groups import get_permission_group


logger = logging.getLogger(__name__)
SERVICE_NAME = 'kayttooikeus-service'


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
        set_service_user_permissions(user, henkilo_oid=henkilo_oid)
    else:
        set_user_kayttooikeudet(henkilo_oid, user)


def set_user_info_for_cas_user(user):
    """
    Get basic information for CAS-user from kayttooikeus-service
    :param user: User instance
    :return: User henkilo_oid
    """
    user_info = get_user_info(user.username)
    if user_info['is_ok']:
        henkilo_oid = user_info['json_msg']['henkilo_oid']
        henkilo_kayttajatyyppi = user_info['json_msg']['henkilo_kayttajatyyppi']
    else:
        # not ok
        return None

    additional_cas_user_fields, created = Z3_AdditionalCasUserFields.objects.update_or_create(
        user=user,
        defaults={
            'kayttajatyyppi': henkilo_kayttajatyyppi,
            'henkilo_oid': henkilo_oid,
            'asiointikieli_koodi': 'fi'
        })

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
    email = user_data.get('sahkoposti', '')
    if user.email != email:
        user.email = email
        user.save()

    additional_cas_user_fields.asiointikieli_koodi = user_data.get('asiointikieli', '')
    additional_cas_user_fields.save()


def set_user_kayttooikeudet(henkilo_oid, user):
    """
    Clear vakajarjestaja-ui cache.
    """
    model_name = 'vakajarjestaja'
    delete_cached_user_permissions_for_model(user.id, model_name)

    """
    If user is OPH-staff, let the permissions be as they are, and exit.
    """
    additional_details = getattr(user, 'additional_cas_user_fields', None)
    if getattr(additional_details, 'approved_oph_staff', False):
        return None

    """
    We need to delete the 'kayttooikeus' groups first (there might be removed access rights).
    Delete + creation is not handled in one atomic-transaction since it involves
    multiple queries to other systems, and this might leave transactions open for too long time.
    These DB-actions are not viewed as critical, since if something goes wrong here, the next
    login should already fix the possible problem.
    """
    Z4_CasKayttoOikeudet.objects.filter(user=user).delete()
    user.groups.clear()  # Remove the permission_groups from user. TODO: If there will be other groups also, then delete only the permission-groups here.

    """
    Also, remove the possible vakajarjestaja-object level permissions from user. These are
    special-permissions given to Toimipaikka-permission level user. See more info below.
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    filters = Q(content_type=ContentType.objects.get_for_model(VakaJarjestaja), user_id=user.id)
    UserObjectPermission.objects.filter(filters).delete()

    """
    After removal, let's set the user permissions.
    """
    user_organisation_permission_and_data_list = _get_organizations_and_perm_groups_of_user(henkilo_oid, user)
    for permission_group_list, organisation_data in user_organisation_permission_and_data_list:
        varda_permissions = [perm['oikeus'] for perm in permission_group_list if perm['palvelu'] == 'VARDA']
        fetch_permissions_roles_for_organization(user.id, henkilo_oid, organisation_data, varda_permissions)


def set_user_permissions(user, organisation, role):
    organization_oid = organisation['oid']
    try:
        Z4_CasKayttoOikeudet.objects.create(user=user, organisaatio_oid=organization_oid, kayttooikeus=role)
    except IntegrityError:
        logger.warning('User with id: ' + str(user.id) + ' is hitting an IntegrityError.')
        return None  # Shouldn't ever come here unless several people are using the same credentials.

    organization_specific_permission_group = get_permission_group(role, organization_oid)
    if organization_specific_permission_group is not None:
        organization_specific_permission_group.user_set.add(user)  # Assign the user to this permission_group


def fetch_permissions_roles_for_organization(user_id, henkilo_oid, organisation, permission_group_list):
    user = User.objects.get(id=user_id)
    organization_oid = organisation['oid']
    """
    User might have multiple of VARDA-permissions to one single organization. We take into account only the 'highest' permission the user has.
    Order from highest to lowest:
    - Z4_CasKayttoOikeudet.TALLENTAJA
    - Z4_CasKayttoOikeudet.KATSELIJA

    There is an exception to this rule: If organization is an 'integraatio-organisaatio',
    then the highest possible VARDA-permission for 'virkailija' is KATSELIJA.
    """
    role_vakatiedot = select_highest_kayttooikeusrooli(permission_group_list,
                                                       organization_oid,
                                                       TietosisaltoRyhma.VAKATIEDOT,
                                                       Z4_CasKayttoOikeudet.TALLENTAJA,
                                                       Z4_CasKayttoOikeudet.KATSELIJA)
    """
    User might have multiple of VARDA-permissions to one single organization. We take into account only the 'highest' permission the user has.
    Order from highest to lowest:
    - Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
    - Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA

    There is an exception to this rule: If organization is an 'integraatio-organisaatio',
    then the highest possible VARDA-HUOLTAJA-permission for 'virkailija' is HUOLTAJATIEDOT_KATSELIJA.
    """
    role_huoltajatiedot = select_highest_kayttooikeusrooli(permission_group_list,
                                                           organization_oid,
                                                           TietosisaltoRyhma.VAKATIEDOT,
                                                           Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
                                                           Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA)
    # Z4_CasKayttoOikeudet.PAAKAYTTAJA
    role_paakayttaja = select_highest_kayttooikeusrooli(permission_group_list,
                                                        organization_oid,
                                                        TietosisaltoRyhma.VAKATIEDOT,
                                                        Z4_CasKayttoOikeudet.PAAKAYTTAJA)
    # Henkilosto
    role_tyontekija = select_highest_kayttooikeusrooli(permission_group_list,
                                                       organization_oid,
                                                       TietosisaltoRyhma.TYONTEKIJATIEDOT,
                                                       Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                                       Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA)

    role_taydennyskoulutus = select_highest_kayttooikeusrooli(permission_group_list,
                                                              organization_oid,
                                                              TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT,
                                                              Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                                                              Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA)

    role_tilapainenhenkilosto = select_highest_kayttooikeusrooli(permission_group_list,
                                                                 organization_oid,
                                                                 TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT,
                                                                 Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA,
                                                                 Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_KATSELIJA)

    role_toimijatiedot = select_highest_kayttooikeusrooli(permission_group_list,
                                                          organization_oid,
                                                          TietosisaltoRyhma.TOIMIJATIEDOT,
                                                          Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA,
                                                          Z4_CasKayttoOikeudet.TOIMIJATIEDOT_KATSELIJA)

    role_raportit = select_highest_kayttooikeusrooli(permission_group_list,
                                                     organization_oid,
                                                     TietosisaltoRyhma.RAPORTIT,
                                                     Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA)

    roles = [role_vakatiedot, role_huoltajatiedot, role_paakayttaja, role_tyontekija, role_taydennyskoulutus,
             role_tilapainenhenkilosto, role_toimijatiedot, role_raportit]
    if all(role is None for role in roles):
        return None

    """
    We know the organization is either vakajarjestaja or vaka-toimipaikka,
    and user has some varda-permission role there.
    """
    try:
        organization_type_vakajarjestaja = organisaatio_client.is_vakajarjestaja(organisation)
        create_vakajarjestaja_or_toimipaikka_if_needed(organization_type_vakajarjestaja, organization_oid, user.id)
    except (InvalidKoodiUriException, KeyError, StopIteration):
        logger.warning('Organisaatio {0} creation failed for henkilo {1}. Skipping role creation.'
                       .format(organization_oid, henkilo_oid))
        return None

    [set_user_permissions(user, organisation, role) for role in roles if role is not None]


def create_vakajarjestaja_or_toimipaikka_if_needed(organization_type_vakajarjestaja, organization_oid, user_id):
    if organization_type_vakajarjestaja:
        if not VakaJarjestaja.objects.filter(organisaatio_oid=organization_oid).exists():
            """
            VakaJarjestaja doesn't exist yet, let's create it.
            """
            create_vakajarjestaja_using_oid(organization_oid, user_id)
    else:  # organization_type is 'vakatoimipaikka'
        if not Toimipaikka.objects.filter(organisaatio_oid=organization_oid).exists():
            """
            Toimipaikka doesn't exist yet, let's create it.
            """
            create_toimipaikka_using_oid(organization_oid, user_id)


def get_user_data(henkilo_oid):
    service_name = 'oppijanumerorekisteri-service'
    henkilo_url = '/henkilo/' + henkilo_oid
    DEFAULT_ASIOINTIKIELI = 'fi'
    user_data = {'asiointikieli': DEFAULT_ASIOINTIKIELI, 'sahkoposti': ''}

    reply_msg = get_json_from_external_service(service_name, henkilo_url)
    if not reply_msg['is_ok']:
        return user_data

    reply_json = reply_msg['json_msg']

    if 'asiointiKieli' not in reply_json:
        logger.error('Missing info from /' + service_name + henkilo_url + ' reply.')
    elif reply_json['asiointiKieli'] is None or 'kieliKoodi' not in reply_json['asiointiKieli'] or reply_json['asiointiKieli']['kieliKoodi'] is None:
        pass
    else:
        user_data['asiointikieli'] = reply_json['asiointiKieli']['kieliKoodi']

    user_data['sahkoposti'] = get_user_sahkoposti(reply_json)
    return user_data


def get_user_sahkoposti(reply_json):
    if 'yhteystiedotRyhma' not in reply_json or len(reply_json['yhteystiedotRyhma']) == 0 or 'yhteystieto' not in reply_json['yhteystiedotRyhma'][0]:
        return ''

    yhteystiedot = reply_json['yhteystiedotRyhma'][0]['yhteystieto']
    for yhteystieto in yhteystiedot:
        if 'yhteystietoTyyppi' in yhteystieto and yhteystieto['yhteystietoTyyppi'] == 'YHTEYSTIETO_SAHKOPOSTI':
            sahkoposti = yhteystieto['yhteystietoArvo']
            if sahkoposti is not None:
                return sahkoposti

    return ''


def get_user_info(username):
    """
    Fetch henkilo_oid and kayttajaTyyppi, based on the username.
    """
    henkilo_url = '/henkilo/kayttajatunnus=' + username
    reply_msg = get_json_from_external_service(SERVICE_NAME, henkilo_url)
    if not reply_msg['is_ok']:
        return get_reply_json(is_ok=False)

    reply_json = reply_msg['json_msg']
    if 'oid' not in reply_json or 'kayttajaTyyppi' not in reply_json:
        logger.error('Missing info from /' + SERVICE_NAME + henkilo_url + ' reply.')
        return get_reply_json(is_ok=False)

    henkilo_oid = reply_json['oid']
    henkilo_kayttajatyyppi = reply_json['kayttajaTyyppi']

    if henkilo_kayttajatyyppi:
        json_msg = {'henkilo_oid': henkilo_oid, 'henkilo_kayttajatyyppi': henkilo_kayttajatyyppi}
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
        vakajarjestaja_obj = VakaJarjestaja.objects.get(organisaatio_oid=organization_oid)
    except VakaJarjestaja.DoesNotExist:
        try:
            toimipaikka_obj = Toimipaikka.objects.get(organisaatio_oid=organization_oid)
            vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        except Toimipaikka.DoesNotExist:
            pass

    # Give integraatio organisaatio always the lowest privilege.
    if (vakajarjestaja_obj and
            tietosisalto_ryhma.value in vakajarjestaja_obj.integraatio_organisaatio and
            any(role in kayttooikeusrooli_list for role in args)):
        # Lowest priority should be katselija
        return args[-1]

    return next(iter([role for role in args if role in kayttooikeusrooli_list]), None)


def _get_organizations_and_perm_groups_of_user(henkilo_oid, user):
    """
    Fetch user permissions and organisation data for organisations user har permissions
    :param henkilo_oid: user henkilo oid
    :param user: local user object
    :return: tuple(list(kayttooikeudet), dict(organisaatio_data))
    """
    organisaatio_kayttooikeudet = _get_permissions_by_organization(henkilo_oid)
    if organisaatio_kayttooikeudet is None:
        # Error while getting permissions
        return {}, {}

    kayttooikeudet_by_organisaatio_oid = [user_info for user_info in organisaatio_kayttooikeudet if len(user_info['kayttooikeudet']) > 0]
    organisaatio_oids = [user_info['organisaatioOid'] for user_info in kayttooikeudet_by_organisaatio_oid]
    organisations = organisaatio_client.get_multiple_organisaatio(organisaatio_oids)
    valid_organisation_oids = [org['oid'] for org in organisations if organisaatio_client.is_valid_vaka_organization(org)]
    organisation_data_dict = {org['oid']: org for org in organisations}
    if settings.OPETUSHALLITUS_ORGANISAATIO_OID in organisaatio_oids:
        oph_staff_group = Group.objects.get(name='oph_staff')
        oph_staff_group.user_set.add(user)

    return ((kayttooikeus['kayttooikeudet'], organisation_data_dict[organisaatio_oid])
            for kayttooikeus
            in kayttooikeudet_by_organisaatio_oid
            if (organisaatio_oid := kayttooikeus['organisaatioOid']) in valid_organisation_oids
            )


def _get_permissions_by_organization(henkilo_oid):
    url = f'/kayttooikeus/kayttaja?oidHenkilo={henkilo_oid}'
    result = get_json_from_external_service(SERVICE_NAME, url)
    if not result['is_ok']:
        return None

    result_msg = result.get('json_msg', [])
    first_user = next(iter(result_msg), {})
    return first_user.get('organisaatiot', [])


def set_service_user_permissions(user, permissions_by_organization=None, henkilo_oid=None):
    if permissions_by_organization is None:
        # Coming from CAS login
        if henkilo_oid:
            permissions_by_organization = _get_permissions_by_organization(henkilo_oid)
            if permissions_by_organization is None:
                # Error while getting permissions
                return
        else:
            logger.error(f'Service user with id: {user.id}, does not have an OID.')
            return

    # Delete old permissions as some of them may have been removed
    Z4_CasKayttoOikeudet.objects.filter(user=user).delete()

    valid_permissions_by_organization = _exclude_non_valid_permissions(permissions_by_organization)

    if len(valid_permissions_by_organization) == 1:
        # PALVELUKAYTTAJA should have permissions only to one organization.
        organization = valid_permissions_by_organization[0]
        organisaatio_oid = organization['organisaatioOid']
        permission_list = [permission['oikeus'] for permission in organization['kayttooikeudet']]
        _create_or_update_vakajarjestaja(permission_list, organisaatio_oid, user)

        # Clear user's permission groups
        user.groups.clear()
        for permission in permission_list:
            organization_specific_permission_group = get_permission_group(permission, organisaatio_oid)
            if organization_specific_permission_group is not None:
                # Assign the user to this permission group
                organization_specific_permission_group.user_set.add(user)
    else:
        # Decline access to Varda if the service user doesn't have correct permissions to VARDA-service
        # in one active vaka-organization.
        raise AuthenticationFailed({'errors': [ErrorMessages.PE008.value]})


def _exclude_non_valid_permissions(permissions_by_organization):
    accepted_service_user_permissions = (Z4_CasKayttoOikeudet.PALVELUKAYTTAJA, Z4_CasKayttoOikeudet.TALLENTAJA,
                                         Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
                                         Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                         Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                                         Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA,
                                         Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA,)
    for organization in permissions_by_organization:
        # Filter out permissions we are not interested in
        organization['kayttooikeudet'] = [permission for permission in organization['kayttooikeudet']
                                          if permission['palvelu'] == 'VARDA' and
                                          (permission['oikeus'] in accepted_service_user_permissions or
                                           _is_opetushallitus_accepted_permission(organization['organisaatioOid'],
                                                                                  permission['oikeus']))]
    valid_permissions_by_organization = [organization for organization in permissions_by_organization
                                         if organization['kayttooikeudet'] and
                                         not is_not_valid_vaka_organization_in_organisaatiopalvelu(organization['organisaatioOid'],
                                                                                                   must_be_vakajarjestaja=True)]
    return valid_permissions_by_organization


def _is_opetushallitus_accepted_permission(organisaatio_oid, permission_group_name):
    return (organisaatio_oid == settings.OPETUSHALLITUS_ORGANISAATIO_OID and
            permission_group_name == Z4_CasKayttoOikeudet.LUOVUTUSPALVELU)


def _create_or_update_vakajarjestaja(permission_list, organisaatio_oid, user):
    """
    Creates vakajarjestaja if one does not exist yet. Marks vakajarjestaja integraatio organisaatio if needed.
    :param permission_list: List of permission strings user has for accessing varda
    :param organisaatio_oid: Oid of the vakajarjestaja user has permissions to
    :param user: user logging in
    """
    # Having any of these permissions means that it is allowed to transfer that data only via integration
    integraatio_permissions = {
        Z4_CasKayttoOikeudet.PALVELUKAYTTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.TALLENTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA: TietosisaltoRyhma.VAKATIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA: TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA: TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
        Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA: TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT.value,
        Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA: TietosisaltoRyhma.TOIMIJATIEDOT.value
    }

    for permission in permission_list:
        k, created = Z4_CasKayttoOikeudet.objects.get_or_create(user=user, organisaatio_oid=organisaatio_oid,
                                                                kayttooikeus=permission)
        if not created:
            logger.info('Already had permission {} for user: {}, organisaatio_oid: {}'
                        .format(permission, user.username, organisaatio_oid))
    vakajarjestaja_obj = VakaJarjestaja.objects.filter(organisaatio_oid=organisaatio_oid).first()
    integration_flags_set = {integraatio_permissions.get(permission) for permission in permission_list
                             if permission in integraatio_permissions}
    if vakajarjestaja_obj:
        # There is only one vakajarjestaja, organisaatio_oid is unique
        existing_integration_flags_set = set(vakajarjestaja_obj.integraatio_organisaatio)
        if not integration_flags_set.issubset(existing_integration_flags_set):
            # User has new permissions, so add integraatio flags for Vakajarjestaja
            vakajarjestaja_obj.integraatio_organisaatio = tuple(existing_integration_flags_set.union(integration_flags_set))
            vakajarjestaja_obj.save()
    else:
        # VakaJarjestaja doesn't exist yet, let's create it.
        create_vakajarjestaja_using_oid(organisaatio_oid, user.id, integraatio_organisaatio=tuple(integration_flags_set))
