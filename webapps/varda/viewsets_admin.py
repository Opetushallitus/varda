from rest_framework.response import Response
from rest_framework.mixins import ListModelMixin
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import GenericViewSet

from varda.enums.error_messages import ErrorMessages
from varda.models import Henkilo
from varda.serializers_admin import AnonymisointiYhteenvetoSerializer


class AnonymisointiYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda anonymisointi-yhteenveto.
    """
    queryset = Henkilo.objects.none()
    permission_classes = (permissions.IsAdminUser, )
    serializer_class = AnonymisointiYhteenvetoSerializer

    def validate_henkilo_query_params(self, attribute):
        henkilo_id = self.request.query_params.get(attribute, None)
        if henkilo_id is not None:
            if henkilo_id.isdigit():
                try:
                    Henkilo.objects.get(id=int(henkilo_id))
                except Henkilo.DoesNotExist:
                    raise ValidationError({attribute: [ErrorMessages.MI015.value]})
            else:
                raise ValidationError({attribute: [ErrorMessages.MI015.value]})

    def validate_henkilo_ids_general(self):
        first_henkilo_id = self.request.query_params.get('first_henkilo_id', None)
        middle_henkilo_id = self.request.query_params.get('middle_henkilo_id', None)
        last_henkilo_id = self.request.query_params.get('last_henkilo_id', None)

        if first_henkilo_id and middle_henkilo_id and first_henkilo_id >= middle_henkilo_id:
            raise ValidationError({'first_henkilo_id': [ErrorMessages.MI017.value]})

        if first_henkilo_id and last_henkilo_id and first_henkilo_id >= last_henkilo_id:
            raise ValidationError({'first_henkilo_id': [ErrorMessages.MI017.value]})

        if middle_henkilo_id and last_henkilo_id and middle_henkilo_id >= last_henkilo_id:
            raise ValidationError({'middle_henkilo_id': [ErrorMessages.MI017.value]})

    def validate_query_params(self):
        self.validate_henkilo_query_params('first_henkilo_id')
        self.validate_henkilo_query_params('middle_henkilo_id')
        self.validate_henkilo_query_params('last_henkilo_id')
        self.validate_henkilo_ids_general()

    def list(self, request, *args, **kwargs):
        self.validate_query_params()
        serializer = self.get_serializer(request)
        return Response(serializer.data)
