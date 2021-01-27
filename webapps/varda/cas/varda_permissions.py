from django.contrib.auth.models import Group
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import GenericViewSet

from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.models import Z4_CasKayttoOikeudet


class HasOppijaPermissions(IsAdminUser):
    """
    Return True if user has logged in from Oppija CAS and user's henkilo_oid or huoltaja_oid is same as requested
    """
    def has_permission(self, request, view):
        if super(HasOppijaPermissions, self).has_permission(request, view):
            return True

        user = request.user
        additional_user_info = getattr(user, 'additional_user_info', None)

        if user.is_anonymous or not additional_user_info:
            return False

        kayttajatyyppi = getattr(additional_user_info, 'kayttajatyyppi', None)
        if kayttajatyyppi not in [Kayttajatyyppi.OPPIJA_CAS.value, Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value]:
            return False

        requested_henkilo_oid = view.kwargs.get('henkilo_oid')

        allowed_oid_list = []
        if henkilo_oid := getattr(additional_user_info, 'henkilo_oid', None):
            allowed_oid_list.append(henkilo_oid)
        if huollettava_oid_list := getattr(additional_user_info, 'huollettava_oid_list', None):
            allowed_oid_list.extend(huollettava_oid_list)

        return requested_henkilo_oid in allowed_oid_list


class IsVardaPaakayttaja(IsAdminUser):
    """
    Checks user is either varda-paakayttaja or admin
    """
    def has_permission(self, request, view):
        user = request.user
        if super().has_permission(request, view):
            return True
        if not user.is_anonymous and isinstance(view, GenericViewSet):
            paakayttaja_prefix = Z4_CasKayttoOikeudet.PAAKAYTTAJA + '_'
            # Requires PAAKAYTTAJA permissions to some organisation.
            return Group.objects.filter(user=user, name__startswith=paakayttaja_prefix).exists()
        return False
