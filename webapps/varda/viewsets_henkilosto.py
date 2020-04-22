import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from guardian.shortcuts import assign_perm
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.viewsets import ModelViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter

from varda.cache import cached_retrieve_response, delete_cache_keys_related_model
from varda.exceptions.conflict_error import ConflictError
from varda.models import Tyontekija
from varda.serializers_henkilosto import TyontekijaSerializer

# Get an instance of a logger
logger = logging.getLogger(__name__)


class TyontekijaViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki tyontekijät.

    create:
        Luo yksi uusi työntekijä.

    delete:
        Poista yksi työntekijä.

    retrieve:
        Nouda yksittäinen työntekijä.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä tyontekijä-tietueesta.

    update:
        Päivitä yhden työntekijän kaikki kentät.
    """
    serializer_class = TyontekijaSerializer
    permission_classes = (permissions.IsAdminUser, )
    filter_backends = (DjangoObjectPermissionsFilter,)
    queryset = Tyontekija.objects.all().order_by('id')

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def return_tyontekija_if_already_created(self, validated_data):
        q_obj = Q(henkilo=validated_data['henkilo'], vakajarjestaja=validated_data['vakajarjestaja'])
        tyontekija_obj = Tyontekija.objects.filter(q_obj).first()
        if tyontekija_obj:
            raise ConflictError(self.get_serializer(tyontekija_obj).data, status_code=status.HTTP_200_OK)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        self.return_tyontekija_if_already_created(validated_data)

        with transaction.atomic():
            user = self.request.user
            try:
                saved_object = serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

            delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)
            assign_perm('view_tyontekija', user, saved_object)
            assign_perm('change_tyontekija', user, saved_object)
            assign_perm('delete_tyontekija', user, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        tyontekija_obj = self.get_object()

        if not user.has_perm('change_tyontekija', tyontekija_obj):
            raise PermissionDenied('User does not have permissions to change this object.')

        with transaction.atomic():
            try:
                serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_tyontekija', instance):
            raise PermissionDenied('User does not have permissions to delete this object.')

        with transaction.atomic():
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyontekija. There are objects referencing it '
                                                 'that need to be deleted first.'})
