import logging
from functools import wraps

from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, IntegrityError
from django.db.models import IntegerField, Q, Model, QuerySet
from django.db.models.functions import Cast
from django.forms import model_to_dict
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.misc import path_parse, single_instance_task
from varda.misc_queries import (get_lapsi_for_maksutieto, get_organisaatio_oid_for_taydennyskoulutus,
                                get_tallentaja_organisaatio_oid_for_paos_lapsi)
from varda.models import (Henkilo, Organisaatio, Taydennyskoulutus, Toimipaikka, Lapsi, Tutkinto, Varhaiskasvatussuhde,
                          PaosToiminta, PaosOikeus, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Z5_AuditLog,
                          LoginCertificate, Maksutieto, Tyontekija, Tyoskentelypaikka, TaydennyskoulutusTyontekija)
from varda.permission_groups import get_oph_yllapitaja_group_name


logger = logging.getLogger(__name__)


VAKA_GROUPS = (Z4_CasKayttoOikeudet.PAAKAYTTAJA, Z4_CasKayttoOikeudet.PALVELUKAYTTAJA, Z4_CasKayttoOikeudet.KATSELIJA,
               Z4_CasKayttoOikeudet.TALLENTAJA, Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
               Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,)
VAKA_LAPSI_GROUPS = (Z4_CasKayttoOikeudet.PAAKAYTTAJA, Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                     Z4_CasKayttoOikeudet.KATSELIJA, Z4_CasKayttoOikeudet.TALLENTAJA,)
HENKILOSTO_GROUPS = (Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_KATSELIJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA)
TYONTEKIJA_GROUPS = (Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
                     Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,)
GENERAL_GROUPS = (Z4_CasKayttoOikeudet.TOIMIJATIEDOT_KATSELIJA, Z4_CasKayttoOikeudet.TOIMIJATIEDOT_TALLENTAJA,
                  Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA, Z4_CasKayttoOikeudet.LUOVUTUSPALVELU,
                  Z4_CasKayttoOikeudet.YLLAPITAJA)


# https://github.com/rpkilby/django-rest-framework-guardian
class CustomModelPermissions(permissions.DjangoModelPermissions):
    """
    Similar to `DjangoModelPermissions`, but adding 'view' permissions.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }


class CustomObjectPermissions(permissions.DjangoObjectPermissions):
    """
    Similar to `DjangoObjectPermissions`, but adding 'view' permissions.
    """
    perms_map = {
        'GET': ['%(app_label)s.view_%(model_name)s'],
        'OPTIONS': ['%(app_label)s.view_%(model_name)s'],
        'HEAD': ['%(app_label)s.view_%(model_name)s'],
        'POST': ['%(app_label)s.add_%(model_name)s'],
        'PUT': ['%(app_label)s.change_%(model_name)s'],
        'PATCH': ['%(app_label)s.change_%(model_name)s'],
        'DELETE': ['%(app_label)s.delete_%(model_name)s'],
    }

    def has_object_permission(self, request, view, obj):
        if not isinstance(obj, Model):
            # Object permissions are checked again in Django REST browserable API, sometimes object is not a Model
            # instance anymore (e.g. NestedLapsiKoosteViewSet, NestedVakajarjestajaYhteenvetoViewSet),
            # so don't check permissions
            return True
        return super(CustomObjectPermissions, self).has_object_permission(request, view, obj)


class IsCertificateAccess(permissions.IsAdminUser):
    """
    Allow access to reporting apis for users requiring data. Nginx validates client certificate here.
    """

    def has_permission(self, request, view):
        user = request.user
        if super().has_permission(request, view):
            return True
        return _user_has_certificate_access(user, request)


class ReadAdminOrOPHUser(permissions.BasePermission):
    """
    Allows access to admin and OPH users.
    Only for GET functions
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(request.user and request.method == 'GET' and (user.is_superuser or is_oph_staff(user)))


class AdminOrOPHUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and (request.user.is_superuser or is_oph_staff(request.user))


class LapsihakuPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        accepted_permissions = ['view_lapsi', 'view_maksutieto']
        return _is_user_group_permissions(accepted_permissions, user)


class HenkilostohakuPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        accepted_permissions = ['view_tyontekija', 'view_taydennyskoulutus']
        return _is_user_group_permissions(accepted_permissions, user)


class ToimipaikkaPermissions(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        accepted_permissions = ['view_toimipaikka']
        return _is_user_group_permissions(accepted_permissions, user)


class RaportitPermissions(permissions.BasePermission):
    """
    Allows access to admin, OPH users, and users who belong to a VARDA_RAPORTTIEN_KATSELIJA group
    """

    def has_permission(self, request, view):
        user = request.user

        return (user.is_superuser or
                is_oph_staff(user) or
                user.groups.filter(name__startswith=Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA).exists())


def _is_user_group_permissions(accepted_permissions, user):
    return user.is_superuser or user.groups.filter(permissions__codename__in=accepted_permissions).exists()


def _user_has_certificate_access(user, request):
    """
    Check required permission group and certificate authentication headers provided by nginx for request path.
    :param user: user object
    :param request: request
    :return: Has user certificate access to current api
    """
    if isinstance(user, AnonymousUser):
        # No permissions for AnonymousUser (used by Swagger)
        return False

    is_cert_auth, common_name = get_certificate_login_info(request)
    login_certificate = LoginCertificate.objects.filter(api_path=request.path, common_name=common_name, user=user).first()
    if not login_certificate:
        return False

    # Certificate authentication must be successful and user must have LUOVUTUSPALVELU permissions
    # in the correct organization specified in LoginCertificate object, or in OPH organisaatio
    organisaatio_oid_list = [settings.OPETUSHALLITUS_ORGANISAATIO_OID,
                             getattr(login_certificate.organisaatio, 'organisaatio_oid', None)]
    return is_cert_auth and user_permission_groups_in_organizations(user, organisaatio_oid_list,
                                                                    [Z4_CasKayttoOikeudet.LUOVUTUSPALVELU]).exists()


def get_certificate_login_info(request):
    """
    Checks request if user has certificate login info and returns that.
    :param request: request
    :return: tuple(is_cert_auth, common_name)
    """
    is_cert_auth = request.headers.get('X-SSL-Authenticated') == 'SUCCESS'
    subject_string = request.headers.get('X-SSL-User-DN')
    subject_dict = _parse_nginx_subject(subject_string)
    common_name = subject_dict.get('CN')  # We match cert with common name!
    return is_cert_auth, common_name


def _parse_nginx_subject(subject_dn_string):
    """
    Nginx current version uses comma ',' to split subject distinguished name separate data.
    :param subject_dn_string: subject DN in nginx format e.g. CN=kela cert,O=user1 company,ST=Some-State,C=FI
    :type subject_dn_string: string
    :return: dict of subject distinguished name data
    """
    subject_data_list = subject_dn_string.split(',') if subject_dn_string else []
    return {subject_data_pair[0]: subject_data_pair[1] for subject_data in subject_data_list
            if len(subject_data_pair := subject_data.split('=', 1)) == 2}


def user_has_tallentaja_permission_in_organization(organisaatio_oid, user):
    """
    Tallentaja-permissions are needed for POST, PUT, PATCH and DELETE

    User must be either Palvelukayttaja in vakajarjestaja-level, or
    Tallentaja either in vakajarjestaja or toimipaikka -level.

    requested_permission is either "add", "change" or "delete"
    """
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA

    PALVELUKAYTTAJA_GROUP_NAME = PALVELUKAYTTAJA + '_' + organisaatio_oid
    TALLENTAJA_GROUP_NAME = TALLENTAJA + '_' + organisaatio_oid

    acceptable_group_names = [PALVELUKAYTTAJA_GROUP_NAME, TALLENTAJA_GROUP_NAME]

    if user.is_superuser:
        return True

    user_groups_query = user.groups.all()
    for user_group in user_groups_query:
        if user_group.name in acceptable_group_names:
            return True  # User has permissions to add/change/delete
    return False


def throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user, oma_organisaatio=None):
    if not oma_organisaatio:
        if user_has_tallentaja_permission_in_organization(vakajarjestaja_organisaatio_oid, user):
            return None

        toimipaikan_organisaatio_oid = toimipaikka_obj.organisaatio_oid if toimipaikka_obj else ''
        if toimipaikka_obj and user_has_tallentaja_permission_in_organization(toimipaikan_organisaatio_oid, user):
            return None
    else:  # PAOS-case, i.e. user might have permission to add lapsi to another organization.
        try:
            paos_organisaatio = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_organisaatio_oid)
        except Organisaatio.DoesNotExist:
            raise ValidationError({'paos_organisaatio': [ErrorMessages.PT009.value]}, code='invalid')

        if toimipaikka_obj:
            paos_toiminta = PaosToiminta.objects.filter(
                Q(voimassa_kytkin=True) &
                Q(oma_organisaatio=oma_organisaatio, paos_toimipaikka=toimipaikka_obj)
            ).first()  # This is either None or the actual paos-toiminta object
            if not paos_toiminta:
                raise ValidationError({'errors': [ErrorMessages.PT010.value]}, code='invalid')

        paos_oikeus = PaosOikeus.objects.filter(
            Q(jarjestaja_kunta_organisaatio=oma_organisaatio) & Q(tuottaja_organisaatio=paos_organisaatio)
        ).first()  # This is either None or the actual paos-oikeus object

        if paos_oikeus:
            paos_tallentaja_organisaatio = paos_oikeus.tallentaja_organisaatio
            paos_voimassa_kytkin = paos_oikeus.voimassa_kytkin

            if (paos_voimassa_kytkin and
                    user_has_tallentaja_permission_in_organization(paos_tallentaja_organisaatio.organisaatio_oid,
                                                                   user)):
                """
                User-organization has tallentaja-permission to paos-toimipaikka, and
                user has tallentaja-permissions in oma_organisaatio.
                """
                return None

    raise PermissionDenied({'errors': [ErrorMessages.PE003.value]})


def check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(oma_organisaatio, paos_organisaatio):
    paos_oikeus = PaosOikeus.objects.filter(
        Q(jarjestaja_kunta_organisaatio=oma_organisaatio) & Q(tuottaja_organisaatio=paos_organisaatio)
    ).first()  # This is either the actual PAOS-Oikeus object or None

    if paos_oikeus and paos_oikeus.voimassa_kytkin:
        return paos_oikeus
    raise PermissionDenied({'errors': [ErrorMessages.PO003.value]})


def is_user_permission(user, permission_group_name):
    """
    Check is user superuser or has user required permission group
    :param user: user instance
    :param permission_group_name: name of the permission requested
    :return: boolean
    """
    return user.is_superuser or user.groups.filter(name=permission_group_name).exists()


def check_if_user_has_paakayttaja_permissions(vakajarjestaja_organisaatio_oid, user):
    VARDA_PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    paakayttaja_group_name = VARDA_PAAKAYTTAJA + '_' + vakajarjestaja_organisaatio_oid
    if not is_user_permission(user, paakayttaja_group_name):
        raise PermissionDenied(ErrorMessages.PE004.value)


def save_audit_log(user, url):
    path, query_params = path_parse(url)
    # path max-length is 200 characters
    path = path[:200]
    Z5_AuditLog.objects.create(user=user, successful_get_request_path=path, query_params=query_params)


def auditlog(function):
    """
    Decorator that audit logs successful responses. Used with GenericViewSet methods
    :param function: Function to be executed
    :return: response from provided function
    """

    @wraps(function)  # @action decorator wants function name not to change
    def argument_wrapper(*args, **kwargs):
        generic_view_set_obj = args[0]
        response = function(*args, **kwargs)
        status_code = response.status_code
        if status.is_success(status_code):
            request = generic_view_set_obj.request
            user = request.user
            path = request.get_full_path()
            save_audit_log(user, path)
        return response

    return argument_wrapper


def auditlogclass(cls):
    """
    Class level decorator that adds auditlog decorator to all supported classes that exist in provided class. If action
    is not in supported methods (see supported_methods list) @auditlog decorator needs to be used explicitly for that
    action.
    :param cls: GenericViewSet subclass
    :return: Provided class with decorated methods
    """
    # create, update and destroy are detected from history table on auditlog send process.
    supported_methods = ['list', 'retrieve', ]
    existing_methods = [method_name for method_name in supported_methods if getattr(cls, method_name, None)]

    for method_name in existing_methods:
        original_method = getattr(cls, method_name)
        setattr(cls, method_name, auditlog(original_method))
    return cls


def user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, vakajarjestaja_organisaatio_oid,
                                                                         toimipaikka_qs=None):
    """
    User must be "palvelukayttaja" or have HUOLTAJATIETO_TALLENNUS-permission under the vakajarjestaja/toimipaikka.
    This is needed since user can have permissions to multiple organizations.
    """
    if user.is_superuser:
        return True

    try:
        user_details = Z3_AdditionalCasUserFields.objects.get(user=user)
    except Z3_AdditionalCasUserFields.DoesNotExist:
        logger.error('Missing cas-user-details, user-id: {}'.format(user.id))
        return False

    if user_details.kayttajatyyppi == 'PALVELU':
        group_vakajarjestaja_palvelukayttaja = 'VARDA-PALVELUKAYTTAJA_' + vakajarjestaja_organisaatio_oid
        if user.groups.filter(name=group_vakajarjestaja_palvelukayttaja).exists():
            return True

    if user_details.kayttajatyyppi == 'VIRKAILIJA':
        group_vakajarjestaja_huoltaja_tallentaja = 'HUOLTAJATIETO_TALLENNUS_' + vakajarjestaja_organisaatio_oid
        if user.groups.filter(name=group_vakajarjestaja_huoltaja_tallentaja).exists():
            return True

    for toimipaikka in toimipaikka_qs or []:
        group_toimipaikka_huoltaja_tallentaja = 'HUOLTAJATIETO_TALLENNUS_' + toimipaikka.organisaatio_oid
        if user.groups.filter(name=group_toimipaikka_huoltaja_tallentaja).exists():
            return True
    return False


def object_ids_organization_has_permissions_to(organisaatio_oid, model):
    content_type = ContentType.objects.get_for_model(model)
    return set(GroupObjectPermission.objects.filter(group__name__endswith=organisaatio_oid,
                                                    content_type=content_type.id)
               .annotate(object_pk_as_int=Cast('object_pk', IntegerField()))
               .values_list('object_pk_as_int', flat=True))


def get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(taydennyskoulutus_tyontekija_list):
    """
    :param taydennyskoulutus_tyontekija_list: list of TaydennyskoulutusTyontekija objects or similar dict objects
    :return tyontekija_id_list: list of Tyontekija ids
    :return toimipaikka_oid_list_list: list of lists of Toimipaikka oids
    """
    # Transform taydennyskoulutus_tyontekija_list to the following format:
    # [{'tyontekija': 1, 'tehtavanimike_koodi': '12345'}]
    if taydennyskoulutus_tyontekija_list and isinstance(taydennyskoulutus_tyontekija_list[0],
                                                        TaydennyskoulutusTyontekija):
        taydennyskoulutus_tyontekija_list = [model_to_dict(taydennyskoulutus_tyontekija,
                                                           fields=['tehtavanimike_koodi', 'tyontekija'])
                                             for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_list]
    else:
        taydennyskoulutus_tyontekija_list = [
            {'tehtavanimike_koodi': taydennyskoulutus_tyontekija['tehtavanimike_koodi'],
             'tyontekija': taydennyskoulutus_tyontekija['tyontekija'].id}
            for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_list]

    tyontekija_id_list = [taydennyskoulutus_tyontekija['tyontekija']
                          for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_list]

    # List of lists of toimipaikka oids
    # Toimipaikka level user must have permissions to at least one toimipaikka in a list
    toimipaikka_oid_list_list = [Tyoskentelypaikka.objects
                                 .filter(palvelussuhde__tyontekija=taydennyskoulutus_tyontekija['tyontekija'],
                                         tehtavanimike_koodi=taydennyskoulutus_tyontekija['tehtavanimike_koodi'])
                                 .values_list('toimipaikka__organisaatio_oid', flat=True)
                                 for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_list]

    return tyontekija_id_list, toimipaikka_oid_list_list


def is_correct_taydennyskoulutus_tyontekija_permission(user, taydennyskoulutus_tyontekija_list, throws=True):
    """
    Checks user has taydennyskoulutus tallentaja group permissions to taydennyskoulutus tyontekijat vakajarjestaja
    or to all toimipaikat that are related to tehtavanimikkeet of tyontekijat.
    :param user: User requesting to access taydennyskoulutus tyontekijat
    :param taydennyskoulutus_tyontekija_list: list of TaydennyskoulutusTyontekija objects or similar dict objects
    :param throws: By default validation fails raise PermissionDenied. Else if this param is False returns False.
    :return: boolean
    """
    if not taydennyskoulutus_tyontekija_list:
        # No TaydennyskoulutusTyontekija objects provided, return True (user has permissions to nothing)
        return True

    tyontekija_id_list, toimipaikka_oid_list_list = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(
        taydennyskoulutus_tyontekija_list)

    permission_format = 'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_{}'
    vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(Tyontekija.objects.filter(id__in=tyontekija_id_list))

    if not is_user_permission(user, permission_format.format(vakajarjestaja_oid)):
        # Check if user has toimipaikka level permissions
        for toimipaikka_oid_list in toimipaikka_oid_list_list:
            if not any(is_user_permission(user, permission_format.format(toimipaikka_oid)) for toimipaikka_oid in
                       toimipaikka_oid_list):
                # User does not have permissions to any toimipaikka with this tehtavanimike
                if throws:
                    raise PermissionDenied({'errors': [ErrorMessages.TK014.value]})
                return False
    return True


def get_available_tehtavanimike_codes_for_user(user, tyontekija, has_permissions=False, organisaatio_oid_list=()):
    permission_qs = user_permission_groups_in_organization(user, tyontekija.vakajarjestaja.organisaatio_oid,
                                                           TYONTEKIJA_GROUPS)
    if user.is_superuser or is_oph_staff(user) or has_permissions or permission_qs.exists():
        # User has Vakajarjestaja level permissions, return all tehtavanimike codes
        tehtavanimike_set = set(tyontekija.palvelussuhteet.all()
                                .values_list('tyoskentelypaikat__tehtavanimike_koodi', flat=True))
    else:
        if not organisaatio_oid_list:
            organisaatio_oid_list = get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user)
        tehtavanimike_set = set(Tyoskentelypaikka.objects
                                .filter((Q(toimipaikka__organisaatio_oid__in=organisaatio_oid_list) |
                                         Q(toimipaikka__vakajarjestaja__organisaatio_oid__in=organisaatio_oid_list)) &
                                        Q(palvelussuhde__tyontekija=tyontekija))
                                .values_list('tehtavanimike_koodi', flat=True))
    # Discard None just in case
    tehtavanimike_set.discard(None)
    return tehtavanimike_set


def get_tyontekija_vakajarjestaja_oid(tyontekijat):
    """
    Gets vakajarjestaja oid if tyontekijat has been added to taydennyskoulutus. Always returns 1 or throws
    :param tyontekijat: taydennyskoulutus instance related tyontekijat
    :return: vakajarjestaja oid or None
    """
    vakajarjestaja_oids = tyontekijat.values_list('vakajarjestaja__organisaatio_oid', flat=True).distinct()
    if len(vakajarjestaja_oids) > 1 or not vakajarjestaja_oids:
        raise IntegrityError('Täydennyskoulutus has tyontekijat on multiple vakatoimijat')
    return vakajarjestaja_oids.first()


def get_tyontekija_filters_for_taydennyskoulutus_groups(user, prefix=''):
    organisaatio_oids = get_organisaatio_oids_from_groups(user, 'HENKILOSTO_TAYDENNYSKOULUTUS_')
    # We can't distinguish vakajarjestaja oids from toimipaikka oids but since oids are unique it doesn't matter
    return (Q(**{prefix + 'vakajarjestaja__organisaatio_oid__in': organisaatio_oids}) |
            Q(**{
                prefix + 'palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid__in': organisaatio_oids})), organisaatio_oids


def filter_authorized_taydennyskoulutus_tyontekijat_list(data, user):
    filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(user)
    checked_data = data.filter(filters).distinct()
    return checked_data, organisaatio_oids


def filter_authorized_taydennyskoulutus_tyontekijat(data, user):
    filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(user, 'tyontekija__')
    checked_data = data.filter(filters).distinct()
    return checked_data, organisaatio_oids


def get_organisaatio_oids_from_groups(user, *group_name_prefixes):
    """
    Returns organisaatio oids that given permission group name prefixes and organisaatio_oid pairs match and are found
    from user's permission groups.
    NOTE: This doesn't take into account if user is superuser or not.
    :param user: User who's permission groups are filtered
    :param group_name_prefixes: List of group_name prefix
    :return: List of organisaatio_oids. Subset of given oids (if any)
    """
    filter_condition = Q()
    for group_name_prefix in group_name_prefixes:
        group_condition = Q(name__startswith=group_name_prefix)
        filter_condition = filter_condition | group_condition
    group_names = user.groups.filter(filter_condition).values_list('name', flat=True)
    return [group_name.split('_')[-1] for group_name in group_names]


def get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user):
    """
    Returns organisaatio oids (toimipaikka and vakajarjestaja!) from taydennyskoulutus and tyontekija (katelija and
    tallentaja) permission group user has access.
    :param user: User who's permission groups are filtered
    :return: List of organisaatio oids (mixed vakajarjestaja and toimipaikka oids)
    """
    return get_organisaatio_oids_from_groups(user, 'HENKILOSTO_TAYDENNYSKOULUTUS_', 'HENKILOSTO_TYONTEKIJA_')


def user_permission_groups_in_organization(user, organisaatio_oid, permission_group_list):
    return user_permission_groups_in_organizations(user, (organisaatio_oid,), permission_group_list)


def user_permission_groups_in_organizations(user, oid_list, permission_group_list):
    group_name_list = [f'{group}_{oid}' for oid in oid_list if oid for group in permission_group_list]
    return user.groups.filter(name__in=group_name_list)


def toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add(user, vakajarjestaja_oid, validated_data):
    # toimipaikka tallentaja can't create a pidempipoissaolo if there is no corresponding tyoskentelypaikka
    if user.is_superuser or user.groups.filter(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_{}'.format(vakajarjestaja_oid)):
        return True
    else:
        user_perm_oids = get_organisaatio_oids_from_groups(user, 'HENKILOSTO_TYONTEKIJA_TALLENTAJA')
        return Tyoskentelypaikka.objects.filter(Q(palvelussuhde=validated_data['palvelussuhde'],
                                                  toimipaikka__organisaatio_oid__in=user_perm_oids)
                                                ).exists()


def user_belongs_to_correct_groups(user, instance, permission_groups=(), accept_toimipaikka_permission=False,
                                   check_paos=False):
    """
    Verifies that given user belongs to pre-defined permission groups.
    Used in ensuring that, for example, if user has vaka permissions to one Organisaatio and henkilosto permissions
    to another Organisaatio, user cannot create Tyontekija objects to Organisaatio with only vaka permissions.
    :param user: User object instance
    :param instance: Organisaatio or Toimipaikka object instance
    :param permission_groups: list of accepted Z4_CasKayttoOikeudet group
    :param accept_toimipaikka_permission: if instance is Organisaatio, permissions in related Toimipaikka groups are
           also accepted
    :param check_paos: if instance is Toimipaikka, permissions in related PAOS-organizations are also accepted
    :return: True if user belongs to correct permission groups or if no specific groups are defined, else False
    """
    if not user.is_superuser and not is_oph_staff(user) and permission_groups:
        oid_list = []
        if isinstance(instance, Toimipaikka):
            oid_list = [instance.organisaatio_oid, instance.vakajarjestaja.organisaatio_oid]
            if check_paos:
                # Include Organisaatio objects that have permissions to this Toimipaikka via PAOS
                paos_organisaatio_oid_list = (PaosToiminta.objects.filter(paos_toimipaikka=instance,
                                                                          voimassa_kytkin=True)
                                              .values_list('oma_organisaatio__organisaatio_oid', flat=True))
                oid_list.extend(paos_organisaatio_oid_list)
        elif isinstance(instance, Organisaatio):
            oid_list = [instance.organisaatio_oid]
            if accept_toimipaikka_permission:
                # User can also have permissions to Toimipaikka of specified Organisaatio
                toimipaikka_oid_list = list(instance.toimipaikat.values_list('organisaatio_oid', flat=True))
                oid_list = oid_list + toimipaikka_oid_list
        return user_permission_groups_in_organizations(user, oid_list, permission_groups).exists()
    else:
        # User is admin, oph_staff or permission groups not specified
        return True


def get_vakajarjestajat_filter_for_raportit(request):
    """
    Return vakajarjestaja filter based on user permissions
    :param request: Request object
    :return: Q filter object
    """
    user = request.user
    vakajarjestajat_param = request.query_params.get('vakajarjestajat', '')

    if not vakajarjestajat_param and (user.is_superuser or is_oph_staff(user)):
        # If vakajarjestajat param is not provided and user is superuser or oph staff, get all request logs
        return Q()

    vakajarjestaja_ids_splitted = vakajarjestajat_param.split(',')
    vakajarjestaja_id_list = []
    for vakajarjestaja_id in vakajarjestaja_ids_splitted:
        if not vakajarjestaja_id.isdigit():
            continue
        vakajarjestaja_qs = Organisaatio.objects.filter(id=vakajarjestaja_id)
        if not vakajarjestaja_qs.exists():
            continue
        vakajarjestaja_obj = vakajarjestaja_qs.first()
        permission_group_qs = user_permission_groups_in_organization(user, vakajarjestaja_obj.organisaatio_oid,
                                                                     [Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA])
        if user.is_superuser or is_oph_staff or permission_group_qs.exists():
            vakajarjestaja_id_list.append(vakajarjestaja_id)
    return Q(vakajarjestaja__in=vakajarjestaja_id_list)


def is_oph_staff(user):
    """
    Return True if user is OPH staff, otherwise return False
    :param user: User object
    :return: boolean
    """
    return user.groups.filter(name=get_oph_yllapitaja_group_name()).exists()


def parse_toimipaikka_id_list(user, toimipaikka_ids_string, required_permission_groups, include_paos=False):
    """
    Return parsed list of toimipaikka ids based on user permissions
    :param user: request user
    :param toimipaikka_ids_string: comma separated string of ids
    :param required_permission_groups: list of permission groups that user must belong to under toimipaikka or
                                       vakajarjestaja of toimipaikka
    :param include_paos: boolean to determine if user can also have permissions to Vakajarjestaja
                         linked via PAOS to toimipaikka
    :return: verified list of toimipaikka ids
    """
    toimipaikka_id_list = []
    toimipaikka_ids_splitted = toimipaikka_ids_string.split(',')
    for toimipaikka_id in toimipaikka_ids_splitted:
        if not toimipaikka_id.isdigit():
            continue
        toimipaikka = Toimipaikka.objects.filter(pk=toimipaikka_id).first()
        if not toimipaikka or not user.has_perm('view_toimipaikka', toimipaikka):
            continue

        oid_list = [toimipaikka.organisaatio_oid, toimipaikka.vakajarjestaja.organisaatio_oid]

        if include_paos:
            paos_oid_list = set(PaosToiminta.objects.filter(Q(paos_toimipaikka=toimipaikka))
                                .values_list('oma_organisaatio__organisaatio_oid', flat=True))
            oid_list.extend(paos_oid_list)

        if (user.is_superuser or is_oph_staff(user) or
                user_permission_groups_in_organizations(user, oid_list, required_permission_groups).exists()):
            toimipaikka_id_list.append(toimipaikka_id)

    return toimipaikka_id_list


def delete_permissions_from_object_instance_by_oid(instance, organisaatio_oid):
    content_type = ContentType.objects.get_for_model(type(instance))
    GroupObjectPermission.objects.filter(content_type=content_type, object_pk=instance.id,
                                         group__name__endswith=organisaatio_oid).delete()


def delete_all_user_permissions(user, delete_henkilo_permissions=True):
    # Delete Z4_CasKayttoOikeudet related objects (not used, only set and deleted)
    Z4_CasKayttoOikeudet.objects.filter(user=user).delete()

    # Clear user group associations
    user.groups.clear()

    # Delete user specific permissions (e.g. to Henkilo objects)
    user_permission_qs = UserObjectPermission.objects.filter(user=user)
    if not delete_henkilo_permissions:
        # Preserve permissions to Henkilo objects, e.g. during API token fetch
        # User can create Henkilo, fetch API token again and then try to create Lapsi
        user_permission_qs = user_permission_qs.exclude(content_type=ContentType.objects.get_for_model(Henkilo))
    user_permission_qs.delete()


def delete_object_permissions(instance):
    """
    Delete object permissions explicitly
    :param instance: object instance
    """
    content_type = ContentType.objects.get_for_model(type(instance))
    filters = {'content_type': content_type, 'object_pk': instance.id}
    UserObjectPermission.objects.filter(**filters).delete()
    GroupObjectPermission.objects.filter(**filters).delete()


def assign_or_remove_object_permissions(instance, oid_list, permission_groups, view_only=False, assign=False):
    """
    Assign or remove object permissions for instance
    :param instance: object instance
    :param oid_list: list of organisaatio_oid values of Organisaatio or Toimipaikka objects
    :param permission_groups: list of Z4_CasKayttoOikeudet values
    :param view_only: assign only view-permissions
    :param assign: flag to assign or remove permissions
    """
    # Get list of group names in the format '{group_name}_{organisaatio_oid}'
    group_name_list = [f'{group}_{oid}' for oid in oid_list if oid for group in permission_groups]
    group_qs = Group.objects.filter(name__in=group_name_list)

    instance_model = instance.model if isinstance(instance, QuerySet) else type(instance)
    content_type = ContentType.objects.get_for_model(instance_model)
    for group in group_qs:
        # Get all permissions that group has for this type of object (view, add, change, delete)
        model_specific_permissions_for_group = group.permissions.filter(content_type=content_type)
        for permission in model_specific_permissions_for_group:
            if view_only and not permission.codename.startswith('view_'):
                # view_only parameter is True and permission is not view-permission, so continue to next permission
                continue
            if assign:
                assign_perm(permission, group, obj=instance)
            else:
                remove_perm(permission, group, obj=instance)


def assign_general_object_permissions(instance, oid_list, view_only=False):
    assign_or_remove_object_permissions(instance, oid_list, VAKA_GROUPS + HENKILOSTO_GROUPS + GENERAL_GROUPS,
                                        view_only=view_only, assign=True)


def assign_vaka_object_permissions(instance, oid_list, view_only=False, paos_tuottaja=False):
    # Huoltajatieto groups of PAOS tuottaja does not have any permissions to PAOS lapsi
    permission_groups = VAKA_LAPSI_GROUPS if paos_tuottaja else VAKA_GROUPS
    assign_or_remove_object_permissions(instance, oid_list, permission_groups, view_only=view_only, assign=True)


def remove_vaka_object_permissions(instance, oid_list):
    assign_or_remove_object_permissions(instance, oid_list, VAKA_GROUPS, assign=False)


def assign_henkilosto_object_permissions(instance, oid_list, view_only=False):
    assign_or_remove_object_permissions(instance, oid_list, HENKILOSTO_GROUPS, view_only=view_only, assign=True)


@transaction.atomic
def assign_organisaatio_permissions(organisaatio, reassign=False):
    """
    Assign object permissions for Organisaatio instance
    :param organisaatio: Organisaatio instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(organisaatio)

    # Organisaatio level permissions for Organisaatio object
    assign_general_object_permissions(organisaatio, (organisaatio.organisaatio_oid,))

    # Assign permissions for all Toimipaikat of Organisaatio in a task so that it doesn't block execution
    assign_organisaatio_all_toimipaikka_permissions.delay(organisaatio.id)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_organisaatio_all_toimipaikka_permissions(organisaatio_id):
    organisaatio = Organisaatio.objects.get(id=organisaatio_id)
    toimipaikka_oid_qs = organisaatio.toimipaikat.values_list('organisaatio_oid', flat=True)
    assign_general_object_permissions(organisaatio, toimipaikka_oid_qs)


@transaction.atomic
def assign_toimipaikka_permissions(toimipaikka, reassign=False):
    """
    Assign object permissions for Toimipaikka instance
    :param toimipaikka: Toimipaikka instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(toimipaikka)
        # Also reassign ToiminnallinenPainotus and KieliPainotus permissions
        toiminnallinen_painotus_qs = toimipaikka.toiminnallisetpainotukset.all()
        for toiminnallinen_painotus in toiminnallinen_painotus_qs:
            assign_toiminnallinen_painotus_permissions(toiminnallinen_painotus, reassign=True)
        kielipainotus_qs = toimipaikka.kielipainotukset.all()
        for kielipainotus in kielipainotus_qs:
            assign_kielipainotus_permissions(kielipainotus, reassign=True)

    # Organisaatio and Toimipaikka level permissions for Toimipaikka object
    assign_general_object_permissions(toimipaikka, (toimipaikka.organisaatio_oid,
                                                    toimipaikka.vakajarjestaja.organisaatio_oid,))
    # Toimipaikka level permissions for related Organisaatio object
    assign_general_object_permissions(toimipaikka.vakajarjestaja, (toimipaikka.organisaatio_oid,))

    # Assign PAOS related permissions (in case of reassignment)
    paos_toiminta_qs = (PaosToiminta.objects.filter(paos_toimipaikka=toimipaikka)
                        .values_list('oma_organisaatio_id', flat=True)
                        .distinct('oma_organisaatio_id').order_by('oma_organisaatio_id'))
    for jarjestaja_organisaatio_id in paos_toiminta_qs:
        paos_oikeus = PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio_id=jarjestaja_organisaatio_id,
                                                tuottaja_organisaatio=toimipaikka.vakajarjestaja,
                                                voimassa_kytkin=True)
        varhaiskasvatussuhde_qs = (Varhaiskasvatussuhde.objects
                                   .filter(toimipaikka=toimipaikka,
                                           varhaiskasvatuspaatos__lapsi__oma_organisaatio_id=jarjestaja_organisaatio_id))
        if paos_oikeus.exists() or varhaiskasvatussuhde_qs.exists():
            # If paos_oikeus voimassa_kytkin is True or there are related Lapsi objects in this Toimipaikka,
            # assign view permission for oma_organisaatio on Organisaatio level
            jarjestaja_organisaatio = Organisaatio.objects.get(id=jarjestaja_organisaatio_id)
            assign_vaka_object_permissions(toimipaikka, (jarjestaja_organisaatio.organisaatio_oid,), view_only=True)

    # Assign permissions for all Taydennyskoulutukset of Organisaatio in a task so that it doesn't block execution
    assign_all_taydennyskoulutus_toimipaikka_permissions.delay(toimipaikka.vakajarjestaja.organisaatio_oid,
                                                               toimipaikka.organisaatio_oid)


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_all_taydennyskoulutus_toimipaikka_permissions(organisaatio_oid, toimipaikka_oid):
    taydennyskoulutus_qs = (Taydennyskoulutus.objects
                            .filter(tyontekijat__vakajarjestaja__organisaatio_oid=organisaatio_oid)
                            .distinct('id').order_by('id'))
    assign_henkilosto_object_permissions(taydennyskoulutus_qs, (toimipaikka_oid,))


@transaction.atomic
def assign_toiminnallinen_painotus_permissions(toiminnallinen_painotus, reassign=False):
    """
    Assign object permissions for ToiminnallinenPainotus instance
    :param toiminnallinen_painotus: ToiminnallinenPainotus instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(toiminnallinen_painotus)

    # Organisaatio and Toimipaikka level permissions for ToiminnallinenPainotus object
    assign_vaka_object_permissions(toiminnallinen_painotus,
                                   (toiminnallinen_painotus.toimipaikka.organisaatio_oid,
                                    toiminnallinen_painotus.toimipaikka.vakajarjestaja.organisaatio_oid,))


@transaction.atomic
def assign_kielipainotus_permissions(kielipainotus, reassign=False):
    """
    Assign object permissions for KieliPainotus instance
    :param kielipainotus: KieliPainotus instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(kielipainotus)

    # Organisaatio and Toimipaikka level permissions for KieliPainotus object
    assign_vaka_object_permissions(kielipainotus, (kielipainotus.toimipaikka.organisaatio_oid,
                                                   kielipainotus.toimipaikka.vakajarjestaja.organisaatio_oid,))


@transaction.atomic
def assign_henkilo_permissions(henkilo, user):
    """
    Assign object permissions for Henkilo instance
    :param henkilo: Henkilo instance
    :param user: User object
    """
    if not user.has_perm('view_henkilo', henkilo):
        # Don't assign user specific permissions if user already has a permission via permission group
        assign_perm('view_henkilo', user, henkilo)


@transaction.atomic
def assign_lapsi_permissions(lapsi, toimipaikka_oid=None, user=None, reassign=False):
    """
    Assign object permissions for Lapsi instance
    :param lapsi: Lapsi instance
    :param toimipaikka_oid: Optional organisaatio_oid of Toimipaikka for setting Toimipaikka level permissions
    :param user: User object, if provided, user permissions to related Henkilo objects are removed as they are now set
        on Organisaatio and Toimipaikka level
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(lapsi)
        # Also reassign Varhaiskasvatuspaatos permissions so we get Toimipaikka level permissions back
        for vakapaatos in lapsi.varhaiskasvatuspaatokset.all():
            assign_varhaiskasvatuspaatos_permissions(vakapaatos, reassign=True)

    henkilo = lapsi.henkilo
    if lapsi.paos_kytkin:
        tallentaja_oid = get_tallentaja_organisaatio_oid_for_paos_lapsi(lapsi)
        jarjestaja_oid = lapsi.oma_organisaatio.organisaatio_oid
        tuottaja_oid = lapsi.paos_organisaatio.organisaatio_oid
        is_not_tuottaja_tallentaja = tuottaja_oid != tallentaja_oid
        is_not_jarjestaja_tallentaja = jarjestaja_oid != tallentaja_oid

        # Organisaatio and Toimipaikka level permissions for Lapsi object
        assign_vaka_object_permissions(lapsi, (toimipaikka_oid, tuottaja_oid,),
                                       view_only=is_not_tuottaja_tallentaja, paos_tuottaja=True)
        assign_vaka_object_permissions(lapsi, (jarjestaja_oid,), view_only=is_not_jarjestaja_tallentaja)
        # Organisaatio and Toimipaikka level permissions for Henkilo object
        assign_vaka_object_permissions(henkilo, (toimipaikka_oid, tuottaja_oid,),
                                       view_only=is_not_tuottaja_tallentaja, paos_tuottaja=True)
        assign_vaka_object_permissions(henkilo, (jarjestaja_oid,), view_only=is_not_jarjestaja_tallentaja)
    else:
        # Organisaatio and Toimipaikka level permissions for Lapsi object
        assign_vaka_object_permissions(lapsi, (toimipaikka_oid, lapsi.vakatoimija.organisaatio_oid,))
        # Organisaatio and Toimipaikka level permissions for Henkilo object
        assign_vaka_object_permissions(henkilo, (toimipaikka_oid, lapsi.vakatoimija.organisaatio_oid,))

    if user:
        # Remove permission from user since they are now set on Organisaatio (and Toimipaikka) level
        remove_perm('view_henkilo', user, henkilo)


@transaction.atomic
def assign_varhaiskasvatuspaatos_permissions(vakapaatos, toimipaikka_oid=None, reassign=False):
    """
    Assign object permissions for Varhaiskasvatuspaatos instance
    :param vakapaatos: Varhaiskasvatuspaatos instance
    :param toimipaikka_oid: Optional organisaatio_oid of Toimipaikka for setting Toimipaikka level permissions
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(vakapaatos)
        # Also reassign Varhaiskasvatussuhde permissions so we get Toimipaikka level permissions back
        for vakasuhde in vakapaatos.varhaiskasvatussuhteet.all():
            assign_varhaiskasvatussuhde_permissions(vakasuhde, reassign=True)

    lapsi = vakapaatos.lapsi
    if lapsi.paos_kytkin:
        tallentaja_oid = get_tallentaja_organisaatio_oid_for_paos_lapsi(lapsi)
        jarjestaja_oid = lapsi.oma_organisaatio.organisaatio_oid
        tuottaja_oid = lapsi.paos_organisaatio.organisaatio_oid

        # Organisaatio and Toimipaikka level permissions for Varhaiskasvatuspaatos object
        assign_vaka_object_permissions(vakapaatos, (toimipaikka_oid, tuottaja_oid,),
                                       view_only=tuottaja_oid != tallentaja_oid, paos_tuottaja=True)
        assign_vaka_object_permissions(vakapaatos, (jarjestaja_oid,), view_only=jarjestaja_oid != tallentaja_oid)
    else:
        # Organisaatio and Toimipaikka level permissions for Varhaiskasvatuspaatos object
        assign_vaka_object_permissions(vakapaatos, (toimipaikka_oid, lapsi.vakatoimija.organisaatio_oid,))


@transaction.atomic
def assign_varhaiskasvatussuhde_permissions(vakasuhde, reassign=False):
    """
    Assign object permissions for Varhaiskasvatussuhde instance
    :param vakasuhde: Varhaiskasvatussuhde instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(vakasuhde)

    toimipaikka_oid = vakasuhde.toimipaikka.organisaatio_oid
    lapsi = vakasuhde.varhaiskasvatuspaatos.lapsi
    if lapsi.paos_kytkin:
        tallentaja_oid = get_tallentaja_organisaatio_oid_for_paos_lapsi(lapsi)
        jarjestaja_oid = lapsi.oma_organisaatio.organisaatio_oid
        tuottaja_oid = lapsi.paos_organisaatio.organisaatio_oid
        is_not_tuottaja_tallentaja = tuottaja_oid != tallentaja_oid

        # Organisaatio and Toimipaikka level permissions for Varhaiskasvatussuhde object
        assign_vaka_object_permissions(vakasuhde, (toimipaikka_oid, tuottaja_oid,),
                                       view_only=is_not_tuottaja_tallentaja, paos_tuottaja=True)
        assign_vaka_object_permissions(vakasuhde, (jarjestaja_oid,), view_only=jarjestaja_oid != tallentaja_oid)
        # Toimipaikka level permissions for Varhaiskasvatuspaatos, Lapsi and Henkilo objects
        # (Organisaatio level permissions have already been set)
        assign_vaka_object_permissions(vakasuhde.varhaiskasvatuspaatos, (toimipaikka_oid,),
                                       view_only=is_not_tuottaja_tallentaja, paos_tuottaja=True)
        assign_vaka_object_permissions(lapsi, (toimipaikka_oid,), view_only=is_not_tuottaja_tallentaja,
                                       paos_tuottaja=True)
        assign_vaka_object_permissions(lapsi.henkilo, (toimipaikka_oid,), view_only=is_not_tuottaja_tallentaja,
                                       paos_tuottaja=True)
    else:
        # Organisaatio and Toimipaikka level permissions for Varhaiskasvatussuhde object
        assign_vaka_object_permissions(vakasuhde, (toimipaikka_oid, lapsi.vakatoimija.organisaatio_oid,))
        # Toimipaikka level permissions for Varhaiskasvatuspaatos, Lapsi and Henkilo objects
        # (Organisaatio level permissions have already been set)
        assign_vaka_object_permissions(vakasuhde.varhaiskasvatuspaatos, (toimipaikka_oid,))
        assign_vaka_object_permissions(lapsi, (toimipaikka_oid,))
        assign_vaka_object_permissions(lapsi.henkilo, (toimipaikka_oid,))
        # Toimipaikka has permissions to all Maksutieto objects of Lapsi
        maksutieto_qs = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).distinct('id').order_by('id')
        assign_vaka_object_permissions(maksutieto_qs, (toimipaikka_oid,))


@transaction.atomic
def assign_maksutieto_permissions(maksutieto, reassign=False):
    """
    Assign object permissions for Maksutieto instance
    :param maksutieto: Maksutieto instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(maksutieto)

    lapsi = get_lapsi_for_maksutieto(maksutieto)
    if lapsi.paos_kytkin:
        # Organisaatio level permissions for Maksutieto object
        # Only oma_organisaatio (PAOS järjestäjä) has permissions to Maksutieto objects
        assign_vaka_object_permissions(maksutieto, (lapsi.oma_organisaatio.organisaatio_oid,))
    else:
        # Organisaatio level permissions for Maksutieto object
        assign_vaka_object_permissions(maksutieto, (lapsi.vakatoimija.organisaatio_oid,))
        # Toimipaikka level permissions for Maksutieto object
        # (all Varhaiskasvatussuhde Toimipaikat have permissions to all Maksutieto objects of Lapsi)
        toimipaikka_oid_qs = (Toimipaikka.objects
                              .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi)
                              .values_list('organisaatio_oid', flat=True)
                              .distinct('organisaatio_oid').order_by('organisaatio_oid'))
        assign_vaka_object_permissions(maksutieto, toimipaikka_oid_qs)


@transaction.atomic
def reassign_all_lapsi_permissions(lapsi):
    """
    Remove and assign all permissions related to Lapsi instance
    :param lapsi: Lapsi instance
    """
    # This function also reassigns Varhaiskasvatuspaatos and Varhaiskasvatussuhde permissions
    assign_lapsi_permissions(lapsi, reassign=True)

    maksutieto_qs = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).distinct('id').order_by('id')
    for maksutieto in maksutieto_qs:
        assign_maksutieto_permissions(maksutieto, reassign=True)


@transaction.atomic
def assign_paos_toiminta_permissions(paos_toiminta, reassign=False):
    """
    Assign object permissions for PaosToiminta instance
    :param paos_toiminta: PaosToiminta instance
    :param reassign: delete old permissions before assignment
    """
    jarjestaja_organisaatio = (paos_toiminta.oma_organisaatio if paos_toiminta.paos_toimipaikka else
                               paos_toiminta.paos_organisaatio)
    tuottaja_organisaatio = (paos_toiminta.paos_toimipaikka.vakajarjestaja if paos_toiminta.paos_toimipaikka else
                             paos_toiminta.oma_organisaatio)
    paos_oikeus = (PaosOikeus.objects
                   .filter(jarjestaja_kunta_organisaatio=jarjestaja_organisaatio,
                           tuottaja_organisaatio=tuottaja_organisaatio)
                   .first())

    if reassign:
        remove_paos_toiminta_permissions(paos_toiminta)
        delete_object_permissions(paos_toiminta)
        if paos_oikeus:
            delete_object_permissions(paos_oikeus)

    # Organisaatio level permissions for PaosToiminta object
    assign_vaka_object_permissions(paos_toiminta, (paos_toiminta.oma_organisaatio.organisaatio_oid,))
    if paos_oikeus and paos_oikeus.voimassa_kytkin:
        # Organisaatio level permissions for jarjestaja_organisaatio to PAOS Toimipaikka objects
        # (two way agreement has been made as PaosOikeus voimassa_kytkin is True)
        paos_toiminta_qs = (PaosToiminta.objects
                            .filter(voimassa_kytkin=True, oma_organisaatio=jarjestaja_organisaatio,
                                    paos_toimipaikka__vakajarjestaja=tuottaja_organisaatio)
                            .values_list('paos_toimipaikka_id', flat=True)
                            .distinct('paos_toimipaikka_id').order_by('paos_toimipaikka_id'))
        paos_toimipaikka_qs = Toimipaikka.objects.filter(id__in=paos_toiminta_qs)
        assign_vaka_object_permissions(paos_toimipaikka_qs, (jarjestaja_organisaatio.organisaatio_oid,), view_only=True)

    paos_oikeus = (PaosOikeus.objects
                   .filter(jarjestaja_kunta_organisaatio=jarjestaja_organisaatio,
                           tuottaja_organisaatio=tuottaja_organisaatio))
    if paos_oikeus:
        # Organisaatio level permissions for PaosOikeus object
        # (jarjestaja_organisaatio has full permissions, tuottaja_organisaatio has only view permissions)
        assign_vaka_object_permissions(paos_oikeus, (jarjestaja_organisaatio.organisaatio_oid,))
        assign_vaka_object_permissions(paos_oikeus, (tuottaja_organisaatio.organisaatio_oid,), view_only=True)


@transaction.atomic
def remove_paos_toiminta_permissions(paos_toiminta):
    """
    Remove object permissions for PaosToiminta instance
    :param paos_toiminta: PaosToiminta instance
    """
    jarjestaja_organisaatio = (paos_toiminta.oma_organisaatio if paos_toiminta.paos_toimipaikka else
                               paos_toiminta.paos_organisaatio)
    tuottaja_organisaatio = (paos_toiminta.paos_toimipaikka.vakajarjestaja if paos_toiminta.paos_toimipaikka else
                             paos_toiminta.oma_organisaatio)

    if (paos_toiminta.paos_toimipaikka and
            not Varhaiskasvatussuhde.objects
                                    .filter(toimipaikka=paos_toiminta.paos_toimipaikka,
                                            varhaiskasvatuspaatos__lapsi__oma_organisaatio=jarjestaja_organisaatio)
                                    .exists()):
        # paos_toimipaikka is known and there are no Lapsi objects related to that Toimipaikka,
        # permissions can be removed
        remove_vaka_object_permissions(paos_toiminta.paos_toimipaikka,
                                       (jarjestaja_organisaatio.organisaatio_oid,))
    elif paos_toiminta.paos_organisaatio:
        # Remove permissions to each Toimipaikka object that have not related Lapsi objects
        paos_toiminta_qs = (PaosToiminta.objects
                            .filter(voimassa_kytkin=True, oma_organisaatio=jarjestaja_organisaatio,
                                    paos_toimipaikka__vakajarjestaja=tuottaja_organisaatio)
                            # Written as unpacked dict to prevent long line
                            .exclude(**{'paos_toimipaikka__varhaiskasvatussuhteet__varhaiskasvatuspaatos__'
                                        'lapsi__oma_organisaatio': jarjestaja_organisaatio})
                            .values_list('paos_toimipaikka_id', flat=True)
                            .distinct('paos_toimipaikka_id').order_by('paos_toimipaikka_id'))
        paos_toimipaikka_qs = Toimipaikka.objects.filter(id__in=paos_toiminta_qs)
        remove_vaka_object_permissions(paos_toimipaikka_qs, (jarjestaja_organisaatio.organisaatio_oid,))


@transaction.atomic
def reassign_paos_permissions(jarjestaja_organisaatio_id, tuottaja_organisaatio_id):
    """
    Normal situation: change tallentaja and katselija roles between the organizations.

    This function can also be used to remove tallentaja-permissions from the current tallentaja-organization.
    If voimassa_kytkin is False -> Remove tallentaja-permissions from the current tallentaja-organization.
    I.e. both of the organizations will have katselija-permissions.
    This can happen e.g. if paos_agreement is not active anymore.
    """
    lapsi_qs = Lapsi.objects.filter(oma_organisaatio_id=jarjestaja_organisaatio_id,
                                    paos_organisaatio_id=tuottaja_organisaatio_id)
    for lapsi in lapsi_qs:
        reassign_all_lapsi_permissions(lapsi)


@transaction.atomic
def assign_tyontekija_permissions(tyontekija, toimipaikka_oid=None, user=None, reassign=False):
    """
    Assign object permissions for Tyontekija instance
    :param tyontekija: Tyontekija instance
    :param toimipaikka_oid: Optional organisaatio_oid of Toimipaikka for setting Toimipaikka level permissions
    :param user: User object, if provided, user permissions to related Henkilo objects are removed as they are now set
        on Organisaatio and Toimipaikka level
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(tyontekija)
        # Also reassign Palvelussuhde permissions so we get Toimipaikka level permissions back
        for palvelussuhde in tyontekija.palvelussuhteet.all():
            assign_palvelussuhde_permissions(palvelussuhde, reassign=True)

    # Organisaatio and Toimipaikka level permissions for Tyontekija object
    assign_henkilosto_object_permissions(tyontekija, (tyontekija.vakajarjestaja.organisaatio_oid, toimipaikka_oid,))
    # Organisaatio and Toimipaikka level permissions for Henkilo object
    assign_henkilosto_object_permissions(tyontekija.henkilo,
                                         (tyontekija.vakajarjestaja.organisaatio_oid, toimipaikka_oid,))
    # Toimipaikka has permissions to all Tutkinto objects of Tyontekija (if provided)
    tutkinto_qs = Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo)
    assign_henkilosto_object_permissions(tutkinto_qs, (toimipaikka_oid,))

    if user:
        # Remove permission from user since they are now set on Organisaatio (and Toimipaikka) level
        remove_perm('view_henkilo', user, tyontekija.henkilo)


@transaction.atomic
def assign_tutkinto_permissions(tutkinto, toimipaikka_oid=None, reassign=False):
    """
    Assign object permissions for Tutkinto instance
    :param tutkinto: Tutkinto instance
    :param toimipaikka_oid: Optional organisaatio_oid of Toimipaikka for setting Toimipaikka level permissions
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(tutkinto)

    # Organisaatio and Toimipaikka level permissions for Tutkinto object
    assign_henkilosto_object_permissions(tutkinto, (tutkinto.vakajarjestaja.organisaatio_oid, toimipaikka_oid,))
    # Rest of the Toimipaikka level permissions for Tutkinto object
    # (all Tyoskentelypaikka Toimipaikat have permissions to all Tutkinto objects of Tyontekija)
    toimipaikka_oid_qs = (Toimipaikka.objects
                          .filter(tyoskentelypaikat__palvelussuhde__tyontekija__vakajarjestaja=tutkinto.vakajarjestaja,
                                  tyoskentelypaikat__palvelussuhde__tyontekija__henkilo=tutkinto.henkilo)
                          .values_list('organisaatio_oid', flat=True)
                          .distinct('organisaatio_oid').order_by('organisaatio_oid'))
    assign_henkilosto_object_permissions(tutkinto, toimipaikka_oid_qs)


@transaction.atomic
def assign_palvelussuhde_permissions(palvelussuhde, toimipaikka_oid=None, reassign=False):
    """
    Assign object permissions for Palvelussuhde instance
    :param palvelussuhde: Palvelussuhde instance
    :param toimipaikka_oid: Optional organisaatio_oid of Toimipaikka for setting Toimipaikka level permissions
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(palvelussuhde)
        # Also reassign Tyoskentelypaikka and PidempiPoissaolo permissions so we get Toimipaikka level permissions back
        for tyoskentelypaikka in palvelussuhde.tyoskentelypaikat.all():
            assign_tyoskentelypaikka_permissions(tyoskentelypaikka, reassign=True)
        for pidempi_poissaolo in palvelussuhde.pidemmatpoissaolot.all():
            assign_pidempi_poissaolo_permissions(pidempi_poissaolo, reassign=True)

    # Organisaatio and Toimipaikka level permissions for Palvelussuhde object
    assign_henkilosto_object_permissions(palvelussuhde,
                                         (palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid, toimipaikka_oid,))


@transaction.atomic
def assign_tyoskentelypaikka_permissions(tyoskentelypaikka, reassign=False):
    """
    Assign object permissions for Tyoskentelypaikka instance
    :param tyoskentelypaikka: Tyoskentelypaikka instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(tyoskentelypaikka)

    # Tyoskentelypaikka does not have related Toimipaikka if kiertava_tyontekija_kytkin is True
    toimipaikka_oid = getattr(tyoskentelypaikka.toimipaikka, 'organisaatio_oid', None)
    tyontekija = tyoskentelypaikka.palvelussuhde.tyontekija

    # Organisaatio and Toimipaikka level permissions for Tyoskentelypaikka object
    assign_henkilosto_object_permissions(tyoskentelypaikka,
                                         (tyontekija.vakajarjestaja.organisaatio_oid, toimipaikka_oid,))
    # Toimipaikka level permissions for Palvelussuhde, Tyontekija and Henkilo objects
    # (Organisaatio level permissions have already been set)
    assign_henkilosto_object_permissions(tyoskentelypaikka.palvelussuhde, (toimipaikka_oid,))
    assign_henkilosto_object_permissions(tyontekija, (toimipaikka_oid,))
    assign_henkilosto_object_permissions(tyontekija.henkilo, (toimipaikka_oid,))
    # Toimipaikka has permissions to all PidempiPoissaolo objects of related Palvelussuhde
    pidempi_poissaolo_qs = tyoskentelypaikka.palvelussuhde.pidemmatpoissaolot.all()
    assign_henkilosto_object_permissions(pidempi_poissaolo_qs, (toimipaikka_oid,))
    # Toimipaikka has permissions to all Tutkinto objects of Tyontekija
    tutkinto_qs = Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo)
    assign_henkilosto_object_permissions(tutkinto_qs, (toimipaikka_oid,))


@transaction.atomic
def assign_pidempi_poissaolo_permissions(pidempi_poissaolo, reassign=False):
    """
    Assign object permissions for PidempiPoissaolo instance
    :param pidempi_poissaolo: PidempiPoissaolo instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(pidempi_poissaolo)

    palvelussuhde = pidempi_poissaolo.palvelussuhde
    # Organisaatio level permissions for PidempiPoissaolo object
    assign_henkilosto_object_permissions(pidempi_poissaolo, (palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid,))
    # Toimipaikka level permissions for PidempiPoissaolo object
    # (all Tyoskentelypaikka Toimipaikat have permissions to all PidempiPoissaolo objects of related Palvelussuhde)
    toimipaikka_oid_qs = (palvelussuhde.tyoskentelypaikat
                          .values_list('toimipaikka__organisaatio_oid', flat=True)
                          .distinct('toimipaikka__organisaatio_oid').order_by('toimipaikka__organisaatio_oid'))
    assign_henkilosto_object_permissions(pidempi_poissaolo, toimipaikka_oid_qs)


@transaction.atomic
def assign_taydennyskoulutus_permissions(taydennyskoulutus, reassign=False):
    """
    Assign object permissions for Taydennyskoulutus instance
    :param taydennyskoulutus: Taydennyskoulutus instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(taydennyskoulutus)

    organisaatio_oid = get_organisaatio_oid_for_taydennyskoulutus(taydennyskoulutus)
    # Organisaatio level permissions for Taydennyskoulutus object
    assign_henkilosto_object_permissions(taydennyskoulutus, (organisaatio_oid,))
    # Toimipaikka level permissions for Taydennyskoulutus object
    # (all Toimipaikat of related Organisaatio have permissions to all Taydennyskoulutus objects)
    # First, assign permissions to Toimipaikat directly related to this Taydennyskoulutus
    toimipaikka_oid_qs = (taydennyskoulutus.tyontekijat
                          .values_list('palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid', flat=True)
                          .distinct('palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid')
                          .order_by('palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid'))
    assign_henkilosto_object_permissions(taydennyskoulutus, toimipaikka_oid_qs)
    # Assign permissions for all Toimipaikat of Organisaatio in a task so that it doesn't block execution
    # Start after transaction has been committed, so that Taydennyskoulutus will exist in database
    transaction.on_commit(
        lambda: assign_taydennyskoulutus_all_toimipaikka_permissions.delay(taydennyskoulutus.id, organisaatio_oid)
    )


@shared_task
@single_instance_task(timeout_in_minutes=8 * 60)
def assign_taydennyskoulutus_all_toimipaikka_permissions(taydennyskoulutus_id, organisaatio_oid):
    from varda.cache import invalidate_cache

    taydennyskoulutus = Taydennyskoulutus.objects.get(id=taydennyskoulutus_id)
    toimipaikka_oid_qs = (Toimipaikka.objects.filter(vakajarjestaja__organisaatio_oid=organisaatio_oid)
                          .values_list('organisaatio_oid', flat=True))
    assign_henkilosto_object_permissions(taydennyskoulutus, toimipaikka_oid_qs)
    invalidate_cache(Taydennyskoulutus.get_name(), taydennyskoulutus_id)


@transaction.atomic
def reassign_all_tyontekija_permissions(tyontekija):
    """
    Remove and assign all permissions related to Tyontekija instance
    :param tyontekija: Tyontekija instance
    """
    # This function also reassigns Palvelussuhde, Tyoskentelypaikka and PidempiPoissaolo permissions
    assign_tyontekija_permissions(tyontekija, reassign=True)

    tutkinto_qs = Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo)
    for tutkinto in tutkinto_qs:
        assign_tutkinto_permissions(tutkinto, reassign=True)


@transaction.atomic
def assign_tilapainen_henkilosto_permissions(tilapainen_henkilosto, reassign=False):
    """
    Assign object permissions for TilapainenHenkilosto intsance
    :param tilapainen_henkilosto: TilapainenHenkilosto instance
    :param reassign: delete old permissions before assignment
    """
    if reassign:
        delete_object_permissions(tilapainen_henkilosto)

    # Organisaatio level permissions for TilapainenHenkilosto object
    assign_henkilosto_object_permissions(tilapainen_henkilosto,
                                         (tilapainen_henkilosto.vakajarjestaja.organisaatio_oid,))
