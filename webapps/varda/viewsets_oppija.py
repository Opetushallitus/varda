from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

import datetime
import logging
from rest_framework.response import Response
from django.db.models import Q
from django.http import Http404
from varda.cas import varda_permissions
from varda.models import Varhaiskasvatuspaatos, Henkilo, Lapsi
from varda.serializers_oppija import HuoltajanLapsiSerializer
from varda.permissions import auditlogclass

logger = logging.getLogger(__name__)


@auditlogclass
class HuoltajanLapsiViewSet(GenericViewSet, mixins.RetrieveModelMixin):
    """
    Returns data for Huoltaja
    """
    queryset = Henkilo.objects.none()
    serializer_class = HuoltajanLapsiSerializer
    permission_classes = (varda_permissions.IsHuoltajaForChild, )
    lookup_field = 'henkilo_oid'

    def retrieve(self, request, **kwargs):
        henkilo_oid = kwargs['henkilo_oid']

        data = self.get_queryset(henkilo_oid=henkilo_oid)
        serializer = self.get_serializer(instance=data)

        return Response(serializer.data)

    def get_queryset(self, henkilo_oid=None, *args, **kwargs):
        """
        Note: related permission handling is done in custom_auth.py oppija_post_login_handler function
        """
        today = datetime.datetime.now(datetime.timezone.utc)

        try:
            henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
        except Henkilo.DoesNotExist:
            raise Http404('Not found.')
        except Henkilo.MultipleObjectsReturned:  # This should not be possible
            logger.error("Multiple of henkilot was found with henkilo_oid: " + henkilo_oid)
            raise Http404('Not found.')

        if henkilo.turvakielto:
            raise Http404('Not found.')

        lapset = (Lapsi.objects.filter(henkilo=henkilo)
                               .prefetch_related('varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja')
                               .select_related('oma_organisaatio'))

        voimassaolo_filter = (Q(alkamis_pvm__lte=today) & (Q(paattymis_pvm__gte=today) | Q(paattymis_pvm=None)))

        voimassaolevat_vakapaatokset = (Varhaiskasvatuspaatos.objects
                                        .filter(voimassaolo_filter & Q(lapsi__henkilo=henkilo))
                                        .distinct('id')
                                        .order_by('id', 'alkamis_pvm')
                                        .count()
                                        )

        return {'henkilo': henkilo,
                'lapset': lapset,
                'voimassaolevia_varhaiskasvatuspaatoksia': voimassaolevat_vakapaatokset,
                }
