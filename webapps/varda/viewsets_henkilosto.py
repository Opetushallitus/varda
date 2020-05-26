import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django_filters.rest_framework import DjangoFilterBackend
from django.http import Http404
from django.shortcuts import get_object_or_404

from guardian.shortcuts import assign_perm

from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter


from varda import filters
from varda.cache import cached_retrieve_response, delete_cache_keys_related_model, cached_list_response
from varda.exceptions.conflict_error import ConflictError
from varda.filters import PalvelussuhdeFilter
from varda.misc_viewsets import ViewSetValidator
from varda.models import TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde
from varda.permission_groups import assign_object_permissions_to_tyontekija_groups
from varda.permissions import CustomObjectPermissions
from varda.related_object_validations import check_overlapping_palvelussuhde_object
from varda.serializers_henkilosto import TilapainenHenkilostoSerializer, TutkintoSerializer, TyontekijaSerializer, PalvelussuhdeSerializer


# Get an instance of a logger
from varda.validators import validate_paattymispvm_after_alkamispvm

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
    permission_classes = (CustomObjectPermissions, )
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
            vakajarjestaja_oid = validated_data['vakajarjestaja'].organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyontekija, saved_object)

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


class TilapainenHenkilostoViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki tilapaiset henkilöstötiedot.

    create:
        Luo yksi uusi tilapäinen henkilöstötieto.

    delete:
        Poista yksi tilapäinen henkilöstötieto.

    retrieve:
        Nouda yksittäinen tilapäinen henkilöstötieto.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä tilapäinen henkilöstö -tietueesta.

    update:
        Päivitä yhden tilapäinen henkilöstö -tietueen kaikki kentät.
    """
    serializer_class = TilapainenHenkilostoSerializer
    permission_classes = (permissions.IsAdminUser, )
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = filters.TilapainenHenkilostoFilter
    queryset = TilapainenHenkilosto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            try:
                serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_update(self, serializer):
        user = self.request.user
        tilapainen_henkilosto_obj = self.get_object()

        if not user.has_perm('change_tilapainenhenkilosto', tilapainen_henkilosto_obj):
            raise PermissionDenied('User does not have permissions to change this object.')

        with transaction.atomic():
            try:
                serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_tilapainenhenkilosto', instance):
            raise PermissionDenied('User does not have permissions to delete this object.')

        instance.delete()


class TutkintoViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki tutkinnot.

    create:
        Luo yksi uusi tutkinto.

    delete:
        Poista yksi tutkinto.

    retrieve:
        Nouda yksittäinen tutkinto.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä tutkinto-tietueesta.

    update:
        Päivitä yhden tutkinnon kaikki kentät.
    """
    serializer_class = TutkintoSerializer
    permission_classes = (permissions.IsAdminUser, )
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = filters.TutkintoFilter
    queryset = Tutkinto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def return_henkilo_already_has_tutkinto(self, validated_data):
        q_obj = Q(henkilo=validated_data['henkilo'], tutkinto_koodi=validated_data['tutkinto_koodi'])
        tutkinto_obj = Tutkinto.objects.filter(q_obj).first()
        if tutkinto_obj:
            raise ConflictError(self.get_serializer(tutkinto_obj).data, status_code=status.HTTP_200_OK)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        self.return_henkilo_already_has_tutkinto(validated_data)

        user = self.request.user
        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)

    def perform_destroy(self, instance):
        user = self.request.user
        henkilo = instance.henkilo
        if not user.has_perm('delete_tutkinto', instance):
            raise PermissionDenied('User does not have permissions to delete this object.')

        delete_cache_keys_related_model('henkilo', henkilo.id)
        instance.delete()

    @action(methods=['delete'], detail=False)
    def delete(self, request):
        """
        Custom delete method for deleting by henkilo_id or henkilo_oid and tutkinto_koodi
        /api/henkilosto/v1/tutkinnot/delete/

        filter:
            henkilo_id=number
            henkilo_oid=string
            tutkinto_koodi=string

            esim. /api/henkilosto/v1/tutkinnot/delete/?henkilo_id=1&tutkinto_koodi=2
        """
        query_params = self.request.query_params
        henkilo_id = query_params.get('henkilo_id', None)
        henkilo_oid = query_params.get('henkilo_oid', None)
        tutkinto_koodi = query_params.get('tutkinto_koodi', None)

        if (henkilo_id is None and henkilo_oid is None) or tutkinto_koodi is None:
            raise Http404

        if henkilo_id:
            henkilo_filter = {'henkilo__id': henkilo_id}
        else:
            henkilo_filter = {'henkilo__henkilo_oid': henkilo_oid}

        tutkinto_obj = get_object_or_404(Tutkinto.objects.all(), **henkilo_filter, tutkinto_koodi=tutkinto_koodi)
        self.perform_destroy(tutkinto_obj)
        return Response(status=status.HTTP_200_OK)


class PalvelussuhdeViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki palvelussuhteet.

    create:
        Luo yksi uusi palvelussuhde.

    delete:
        Poista yksi palvelussuhde.

    retrieve:
        Nouda yksittäinen palvelussuhde.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä palvelussuhde-tietueesta.

    update:
        Päivitä yhden palvelussuhteen kaikki kentät.
    """
    serializer_class = PalvelussuhdeSerializer
    permission_classes = (permissions.IsAdminUser, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = PalvelussuhdeFilter
    queryset = Palvelussuhde.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data

        with ViewSetValidator() as validator:
            with validator.wrap():
                validate_paattymispvm_after_alkamispvm(validated_data)

            with validator.wrap():
                check_overlapping_palvelussuhde_object(validated_data, Palvelussuhde)

        with transaction.atomic():
            user = self.request.user
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('tyontekija', saved_object.tyontekija.id)
            assign_perm('view_palvelussuhde', user, saved_object)
            assign_perm('change_palvelussuhde', user, saved_object)
            assign_perm('delete_palvelussuhde', user, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        palvelussuhde = self.get_object()

        if not user.has_perm('change_palvelussuhde', palvelussuhde):
            raise PermissionDenied('User does not have permissions to change this object.')

        with ViewSetValidator() as validator:
            with validator.wrap():
                validate_paattymispvm_after_alkamispvm(validated_data)

            with validator.wrap():
                check_overlapping_palvelussuhde_object(validated_data, Palvelussuhde, palvelussuhde.id)

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('palvelussuhde', saved_object.id)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_palvelussuhde', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        with transaction.atomic():
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete palvelussuhde. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('tyontekija', instance.tyontekija.id)
