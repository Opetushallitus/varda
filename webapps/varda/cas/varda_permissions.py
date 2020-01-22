from django.contrib.auth.models import Group
from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import GenericViewSet

from varda.models import Lapsi, Z4_CasKayttoOikeudet


class HasHuoltajaRelation(IsAdminUser):
    """
    Allow huoltaja access child data when impersonating the child. Basically the child has access to his own data and
    parent logs in as the child.
    """
    def has_permission(self, request, view):
        user = request.user
        if super().has_permission(request, view):
            return True
        if (not user.is_anonymous and
                isinstance(view, GenericViewSet) and
                view.queryset.model == Lapsi and
                hasattr(user, 'additional_user_info')):
            lapsi_id = view.kwargs.get('pk')
            lapsi = view.queryset.filter(pk=lapsi_id,
                                         henkilo__henkilo_oid=user.additional_user_info.henkilo_oid)
            return lapsi.exists()
        return False


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
