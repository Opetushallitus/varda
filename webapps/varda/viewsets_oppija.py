import logging

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import Http404
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet

from varda.cas.varda_permissions import HasOppijaPermissions
from varda.models import Henkilo
from varda.serializers_oppija import (HuoltajatiedotSerializer, TyontekijatiedotSerializer, HenkilotiedotSerializer,
                                      VarhaiskasvatustiedotSerializer)
from varda.permissions import auditlogclass

logger = logging.getLogger(__name__)


class AbstractOppijaViewSet(GenericViewSet, RetrieveModelMixin):
    queryset = Henkilo.objects.all()
    permission_classes = (HasOppijaPermissions,)
    lookup_field = 'henkilo_oid'
    lookup_value_regex = r'[.0-9]{26,}'

    def get_object(self):
        henkilo_oid = self.kwargs[self.lookup_field]

        try:
            henkilo = self.get_queryset().get(henkilo_oid=henkilo_oid)
        except ObjectDoesNotExist:
            raise Http404
        except MultipleObjectsReturned:
            # This should not be possible
            logger.error('Multiple of henkilot was found with henkilo_oid: {}'.format(henkilo_oid))
            raise Http404

        user = self.request.user
        if (hasattr(user, 'additional_user_info') and
                ((huollettava_oid_list := getattr(user.additional_user_info, 'huollettava_oid_list', None)) and
                 henkilo_oid in huollettava_oid_list) and henkilo.turvakielto):
            # If user gets information of huollettava and target henkilo has turvakielto, raise 404
            raise Http404

        return henkilo


@auditlogclass
class HenkilotiedotViewSet(AbstractOppijaViewSet):
    serializer_class = HenkilotiedotSerializer


@auditlogclass
class VarhaiskasvatustiedotViewSet(AbstractOppijaViewSet):
    serializer_class = VarhaiskasvatustiedotSerializer


@auditlogclass
class HuoltajatiedotViewSet(AbstractOppijaViewSet):
    serializer_class = HuoltajatiedotSerializer


@auditlogclass
class TyontekijatiedotViewSet(AbstractOppijaViewSet):
    serializer_class = TyontekijatiedotSerializer
