from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from varda import serializers
from varda.cas import varda_permissions
from varda.models import Lapsi


class TestViewSet(GenericViewSet, mixins.RetrieveModelMixin):
    """
    Example viewset to confirm oppija-cas functionality. Can be removed after the first real viewset is implemented.
    """
    queryset = Lapsi.objects
    serializer_class = serializers.LapsiSerializer
    permission_classes = (varda_permissions.HasHuoltajaRelation, )

    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
