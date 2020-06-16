import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter

from varda import filters
from varda.cache import cached_retrieve_response, delete_cache_keys_related_model, cached_list_response
from varda.exceptions.conflict_error import ConflictError
from varda.filters import PalvelussuhdeFilter, TyoskentelypaikkaFilter, PidempiPoissaoloFilter
from varda.models import (TilapainenHenkilosto, Tutkinto, Tyontekija, VakaJarjestaja, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo)
from varda.permission_groups import (assign_object_permissions_to_tyontekija_groups,
                                     remove_object_level_permissions,
                                     assign_object_permissions_to_tilapainenhenkilosto_groups)
from varda.permissions import CustomObjectPermissions
from varda.serializers_henkilosto import (TyoskentelypaikkaSerializer, PalvelussuhdeSerializer, PidempiPoissaoloSerializer,
                                          TilapainenHenkilostoSerializer, TutkintoSerializer, TyontekijaSerializer,
                                          TyoskentelypaikkaUpdateSerializer)

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
        user = self.request.user
        vakajarjestaja = validated_data['vakajarjestaja']
        self.return_tyontekija_if_already_created(validated_data)

        with transaction.atomic():
            try:
                tyontekija_obj = serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

            delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)
            vakajarjestaja_oid = vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyontekija, tyontekija_obj)
            tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija_obj.henkilo)
            [assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]

    def perform_update(self, serializer):
        user = self.request.user
        with transaction.atomic():
            try:
                serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_destroy(self, instance):
        with transaction.atomic():
            try:
                vakajarjestaja_oid = instance.vakajarjestaja.organisaatio_oid
                remove_object_level_permissions(vakajarjestaja_oid, Tyontekija, instance)
                tutkinnot = Tutkinto.objects.filter(henkilo=instance.henkilo)
                [remove_object_level_permissions(vakajarjestaja_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]
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
    permission_classes = (CustomObjectPermissions, )
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
                tilapainenhenkilosto_obj = serializer.save(changed_by=user)
                vakajarjestaja_oid = tilapainenhenkilosto_obj.vakajarjestaja.organisaatio_oid
                assign_object_permissions_to_tilapainenhenkilosto_groups(vakajarjestaja_oid, TilapainenHenkilosto, tilapainenhenkilosto_obj)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_update(self, serializer):
        user = self.request.user

        with transaction.atomic():
            try:
                serializer.save(changed_by=user)
            except DjangoValidationError as e:
                raise ValidationError(dict(e))

    def perform_destroy(self, instance):
        with transaction.atomic():
            vakajarjestaja_oid = instance.vakajarjestaja.organisaatio_oid
            remove_object_level_permissions(vakajarjestaja_oid, TilapainenHenkilosto, instance)
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
    permission_classes = (CustomObjectPermissions, )
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
        user = self.request.user
        validated_data = serializer.validated_data
        self.return_henkilo_already_has_tutkinto(validated_data)

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)
        vakajarjestaja_oids = VakaJarjestaja.objects.filter(tyontekijat__henkilo=saved_object.henkilo).values_list('organisaatio_oid', flat=True)
        [assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, saved_object) for vakajarjestaja_oid in vakajarjestaja_oids]

    def perform_destroy(self, instance):
        henkilo = instance.henkilo

        delete_cache_keys_related_model('henkilo', henkilo.id)
        with transaction.atomic():
            vakajarjestaja_oids = VakaJarjestaja.objects.filter(tyontekijat__henkilo=instance.henkilo).values_list('organisaatio_oid', flat=True)
            [remove_object_level_permissions(vakajarjestaja_oid, Tutkinto, instance) for vakajarjestaja_oid in vakajarjestaja_oids]
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
    permission_classes = (CustomObjectPermissions, )
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = PalvelussuhdeFilter
    queryset = Palvelussuhde.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data

        with transaction.atomic():
            user = self.request.user
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('tyontekija', saved_object.tyontekija.id)
            vakajarjestaja_oid = validated_data['tyontekija'].vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Palvelussuhde, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('palvelussuhde', saved_object.id)

    def perform_destroy(self, instance):
        with transaction.atomic():
            organisaatio_oid = instance.tyontekija.vakajarjestaja.organisaatio_oid
            remove_object_level_permissions(organisaatio_oid, Palvelussuhde, instance)
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete palvelussuhde. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('tyontekija', instance.tyontekija.id)


class TyoskentelypaikkaViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki tyoskentelypaikat.

    create:
        Luo yksi uusi tyoskentelypaikka.

    delete:
        Poista yksi tyoskentelypaikka.

    retrieve:
        Nouda yksittäinen tyoskentelypaikka.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä tyoskentelypaikka-tietueesta.

    update:
        Päivitä yhden tyoskentelypaikan kaikki kentät.
    """
    serializer_class = None
    permission_classes = (CustomObjectPermissions, )
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = TyoskentelypaikkaFilter
    queryset = Tyoskentelypaikka.objects.all().order_by('id')

    def get_serializer_class(self):
        request = self.request
        if request.method == 'PUT' or request.method == 'PATCH':
            return TyoskentelypaikkaUpdateSerializer
        else:
            return TyoskentelypaikkaSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            tyoskentelypaikka = serializer.save(changed_by=user)
            palvelussuhde = tyoskentelypaikka.palvelussuhde
            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)
            vakajarjestaja_oid = palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyoskentelypaikka, tyoskentelypaikka)
            if (tyoskentelypaikka.kiertava_tyontekija_kytkin and not user.is_superuser and
                    not user.groups.filter(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_{}'.format(vakajarjestaja_oid)).exists()):
                raise PermissionDenied('Vakajarjestaja level permissions required for kiertava tyontekija.')
            if tyoskentelypaikka.toimipaikka:
                toimipaikka_oid = tyoskentelypaikka.toimipaikka.organisaatio_oid
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyoskentelypaikka, tyoskentelypaikka)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        with transaction.atomic():
            organisaatio_oid = instance.palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid
            remove_object_level_permissions(organisaatio_oid, Tyoskentelypaikka, instance)
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyoskentelypaikka. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('palvelussuhde', instance.palvelussuhde.id)
            if instance.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)


class PidempiPoissaoloViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki pidemmatpoissaolot.

    create:
        Luo yksi uusi pidempipoissaolo.

    delete:
        Poista yksi pidempipoissaolo.

    retrieve:
        Nouda yksittäinen pidempipoissaolo.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä pidempipoissaolo-tietueesta.

    update:
        Päivitä yhden pidempipoissaolo-tietueen kaikki kentät.
    """
    serializer_class = PidempiPoissaoloSerializer
    permission_classes = (permissions.IsAdminUser, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = PidempiPoissaoloFilter
    queryset = PidempiPoissaolo.objects.all().order_by('id')

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.path)

    def perform_create(self, serializer):

        with transaction.atomic():
            user = self.request.user
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('palvelussuhde', saved_object.palvelussuhde.id)

    def perform_update(self, serializer):
        user = self.request.user
        pidempipoissaolo_obj = self.get_object()

        if not user.has_perm('change_pidempipoissaolo', pidempipoissaolo_obj):
            raise PermissionDenied('User does not have permissions to change this object.')

        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_pidempipoissaolo', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        with transaction.atomic():
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete pidempipoissaolo. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('palvelussuhde', instance.palvelussuhde.id)
