import logging

from django.core.cache import cache
from django.db import transaction
from django.db.models import BooleanField, Case, Exists, F, OuterRef, ProtectedError, Q, Value, When
from django.db.models.functions import Lower
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from varda import filters
from varda.cache import delete_cache_keys_related_model, cached_list_response, get_object_ids_for_user_by_model
from varda.enums.error_messages import ErrorMessages
from varda.exceptions.conflict_error import ConflictError
from varda.misc import flatten_nested_list
from varda.misc_viewsets import IncreasedModifyThrottleMixin, ObjectByTunnisteMixin
from varda.models import (Organisaatio, TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Z4_CasKayttoOikeudet)
from varda.permission_groups import (assign_object_permissions_to_tyontekija_groups,
                                     assign_object_permissions_to_tilapainenhenkilosto_groups,
                                     assign_object_permissions_to_taydennyskoulutus_groups)
from varda.permissions import (CustomModelPermissions, delete_object_permissions_explicitly, is_user_permission,
                               is_correct_taydennyskoulutus_tyontekija_permission, get_tyontekija_vakajarjestaja_oid,
                               filter_authorized_taydennyskoulutus_tyontekijat_list, auditlog, auditlogclass,
                               user_belongs_to_correct_groups, user_permission_groups_in_organization,
                               HenkilostohakuPermissions, get_tyontekija_filters_for_taydennyskoulutus_groups,
                               toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add,
                               get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus, is_oph_staff,
                               assign_tyontekija_henkilo_permissions, assign_tyoskentelypaikka_henkilo_permissions,
                               CustomObjectPermissions, get_available_tehtavanimike_codes_for_user)
from varda.request_logging import request_log_viewset_decorator_factory
from varda.serializers_henkilosto import (TaydennyskoulutusCreateV2Serializer, TaydennyskoulutusUpdateV2Serializer,
                                          TaydennyskoulutusV2Serializer,
                                          TyoskentelypaikkaSerializer, PalvelussuhdeSerializer,
                                          PidempiPoissaoloSerializer, TilapainenHenkilostoSerializer,
                                          TutkintoSerializer, TyontekijaSerializer, TyoskentelypaikkaUpdateSerializer,
                                          TaydennyskoulutusSerializer, TaydennyskoulutusUpdateSerializer,
                                          TaydennyskoulutusTyontekijaListSerializer, TyontekijaKoosteSerializer)
from varda.tasks import assign_taydennyskoulutus_permissions_for_all_toimipaikat_task, update_henkilo_data_by_oid

logger = logging.getLogger(__name__)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=[])
class TyontekijaViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.TyontekijaFilter
    queryset = Tyontekija.objects.all().order_by('id')

    def return_tyontekija_if_already_created(self, validated_data, toimipaikka_oid):
        q_obj = Q(henkilo=validated_data['henkilo'], vakajarjestaja=validated_data['vakajarjestaja'])
        tyontekija_obj = Tyontekija.objects.filter(q_obj).first()
        if tyontekija_obj:
            if toimipaikka_oid:
                self._assign_toimipaikka_permissions(toimipaikka_oid, tyontekija_obj)
                # Assign Toimipaikka level permissions to Henkilo object
                assign_tyontekija_henkilo_permissions(tyontekija_obj, user=self.request.user,
                                                      toimipaikka_oid=toimipaikka_oid)
            if (validated_data['lahdejarjestelma'] != tyontekija_obj.lahdejarjestelma or
                    validated_data.get('tunniste', None) != tyontekija_obj.tunniste):
                # If lahdejarjestelma or tunniste have been changed, update change
                tyontekija_obj.lahdejarjestelma = validated_data['lahdejarjestelma']
                tyontekija_obj.tunniste = validated_data.get('tunniste', None)
                tyontekija_obj.save()
            # Make sure that ConflictError is not raised inside a transaction, otherwise permission changes
            # are rolled back
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
        if (not hasattr(henkilo, 'huoltaja') and
                (henkilo.kotikunta_koodi or henkilo.katuosoite or henkilo.postinumero or henkilo.postitoimipaikka)):
            henkilo.remove_address_information()
            henkilo.save()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        user = self.request.user
        vakajarjestaja = validated_data['vakajarjestaja']
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid
        self.return_tyontekija_if_already_created(validated_data, toimipaikka_oid)

        try:
            with transaction.atomic():
                tyontekija_obj = serializer.save()

                vakajarjestaja_oid = vakajarjestaja.organisaatio_oid
                assign_tyontekija_henkilo_permissions(tyontekija_obj, user=user, toimipaikka_oid=toimipaikka_oid)
                assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyontekija, tyontekija_obj)
                if toimipaikka_oid:
                    self._assign_toimipaikka_permissions(toimipaikka_oid, tyontekija_obj)

                delete_cache_keys_related_model('henkilo', tyontekija_obj.henkilo.id)
                delete_cache_keys_related_model('organisaatio', tyontekija_obj.vakajarjestaja.id)
                cache.delete('organisaatio_yhteenveto_' + str(tyontekija_obj.vakajarjestaja.id))

                henkilo = tyontekija_obj.henkilo
                self.remove_address_information_from_henkilo(henkilo)
                if henkilo.henkilo_oid and not henkilo.syntyma_pvm:
                    # If Henkilo has only been related to a Huoltaja, syntyma_pvm field may have been removed,
                    # so fetch Henkilo data again from ONR
                    update_henkilo_data_by_oid.delay(henkilo.henkilo_oid, henkilo.id)
        except ValidationError as validation_error:
            if 'TY005' in str(validation_error.detail):
                # Try to return the existing Tyontekija object again
                self.return_tyontekija_if_already_created(validated_data, toimipaikka_oid)
            raise validation_error

    def perform_update(self, serializer):
        with transaction.atomic():
            tyontekija_obj = serializer.save()
            cache.delete('organisaatio_yhteenveto_' + str(tyontekija_obj.vakajarjestaja.id))

    def perform_destroy(self, tyontekija):
        if Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo).exists():
            raise ValidationError({'errors': [ErrorMessages.TY001.value]})
        with transaction.atomic():
            try:
                delete_object_permissions_explicitly(Tyontekija, tyontekija)
                tyontekija.delete()
            except ProtectedError:
                raise ValidationError({'errors': [ErrorMessages.TY002.value]})
            delete_cache_keys_related_model('henkilo', tyontekija.henkilo.id)
            delete_cache_keys_related_model('organisaatio', tyontekija.vakajarjestaja.id)
            cache.delete('organisaatio_yhteenveto_' + str(tyontekija.vakajarjestaja.id))

    @action(methods=['delete'], detail=True, url_path='delete-all')
    def delete_all(self, request, pk=None):
        """
        Poista yhden tyontekijän kaikki henkilöstötiedot (palvelussuhteet, tyoskentelypaikat, pidemmät poissaolot,
        täydennyskoulutukset, tutkinnot)
        """
        user = self.request.user
        instance = self.get_object()

        # Taydennyskoulutus permissions are more complicated and require custom logic
        taydennyskoulutus_tyontekija_qs = instance.taydennyskoulutukset_tyontekijat.all()
        has_taydennyskoulutus_permissions = is_correct_taydennyskoulutus_tyontekija_permission(
            user, taydennyskoulutus_tyontekija_qs, throws=False
        )
        if not has_taydennyskoulutus_permissions:
            # Raise PermissionDenied if user does not have delete permission to all TaydennyskoulutusTyontekija objects
            raise PermissionDenied({'errors': [ErrorMessages.PE002.value]})

        tyoskentelypaikka_qs = Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=instance).distinct('id')
        pidempi_poissaolo_qs = PidempiPoissaolo.objects.filter(palvelussuhde__tyontekija=instance).distinct('id')
        palvelussuhde_qs = instance.palvelussuhteet.distinct('id')
        tutkinto_qs = Tutkinto.objects.filter(vakajarjestaja=instance.vakajarjestaja, henkilo=instance.henkilo).distinct('id')
        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(tyontekijat=instance).distinct('id')

        with transaction.atomic():
            for object_list in [tyoskentelypaikka_qs, pidempi_poissaolo_qs, palvelussuhde_qs, tutkinto_qs,
                                taydennyskoulutus_qs]:
                for object_instance in object_list:
                    # Verify that user has permission to delete object
                    delete_permission = f'delete_{type(object_instance).get_name()}'
                    if not user.has_perm(delete_permission, object_instance):
                        raise PermissionDenied({'errors': [ErrorMessages.PE002.value]})
                    if type(object_instance) == Taydennyskoulutus:
                        # Custom logic for Taydennyskoulutus objects
                        object_instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=instance).delete()
                        if object_instance.taydennyskoulutukset_tyontekijat.all().count() == 0:
                            # Taydennyskoulutus object did not have other related Tyontekija objects
                            object_instance.delete()
                    else:
                        object_instance.delete()
            instance.delete()
            delete_cache_keys_related_model('henkilo', instance.henkilo.id)
            delete_cache_keys_related_model('organisaatio', instance.vakajarjestaja.id)
            cache.delete('organisaatio_yhteenveto_' + str(instance.vakajarjestaja.id))
        return Response(status=status.HTTP_204_NO_CONTENT)


@auditlogclass
class NestedTyontekijaKoosteViewSet(ObjectByTunnisteMixin, GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn työntekijän kooste
    """
    serializer_class = TyontekijaKoosteSerializer
    permission_classes = (HenkilostohakuPermissions, )
    queryset = Tyontekija.objects.all().order_by('id')
    pagination_class = None

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

    @swagger_auto_schema(responses={status.HTTP_200_OK: TyontekijaKoosteSerializer(many=False)})
    def list(self, request, *args, **kwargs):
        # Enable support for ObjectByTunnisteMixin
        self.kwargs['pk'] = self.kwargs['tyontekija_pk']

        user = request.user
        is_superuser_or_oph_staff = user.is_superuser or is_oph_staff(user)

        tyontekija = self.get_object()
        tyontekija_data = {
            'tyontekija': tyontekija
        }

        # Get palvelussuhteet
        palvelussuhde_filter = Q(tyontekija=tyontekija)
        tyontekija_organization_groups_qs = user_permission_groups_in_organization(user, tyontekija.vakajarjestaja.organisaatio_oid,
                                                                                   [Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                                                                                    Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA])
        if not is_superuser_or_oph_staff and not tyontekija_organization_groups_qs.exists():
            palvelussuhde_filter = palvelussuhde_filter & Q(id__in=get_object_ids_for_user_by_model(user, 'palvelussuhde'))

        palvelussuhteet = Palvelussuhde.objects.filter(palvelussuhde_filter).distinct().order_by('-alkamis_pvm')
        tyontekija_data['palvelussuhteet'] = palvelussuhteet

        # Get täydennyskoulutukset
        taydennyskoulutus_filter = Q(tyontekija=tyontekija)
        taydennyskoulutus_organization_groups_qs = user_permission_groups_in_organization(user, tyontekija.vakajarjestaja.organisaatio_oid,
                                                                                          [Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
                                                                                           Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA])
        available_tehtavanimike_codes = [code.lower() for code in get_available_tehtavanimike_codes_for_user(user, tyontekija)]
        if not is_superuser_or_oph_staff and not taydennyskoulutus_organization_groups_qs.exists():
            taydennyskoulutus_id_list = get_object_ids_for_user_by_model(user, 'taydennyskoulutus')
            taydennyskoulutus_filter &= Q(taydennyskoulutus__id__in=taydennyskoulutus_id_list)
            if not user_belongs_to_correct_groups(user, tyontekija.vakajarjestaja, accept_toimipaikka_permission=True,
                                                  permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA]):
                # User does not have add_taydennyskoulutus permission in Toimipaikka of Vakajarjestaja so return only
                # TaydennyskoulutusTyontekija objects that have correct tehtavanimike_koodi
                taydennyskoulutus_filter &= Q(tehtavanimike_koodi__in=available_tehtavanimike_codes)

        taydennyskoulutukset = (
            TaydennyskoulutusTyontekija.objects.filter(taydennyskoulutus_filter).annotate(
                contains_other_tyontekija=Exists(
                    TaydennyskoulutusTyontekija.objects
                    .filter(taydennyskoulutus=OuterRef('taydennyskoulutus'))
                    .exclude(tyontekija=tyontekija)
                ),
                tehtavanimike_koodi_lower=Lower(F('tehtavanimike_koodi')),
                read_only=Case(
                    When(
                        tehtavanimike_koodi_lower__in=available_tehtavanimike_codes,
                        then=Value(False)
                    ),
                    output_field=BooleanField(),
                    default=Value(True)
                )
            )
            .order_by('-taydennyskoulutus__suoritus_pvm')
        )
        tyontekija_data['taydennyskoulutukset'] = taydennyskoulutukset

        # Get tutkinnot
        tutkinto_filter = Q(henkilo=tyontekija.henkilo) & Q(vakajarjestaja=tyontekija.vakajarjestaja)
        if not is_superuser_or_oph_staff and not tyontekija_organization_groups_qs.exists():
            tutkinto_filter = tutkinto_filter & Q(id__in=get_object_ids_for_user_by_model(user, 'tutkinto'))

        tutkinnot = set(Tutkinto.objects
                        .filter(tutkinto_filter)
                        .distinct()
                        .order_by('-luonti_pvm'))
        tyontekija_data['tutkinnot'] = tutkinnot

        return Response(self.get_serializer(tyontekija_data).data)


@auditlogclass
@request_log_viewset_decorator_factory()
class TilapainenHenkilostoViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.TilapainenHenkilostoFilter
    queryset = TilapainenHenkilosto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def perform_create(self, serializer):
        with transaction.atomic():
            tilapainenhenkilosto_obj = serializer.save()
            vakajarjestaja_oid = tilapainenhenkilosto_obj.vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tilapainenhenkilosto_groups(vakajarjestaja_oid, TilapainenHenkilosto, tilapainenhenkilosto_obj)
            cache.delete('organisaatio_yhteenveto_' + str(tilapainenhenkilosto_obj.vakajarjestaja.id))

    def perform_update(self, serializer):
        tilapainenhenkilosto = serializer.save()
        cache.delete('organisaatio_yhteenveto_' + str(tilapainenhenkilosto.vakajarjestaja.id))

    def perform_destroy(self, tilapainenhenkilosto):
        with transaction.atomic():
            delete_object_permissions_explicitly(TilapainenHenkilosto, tilapainenhenkilosto)
            cache.delete('organisaatio_yhteenveto_' + str(tilapainenhenkilosto.vakajarjestaja.id))
            tilapainenhenkilosto.delete()


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['henkilo'])
class TutkintoViewSet(IncreasedModifyThrottleMixin, CreateModelMixin, RetrieveModelMixin, DestroyModelMixin,
                      ListModelMixin, GenericViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.TutkintoFilter
    queryset = Tutkinto.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def return_henkilo_already_has_tutkinto(self, validated_data):
        tutkinto_condition = Q(henkilo=validated_data['henkilo'],
                               tutkinto_koodi=validated_data['tutkinto_koodi'],
                               vakajarjestaja=validated_data['vakajarjestaja'])
        tutkinto = Tutkinto.objects.filter(tutkinto_condition).first()
        if tutkinto:
            # Toimipaikka user might be trying to add existing tutkinto he simply doesn't have permissions
            self._assign_toimipaikka_permissions(tutkinto, validated_data)
            # Make sure that ConflictError is not raised inside a transaction, otherwise permission changes
            # are rolled back
            raise ConflictError(self.get_serializer(tutkinto).data, status_code=status.HTTP_200_OK)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        self.return_henkilo_already_has_tutkinto(validated_data)
        tutkinto = serializer.save()
        delete_cache_keys_related_model('henkilo', tutkinto.henkilo.id)

        vakajarjestaja_oid = validated_data['vakajarjestaja'].organisaatio_oid
        assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tutkinto, tutkinto)
        self._assign_toimipaikka_permissions(tutkinto, validated_data)
        self._assign_all_toimipaikka_permissions(tutkinto)
        cache.delete('organisaatio_yhteenveto_' + str(validated_data['vakajarjestaja'].id))

    def _assign_toimipaikka_permissions(self, tutkinto, validated_data):
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid
        if toimipaikka_oid:
            assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto)

    def _assign_all_toimipaikka_permissions(self, tutkinto):
        tyontekija = Tyontekija.objects.filter(vakajarjestaja=tutkinto.vakajarjestaja, henkilo=tutkinto.henkilo).first()
        if tyontekija:
            oid_set = set(Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija)
                          .values_list('toimipaikka__organisaatio_oid', flat=True))
            oid_set.discard(None)
            for oid in oid_set:
                assign_object_permissions_to_tyontekija_groups(oid, Tutkinto, tutkinto)

    def perform_destroy(self, tutkinto):
        henkilo = tutkinto.henkilo
        tutkinto_koodi = tutkinto.tutkinto_koodi
        vakajarjestaja = tutkinto.vakajarjestaja
        palvelussuhde_condition = Q(tyontekija__vakajarjestaja=vakajarjestaja,
                                    tutkinto_koodi=tutkinto_koodi,
                                    tyontekija__henkilo=henkilo,
                                    )
        if Palvelussuhde.objects.filter(palvelussuhde_condition).exists():
            raise ValidationError({'errors': [ErrorMessages.TU001.value]})
        with transaction.atomic():
            delete_object_permissions_explicitly(Tutkinto, tutkinto)
            tutkinto.delete()
            delete_cache_keys_related_model('henkilo', henkilo.id)
            cache.delete('organisaatio_yhteenveto_' + str(vakajarjestaja.id))

    @action(methods=['delete'], detail=False)
    @swagger_auto_schema(manual_parameters=[
        openapi.Parameter('henkilo_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter('henkilo_oid', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        openapi.Parameter('vakajarjestaja_id', openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        openapi.Parameter('vakajarjestaja_oid', openapi.IN_QUERY, type=openapi.TYPE_STRING),
        openapi.Parameter('tutkinto_koodi', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=True),
    ])
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

        # Set lookup arg so that get_object() can be used in request logging
        self.kwargs['pk'] = tutkinto_obj.id

        self.perform_destroy(tutkinto_obj)
        return Response(status=status.HTTP_204_NO_CONTENT)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['tyontekija'])
class PalvelussuhdeViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.PalvelussuhdeFilter
    queryset = Palvelussuhde.objects.all().order_by('id')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        with transaction.atomic():
            palvelussuhde = serializer.save()
            delete_cache_keys_related_model('tyontekija', palvelussuhde.tyontekija.id)
            vakajarjestaja_oid = validated_data['tyontekija'].vakajarjestaja.organisaatio_oid
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Palvelussuhde, palvelussuhde)
            if toimipaikka_oid:
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Palvelussuhde, palvelussuhde)
            cache.delete('organisaatio_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_update(self, serializer):
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        palvelussuhde = serializer.save()
        cache.delete('organisaatio_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_destroy(self, palvelussuhde):
        self._throw_if_not_all_tyoskentelypaikka_permissions()
        with transaction.atomic():
            delete_object_permissions_explicitly(Palvelussuhde, palvelussuhde)
            try:
                palvelussuhde.delete()
            except ProtectedError:
                raise ValidationError({'errors': [ErrorMessages.PS001.value]})

            delete_cache_keys_related_model('tyontekija', palvelussuhde.tyontekija.id)
            cache.delete('organisaatio_yhteenveto_' + str(palvelussuhde.tyontekija.vakajarjestaja.id))

    def _throw_if_not_all_tyoskentelypaikka_permissions(self):
        """
        User is required to have permission to all tyoskentelypaikkas related to palvelussuhde in order to modify it.
        Object level permission is still required.
        :return: None
        """
        user = self.request.user
        tyoskentelypaikat = self.get_object().tyoskentelypaikat.all()
        if any(not user.has_perm('change_tyoskentelypaikka', tyoskentelypaikka) for tyoskentelypaikka in tyoskentelypaikat):
            raise PermissionDenied({'errors': [ErrorMessages.PS002.value]})


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['palvelussuhde', 'tyontekija'])
class TyoskentelypaikkaViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.TyoskentelypaikkaFilter
    queryset = Tyoskentelypaikka.objects.all().order_by('id')

    def _validate_relation_to_taydennyskoulutus(self, tyoskentelypaikka, error_message):
        tyontekija = tyoskentelypaikka.palvelussuhde.tyontekija
        tehtavanimike = tyoskentelypaikka.tehtavanimike_koodi

        taydennyskoulutus_qs = TaydennyskoulutusTyontekija.objects.filter(tyontekija=tyontekija,
                                                                          tehtavanimike_koodi=tehtavanimike)
        tyoskentelypaikka_qs = (Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija,
                                                                 tehtavanimike_koodi=tehtavanimike)
                                .exclude(id=tyoskentelypaikka.id))

        if taydennyskoulutus_qs.exists() and not tyoskentelypaikka_qs.exists():
            raise ValidationError({'tehtavanimike_koodi': [error_message]})

    def get_serializer_class(self):
        request = self.request
        if request.method == 'PUT' or request.method == 'PATCH':
            return TyoskentelypaikkaUpdateSerializer
        else:
            return TyoskentelypaikkaSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        vakajarjestaja_oid = validated_data['palvelussuhde'].tyontekija.vakajarjestaja.organisaatio_oid
        tyontekija_tallentaja_group = 'HENKILOSTO_TYONTEKIJA_TALLENTAJA_{}'.format(vakajarjestaja_oid)
        if validated_data.get('kiertava_tyontekija_kytkin') and not is_user_permission(user, tyontekija_tallentaja_group):
            raise PermissionDenied({'errors': [ErrorMessages.TA001.value]})

        with transaction.atomic():
            tyoskentelypaikka = serializer.save()
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, Tyoskentelypaikka, tyoskentelypaikka)
            if tyoskentelypaikka.toimipaikka:
                toimipaikka_oid = tyoskentelypaikka.toimipaikka.organisaatio_oid
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyoskentelypaikka, tyoskentelypaikka)
                # Since it's allowed for vakatoimija level user to not provide toimipaikka earlier than
                # tyoskentelypaikka in related objects toimipaikka permissions need to be filled here to make sure
                palvelussuhde = tyoskentelypaikka.palvelussuhde
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Palvelussuhde, palvelussuhde)
                [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempi_poissaolo)
                 for pidempi_poissaolo in palvelussuhde.pidemmatpoissaolot.all()]
                tyontekija = palvelussuhde.tyontekija
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tyontekija, tyontekija)
                tutkinnot = Tutkinto.objects.filter(henkilo=tyontekija.henkilo, vakajarjestaja=tyontekija.vakajarjestaja)
                [assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, Tutkinto, tutkinto) for tutkinto in tutkinnot]

                assign_tyoskentelypaikka_henkilo_permissions(tyoskentelypaikka)

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            cache.delete('organisaatio_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)

    def perform_update(self, serializer):
        tyoskentelypaikka = self.get_object()
        validated_data = serializer.validated_data
        if tyoskentelypaikka.tehtavanimike_koodi != validated_data.get('tehtavanimike_koodi', None):
            # Validate relation to Taydennyskoulutus objects if tehtavanimike_koodi has been changed
            self._validate_relation_to_taydennyskoulutus(tyoskentelypaikka, ErrorMessages.TA015.value)

        tyoskentelypaikka = serializer.save()
        cache.delete('organisaatio_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_destroy(self, tyoskentelypaikka):
        self._validate_relation_to_taydennyskoulutus(tyoskentelypaikka, ErrorMessages.TA002.value)

        with transaction.atomic():
            delete_object_permissions_explicitly(Tyoskentelypaikka, tyoskentelypaikka)
            try:
                tyoskentelypaikka.delete()
            except ProtectedError:
                raise ValidationError({'errors': [ErrorMessages.TA003.value]})

            delete_cache_keys_related_model('palvelussuhde', tyoskentelypaikka.palvelussuhde.id)
            cache.delete('organisaatio_yhteenveto_' + str(tyoskentelypaikka.palvelussuhde.tyontekija.vakajarjestaja.id))
            if tyoskentelypaikka.toimipaikka:
                delete_cache_keys_related_model('toimipaikka', tyoskentelypaikka.toimipaikka.id)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['palvelussuhde', 'tyontekija'])
class PidempiPoissaoloViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.PidempiPoissaoloFilter
    queryset = PidempiPoissaolo.objects.all()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def perform_create(self, serializer):
        with transaction.atomic():
            user = self.request.user
            validated_data = serializer.validated_data
            palvelussuhde = validated_data['palvelussuhde']
            vakajarjestaja_oid = palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid
            if not toimipaikka_tallentaja_pidempipoissaolo_has_perm_to_add(user, vakajarjestaja_oid, validated_data):
                raise ValidationError({'tyoskentelypaikka': [ErrorMessages.PP002.value]})
            pidempipoissaolo = serializer.save()
            assign_object_permissions_to_tyontekija_groups(vakajarjestaja_oid, PidempiPoissaolo, pidempipoissaolo)

            # Assign Toimipaikka permissions
            toimipaikka_oid_set = set(palvelussuhde.tyoskentelypaikat
                                      .values_list('toimipaikka__organisaatio_oid', flat=True))
            toimipaikka_oid_set.discard(None)
            for toimipaikka_oid in toimipaikka_oid_set:
                assign_object_permissions_to_tyontekija_groups(toimipaikka_oid, PidempiPoissaolo, pidempipoissaolo)

            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
            cache.delete('organisaatio_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_update(self, serializer):
        pidempipoissaolo = serializer.save()
        delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
        cache.delete('organisaatio_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))

    def perform_destroy(self, pidempipoissaolo):
        with transaction.atomic():
            delete_object_permissions_explicitly(PidempiPoissaolo, pidempipoissaolo)
            try:
                pidempipoissaolo.delete()
            except ProtectedError:
                raise ValidationError({'errors': [ErrorMessages.PP001.value]})
            delete_cache_keys_related_model('palvelussuhde', pidempipoissaolo.palvelussuhde.id)
            cache.delete('organisaatio_yhteenveto_' + str(pidempipoissaolo.palvelussuhde.tyontekija.vakajarjestaja.id))


@auditlogclass
@request_log_viewset_decorator_factory()
class TaydennyskoulutusViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
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
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    filter_backends = (DjangoFilterBackend, )
    filterset_class = filters.TaydennyskoulutusFilter
    queryset = Taydennyskoulutus.objects.all().order_by('id')

    def get_serializer_class(self):
        request = self.request
        if self.action == 'tyontekija_list':
            return TaydennyskoulutusTyontekijaListSerializer
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

    def perform_create(self, serializer):
        with transaction.atomic():
            taydennyskoulutus = serializer.save()
            tyontekijat = taydennyskoulutus.tyontekijat
            if tyontekijat.exists:
                vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(tyontekijat)
                assign_object_permissions_to_taydennyskoulutus_groups(vakajarjestaja_oid, Taydennyskoulutus, taydennyskoulutus)

                # Assign toimipaikka level permissions to toimipaikat that are related to this taydennyskoulutus,
                # other toimipaikka level permissions are set in a celery task
                tyontekija_id_list, toimipaikka_oid_list_list = get_tyontekija_and_toimipaikka_lists_for_taydennyskoulutus(
                    taydennyskoulutus.taydennyskoulutukset_tyontekijat.all()
                )
                toimipaikka_oid_list_flat = flatten_nested_list(toimipaikka_oid_list_list)
                [assign_object_permissions_to_taydennyskoulutus_groups(toimipaikka_oid, Taydennyskoulutus, taydennyskoulutus)
                 for toimipaikka_oid in set(toimipaikka_oid_list_flat)]

                for tyontekija in tyontekijat.all():
                    delete_cache_keys_related_model('tyontekija', tyontekija.id)
                vakajarjestaja_obj = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid)
                cache.delete('organisaatio_yhteenveto_' + str(vakajarjestaja_obj.id))

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

            updated_taydennyskoulutus = serializer.save()

            # Delete cache keys from new tyontekijat (some may be added)
            tyontekijat = updated_taydennyskoulutus.tyontekijat.all()
            for tyontekija in tyontekijat:
                delete_cache_keys_related_model('tyontekija', tyontekija.id)

            vakajarjestaja_oid = get_tyontekija_vakajarjestaja_oid(tyontekijat)
            vakajarjestaja_obj = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid)
            cache.delete('organisaatio_yhteenveto_' + str(vakajarjestaja_obj.id))

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

            vakajarjestaja_obj = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid)
            cache.delete('organisaatio_yhteenveto_' + str(vakajarjestaja_obj.id))


class TaydennyskoulutusV2ViewSet(TaydennyskoulutusViewSet):
    def get_serializer_class(self):
        request = self.request
        if self.action == 'tyontekija_list':
            return TaydennyskoulutusTyontekijaListSerializer
        if request.method == 'PUT' or request.method == 'PATCH':
            return TaydennyskoulutusUpdateV2Serializer
        elif request.method == 'POST':
            return TaydennyskoulutusCreateV2Serializer
        else:
            return TaydennyskoulutusV2Serializer
