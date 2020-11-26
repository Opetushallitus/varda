import functools
import logging
import operator

import coreapi
import coreschema
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.schemas.coreapi import AutoSchema
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from varda import filters
from varda.cache import (cached_retrieve_response, delete_cache_keys_related_model, cached_list_response,
                         get_object_ids_for_user_by_model)
from varda.exceptions.conflict_error import ConflictError
from varda.models import (VakaJarjestaja, TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Z4_CasKayttoOikeudet)
from varda.permission_groups import (assign_object_permissions_to_tyontekija_groups,
                                     assign_object_permissions_to_tilapainenhenkilosto_groups,
                                     assign_object_permissions_to_taydennyskoulutus_groups)
from varda.permissions import (CustomObjectPermissions, delete_object_permissions_explicitly, is_user_permission,
                               is_correct_taydennyskoulutus_tyontekija_permission, get_tyontekija_vakajarjestaja_oid,
                               filter_authorized_taydennyskoulutus_tyontekijat_list, auditlog, auditlogclass,
                               permission_groups_in_organization, HenkilostohakuPermissions,
                               get_tyontekija_filters_for_taydennyskoulutus_groups,
                               get_permission_checked_pidempi_poissaolo_katselija_queryset_for_user,
                               get_permission_checked_pidempi_poissaolo_tallentaja_queryset_for_user,
                               toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add,
                               get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus)
from varda.serializers_henkilosto import (TyoskentelypaikkaSerializer, PalvelussuhdeSerializer,
                                          PidempiPoissaoloSerializer,
                                          TilapainenHenkilostoSerializer, TutkintoSerializer, TyontekijaSerializer,
                                          TyoskentelypaikkaUpdateSerializer, TaydennyskoulutusSerializer,
                                          TaydennyskoulutusUpdateSerializer, TaydennyskoulutusTyontekijaListSerializer,
                                          TyontekijaKoosteSerializer)
from varda.tasks import assign_taydennyskoulutus_permissions_for_all_toimipaikat_task


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
    """
    @DynamicAttrs
    """
    schema = TunnisteIdSchema()
    lookup_value_regex = '[^/]+'

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


@auditlogclass
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
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend, )
    filterset_class = filters.TyontekijaFilter
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
        tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija_obj.henkilo, vakajarjestaja=tyontekija_obj.vakajarjestaja)
        [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]

    def remove_address_information_from_henkilo(self, henkilo):
        """
        If henkilo is related only to Tyontekijat, we need to remove address information
        :param henkilo: Henkilo object linked to this Tyontekija
        """
        if not hasattr(henkilo, 'huoltaja'):
            henkilo.remove_address_information()
            henkilo.save()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        user = self.request.user
        vakajarjestaja = validated_data['vakajarjestaja']
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid
        self.return_tyontekija_if_already_created(validated_data, toimipaikka_oid)

        with transaction.atomic():
            try:
                tyontekija_obj = serializer.save(changed_by=user)
            except DjangoValidationError as error:
                # Catch Tyontekija model's UniqueConstraint, otherwise it will return 500
                if 'Tyontekija with this Henkilo and Vakajarjestaja already exists' in ' '.join(error.messages):
                    raise ValidationError({'tyontekija': ['tyontekija with this henkilo and vakajarjestaja pair already exists']})
                else:
                    raise error

            self.remove_address_information_from_henkilo(tyontekija_obj.henkilo)
            delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)
            vakajarjestaja_oid = vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyontekija, tyontekija_obj)
            if toimipaikka_oid:
                self._assign_toimipaikka_permissions(toimipaikka_oid, tyontekija_obj)
            delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)
            delete_cache_keys_related_model('vakajarjestaja', tyontekija_obj.vakajarjestaja.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tyontekija_obj.vakajarjestaja.id))

    def perform_update(self, serializer):
        user = self.request.user
        with transaction.atomic():
            tyontekija_obj = serializer.save(changed_by=user)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tyontekija_obj.vakajarjestaja.id))

    def perform_destroy(self, tyontekija):
        if Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo).exists():
            raise ValidationError({'detail': 'Cannot delete tyontekija. There are tutkinto objects referencing it '
                                             'that need to be deleted first.'})
        with transaction.atomic():
            try:
                delete_object_permissions_explicitly(Tyontekija, tyontekija)
                tyontekija.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyontekija. There are objects referencing it '
                                                 'that need to be deleted first.'})
            delete_cache_keys_related_model('henkilo', tyontekija.henkilo.id)
            delete_cache_keys_related_model('vakajarjestaja', tyontekija.vakajarjestaja.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tyontekija.vakajarjestaja.id))


@auditlogclass
class NestedTyontekijaKoosteViewSet(ObjectByTunnisteMixin, GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn työntekijän kooste
    """
    serializer_class = TyontekijaKoosteSerializer
    permission_classes = (HenkilostohakuPermissions, )
    queryset = Tyontekija.objects.all().order_by('id')

    def get_object(self):
        user = self.request.user
        tyontekija = super(NestedTyontekijaKoosteViewSet, self).get_object()

        # Raise 404 if user doesn't have object level permissions to tyontekija, or if tyontekija is not
        # linked to one of user's taydennyskoulutus groups
        tyontekija_taydennyskoulutus_filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(user)
        if (user.has_perm('view_tyontekija', tyontekija) or
                Tyontekija.objects.filter(Q(pk=tyontekija.id) & tyontekija_taydennyskoulutus_filters).exists()):
            return tyontekija
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        # Enable support for ObjectByTunnisteMixin
        self.kwargs['pk'] = self.kwargs['tyontekija_pk']

        user = request.user
        tyontekija = self.get_object()
        tyontekija_data = {
            'tyontekija': tyontekija
        }

        # Get palvelussuhteet
        palvelussuhde_filter = Q(tyontekija=tyontekija)
        tyontekija_organization_groups_qs = permission_groups_in_organization(user, tyontekija.vakajarjestaja.organisaatio_oid,
                                                                              [Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                                                                               Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA])
        if not user.is_superuser and not tyontekija_organization_groups_qs.exists():
            palvelussuhde_filter = palvelussuhde_filter & Q(id__in=get_object_ids_for_user_by_model(user, 'palvelussuhde'))

        palvelussuhteet = Palvelussuhde.objects.filter(palvelussuhde_filter).distinct().order_by('-alkamis_pvm')
        tyontekija_data['palvelussuhteet'] = palvelussuhteet

        # Get täydennyskoulutukset
        taydennyskoulutus_filter = Q(tyontekija=tyontekija)
        taydennyskoulutus_organization_groups_qs = permission_groups_in_organization(user, tyontekija.vakajarjestaja.organisaatio_oid,
                                                                                     [Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
                                                                                      Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA])
        if not user.is_superuser and not taydennyskoulutus_organization_groups_qs.exists():
            taydennyskoulutus_filter = taydennyskoulutus_filter & Q(taydennyskoulutus__id__in=get_object_ids_for_user_by_model(user, 'taydennyskoulutus'))

        taydennyskoulutukset = (TaydennyskoulutusTyontekija.objects
                                .filter(taydennyskoulutus_filter)
                                .distinct()
                                .order_by('-taydennyskoulutus__suoritus_pvm'))
        tyontekija_data['taydennyskoulutukset'] = taydennyskoulutukset

        # Get tutkinnot
        tutkinto_filter = Q(henkilo=tyontekija.henkilo) & Q(vakajarjestaja=tyontekija.vakajarjestaja)
        if not user.is_superuser:
            tutkinto_filter = tutkinto_filter & Q(id__in=get_object_ids_for_user_by_model(user, 'tutkinto'))

        tutkinnot = set(Tutkinto.objects
                        .filter(tutkinto_filter)
                        .distinct()
                        .order_by('-luonti_pvm'))
        tyontekija_data['tutkinnot'] = tutkinnot

        return Response(self.get_serializer(tyontekija_data).data)


@auditlogclass
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
            cache.delete('vakajarjestaja_yhteenveto_' + str(tilapainenhenkilosto_obj.vakajarjestaja.id))

    def perform_update(self, serializer):
        user = self.request.user
        tilapainenhenkilosto = serializer.save(changed_by=user)
        cache.delete('vakajarjestaja_yhteenveto_' + str(tilapainenhenkilosto.vakajarjestaja.id))

    def perform_destroy(self, tilapainenhenkilosto):
        with transaction.atomic():
            delete_object_permissions_explicitly(TilapainenHenkilosto, tilapainenhenkilosto)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tilapainenhenkilosto.vakajarjestaja.id))
            tilapainenhenkilosto.delete()


@auditlogclass
class TutkintoViewSet(CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, ListModelMixin, GenericViewSet):
    """
    list:
        Nouda kaikki tutkinnot joita käyttäjä pystyy muokkaamaan.

    create:
        Luo yksi uusi tutkinto.

    delete:
        Poista yksi tutkinto.

    retrieve:
        Nouda yksittäinen tutkinto.
    """
    serializer_class = TutkintoSerializer
    permission_classes = (CustomObjectPermissions, )
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend,)
    filterset_class = filters.TutkintoFilter
    queryset = Tutkinto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def return_henkilo_already_has_tutkinto(self, validated_data):
        tutkinto_condition = Q(henkilo=validated_data['henkilo'],
                               tutkinto_koodi=validated_data['tutkinto_koodi'],
                               vakajarjestaja=validated_data['vakajarjestaja'])
        tutkinto = Tutkinto.objects.filter(tutkinto_condition).first()
        if tutkinto:
            # Toimipaikka user might be trying to add existing tutkinto he simply doesn't have permissions
            self._assign_toimipaikka_permissions(tutkinto, validated_data)
            raise ConflictError(self.get_serializer(tutkinto).data, status_code=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        self.return_henkilo_already_has_tutkinto(validated_data)
        tutkinto = serializer.save(changed_by=user)
        delete_cache_keys_related_model('henkilo', tutkinto.henkilo.id)

        vakajarjestaja_oid = validated_data['vakajarjestaja'].organisaatio_oid
        assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, tutkinto)
        self._assign_toimipaikka_permissions(tutkinto, validated_data)
        cache.delete('vakajarjestaja_yhteenveto_' + str(validated_data['vakajarjestaja'].id))

    def _assign_toimipaikka_permissions(self, tutkinto, validated_data):
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid
        if toimipaikka_oid:
            assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto)

    def perform_destroy(self, tutkinto):
        henkilo = tutkinto.henkilo
        tutkinto_koodi = tutkinto.tutkinto_koodi
        vakajarjestaja = tutkinto.vakajarjestaja
        palvelussuhde_condition = Q(tyontekija__vakajarjestaja=vakajarjestaja,
                                    tutkinto_koodi=tutkinto_koodi,
                                    tyontekija__henkilo=henkilo,
                                    )
        if Palvelussuhde.objects.filter(palvelussuhde_condition).exists():
            raise ValidationError({'detail': 'Cannot delete tutkinto. There are palvelussuhde objects referencing it '
                                             'that need to be deleted first.'})
        with transaction.atomic():
            delete_object_permissions_explicitly(Tutkinto, tutkinto)
            tutkinto.delete()
            delete_cache_keys_related_model('henkilo', henkilo.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))

    @action(methods=['delete'], detail=False)
    def delete(self, request):
        """
        Custom delete method for deleting by henkilo_id or henkilo_oid and tutkinto_koodi
        /api/henkilosto/v1/tutkinnot/delete/

        filter:
            henkilo_id=number
            henkilo_oid=string
            vakajarjestaja_id=number
            vakajarjestaja_oid=string
            tutkinto_koodi=string

            esim. /api/henkilosto/v1/tutkinnot/delete/?henkilo_id=1&tutkinto_koodi=2&vakajarjestaja_id=1
        """
        query_params = self.request.query_params
        henkilo_id = query_params.get('henkilo_id', None)
        henkilo_oid = query_params.get('henkilo_oid', None)
        vakajarjestaja_id = query_params.get('vakajarjestaja_id', None)
        vakajarjestaja_oid = query_params.get('vakajarjestaja_oid', None)
        tutkinto_koodi = query_params.get('tutkinto_koodi', None)

        if (not henkilo_id and not henkilo_oid) or not tutkinto_koodi or (not vakajarjestaja_id and not vakajarjestaja_oid):
            raise Http404

        if henkilo_id:
            henkilo_filter = {'henkilo__id': henkilo_id}
        else:
            henkilo_filter = {'henkilo__henkilo_oid': henkilo_oid}

        if vakajarjestaja_id:
            henkilo_filter['vakajarjestaja'] = vakajarjestaja_id
        else:
            henkilo_filter['vakajarjestaja__organisaatio_oid'] = vakajarjestaja_oid

        tutkinto_obj = get_object_or_404(Tutkinto.objects.all(), **henkilo_filter, tutkinto_koodi=tutkinto_koodi)
        self.perform_destroy(tutkinto_obj)

        return Response(status=status.HTTP_200_OK)


@auditlogclass
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
    filterset_class = filters.PalvelussuhdeFilter
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
            cache.delete('vakajarjestaja_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_update(self, serializer):
        user = self.request.user
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        palvelussuhde = serializer.save(changed_by=user)
        cache.delete('vakajarjestaja_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

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
            cache.delete('vakajarjestaja_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

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


@auditlogclass
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
    filterset_class = filters.TyoskentelypaikkaFilter
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
                # Since it's allowed for vakatoimija level user to not provide toimipaikka earlier than
                # tyoskentelypaikka in related objects toimipaikka permissions need to be filled here to make sure
                palvelussuhde = tyoskentelypaikka.palvelussuhde
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Palvelussuhde, palvelussuhde)
                # toimipaikka permissions are not added to pidempipoissaolo objects until they are directly linked to tyoskentelypaikka
                # CSCVARDA-1868
                tyontekija = palvelussuhde.tyontekija
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyontekija, tyontekija)
                tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija.henkilo, vakajarjestaja=tyontekija.vakajarjestaja)
                [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)

    def perform_update(self, serializer):
        user = self.request.user
        tyoskentelypaikka = serializer.save(changed_by=user)
        cache.delete('vakajarjestaja_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_destroy(self, tyoskentelypaikka):
        tyontekija = tyoskentelypaikka.palvelussuhde.tyontekija
        tehtavanimike = tyoskentelypaikka.tehtavanimike_koodi
        taydennyskoulutus_qs = TaydennyskoulutusTyontekija.objects.filter(tyontekija=tyontekija,
                                                                          tehtavanimike_koodi=tehtavanimike)
        tyoskentelypaikka_qs = (Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija,
                                                                 tehtavanimike_koodi=tehtavanimike)
                                .exclude(id=tyoskentelypaikka.id))

        if taydennyskoulutus_qs.exists() and not tyoskentelypaikka_qs.exists():
            raise ValidationError({'detail': 'Cannot delete tyoskentelypaikka. Taydennyskoulutukset with this '
                                             'tehtavanimike_koodi must be deleted first.'})

        with transaction.atomic():
            delete_object_permissions_explicitly(Tyoskentelypaikka, tyoskentelypaikka)
            try:
                tyoskentelypaikka.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete tyoskentelypaikka. There are objects referencing it '
                                                 'that need to be deleted first.'})

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)


@auditlogclass
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
    filter_backends = (DjangoFilterBackend, )
    filterset_class = filters.PidempiPoissaoloFilter
    queryset = PidempiPoissaolo.objects.none()

    def get_queryset(self):
        user = self.request.user
        method = self.request.method
        if method == 'GET' or method == 'RETRIEVE':
            queryset = get_permission_checked_pidempi_poissaolo_katselija_queryset_for_user(user).order_by('id')
        else:
            queryset = get_permission_checked_pidempi_poissaolo_tallentaja_queryset_for_user(user).order_by('id')
        return queryset

    def perform_create(self, serializer):

        with transaction.atomic():
            user = self.request.user
            validated_data = serializer.validated_data
            vakajarjestaja_oid = validated_data['palvelussuhde'].tyontekija.vakajarjestaja.organisaatio_oid
            if not toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add(user, vakajarjestaja_oid, validated_data):
                raise ValidationError({'tyoskentelypaikka': ['no matching tyoskentelypaikka exists']})
            pidempipoissaolo = serializer.save(changed_by=user)
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, PidempiPoissaolo, pidempipoissaolo)
            # toimipaikka permissions are not added to pidempipoissaolo objects until they are directly linked to tyoskentelypaikkas
            # CSCVARDA-1868
            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_update(self, serializer):
        user = self.request.user
        queryset = self.get_queryset()

        if not queryset.filter(id=self.get_object().id):
            raise PermissionDenied('user does not have permission to change this object')
        pidempipoissaolo = serializer.save(changed_by=user)
        delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
        cache.delete('vakajarjestaja_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_destroy(self, pidempipoissaolo):
        queryset = self.get_queryset()

        if not queryset.filter(id=self.get_object().id):
            raise PermissionDenied('user does not have permission to delete this object')
        with transaction.atomic():
            delete_object_permissions_explicitly(PidempiPoissaolo, pidempipoissaolo)
            try:
                pidempipoissaolo.delete()
            except ProtectedError:
                raise ValidationError({'detail': 'Cannot delete pidempipoissaolo. There are objects referencing it '
                                                 'that need to be deleted first.'})
            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))


@auditlogclass
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
    filterset_class = filters.TaydennyskoulutusFilter
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
            self.filterset_class = filters.TaydennyskoulutusTyontekijaListFilter
        else:
            self.filterset_class = filters.TaydennyskoulutusFilter
        return self.queryset

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    @auditlog
    @action(methods=['get'], detail=False, url_path='tyontekija-list', url_name='tyontekija_list')
    def tyontekija_list(self, request, *args, **kwargs):
        """
        Palauttaa kaikki tyontekijät joihin täydennyskoulutuskäyttäjällä on oikeus.
        """
        user = request.user
        queryset = Tyontekija.objects.all().prefetch_related('palvelussuhteet').order_by('id')
        if not user.is_superuser:
            queryset, organisaatio_oids = filter_authorized_taydennyskoulutus_tyontekijat_list(queryset, user)
        tyontekija_filter = filters.TaydennyskoulutusTyontekijaListFilter(request.query_params, queryset, request=request)
        page = self.paginate_queryset(tyontekija_filter.qs)
        serializer = TaydennyskoulutusTyontekijaListSerializer(page, many=True, context=self.get_serializer_context())
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

                # Assign toimipaikka level permissions to toimipaikat that are related to this taydennyskoulutus,
                # other toimipaikka level permissions are set in a celery task
                tyontekija_id_list, toimipaikka_oid_list_list = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(
                    taydennyskoulutus.taydennyskoulutukset_tyontekijat.all()
                )
                toimipaikka_oid_list_flat = functools.reduce(operator.iconcat, toimipaikka_oid_list_list, [])
                [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
                 for toimipaikka_oid in set(toimipaikka_oid_list_flat)]

                for tyontekija in tyontekijat.all():
                    delete_cache_keys_related_model('tyontekija', tyontekija.id)
                vakajarjestaja_obj = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
                cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja_obj.id))

                # Assign permissions for all toimipaikat of vakajarjestaja in a task so that it doesn't block execution
                transaction.on_commit(lambda: assign_taydennyskoulutus_permissions_for_all_toimipaikat_task
                                      .delay(vakajarjestaja_oid, taydennyskoulutus.id))

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        taydennyskoulutus = self.get_object()

        if 'taydennyskoulutukset_tyontekijat' in validated_data:
            # When doing full update (both put and patch) user needs permission to all previous tyontekijat
            is_correct_taydennyskoulutus_tyontekija_permission(user,
                                                               taydennyskoulutus.taydennyskoulutukset_tyontekijat.all(),
                                                               throws=True)

        with transaction.atomic():
            # Delete cache keys from old tyontekijat (some may be removed)
            for tyontekija in taydennyskoulutus.tyontekijat.all():
                delete_cache_keys_related_model('tyontekija', tyontekija.id)

            updated_taydennyskoulutus = serializer.save(changed_by=user)

            # Delete cache keys from new tyontekijat (some may be added)
            tyontekijat = updated_taydennyskoulutus.tyontekijat.all()
            for tyontekija in tyontekijat:
                delete_cache_keys_related_model('tyontekija', tyontekija.id)

            vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(tyontekijat)
            vakajarjestaja_obj = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja_obj.id))

    def perform_destroy(self, taydennyskoulutus):
        user = self.request.user
        tyontekija_id_list = list(taydennyskoulutus.tyontekijat.values_list('id', flat=True))
        is_correct_taydennyskoulutus_tyontekija_permission(user,
                                                           taydennyskoulutus.taydennyskoulutukset_tyontekijat.all(),
                                                           throws=True)

        with transaction.atomic():
            delete_object_permissions_explicitly(Taydennyskoulutus, taydennyskoulutus)
            vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(taydennyskoulutus.tyontekijat)
            TaydennyskoulutusTyontekija.objects.filter(taydennyskoulutus=taydennyskoulutus).delete()
            taydennyskoulutus.delete()

            for tyontekija_id in tyontekija_id_list:
                delete_cache_keys_related_model('tyontekija', tyontekija_id)

            vakajarjestaja_obj = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja_obj.id))
