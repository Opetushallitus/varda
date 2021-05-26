import logging
from functools import wraps

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction, IntegrityError
from django.db.models import IntegerField, Q, Model
from django.db.models.functions import Cast
from django.forms import model_to_dict
from django.http import Http404
from django.shortcuts import get_object_or_404
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError

from varda.enums.error_messages import ErrorMessages
from varda.misc import path_parse
from varda.models import (VakaJarjestaja, Toimipaikka, Lapsi, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          PaosToiminta, PaosOikeus, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Z5_AuditLog,
                          LoginCertificate, Maksutieto, Tyontekija, Tyoskentelypaikka, PidempiPoissaolo,
                          TaydennyskoulutusTyontekija,)
from varda.permission_groups import assign_object_level_permissions, remove_object_level_permissions


logger = logging.getLogger(__name__)


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
    if user.groups.filter(name__icontains='VARDA_LUOVUTUSPALVELU').exists():
        api_path = request.path
        is_cert_auth, common_name = get_certificate_login_info(request)
        return is_cert_auth and LoginCertificate.objects.filter(api_path=api_path, common_name=common_name, user=user).exists()
    return False


def get_certificate_login_info(request):
    """
    Checks request if user has certificate login info and returns that.
    :param request: request
    :return: tuple( common_name, is_cert_auth )
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
            paos_organisaatio = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_organisaatio_oid)
        except VakaJarjestaja.DoesNotExist:
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
                    user_has_tallentaja_permission_in_organization(paos_tallentaja_organisaatio.organisaatio_oid, user)):
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
    path = path_parse(url)
    Z5_AuditLog.objects.create(user=user, successful_get_request_path=path[:100])  # path max-length is 100 characters


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


def user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, vakajarjestaja_organisaatio_oid, toimipaikka_qs=None):
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


def get_object_ids_user_has_view_permissions(user, model_name, content_type):
    permission_codename = 'view_' + model_name
    perm = Permission.objects.get(codename=permission_codename.split('.')[-1])
    user_permission_objects = (UserObjectPermission
                               .objects
                               .filter(user=user, permission=perm, content_type=content_type)
                               .annotate(object_pk_as_int=Cast('object_pk', IntegerField()))
                               .values_list('object_pk_as_int', flat=True))
    group_permission_objects = (GroupObjectPermission
                                .objects
                                .filter(group__user=user, permission=perm, content_type=content_type)
                                .annotate(object_pk_as_int=Cast('object_pk', IntegerField()))
                                .values_list('object_pk_as_int', flat=True))

    all_object_ids_user_has_permissions = (user_permission_objects
                                           .union(group_permission_objects)
                                           .order_by('object_pk_as_int'))

    return list(all_object_ids_user_has_permissions)


def grant_or_deny_access_to_paos_toimipaikka(voimassa_kytkin, jarjestaja_kunta_organisaatio, tuottaja_organisaatio):
    """
    Either grant permissions to jarjestaja_kunta_organisaatio to access tuottaja_organisaatio-paos-toimipaikat, or deny the access.
    Based on the value of voimassa_kytkin:
    True ==> Grant
    False => Deny
    """
    tuottaja_organization_toimipaikka_ids = (Toimipaikka
                                             .objects
                                             .filter(vakajarjestaja=tuottaja_organisaatio)
                                             .values_list('id', flat=True))

    paos_toimipaikka_qs = (PaosToiminta
                           .objects
                           .filter(Q(voimassa_kytkin=True) &
                                   Q(oma_organisaatio=jarjestaja_kunta_organisaatio) &
                                   Q(paos_toimipaikka__id__in=tuottaja_organization_toimipaikka_ids)
                                   ))
    # Allow removing toimipaikka access only if there are no children added by jarjestaja else access is left untouched.
    if not voimassa_kytkin:
        paos_toimipaikka_qs = paos_toimipaikka_qs.exclude(paos_toimipaikka__varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__oma_organisaatio=jarjestaja_kunta_organisaatio)

    for paos_toimipaikka in Toimipaikka.objects.filter(id__in=paos_toimipaikka_qs.values_list('paos_toimipaikka__id', flat=True)):
        if voimassa_kytkin:
            assign_object_level_permissions(jarjestaja_kunta_organisaatio.organisaatio_oid, Toimipaikka, paos_toimipaikka, paos_kytkin=True)
        else:
            remove_object_level_permissions(jarjestaja_kunta_organisaatio.organisaatio_oid, Toimipaikka, paos_toimipaikka, paos_kytkin=True)


def change_paos_tallentaja_organization(jarjestaja_kunta_organisaatio_id, tuottaja_organisaatio_id, tallentaja_organisaatio_id, voimassa_kytkin):
    """
    Normal situation: change tallentaja and katselija roles between the organizations.

    This function can also be used to remove tallentaja-permissions from the current tallentaja-organization.
    If voimassa_kytkin is False -> Remove tallentaja-permissions from the current tallentaja-organization.
    I.e. both of the organizations will have katselija-permissions.
    This can happen e.g. if paos_agreement is not active anymore.
    """
    try:
        with transaction.atomic():
            jarjestaja_kunta_organisaatio = VakaJarjestaja.objects.get(id=jarjestaja_kunta_organisaatio_id)
            tuottaja_organisaatio = VakaJarjestaja.objects.get(id=tuottaja_organisaatio_id)
            tallentaja_organisaatio = VakaJarjestaja.objects.get(id=tallentaja_organisaatio_id)
            katselija_organisaatio = jarjestaja_kunta_organisaatio if tallentaja_organisaatio == tuottaja_organisaatio else tuottaja_organisaatio

            tallentaja_organisaatio_tallentaja_group = Group.objects.get(name='VARDA-TALLENTAJA_' + tallentaja_organisaatio.organisaatio_oid)
            tallentaja_organisaatio_palvelukayttaja_group = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_' + tallentaja_organisaatio.organisaatio_oid)
            tallentaja_organization_permission_groups = [tallentaja_organisaatio_tallentaja_group, tallentaja_organisaatio_palvelukayttaja_group]

            katselija_organisaatio_tallentaja_group = Group.objects.get(name='VARDA-TALLENTAJA_' + katselija_organisaatio.organisaatio_oid)
            katselija_organisaatio_palvelukayttaja_group = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_' + katselija_organisaatio.organisaatio_oid)
            katselija_organization_permission_groups = [katselija_organisaatio_tallentaja_group, katselija_organisaatio_palvelukayttaja_group]

            lapsi_qs = (Lapsi
                        .objects
                        .filter(oma_organisaatio=jarjestaja_kunta_organisaatio, paos_organisaatio=tuottaja_organisaatio)
                        .prefetch_related('varhaiskasvatuspaatokset', 'varhaiskasvatuspaatokset__varhaiskasvatussuhteet'))
            vakapaatos_qs = Varhaiskasvatuspaatos.objects.filter(lapsi__in=lapsi_qs)
            vakasuhde_qs = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__in=vakapaatos_qs)

            """
            Katselija_organisaatio had the tallentaja-permission previously.
            => We need to remove change & delete -permissions from katselija_organisaatio
            => And similarly, we need to assign change & delete -permissions to tallentaja_organisaatio.
            """
            for lapsi in lapsi_qs:
                if voimassa_kytkin:
                    [remove_perm('change_lapsi', permission_group, lapsi) for permission_group in katselija_organization_permission_groups]
                    [remove_perm('delete_lapsi', permission_group, lapsi) for permission_group in katselija_organization_permission_groups]
                    [assign_perm('change_lapsi', permission_group, lapsi) for permission_group in tallentaja_organization_permission_groups]
                    [assign_perm('delete_lapsi', permission_group, lapsi) for permission_group in tallentaja_organization_permission_groups]
                else:
                    [remove_perm('change_lapsi', permission_group, lapsi) for permission_group in tallentaja_organization_permission_groups]
                    [remove_perm('delete_lapsi', permission_group, lapsi) for permission_group in tallentaja_organization_permission_groups]

            for vakapaatos in vakapaatos_qs:
                if voimassa_kytkin:
                    [remove_perm('change_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in katselija_organization_permission_groups]
                    [remove_perm('delete_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in katselija_organization_permission_groups]
                    [assign_perm('change_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in tallentaja_organization_permission_groups]
                    [assign_perm('delete_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in tallentaja_organization_permission_groups]
                else:
                    [remove_perm('change_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in tallentaja_organization_permission_groups]
                    [remove_perm('delete_varhaiskasvatuspaatos', permission_group, vakapaatos) for permission_group in tallentaja_organization_permission_groups]

            for vakasuhde in vakasuhde_qs:
                if voimassa_kytkin:
                    [remove_perm('change_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in katselija_organization_permission_groups]
                    [remove_perm('delete_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in katselija_organization_permission_groups]
                    [assign_perm('change_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in tallentaja_organization_permission_groups]
                    [assign_perm('delete_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in tallentaja_organization_permission_groups]
                else:
                    [remove_perm('change_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in tallentaja_organization_permission_groups]
                    [remove_perm('delete_varhaiskasvatussuhde', permission_group, vakasuhde) for permission_group in tallentaja_organization_permission_groups]

                # Assign or remove Toimipaikka specific permissions
                toimipaikka_group = Group.objects.get(name='VARDA-TALLENTAJA_' + vakasuhde.toimipaikka.organisaatio_oid)
                vakapaatos = vakasuhde.varhaiskasvatuspaatos
                lapsi = vakapaatos.lapsi
                if voimassa_kytkin and vakasuhde.toimipaikka.vakajarjestaja.id == tallentaja_organisaatio_id:
                    # If toimipaikka belongs to tallentaja_organisaatio, assign permissions for Toimipaikka level groups
                    assign_perm('change_lapsi', toimipaikka_group, lapsi)
                    assign_perm('delete_lapsi', toimipaikka_group, lapsi)
                    assign_perm('change_varhaiskasvatuspaatos', toimipaikka_group, vakapaatos)
                    assign_perm('delete_varhaiskasvatuspaatos', toimipaikka_group, vakapaatos)
                    assign_perm('change_varhaiskasvatussuhde', toimipaikka_group, vakasuhde)
                    assign_perm('delete_varhaiskasvatussuhde', toimipaikka_group, vakasuhde)
                else:
                    remove_perm('change_lapsi', toimipaikka_group, lapsi)
                    remove_perm('delete_lapsi', toimipaikka_group, lapsi)
                    remove_perm('change_varhaiskasvatuspaatos', toimipaikka_group, vakapaatos)
                    remove_perm('delete_varhaiskasvatuspaatos', toimipaikka_group, vakapaatos)
                    remove_perm('change_varhaiskasvatussuhde', toimipaikka_group, vakasuhde)
                    remove_perm('delete_varhaiskasvatussuhde', toimipaikka_group, vakasuhde)
    except VakaJarjestaja.DoesNotExist:
        logger.error('Could not find one of the VakaJarjestajat: {}, {}, {}'.format(jarjestaja_kunta_organisaatio_id,
                                                                                    tuottaja_organisaatio_id,
                                                                                    tallentaja_organisaatio_id))


def delete_object_permissions_explicitly(model, instance_id):
    """
    Object permissions need to be deleted explicitly:
    https://django-guardian.readthedocs.io/en/stable/userguide/caveats.html
    """
    filters = {'content_type': ContentType.objects.get_for_model(model).id, 'object_pk': instance_id}
    UserObjectPermission.objects.filter(**filters).delete()
    GroupObjectPermission.objects.filter(**filters).delete()


def assign_object_level_permissions_for_instance(instance, oid_list=()):
    for organization_oid in oid_list:
        assign_object_level_permissions(organization_oid, type(instance), instance)


def assign_maksutieto_permissions(vakajarjestaja_oid, instance, toimipaikka_oid_list=()):
    assign_object_level_permissions(vakajarjestaja_oid, Maksutieto, instance)
    for toimipaikka_oid in toimipaikka_oid_list:
        if toimipaikka_oid:
            assign_object_level_permissions(toimipaikka_oid, Maksutieto, instance)


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
    if taydennyskoulutus_tyontekija_list and isinstance(taydennyskoulutus_tyontekija_list[0], TaydennyskoulutusTyontekija):
        taydennyskoulutus_tyontekija_list = [model_to_dict(taydennyskoulutus_tyontekija,
                                                           fields=['tehtavanimike_koodi', 'tyontekija'])
                                             for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_list]
    else:
        taydennyskoulutus_tyontekija_list = [{'tehtavanimike_koodi': taydennyskoulutus_tyontekija['tehtavanimike_koodi'],
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
    tyontekija_id_list, toimipaikka_oid_list_list = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(taydennyskoulutus_tyontekija_list)

    permission_format = 'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_{}'
    vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(Tyontekija.objects.filter(id__in=tyontekija_id_list))

    if not is_user_permission(user, permission_format.format(vakajarjestaja_oid)):
        # Check if user has toimipaikka level permissions
        for toimipaikka_oid_list in toimipaikka_oid_list_list:
            if not any(is_user_permission(user, permission_format.format(toimipaikka_oid)) for toimipaikka_oid in toimipaikka_oid_list):
                # User does not have permissions to any toimipaikka with this tehtavanimike
                if throws:
                    raise PermissionDenied({'errors': [ErrorMessages.TK014.value]})
                return False
    return True


def get_tyontekija_vakajarjestaja_oid(tyontekijat):
    """
    Gets vakajarjestaja oid if tyontekijat has been added to taydennyskoulutus. Always returns 1 or throws
    :param tyontekijat: taydennyskoulutus instance related tyontekijat
    :return: vakajarjestaja oid or None
    """
    vakajarjestaja_oids = (tyontekijat.values_list('vakajarjestaja__organisaatio_oid', flat=True)
                           .distinct()
                           )
    if len(vakajarjestaja_oids) > 1 or not vakajarjestaja_oids:
        raise IntegrityError('Täydennyskoulutus has tyontekijat on multiple vakatoimijat')
    return vakajarjestaja_oids.first()


def get_tyontekija_filters_for_taydennyskoulutus_groups(user, prefix=''):
    organisaatio_oids = get_organisaatio_oids_from_groups(user, 'HENKILOSTO_TAYDENNYSKOULUTUS_')
    # We can't distinguish vakajarjestaja oids from toimipaikka oids but since oids are unique it doesn't matter
    return (Q(**{prefix + 'vakajarjestaja__organisaatio_oid__in': organisaatio_oids}) |
            Q(**{prefix + 'palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid__in': organisaatio_oids})), organisaatio_oids


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


def get_toimipaikat_group_has_access(user, vakajarjestaja_pk, *group_name_prefixes):
    """
    Check is user toimipaikka level access to given permission groups
    :param user: User who's toimipaikka permissions are checked
    :param vakajarjestaja_pk: id for vakajarjestaja which toimipaikka must be under
    :param group_name_prefixes: List of group_name prefix
    :return: queryset containing toimipaikat user has access
    """
    organisaatio_oids = get_organisaatio_oids_from_groups(user, *group_name_prefixes)
    toimipaikat_qs = Toimipaikka.objects.filter(organisaatio_oid__in=organisaatio_oids,
                                                vakajarjestaja=vakajarjestaja_pk)
    return toimipaikat_qs


def get_toimipaikka_or_404(user, toimipaikka_pk=None):
    """
    Get toimipaikka or 404 if not found or user has no view permission to the toimipaikka.
    :param user: User whose permissions are checked
    :param toimipaikka_pk: Toimipaikka id
    :return: Toimipaikka object
    """
    toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
    if user.has_perm('view_toimipaikka', toimipaikka):
        return toimipaikka
    raise Http404


def user_permission_groups_in_organization(user, organisaatio_oid, permission_group_list):
    return user_permission_groups_in_organizations(user, (organisaatio_oid,), permission_group_list)


def user_permission_groups_in_organizations(user, oid_list, permission_group_list):
    group_name_list = [f'{group}_{oid}' for oid in oid_list for group in permission_group_list]
    return user.groups.filter(name__in=group_name_list)


def get_permission_checked_pidempi_poissaolo_katselija_queryset_for_user(user):
    additional_details = getattr(user, 'additional_cas_user_fields', None)
    extra_view_perms = getattr(additional_details, 'approved_oph_staff', False)
    permission = 'HENKILOSTO_TYONTEKIJA'
    return _get_permission_checked_pidempi_poissaolo_queryset_for_user(user, permission, extra_view_perms)


def get_permission_checked_pidempi_poissaolo_tallentaja_queryset_for_user(user):
    permission = 'HENKILOSTO_TYONTEKIJA_TALLENTAJA'
    return _get_permission_checked_pidempi_poissaolo_queryset_for_user(user, permission)


def _get_permission_checked_pidempi_poissaolo_queryset_for_user(user, permission, extra_perms=False):
    if user.is_superuser or extra_perms:
        return PidempiPoissaolo.objects.all()
    else:
        # since we cannot distinguish between toimipaikka user and toimija user we need to fetch for both
        # either the user has permission for the vakatoimija that the tyontekija is linked to or toimipaikka that is
        # related to tyoskentelypaikka
        user_perm_oids = get_organisaatio_oids_from_groups(user, permission)
        # vakajarjestaja permissions
        tyontekijat = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid__in=user_perm_oids)
        # toimipaikka permissions
        tyoskentelypaikat = Tyoskentelypaikka.objects.filter(toimipaikka__organisaatio_oid__in=user_perm_oids)
        palvelussuhde_ids = [tyoskentelypaikka.palvelussuhde_id for tyoskentelypaikka in tyoskentelypaikat]
        return PidempiPoissaolo.objects.filter(Q(palvelussuhde_id__in=palvelussuhde_ids) | Q(palvelussuhde__tyontekija__in=tyontekijat))


def toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add(user, vakajarjestaja_oid, validated_data):
    # toimipaikka tallentaja can't create a pidempipoissaolo if there is no corresponding tyoskentelypaikka
    if user.is_superuser or user.groups.filter(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_{}'.format(vakajarjestaja_oid)):
        return True
    else:
        user_perm_oids = get_organisaatio_oids_from_groups(user, 'HENKILOSTO_TYONTEKIJA_TALLENTAJA')
        return Tyoskentelypaikka.objects.filter(Q(palvelussuhde=validated_data['palvelussuhde'],
                                                  toimipaikka__organisaatio_oid__in=user_perm_oids)
                                                ).exists()


def user_has_vakajarjestaja_level_permission(user, organisaatio_oid, permission_name):
    return user.groups.filter(Q(name__endswith=organisaatio_oid) &
                              Q(permissions__codename__exact=permission_name)).exists()


def user_belongs_to_correct_groups(field, user, field_object):
    """
    Verifies that given user belongs to pre-defined permission groups.
    Used in ensuring that, for example, if user has vaka permissions to one VakaJarjestaja and henkilosto permissions
    to another VakaJarjestaja, user cannot create Tyontekija objects to VakaJarjestaja with only vaka permissions.
    :param user: User object instance
    :param field: PermissionCheckedHLFieldMixin instance
    :param field_object: VakaJarjestaja or Toimipaikka object instance
    :return: True if user belongs to correct permission groups or if no specific groups are defined, else False
    """
    if not user.is_superuser and not is_oph_staff(user) and getattr(field, 'permission_groups', None):
        oid_list = []
        if isinstance(field_object, Toimipaikka):
            oid_list = [field_object.organisaatio_oid, field_object.vakajarjestaja.organisaatio_oid]
            if getattr(field, 'check_paos', False):
                # Include VakaJarjestaja objects that have permissions to this Toimipaikka via PAOS
                paos_organisaatio_oid_list = (PaosToiminta.objects.filter(paos_toimipaikka=field_object,
                                                                          voimassa_kytkin=True)
                                              .values_list('oma_organisaatio__organisaatio_oid', flat=True))
                oid_list.extend(paos_organisaatio_oid_list)
        elif isinstance(field_object, VakaJarjestaja):
            oid_list = [field_object.organisaatio_oid]
            if hasattr(field, 'accept_toimipaikka_permission') and field.accept_toimipaikka_permission:
                # User can also have permissions to Toimipaikka of specified VakaJarjestaja
                toimipaikka_oid_list = list(field_object.toimipaikat.values_list('organisaatio_oid', flat=True))
                oid_list = oid_list + toimipaikka_oid_list
        return user_permission_groups_in_organizations(user, oid_list, field.permission_groups).exists()
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
        vakajarjestaja_qs = VakaJarjestaja.objects.filter(id=vakajarjestaja_id)
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
    additional_details = getattr(user, 'additional_cas_user_fields', None)
    return getattr(additional_details, 'approved_oph_staff', False)


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
            paos_oid_list = set(PaosToiminta.objects.filter(Q(paos_toimipaikka=toimipaikka) & Q(voimassa_kytkin=True))
                                .values_list('oma_organisaatio__organisaatio_oid', flat=True))
            oid_list.extend(paos_oid_list)

        if (user.is_superuser or is_oph_staff(user) or
                user_permission_groups_in_organizations(user, oid_list, required_permission_groups).exists()):
            toimipaikka_id_list.append(toimipaikka_id)

    return toimipaikka_id_list


def assign_henkilo_permissions_for_vaka_groups(oid_list, henkilo_object):
    permission_group_list = (Z4_CasKayttoOikeudet.PAAKAYTTAJA, Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                             Z4_CasKayttoOikeudet.KATSELIJA, Z4_CasKayttoOikeudet.TALLENTAJA,
                             Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
                             Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,)
    _assign_henkilo_permissions_for_groups(permission_group_list, oid_list, henkilo_object)


def assign_henkilo_permissions_for_tyontekija_groups(oid_list, henkilo_object):
    permission_group_list = (Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                             Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,)
    _assign_henkilo_permissions_for_groups(permission_group_list, oid_list, henkilo_object)


def _assign_henkilo_permissions_for_groups(permission_group_list, oid_list, henkilo_object):
    permission_name = 'view_henkilo'
    view_henkilo_permission = Permission.objects.get(codename=permission_name)

    group_name_list = [f'{group}_{oid}' for oid in oid_list for group in permission_group_list]
    group_qs = Group.objects.filter(name__in=group_name_list)

    for group in group_qs:
        assign_perm(view_henkilo_permission, group, henkilo_object)


def assign_lapsi_henkilo_permissions(lapsi, user=None, toimipaikka_oid=None):
    if lapsi.vakatoimija:
        oid_list = [lapsi.vakatoimija.organisaatio_oid]
    elif lapsi.oma_organisaatio and lapsi.paos_organisaatio:
        oid_list = [lapsi.oma_organisaatio.organisaatio_oid, lapsi.paos_organisaatio.organisaatio_oid]
    else:
        oid_list = []
    if toimipaikka_oid:
        oid_list.append(toimipaikka_oid)

    henkilo = lapsi.henkilo
    assign_henkilo_permissions_for_vaka_groups(oid_list, henkilo)

    if user:
        # Remove permission from user since they are now set on Vakajarjestaja level
        remove_perm('view_henkilo', user, henkilo)


def assign_vakasuhde_henkilo_permissions(vakasuhde):
    oid_list = (vakasuhde.toimipaikka.organisaatio_oid,)
    henkilo = vakasuhde.varhaiskasvatuspaatos.lapsi.henkilo
    assign_henkilo_permissions_for_vaka_groups(oid_list, henkilo)


def assign_tyontekija_henkilo_permissions(tyontekija, user=None, toimipaikka_oid=None):
    oid_list = [tyontekija.vakajarjestaja.organisaatio_oid]
    if toimipaikka_oid:
        oid_list.append(toimipaikka_oid)

    henkilo = tyontekija.henkilo
    assign_henkilo_permissions_for_tyontekija_groups(oid_list, henkilo)

    if user:
        # Remove permission from user since they are now set on Vakajarjestaja level
        remove_perm('view_henkilo', user, henkilo)


def assign_tyoskentelypaikka_henkilo_permissions(tyoskentelypaikka):
    oid_list = (tyoskentelypaikka.toimipaikka.organisaatio_oid,)
    henkilo = tyoskentelypaikka.palvelussuhde.tyontekija.henkilo
    assign_henkilo_permissions_for_tyontekija_groups(oid_list, henkilo)


def delete_permissions_from_object_instance_by_oid(instance, organisaatio_oid):
    content_type = ContentType.objects.get_for_model(type(instance))
    GroupObjectPermission.objects.filter(content_type=content_type, object_pk=instance.id,
                                         group__name__endswith=organisaatio_oid).delete()
