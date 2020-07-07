import logging

import coreapi
import coreschema
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.viewsets import ModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from varda import filters
from varda.cache import cached_retrieve_response, delete_cache_keys_related_model, cached_list_response
from varda.exceptions.conflict_error import ConflictError
from varda.filters import PalvelussuhdeFilter, TyoskentelypaikkaFilter, PidempiPoissaoloFilter, TaydennyskoulutusFilter, \
    TaydennyskoulutusTyontekijaFilter
from varda.models import (TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Toimipaikka)
from varda.permission_groups import (assign_object_permissions_to_tyontekija_groups,
                                     remove_object_level_permissions,
                                     assign_object_permissions_to_tilapainenhenkilosto_groups,
                                     assign_object_permissions_to_taydennyskoulutus_groups)
from varda.permissions import (CustomObjectPermissions, delete_object_permissions_explicitly, is_user_permission,
                               is_correct_taydennyskoulutus_tyontekija_permission, get_tyontekija_vakajarjestaja_oid,
                               filter_authorized_taydennyskoulutus_tyontekijat)
from varda.serializers_henkilosto import (TyoskentelypaikkaSerializer, PalvelussuhdeSerializer,
                                          PidempiPoissaoloSerializer,
                                          TilapainenHenkilostoSerializer, TutkintoSerializer, TyontekijaSerializer,
                                          TyoskentelypaikkaUpdateSerializer, TaydennyskoulutusSerializer,
                                          TaydennyskoulutusUpdateSerializer,
                                          TaydennyskoulutusTyontekijaSerializer)

# Get an instance of a logger
logger = logging.getLogger(__name__)


class TunnisteIdSchema(AutoSchema):
    def get_manual_fields(self, path, method):
        model_name = self.view.queryset.model._meta.verbose_name

        extra_fields = []
        path_array = path.split('/')
        if path_array[-2] == '{id}':
            field = coreapi.Field('id',
                                  required=True,
                                  location='path',
                                  schema=coreschema.String(),
                                  description=f'A unique integer value identifying this {model_name}. Can also be '
                                              'lahdejarjestelma and tunniste pair (lahdejarjestelma:tunniste).',
                                  type=None,
                                  example=None)
            extra_fields.append(field)

        manual_fields = super().get_manual_fields(path, method)
        return manual_fields + extra_fields


class ObjectByTunnisteMixin:
    schema = TunnisteIdSchema()

    def get_object(self):
        path_param = self.kwargs[self.lookup_field]

        if not path_param.isdigit():
            params = path_param.split(':', 1)
            # Check that both lahdejarjestelma and tunniste have been provided and that they are not empty
            if len(params) != 2 or (len(params) == 2 and (not params[0] or not params[1])):
                raise Http404

            model_qs = self.get_queryset().filter(lahdejarjestelma=params[0], tunniste=params[1])
            if not model_qs.exists():
                raise Http404
            self.kwargs[self.lookup_field] = str(model_qs.first().id)

        return super().get_object()


class TyontekijaViewSet(ObjectByTunnisteMixin, ModelViewSet):
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
    filter_backends = (ObjectPermissionsFilter,)
    queryset = Tyontekija.objects.all().order_by('id')

    def return_tyontekija_if_already_created(self, validated_data, toimipaikka_oid):
        q_obj = Q(henkilo=validated_data['henkilo'], vakajarjestaja=validated_data['vakajarjestaja'])
        tyontekija_obj = Tyontekija.objects.filter(q_obj).first()
        if tyontekija_obj:
            if toimipaikka_oid:
                self._assign_toimipaikka_permissions(toimipaikka_oid, tyontekija_obj)
            raise ConflictError(self.get_serializer(tyontekija_obj).data, status_code=status.HTTP_200_OK)

    def _assign_toimipaikka_permissions(self, toimipaikka_oid, tyontekija_obj):
        assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyontekija, tyontekija_obj)
        tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija_obj.henkilo)
        [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]

    def remove_address_information_from_henkilo(self, henkilo):
        """
        If henkilo is related only to Tyontekijat, we need to remove address information
        :param henkilo: Henkilo object linked to this Tyontekija
        """
        if not hasattr(henkilo, 'huoltaja'):
            henkilo.remove_address_information()
            henkilo.save()

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        user = self.request.user
        vakajarjestaja = validated_data['vakajarjestaja']
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid
        self.return_tyontekija_if_already_created(validated_data, toimipaikka_oid)

        with transaction.atomic():
            tyontekija_obj = serializer.save(changed_by=user)
            self.remove_address_information_from_henkilo(tyontekija_obj.henkilo)
            delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)
            vakajarjestaja_oid = vakajarjestaja.organisaatio_oid
            tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija_obj.henkilo)

            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyontekija, tyontekija_obj)
            [assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]
            if toimipaikka_oid:
                self._assign_toimipaikka_permissions(toimipaikka_oid, tyontekija_obj)
            delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)

    def perform_update(self, serializer):
        user = self.request.user
        with transaction.atomic():
            serializer.save(changed_by=user)

    def perform_destroy(self, tyontekija):
        with transaction.atomic():
            try:
                delete_object_permissions_explicitly(Tyontekija, tyontekija)
                vakajarjestaja_oid = tyontekija.vakajarjestaja.organisaatio_oid
                tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija.henkilo)
                [remove_object_level_permissions(vakajarjestaja_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]
                tyontekija.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyontekija. There are objects referencing it '
                                                 'that need to be deleted first.'})


class TilapainenHenkilostoViewSet(ObjectByTunnisteMixin, ModelViewSet):
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
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = filters.TilapainenHenkilostoFilter
    queryset = TilapainenHenkilosto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            tilapainenhenkilosto_obj = serializer.save(changed_by=user)
            vakajarjestaja_oid = tilapainenhenkilosto_obj.vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tilapainenhenkilosto_groups(vakajarjestaja_oid, TilapainenHenkilosto, tilapainenhenkilosto_obj)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(changed_by=user)

    def perform_destroy(self, tilapainenhenkilosto):
        with transaction.atomic():
            delete_object_permissions_explicitly(TilapainenHenkilosto, tilapainenhenkilosto)
            tilapainenhenkilosto.delete()


class TutkintoViewSet(ModelViewSet):
    """
    list:
        Nouda kaikki tutkinnot joita käyttäjä pystyy muokkaamaan. Kaikkien hakuun käytä /tutkinto-list-all

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
    filter_backends = None
    filterset_class = filters.TutkintoFilter
    queryset = Tutkinto.objects.all().order_by('id')

    def filter_queryset(self, queryset):
        if self.action == 'tutkinto_list_all':
            # We are allowing users to view all tutkinto without object level permission check.
            self.filter_backends = DjangoFilterBackend,
        else:
            self.filter_backends = ObjectPermissionsFilter, DjangoFilterBackend,
        return super().filter_queryset(queryset)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    @action(methods=['get'], detail=False, url_path='tutkinto-list-all', url_name='tutkinto_list_all')
    def tutkinto_list_all(self, request, *args, **kwargs):
        """
        Kaikkien henkilön tutkintojen hakuun.
        """
        # cached_list_response is permission check based
        return super().list(request, *args, **kwargs)

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
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        tutkinto = serializer.save(changed_by=user)
        delete_cache_keys_related_model('henkilo', tutkinto.henkilo.id)
        vakajarjestaja_oid = validated_data['vakajarjestaja'].organisaatio_oid
        assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, tutkinto)

        if toimipaikka_oid:
            assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto)

    def perform_destroy(self, tutkinto):
        henkilo = tutkinto.henkilo

        with transaction.atomic():
            delete_object_permissions_explicitly(Tutkinto, tutkinto)
            tutkinto.delete()
        delete_cache_keys_related_model('henkilo', henkilo.id)

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


class PalvelussuhdeViewSet(ObjectByTunnisteMixin, ModelViewSet):
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
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = PalvelussuhdeFilter
    queryset = Palvelussuhde.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        with transaction.atomic():
            user = self.request.user
            palvelussuhde = serializer.save(changed_by=user)
            delete_cache_keys_related_model('tyontekija', palvelussuhde.tyontekija.id)
            vakajarjestaja_oid = validated_data['tyontekija'].vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Palvelussuhde, palvelussuhde)
            if toimipaikka_oid:
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Palvelussuhde, palvelussuhde)

    def perform_update(self, serializer):
        user = self.request.user
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        palvelussuhde = serializer.save(changed_by=user)
        delete_cache_keys_related_model('palvelussuhde', palvelussuhde.id)

    def perform_destroy(self, palvelussuhde):
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        with transaction.atomic():
            delete_object_permissions_explicitly(Palvelussuhde, palvelussuhde)
            try:
                palvelussuhde.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete palvelussuhde. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('tyontekija', palvelussuhde.tyontekija.id)

    def _throw_if_not_all_tyoskentelypaikka_permissions(self):
        """
        User is required to have permission to all tyoskentelypaikkas related to palvelussuhde in order to modify it.
        Object level permission is still required.
        :return: None
        """
        user = self.request.user
        tyoskentelypaikat = self.get_object().tyoskentelypaikat.all()
        if any(not user.has_perm('change_tyoskentelypaikka', tyoskentelypaikka) for tyoskentelypaikka in tyoskentelypaikat):
            raise PermissionDenied('Modify actions requires permissions to all tyoskentelypaikkas.')


class TyoskentelypaikkaViewSet(ObjectByTunnisteMixin, ModelViewSet):
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
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
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
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        vakajarjestaja_oid = validated_data['palvelussuhde'].tyontekija.vakajarjestaja.organisaatio_oid
        tyontekija_tallentaja_group = 'HENKILOSTO_TYONTEKIJA_TALLENTAJA_{}'.format(vakajarjestaja_oid)
        if validated_data.get('kiertava_tyontekija_kytkin') and not is_user_permission(user, tyontekija_tallentaja_group):
            raise PermissionDenied('Vakajarjestaja level permissions required for kiertava tyontekija.')

        with transaction.atomic():
            tyoskentelypaikka = serializer.save(changed_by=user)
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyoskentelypaikka, tyoskentelypaikka)
            if tyoskentelypaikka.toimipaikka:
                toimipaikka_oid = tyoskentelypaikka.toimipaikka.organisaatio_oid
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyoskentelypaikka, tyoskentelypaikka)
                # Since it's allowed for vakatoimija level user to not provide toimipaikka earlier related objects this
                # needs to be filled here to make sure
                palvelussuhde = tyoskentelypaikka.palvelussuhde
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Palvelussuhde, palvelussuhde)
                pidemmatpoissaolot = palvelussuhde.pidemmatpoissaolot.all()
                [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempipoissaolo)
                 for pidempipoissaolo in pidemmatpoissaolot
                 ]
                tyontekija = palvelussuhde.tyontekija
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyontekija, tyontekija)
                # Add also permission to all taydennyskoulutukset for current jarjestaja
                taydennyskoulutukset = Taydennyskoulutus.objects.filter(tyontekijat__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
                 for taydennyskoulutus in taydennyskoulutukset
                 ]

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(changed_by=user)

    def perform_destroy(self, tyoskentelypaikka):
        with transaction.atomic():
            delete_object_permissions_explicitly(Tyoskentelypaikka, tyoskentelypaikka)
            try:
                tyoskentelypaikka.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyoskentelypaikka. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)


class PidempiPoissaoloViewSet(ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomObjectPermissions, )
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = PidempiPoissaoloFilter
    queryset = PidempiPoissaolo.objects.all().order_by('id')

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.path)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        with transaction.atomic():
            user = self.request.user
            pidempipoissaolo = serializer.save(changed_by=user)
            vakajarjestaja_oid = pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, PidempiPoissaolo, pidempipoissaolo)
            if toimipaikka_oid:
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempipoissaolo)
            tyontekija_toimipaikka_oids = pidempipoissaolo.palvelussuhde.tyoskentelypaikat.values_list('toimipaikka__organisaatio_oid', flat=True)
            [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempipoissaolo)
             for toimipaikka_oid in tyontekija_toimipaikka_oids
             ]
            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)

    def perform_update(self, serializer):
        user = self.request.user
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        serializer.save(changed_by=user)

    def perform_destroy(self, pidempipoissaolo):
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        with transaction.atomic():
            delete_object_permissions_explicitly(PidempiPoissaolo, pidempipoissaolo)
            try:
                pidempipoissaolo.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete pidempipoissaolo. There are objects referencing it '
                                                 'that need to be deleted first.'})
            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)

    def _throw_if_not_all_tyoskentelypaikka_permissions(self):
        """
        User is required to have permission to all tyoskentelypaikkas related to palvelussuhde in order to modify it.
        Object level permission is still required.
        :return: None
        """
        user = self.request.user
        tyoskentelypaikat = self.get_object().palvelussuhde.tyoskentelypaikat.all()
        if any(not user.has_perm('change_tyoskentelypaikka', tyoskentelypaikka) for tyoskentelypaikka in tyoskentelypaikat):
            raise PermissionDenied('Modify actions requires permissions to all tyoskentelypaikkas.')


class TaydennyskoulutusViewSet(ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki taydennyskoulutukset.

    create:
        Luo yksi uusi taydennyskoulutus.

    delete:
        Poista yksi taydennyskoulutus.

    retrieve:
        Nouda yksittäinen taydennyskoulutus.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä taydennyskoulutus-tietueesta.

    update:
        Päivitä yhden taydennyskoulutuksen kaikki kentät.
    """
    serializer_class = None
    permission_classes = (CustomObjectPermissions, )
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = TaydennyskoulutusFilter
    queryset = Taydennyskoulutus.objects.all().order_by('id')

    def get_serializer_class(self):
        request = self.request
        if request.method == 'PUT' or request.method == 'PATCH':
            return TaydennyskoulutusUpdateSerializer
        else:
            return TaydennyskoulutusSerializer

    def get_queryset(self):
        # For browsable
        if self.action == 'tyontekija_list':
            self.filterset_class = TaydennyskoulutusTyontekijaFilter
        else:
            self.filterset_class = TaydennyskoulutusFilter
        return self.queryset

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    @action(methods=['get'], detail=False, url_path='tyontekija-list', url_name='tyontekija_list')
    def tyontekija_list(self, request, *args, **kwargs):
        """
        Palauttaa kaikki tyontekijät joihin täydennyskoulutuskäyttäjällä on oikeus.
        """
        user = request.user
        queryset = TaydennyskoulutusTyontekija.objects.all().order_by('id')
        if not user.is_superuser:
            queryset, organisaatio_oids = filter_authorized_taydennyskoulutus_tyontekijat(queryset, user)
        tyontekija_filter = TaydennyskoulutusTyontekijaFilter(request.query_params, queryset, request=request)
        page = self.paginate_queryset(tyontekija_filter.qs)
        serializer = TaydennyskoulutusTyontekijaSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            taydennyskoulutus = serializer.save(changed_by=user)
            tyontekijat = taydennyskoulutus.tyontekijat
            if tyontekijat.exists:
                vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(tyontekijat)
                assign_object_permissions_to_taydennyskoulutus_groups(vakajarjestaja_oid, Taydennyskoulutus, taydennyskoulutus)
                toimipaikka_oids = (Toimipaikka.objects
                                    .filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                                    .values_list('organisaatio_oid', flat=True)
                                    )
                [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
                 for toimipaikka_oid in toimipaikka_oids]
                for tyontekija in tyontekijat.all():
                    delete_cache_keys_related_model('tyontekija', tyontekija.id)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        taydennyskoulutus = self.get_object()
        current_tyontekijat = taydennyskoulutus.tyontekijat
        # When doing full update (both put and patch) user needs permission to all previous tyontekijat
        if 'taydennyskoulutukset_tyontekijat' in validated_data:
            is_correct_taydennyskoulutus_tyontekija_permission(user, current_tyontekijat, throws=True)

        # Delete cache keys from old tyontekijat (some may be removed)
        for tyontekija in current_tyontekijat.all():
            delete_cache_keys_related_model('tyontekija', tyontekija.id)
        with transaction.atomic():
            updated_taydennyskoulutus = serializer.save(changed_by=user)

        # Delete cache keys from new tyontekijat (some may be added)
        for tyontekija in updated_taydennyskoulutus.tyontekijat.all():
            delete_cache_keys_related_model('tyontekija', tyontekija.id)

    def perform_destroy(self, taydennyskoulutus):
        user = self.request.user
        tyontekija_id_list = list(taydennyskoulutus.tyontekijat.values_list('id', flat=True))
        is_correct_taydennyskoulutus_tyontekija_permission(user, taydennyskoulutus.tyontekijat, throws=True)

        with transaction.atomic():
            delete_object_permissions_explicitly(Taydennyskoulutus, taydennyskoulutus)
            TaydennyskoulutusTyontekija.objects.filter(taydennyskoulutus=taydennyskoulutus).delete()
            taydennyskoulutus.delete()

            for tyontekija_id in tyontekija_id_list:
                delete_cache_keys_related_model('tyontekija', tyontekija_id)
