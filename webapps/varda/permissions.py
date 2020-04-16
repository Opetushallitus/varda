import logging

from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import IntegerField, Q
from django.db.models.functions import Cast
from guardian.models import UserObjectPermission, GroupObjectPermission
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from varda.misc import path_parse
from varda.models import (VakaJarjestaja, Toimipaikka, Lapsi, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          PaosToiminta, PaosOikeus, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Z5_AuditLog)
from varda.permission_groups import assign_object_level_permissions, remove_object_level_permissions


# Get an instance of a logger
logger = logging.getLogger(__name__)


# https://github.com/rpkilby/django-rest-framework-guardian
class CustomObjectPermissions(permissions.DjangoModelPermissions):
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


class CustomReportingViewAccess(permissions.BasePermission):
    """
    Allow access to reporting api for users in the "reporting_view_access"-group.
    """
    def has_permission(self, request, view):
        user = request.user
        if user.is_authenticated and user.groups.filter(name='reporting_view_access').exists():
            return True
        else:
            return False


def user_has_tallentaja_permission_in_organization(organisaatio_oid, user):
    """
    Tallentaja-permissions are needed for POST, PUT, PATCH and DELETE

    User must be either Palvelukayttaja in vakajarjestaja-level, or
    Tallentaja either in vakajarjestaja or toimipaikka -level.

    requested_permission is either "add", "change" or "delete"
    """
    PALVELUKAYTTAJA = Z4_CasKayttoOikeudet.PALVELUKAYTTAJA
    TALLENTAJA = Z4_CasKayttoOikeudet.TALLENTAJA

    PALVELUKAYTTAJA_GROUP_NAME = PALVELUKAYTTAJA + "_" + organisaatio_oid
    TALLENTAJA_GROUP_NAME = TALLENTAJA + "_" + organisaatio_oid

    acceptable_group_names = [PALVELUKAYTTAJA_GROUP_NAME, TALLENTAJA_GROUP_NAME]

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
            msg = {"paos_organisaatio": ["VakaJarjestaja must have an organisaatio_oid.", ]}
            raise ValidationError(msg, code='invalid')

        if toimipaikka_obj:
            paos_toiminta = PaosToiminta.objects.filter(
                Q(voimassa_kytkin=True) &
                Q(oma_organisaatio=oma_organisaatio, paos_toimipaikka=toimipaikka_obj)
            ).first()  # This is either None or the actual paos-toiminta object
            if not paos_toiminta:
                msg = {'non_field_errors': ['There is no active paos-agreement to this toimipaikka.']}
                raise ValidationError(msg, code='invalid')

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

    raise PermissionDenied("User does not have permissions.")


def check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(oma_organisaatio, paos_organisaatio):
    paos_oikeus = PaosOikeus.objects.filter(
        Q(jarjestaja_kunta_organisaatio=oma_organisaatio) & Q(tuottaja_organisaatio=paos_organisaatio)
    ).first()  # This is either the actual PAOS-Oikeus object or None

    if paos_oikeus and paos_oikeus.voimassa_kytkin:
        return paos_oikeus
    raise PermissionDenied('There is no active paos-agreement.')


def check_if_user_has_paakayttaja_permissions(vakajarjestaja_organisaatio_oid, user):
    VARDA_PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
    paakayttaja_group_name = VARDA_PAAKAYTTAJA + '_' + vakajarjestaja_organisaatio_oid
    if not user.is_superuser and not user.groups.filter(name=paakayttaja_group_name).exists():
        raise PermissionDenied("User does not have paakayttaja-permissions.")


def save_audit_log(user, url):
    path = path_parse(url)
    Z5_AuditLog.objects.create(user=user, successful_get_request_path=path[:100])  # path max-length is 100 characters


def user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, vakajarjestaja_organisaatio_oid, toimipaikka_qs):
    """
    User must be "palvelukayttaja" or have HUOLTAJATIETO_TALLENNUS-permission under the vakajarjestaja/toimipaikka.
    This is needed since user can have permissions to multiple organizations.
    """
    try:
        user_details = Z3_AdditionalCasUserFields.objects.get(user=user)
    except Z3_AdditionalCasUserFields.DoesNotExist:
        logger.error('Missing cas-user-details, user-id: {}'.format(user.id))
        return False

    if user_details.kayttajatyyppi == "PALVELU":
        return True

    # Kayttaja == "VIRKAILIJA"
    group_vakajarjestaja_huoltaja_tallentaja = 'HUOLTAJATIETO_TALLENNUS_' + vakajarjestaja_organisaatio_oid
    if user.groups.filter(name=group_vakajarjestaja_huoltaja_tallentaja).exists():
        return True

    for toimipaikka in toimipaikka_qs:
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

            if jarjestaja_kunta_organisaatio == tallentaja_organisaatio:
                katselija_organisaatio = tuottaja_organisaatio
            else:
                katselija_organisaatio = jarjestaja_kunta_organisaatio

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
    except VakaJarjestaja.DoesNotExist:
        logger.error('Could not find one of the VakaJarjestajat: {}, {}, {}'.format(jarjestaja_kunta_organisaatio_id,
                                                                                    tuottaja_organisaatio_id,
                                                                                    tallentaja_organisaatio_id))
