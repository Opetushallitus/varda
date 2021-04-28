import logging
import datetime

import pytz
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Prefetch, ProtectedError, Q, Subquery, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import (NotAuthenticated, NotFound, PermissionDenied, ValidationError)
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin,
                                   UpdateModelMixin)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_guardian.filters import ObjectPermissionsFilter

from varda import filters, validators, permission_groups
from varda.cache import (cached_list_response, cached_retrieve_response, delete_toimipaikan_lapset_cache,
                         delete_cache_keys_related_model, get_object_ids_for_user_by_model)
from varda.clients.oppijanumerorekisteri_client import (get_henkilo_data_by_oid,
                                                        add_henkilo_to_oppijanumerorekisteri,
                                                        get_henkilo_by_henkilotunnus)
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.exceptions.conflict_error import ConflictError
from varda.kayttooikeuspalvelu import set_user_info_from_onr
from varda.misc import (CustomServerErrorException, decrypt_henkilotunnus, encrypt_string, hash_string,
                        update_painotus_kytkin)
from varda.misc_queries import get_paos_toimipaikat
from varda.misc_viewsets import IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, IntegerIdSchema
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, PaosToiminta,
                          Lapsi, Huoltaja, Huoltajuussuhde, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Maksutieto,
                          PaosOikeus, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet, Tyontekija, Palvelussuhde,
                          Taydennyskoulutus, Tyoskentelypaikka, TilapainenHenkilosto, Tutkinto)
from varda.oppijanumerorekisteri import fetch_henkilo_with_oid, save_henkilo_to_db
from varda.organisaatiopalvelu import (check_if_toimipaikka_exists_in_organisaatiopalvelu,
                                       create_toimipaikka_in_organisaatiopalvelu)
from varda.pagination import ChangeableReportingPageSizePagination
from varda.permission_groups import (assign_object_level_permissions, create_permission_groups_for_organisaatio,
                                     assign_toimipaikka_lapsi_paos_permissions,
                                     assign_vakajarjestaja_lapsi_paos_permissions,
                                     assign_vakajarjestaja_vakatiedot_paos_permissions,
                                     assign_toimipaikka_vakatiedot_paos_permissions,
                                     assign_object_permissions_to_all_henkilosto_groups)
from varda.permissions import (throw_if_not_tallentaja_permissions,
                               check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement,
                               check_if_user_has_paakayttaja_permissions, ReadAdminOrOPHUser, CustomModelPermissions,
                               user_has_huoltajatieto_tallennus_permissions_to_correct_organization,
                               grant_or_deny_access_to_paos_toimipaikka, user_has_tallentaja_permission_in_organization,
                               auditlogclass, save_audit_log, ToimipaikkaPermissions, get_toimipaikka_or_404, auditlog,
                               is_oph_staff, user_permission_groups_in_organizations,
                               user_permission_groups_in_organization, CustomObjectPermissions,
                               assign_lapsi_henkilo_permissions, assign_vakasuhde_henkilo_permissions,
                               assign_permissions_for_non_paos_lapsi)
from varda.related_object_validations import (check_toimipaikka_and_vakajarjestaja_have_oids,
                                              toimipaikka_is_valid_to_organisaatiopalvelu,
                                              check_overlapping_toiminnallinen_painotus,
                                              check_overlapping_kielipainotus, check_overlapping_varhaiskasvatuspaatos,
                                              check_overlapping_varhaiskasvatussuhde,
                                              check_if_immutable_object_is_changed)
from varda.request_logging import request_log_viewset_decorator_factory
from varda.serializers import (ExternalPermissionsSerializer, GroupSerializer,
                               UpdateHenkiloWithOidSerializer, UpdateOphStaffSerializer, ClearCacheSerializer,
                               ActiveUserSerializer, AuthTokenSerializer, VakaJarjestajaSerializer,
                               ToimipaikkaSerializer, ToiminnallinenPainotusSerializer, KieliPainotusSerializer,
                               HaeHenkiloSerializer, HenkiloSerializer, HenkiloSerializerAdmin,
                               YksiloimattomatHenkilotSerializer, LapsiSerializer, LapsiSerializerAdmin,
                               HuoltajaSerializer, HuoltajuussuhdeSerializer, MaksutietoPostSerializer,
                               MaksutietoGetUpdateSerializer, VarhaiskasvatuspaatosSerializer,
                               VarhaiskasvatussuhdeSerializer, VakaJarjestajaYhteenvetoSerializer,
                               HenkilohakuLapsetSerializer, PaosToimintaSerializer, PaosToimijatSerializer,
                               PaosToimipaikatSerializer, PaosOikeusSerializer, LapsiKoosteSerializer, UserSerializer,
                               ToimipaikkaKoosteSerializer)
from varda.tasks import (update_oph_staff_to_vakajarjestaja_groups,
                         assign_taydennyskoulutus_permissions_for_toimipaikka_task)
from webapps.api_throttles import (BurstRateThrottleStrict, SustainedRateThrottleStrict)


logger = logging.getLogger(__name__)


"""
ADMIN-specific viewsets below
"""


@auditlogclass
class UserViewSet(ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser, )


@auditlogclass
class GroupViewSet(ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all().order_by('id')
    serializer_class = GroupSerializer
    permission_classes = (permissions.IsAdminUser, )


class UpdateHenkiloWithOid(GenericViewSet, CreateModelMixin):
    """
    create:
        Päivitä henkilön tiedot Oppijanumerorekisteristä.
    """
    queryset = Henkilo.objects.none()
    serializer_class = UpdateHenkiloWithOidSerializer
    permission_classes = (permissions.IsAdminUser, )

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            raise NotAuthenticated("Not authenticated.")
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            result = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(result, status=status.HTTP_200_OK, headers=headers)

    def perform_create(self, serializer):
        fetch_henkilo_with_oid(serializer.validated_data["henkilo_oid"])
        return {"result": "Henkilo-data fetched."}


class UpdateOphStaff(GenericViewSet, CreateModelMixin):
    """
    create:
        Päivitä henkilön OPH-staff status.
    """
    queryset = Henkilo.objects.none()
    serializer_class = UpdateOphStaffSerializer
    permission_classes = (permissions.IsAdminUser, )

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            raise NotAuthenticated("Not authenticated.")
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            result = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(result, status=status.HTTP_200_OK, headers=headers)

    def perform_create(self, serializer):
        update_oph_staff_to_vakajarjestaja_groups.delay()
        return {"result": "Update-task started."}


class ClearCacheViewSet(GenericViewSet, CreateModelMixin):
    """
    create:
        Tyhjennä memcached-sisältö kokonaisuudessaan.
    """
    serializer_class = ClearCacheSerializer
    permission_classes = (permissions.IsAdminUser, )

    def create(self, request, *args, **kwargs):
        user = request.user
        if user.is_anonymous:
            raise NotAuthenticated("Not authenticated.")
        else:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            result = self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(result, status=status.HTTP_200_OK, headers=headers)

    def perform_create(self, serializer):
        cache.clear()
        return {"result": "Cache was cleared successfully."}


@auditlogclass
class HaeYksiloimattomatHenkilotViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda yksilöimättömat henkilot.
    filters:
        vakatoimija_oid: Suodata lapsen tai työntekijän oidin perusteella
        henkilo_oid: Suodata henkilön oidin perusteella
        henkilotunnus: SHA256 hash henkilötunnus
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = filters.YksiloimattomatHenkilotFilter
    queryset = Henkilo.objects.filter(Q(vtj_yksiloity=False) & Q(vtj_yksilointi_yritetty=True))
    serializer_class = YksiloimattomatHenkilotSerializer
    permission_classes = (ReadAdminOrOPHUser, )
    pagination_class = ChangeableReportingPageSizePagination

    def get_queryset(self):
        return (self.queryset.order_by('lapsi__vakatoimija__organisaatio_oid',
                                       'tyontekijat__vakajarjestaja__organisaatio_oid'))


"""
Huoltaja-info currently available only for ADMIN-user.
"""


@auditlogclass
class HuoltajaViewSet(ModelViewSet):
    """
    list:
        Listaa kaikki huoltajat.

    retrieve:
        Hae yksittäinen huoltaja.
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = filters.HuoltajaFilter
    queryset = Huoltaja.objects.none()
    serializer_class = HuoltajaSerializer
    permission_classes = (permissions.IsAdminUser, )
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Huoltaja.objects.all().order_by('id')
        else:
            return Huoltaja.objects.none()


@auditlogclass
class NestedHuoltajaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki huoltajat.
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = filters.HuoltajaFilter
    queryset = Huoltaja.objects.none()
    serializer_class = HuoltajaSerializer
    permission_classes = (permissions.IsAdminUser, )
    swagger_schema = IntegerIdSchema
    swagger_path_model = Lapsi

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        # Explicit check that given primary key is integer
        # TODO: This should be handled by schema validation. Compare to e.g. /lapset/{id} : A unique integer value identifying this lapsi.
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404

        # checking if lapsi exists and user has permissions
        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        queryset = self.filter_queryset(Huoltaja.objects.filter(huoltajuussuhteet__lapsi__id=kwargs['lapsi_pk'])).order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@auditlogclass
class HuoltajuussuhdeViewSet(ModelViewSet):
    """
    list:
        Listaa huoltajuussuhteet.

    retrieve:
        Hae yksittainen huoltajuussuhde.
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = None
    queryset = Huoltajuussuhde.objects.none()
    serializer_class = HuoltajuussuhdeSerializer
    permission_classes = (permissions.IsAdminUser, )
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Huoltajuussuhde.objects.all().order_by('id')
        else:
            return Huoltajuussuhde.objects.none()


@auditlogclass
class NestedLapsiViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn huoltajan kaikki lapset.
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = filters.LapsiFilter
    queryset = Lapsi.objects.none()
    serializer_class = LapsiSerializer
    permission_classes = (permissions.IsAdminUser, )

    def get_huoltaja(self, request, huoltaja_pk=None):
        huoltaja = get_object_or_404(Huoltaja.objects.all(), pk=huoltaja_pk)
        user = request.user
        if user.has_perm("view_huoltaja", huoltaja):
            return huoltaja
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        if not kwargs['huoltaja_pk'].isdigit():
            raise Http404

        self.get_huoltaja(request, huoltaja_pk=kwargs['huoltaja_pk'])
        queryset = self.filter_queryset(Lapsi.objects.filter(huoltajuussuhteet__huoltaja__id=kwargs['huoltaja_pk'])).order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


"""
Pulssi-specific viewsets below
"""


class PulssiVakajarjestajat(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda vakajarjestajien lukumaara.
    """
    permission_classes = (permissions.AllowAny, )
    throttle_classes = ()  # TODO: Add ratelimit for Pulssi

    def list(self, request, *args, **kwargs):
        return Response(
            {"number_of_vakajarjestajat": VakaJarjestaja.objects.count()}
        )


"""
User-specific viewsets below
"""


@auditlogclass
class ActiveUserViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda käyttäjän tiedot.
    """
    queryset = User.objects.none()
    serializer_class = ActiveUserSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        request_user = request.user
        user_object = User.objects.get(id=request_user.id)

        if ((additional_cas_user_fields := getattr(user_object, 'additional_cas_user_fields', None)) and
                getattr(additional_cas_user_fields, 'kayttajatyyppi', None) == Kayttajatyyppi.VIRKAILIJA.value and
                (settings.PRODUCTION_ENV or settings.QA_ENV)):
            # In production and QA, if user is CAS Virkailija user, refresh user info from ONR
            # (e.g. if user language has changed)
            set_user_info_from_onr(additional_cas_user_fields)

        serializer = self.get_serializer(user_object, many=False)
        return Response(serializer.data)


@auditlogclass
class ApikeyViewSet(GenericViewSet, ListModelMixin, CreateModelMixin):
    """
    list:
        Nouda käyttäjän apikey.

    create:
        Päivitä käyttäjän apikey.
    """
    queryset = Token.objects.none()
    permission_classes = (permissions.IsAuthenticated, )
    serializer_class = AuthTokenSerializer

    def list(self, request, *args, **kwargs):
        user = request.user
        token = Token.objects.get_or_create(user=user)
        return Response({"token": token[0].key})

    @auditlog
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_token = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(new_token, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create a new token for the user, and delete the old one.
        """
        user = self.request.user
        Token.objects.get(user=user).delete()
        token = Token.objects.get_or_create(user=user)
        return {"token": token[0].key}


class ExternalPermissionsViewSet(GenericViewSet, CreateModelMixin):
    """
    create:
        Tarkista onko käyttäjällä oikeus lapsen tietoihin Vardassa.
    """
    queryset = Henkilo.objects.none()
    serializer_class = ExternalPermissionsSerializer
    permission_classes = (permissions.AllowAny, )
    # TODO: Allow queries only from Varda fe-proxy; it then allows only from ONR.

    @auditlog
    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        permit_identification = False
        headers = self.get_success_headers(serializer.data)

        """
        No cas user (virkailija) found
        """
        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(henkilo_oid=data['loggedInUserOid'])
        except Z3_AdditionalCasUserFields.DoesNotExist:
            return Response({"accessAllowed": permit_identification, "errorMessage": "loggedInUserOid was not found"}, status=status.HTTP_200_OK, headers=headers)
        user = cas_user_obj.user

        henkilot_qs = Henkilo.objects.filter(henkilo_oid__in=data['personOidsForSamePerson'])
        henkilot_qs_length = len(henkilot_qs)

        """
        Henkilo not found
        """
        if henkilot_qs_length == 0:
            return Response({"accessAllowed": permit_identification, "errorMessage": "Person not found"}, status=status.HTTP_200_OK, headers=headers)
        elif henkilot_qs_length > 1:
            logger.error('Multiple of henkilot was found with oids: ' + ', '.join(data['personOidsForSamePerson']))
            raise CustomServerErrorException

        """
        We know there is exactly one henkilo found with the given personOids.
        """
        henkilo = henkilot_qs[0]

        """
        Lapsi (henkilo) can be in multiple of organizations.
        """
        lapset = Lapsi.objects.filter(henkilo=henkilo)

        """
        If virkailija can view the lapsi in any organization, return True, otherwise return False.
        """
        for lapsi in lapset:
            if user.has_perm("view_lapsi", lapsi):
                permit_identification = True
                break

        return Response({"accessAllowed": permit_identification, "errorMessage": ""}, status=status.HTTP_200_OK, headers=headers)


"""
VARDA-specific viewsets below


We use django guardian for model- and object-level permissions.

For non-authenticated users (AnonymousUser) we do not show anything.
For authenticated users, we respect first model-level permissions. And next, object-level permissions.

When a user makes a query to the API, we return:
- if AnonymousUser: we return nothing
- if authenticated & do not have model-permissions: we return nothing
- if authenticated & has model-permissions: we return all objects where user has object-level view-permissions.

When a new instance is created (POST-request), we give object-level permissions only to the organization (group) itself, using assign_perm-method.
    E.g. users in group "organization_Y_view_toimipaikat" can see all toimipaikat in organization Y at: /api/vx/toimipaikat/
"""


@auditlogclass
@request_log_viewset_decorator_factory()
class VakaJarjestajaViewSet(IncreasedModifyThrottleMixin, ModelViewSet):
    """
    list:
        Nouda kaikki vakajarjestajat.

    create:
        Luo yksi uusi vakajarjestaja.

    delete:
        Poista yksi vakajarjestaja.

    retrieve:
        Nouda yksittäinen vakajarjestaja.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä vakajarjestaja-tietueesta.

    update:
        Päivitä yhden vakajarjestajan kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VakaJarjestajaFilter
    queryset = VakaJarjestaja.objects.all().order_by('id')
    serializer_class = VakaJarjestajaSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_update(self, serializer):
        user = self.request.user
        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'errors': ErrorMessages.VJ001.value})


@auditlogclass
@request_log_viewset_decorator_factory(target_path=[])
class ToimipaikkaViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, GenericViewSet, CreateModelMixin,
                         RetrieveModelMixin, UpdateModelMixin, ListModelMixin):
    """
    list:
        Nouda kaikki toimipaikat.

    create:
        Luo yksi uusi toimipaikka.

    retrieve:
        Nouda yksittäinen toimipaikka.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä toimipaikka-tietueesta.

    update:
        Päivitä yhden toimipaikan kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.all().order_by('id')
    serializer_class = ToimipaikkaSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        vakajarjestaja_obj = validated_data['vakajarjestaja']
        vakajarjestaja_id = vakajarjestaja_obj.id

        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        check_if_toimipaikka_exists_in_organisaatiopalvelu(vakajarjestaja_id, validated_data['nimi'])
        """
        Toimipaikka was not found in Organisaatiopalvelu. We can POST it there.
        """
        try:
            with transaction.atomic():
                # Save first internally so we can catch possible IntegrityError before POSTing to Org.palvelu.
                serializer.save(changed_by=user)

                result = create_toimipaikka_in_organisaatiopalvelu(validated_data)
                if result['toimipaikka_created']:
                    toimipaikka_organisaatio_oid = result['organisaatio_oid']
                else:
                    # transaction.set_rollback(True)  This would be otherwise nice but the user wouldn't get an error-msg.
                    raise IntegrityError('Org.palvelu-integration')

                serializer.validated_data['organisaatio_oid'] = toimipaikka_organisaatio_oid
                saved_object = serializer.save(changed_by=user)
                delete_cache_keys_related_model('vakajarjestaja', saved_object.vakajarjestaja.id)
                cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.vakajarjestaja.id))

                """
                New organization, let's create pre-defined permission_groups for it.
                """
                create_permission_groups_for_organisaatio(toimipaikka_organisaatio_oid, vakajarjestaja=False)

                vakajarjestaja_obj = VakaJarjestaja.objects.get(id=vakajarjestaja_id)
                vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid
                assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Toimipaikka, saved_object)
                assign_object_permissions_to_all_henkilosto_groups(toimipaikka_organisaatio_oid, Toimipaikka, saved_object)
                assign_object_level_permissions(toimipaikka_organisaatio_oid, Toimipaikka, saved_object)
                assign_object_permissions_to_all_henkilosto_groups(vakajarjestaja_organisaatio_oid, Toimipaikka, saved_object)

                """
                Assign permissions to all taydennyskoulutukset of vakajarjestaja in a task
                so that it doesn't block execution
                """
                assign_taydennyskoulutus_permissions_for_toimipaikka_task.delay(vakajarjestaja_organisaatio_oid,
                                                                                toimipaikka_organisaatio_oid)
        except IntegrityError as e:
            logger.error('Could not create a toimipaikka in Org.Palvelu. Data: {}. Error: {}.'
                         .format(validated_data, e.__cause__))
            raise ValidationError({'toimipaikka': [ErrorMessages.TP002.value]})

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = self.get_object()

        if Hallinnointijarjestelma[toimipaikka_obj.hallinnointijarjestelma] is not Hallinnointijarjestelma.VARDA:
            raise ValidationError({'hallinnointijarjestelma': [ErrorMessages.TP003.value]})
        if validated_data['toimintamuoto_koodi'] != toimipaikka_obj.toimintamuoto_koodi and toimipaikka_obj.organisaatio_oid is None:
            raise ValidationError({'toimintamuoto_koodi': [ErrorMessages.TP005.value]})
        check_if_immutable_object_is_changed(toimipaikka_obj, validated_data, 'vakajarjestaja')

        # Validate that paattymis_pvm is after alkamis_pvm if toimipaikka has paattymis_pvm, or if paattymis_pvm
        # is other than null in request
        paattymis_pvm = validated_data.get('paattymis_pvm', None) or toimipaikka_obj.paattymis_pvm
        if paattymis_pvm and not ('paattymis_pvm' in validated_data and not validated_data['paattymis_pvm']):
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], paattymis_pvm):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('vakajarjestaja', saved_object.vakajarjestaja.id)
        cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.vakajarjestaja.id))

    @auditlog
    @action(methods=['get'], detail=True, serializer_class=ToimipaikkaKoosteSerializer,
            permission_classes=(CustomModelPermissions, CustomObjectPermissions,))
    def kooste(self, request, pk=None):
        toimipaikka_obj = self.get_object()
        serialized_data = self.get_serializer(toimipaikka_obj).data
        return Response(data=serialized_data)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['toimipaikka'])
class ToiminnallinenPainotusViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki toiminnalliset painotukset.

    create:
        Luo yksi uusi toiminnallinen painotus.

    delete:
        Poista yksi toiminnallinen painotus.

    retrieve:
        Nouda yksittäinen toiminnallinen painotus.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä toiminnallinen painotus -tietueesta.

    update:
        Päivitä yhden toiminnallisen painotuksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.ToiminnallinenPainotusFilter
    queryset = ToiminnallinenPainotus.objects.all().order_by('id')
    serializer_class = ToiminnallinenPainotusSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def _toggle_toimipaikka_kytkin(self, toimipaikka):
        update_painotus_kytkin(toimipaikka, 'toiminnallisetpainotukset', 'toiminnallinenpainotus_kytkin')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data['toimipaikka']
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        check_overlapping_toiminnallinen_painotus(validated_data)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            self._toggle_toimipaikka_kytkin(saved_object.toimipaikka)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, ToiminnallinenPainotus, saved_object)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, ToiminnallinenPainotus, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        instance = self.get_object()
        toimipaikka_obj = instance.toimipaikka
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_organisaatio_oid = toimipaikka_obj.vakajarjestaja.organisaatio_oid

        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

        if 'alkamis_pvm' in validated_data or 'paattymis_pvm' in validated_data:
            alkamis_pvm = validated_data['alkamis_pvm'] if 'alkamis_pvm' in validated_data else instance.alkamis_pvm
            paattymis_pvm = validated_data['paattymis_pvm'] if 'paattymis_pvm' in validated_data else instance.paattymis_pvm
            if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        check_overlapping_toiminnallinen_painotus(validated_data, instance.id)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            self._toggle_toimipaikka_kytkin(saved_object.toimipaikka)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        with transaction.atomic():
            toimipaikka = instance.toimipaikka
            instance.delete()
            self._toggle_toimipaikka_kytkin(toimipaikka)
            delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['toimipaikka'])
class KieliPainotusViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki kielipainotukset.

    create:
        Luo yksi uusi kielipainotus.

    delete:
        Poista yksi kielipainotus.

    retrieve:
        Nouda yksittäinen kielipainotus.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä kielipainotus-tietueesta.

    update:
        Päivitä yhden kielipainotuksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.KieliPainotusFilter
    queryset = KieliPainotus.objects.all().order_by('id')
    serializer_class = KieliPainotusSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def _toggle_toimipaikka_kytkin(self, toimipaikka):
        update_painotus_kytkin(toimipaikka, 'kielipainotukset', 'kielipainotus_kytkin')

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data['toimipaikka']
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

        if 'paattymis_pvm' in validated_data:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        check_overlapping_kielipainotus(validated_data)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            self._toggle_toimipaikka_kytkin(saved_object.toimipaikka)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, KieliPainotus, saved_object)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, KieliPainotus, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        instance = self.get_object()
        toimipaikka_obj = instance.toimipaikka
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

        if 'alkamis_pvm' in validated_data or 'paattymis_pvm' in validated_data:
            alkamis_pvm = validated_data['alkamis_pvm'] if 'alkamis_pvm' in validated_data else instance.alkamis_pvm
            paattymis_pvm = validated_data['paattymis_pvm'] if 'paattymis_pvm' in validated_data else instance.paattymis_pvm
            if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI003.value]})

        check_overlapping_kielipainotus(validated_data, self_id=instance.id)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            self._toggle_toimipaikka_kytkin(saved_object.toimipaikka)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        with transaction.atomic():
            toimipaikka = instance.toimipaikka
            instance.delete()
            self._toggle_toimipaikka_kytkin(toimipaikka)
            delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))


class HaeHenkiloViewSet(GenericViewSet, CreateModelMixin):
    """
    create:
        Nouda yksittäinen henkilö joko oppijanumerolla (oid) tai henkilotunnuksella.
    """
    queryset = Henkilo.objects.none()
    serializer_class = HaeHenkiloSerializer
    # We need more strict throttling on henkilo-haku, due to security reasons.
    throttle_classes = (BurstRateThrottleStrict, SustainedRateThrottleStrict)
    permission_classes = (CustomModelPermissions,)

    def get_henkilo(self, query_param, query_param_value):
        try:
            henkilo = Henkilo.objects.get(**{query_param: query_param_value})
        except Henkilo.DoesNotExist:
            raise NotFound(detail='Henkilo was not found.', code=404)
        except Henkilo.MultipleObjectsReturned:  # This should never be possible
            logger.error('Multiple of henkilot was found with ' + query_param + ': ' + query_param_value)
            raise CustomServerErrorException

        user = self.request.user
        if user.has_perm('view_henkilo', henkilo):
            return henkilo
        else:
            """
            For security reasons give HTTP 404 Not found, instead of 403 Permission denied.
            """
            raise NotFound(detail='Henkilo was not found.', code=404)

    def get_successful_response(self, henkilo):
        serializer = HenkiloSerializer(henkilo, context={'request': self.request})
        headers = self.get_success_headers(serializer.data)
        save_audit_log(self.request.user, self.request.path + 'id=' + str(serializer.data['id']))
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @auditlog
    def create(self, request, *args, **kwargs):
        # Function name (create) is misleading! Here we get the henkilo based on henkilotunnus or henkilo_oid.
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'henkilotunnus' in serializer.validated_data:
            henkilotunnus = serializer.validated_data['henkilotunnus']
            validators.validate_henkilotunnus(henkilotunnus)
            with transaction.atomic():
                henkilo = self.get_henkilo('henkilotunnus_unique_hash', hash_string(henkilotunnus))
                if user.has_perm('varda.view_henkilo', henkilo):  # Explicit permission checking - Very important!
                    return self.get_successful_response(henkilo)
                else:
                    raise NotFound(detail='Henkilo was not found.', code=404)
        else:  # "henkilo_oid" in serializer.validated_data
            henkilo_oid = serializer.validated_data['henkilo_oid']
            validators.validate_henkilo_oid(henkilo_oid)
            with transaction.atomic():
                henkilo = self.get_henkilo('henkilo_oid', henkilo_oid)
                if user.has_perm('varda.view_henkilo', henkilo):
                    return self.get_successful_response(henkilo)
                else:
                    raise NotFound(detail='Henkilo was not found.', code=404)


@auditlogclass
@request_log_viewset_decorator_factory()
class HenkiloViewSet(IncreasedModifyThrottleMixin, GenericViewSet, RetrieveModelMixin, CreateModelMixin):
    """
    retrieve:
        Nouda yksittäinen henkilö.

    create:
        Luo yksi uusi henkilö.
    """
    queryset = Henkilo.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomModelPermissions,)

    def get_serializer_class(self):
        request = self.request
        if request is not None and request.user.is_superuser:
            return HenkiloSerializerAdmin
        return HenkiloSerializer

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def validate_henkilo_uniqueness_henkilotunnus(self, henkilotunnus_hash, etunimet, sukunimi):
        try:
            henkilo = Henkilo.objects.get(henkilotunnus_unique_hash=henkilotunnus_hash)
        except Henkilo.DoesNotExist:
            return None  # Create a new one
        self.validate_names_match(henkilo, etunimet, sukunimi)

    def validate_henkilo_uniqueness_oid(self, henkilo_oid, etunimet, sukunimi):
        try:
            henkilo = Henkilo.objects.get(henkilo_oid=henkilo_oid)
        except Henkilo.DoesNotExist:
            return None  # Create a new one
        self.validate_names_match(henkilo, etunimet, sukunimi)

    def validate_names_match(self, henkilo, etunimet, sukunimi):
        etunimet_list = etunimet.split(' ')
        etunimet_list_lowercase = [x.lower() for x in etunimet_list]
        henkilo_etunimet_list = henkilo.etunimet.split(' ')
        henkilo_etunimet_list_lowercase = [x.lower() for x in henkilo_etunimet_list]
        if set(etunimet_list_lowercase) & set(henkilo_etunimet_list_lowercase) or sukunimi.lower() == henkilo.sukunimi.lower():
            # Set permissions to Henkilo object for current user
            self._assign_henkilo_permissions(self.request.user, henkilo)
            raise ConflictError(self.get_serializer(henkilo).data, status_code=status.HTTP_200_OK)
        else:
            raise ValidationError({'errors': [ErrorMessages.HE001.value]})

    def _assign_henkilo_permissions(self, user, henkilo):
        if not user.has_perm('view_henkilo', henkilo):
            # Don't assign user specific permissions if user already has a permission via permission group
            assign_perm('view_henkilo', self.request.user, henkilo)

    def _get_henkilo_data_by_henkilotunnus(self, validated_data, henkilotunnus, etunimet, kutsumanimi, sukunimi):
        validators.validate_henkilotunnus(henkilotunnus)
        """
        We are ready to create a new henkilo, let's first create a unique hash so that we are sure every
        henkilotunnus exists in the DB only once, and definately not more often.
        Return HTTP 200 if henkilo already exists in DB.
        After that, let's encrypt henkilotunnus due to security reasons.
        """
        henkilotunnus_unique_hash = hash_string(henkilotunnus)
        henkilotunnus_encrypted = encrypt_string(henkilotunnus)
        self.validate_henkilo_uniqueness_henkilotunnus(henkilotunnus_unique_hash, etunimet, sukunimi)

        # It is possible we get different hetu than user provided
        henkilo_result = get_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi)
        henkilo_data = henkilo_result['result']
        if henkilo_data and henkilo_data.get('hetu', None):
            self.validate_henkilo_uniqueness_henkilotunnus(hash_string(henkilo_data['hetu']), etunimet, sukunimi)
            henkilotunnus_unique_hash = hash_string(henkilo_data['hetu'])
            henkilotunnus_encrypted = encrypt_string(henkilo_data['hetu'])

        validated_data['henkilotunnus_unique_hash'] = henkilotunnus_unique_hash
        validated_data['henkilotunnus'] = henkilotunnus_encrypted
        return henkilo_data

    def _get_henkilo_data_by_oid(self, henkilo_oid, etunimet, sukunimi):
        validators.validate_henkilo_oid(henkilo_oid)
        # checking we don't have this henkilo already (return HTTP 200 if so)
        self.validate_henkilo_uniqueness_oid(henkilo_oid, etunimet, sukunimi)
        henkilo_data = get_henkilo_data_by_oid(henkilo_oid)
        if not henkilo_data:
            # If adding henkilo to varda using OID they should always be found from ONR. Later adding henkilo with
            # just name data might be possible here when manual yksilointi is functional.
            raise ValidationError({'henkilo_oid': [ErrorMessages.HE003.value]})
        return henkilo_data

    def validate_henkilo_data(self, henkilo_data):
        """
        Validate if henkilo is found in Oppijanumerorekisteri and he has been identified as unique.
        """
        if henkilo_data:
            is_hetullinen = henkilo_data.get('hetu', None)
            is_hetuton_yksiloity = (not henkilo_data.get('hetu', None) and
                                    henkilo_data.get('yksiloity', None))
            if not is_hetullinen and not is_hetuton_yksiloity:
                raise ValidationError({'henkilo_oid': [ErrorMessages.HE002.value, ]})

    def _handle_validation_error(self, validation_error, henkilotunnus, henkilo_oid, etunimet, sukunimi):
        validation_error_message = str(validation_error.detail)
        if 'HE014' in validation_error_message or 'HE015' in validation_error_message:
            # If same henkilo was created twice in a short period of time, it is possible that henkilo is already
            # created (because we wait for ONR response) and ValidationError is thrown, so check uniqueness again
            if henkilotunnus:
                self.validate_henkilo_uniqueness_henkilotunnus(hash_string(henkilotunnus), etunimet, sukunimi)
            else:
                self.validate_henkilo_uniqueness_oid(henkilo_oid, etunimet, sukunimi)
        raise validation_error

    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        etunimet = validated_data['etunimet']
        kutsumanimi = validated_data['kutsumanimi']
        sukunimi = validated_data['sukunimi']
        validators.validate_kutsumanimi(etunimet, kutsumanimi)

        henkilotunnus = validated_data.get('henkilotunnus', None)
        henkilo_oid = validated_data.get('henkilo_oid', None)
        if henkilotunnus:
            henkilo_data = self._get_henkilo_data_by_henkilotunnus(validated_data, henkilotunnus, etunimet,
                                                                   kutsumanimi, sukunimi)
        else:
            # Henkilo created using henkilo_oid
            henkilo_data = self._get_henkilo_data_by_oid(henkilo_oid, etunimet, sukunimi)

        self.validate_henkilo_data(henkilo_data)

        # It is possible we get different oid than user provided
        if henkilo_data and henkilo_data.get('oidHenkilo', None):
            self.validate_henkilo_uniqueness_oid(henkilo_data['oidHenkilo'], etunimet, sukunimi)

        user = self.request.user
        with transaction.atomic():
            if henkilotunnus and not henkilo_data:
                # Create henkilo in Oppijanumerorekisteri if it did not exist there
                henkilo_result = add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi,
                                                                      henkilotunnus=henkilotunnus)
                henkilo_data = henkilo_result['result']

            # In order to return henkilo_oid and syntyma_pvm in create we need to wait until the new henkilo has been
            # added to oppijanumerorekisteri before saving to database
            if henkilo_data:
                validated_data['etunimet'] = henkilo_data.get('etunimet', etunimet)
                validated_data['kutsumanimi'] = henkilo_data.get('kutsumanimi', kutsumanimi)
                validated_data['sukunimi'] = henkilo_data.get('sukunimi', sukunimi)
                validated_data['syntyma_pvm'] = henkilo_data.get('syntymaaika', None)
                validated_data['henkilo_oid'] = henkilo_data.get('oidHenkilo', henkilo_oid)

            try:
                saved_object = serializer.save(changed_by=user)
                # Give user object level permissions to Henkilo object, until we can determine related VakaJarjestaja
                # from Lapsi or Tyontekija object
                self._assign_henkilo_permissions(user, saved_object)

                henkilo_id = serializer.data['id']
                if henkilo_data is not None:
                    # Save remaining ONR-related data for Henkilo
                    save_henkilo_to_db(henkilo_id, henkilo_data)
            except ValidationError as validation_error:
                self._handle_validation_error(validation_error, henkilotunnus, henkilo_oid, etunimet, sukunimi)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=[])
class LapsiViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki lapset.

    create:
        Luo yksi uusi lapsi.

    delete:
        Poista yksi lapsi.

    retrieve:
        Nouda yksittäinen lapsi.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä lapsi-tietueesta.

    update:
        Päivitä yhden lapsen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.LapsiFilter
    queryset = Lapsi.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def get_serializer_class(self):
        request = self.request
        if request is not None and request.user.is_superuser:
            return LapsiSerializerAdmin
        return LapsiSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def return_lapsi_if_already_created(self, validated_data, toimipaikka_oid, paos_oikeus):
        user = self.request.user
        q_obj = Q()
        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            q_obj = Q(henkilo=validated_data['henkilo'],
                      oma_organisaatio=validated_data['oma_organisaatio'],
                      paos_organisaatio=validated_data['paos_organisaatio'])
        elif 'vakatoimija' in validated_data and validated_data['vakatoimija'] is not None:
            q_obj = Q(Q(henkilo=validated_data['henkilo']) &
                      Q(Q(vakatoimija=validated_data['vakatoimija']) |
                      (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja=validated_data['vakatoimija'],
                         paos_kytkin=False))))

        lapsi_qs = Lapsi.objects.filter(q_obj).distinct()
        if len(lapsi_qs) > 1:
            logger.error(f'unable to fetch a single child for {user} with henkilo {validated_data["henkilo"]}')
            raise ValidationError({'errors': [ErrorMessages.LA001.value]})
        else:
            lapsi_obj = lapsi_qs.first()
        if lapsi_obj:
            if toimipaikka_oid:
                # Assign permissions again to include Toimipaikka related groups
                self._assign_permissions_for_lapsi_obj(lapsi_obj, paos_oikeus, toimipaikka_oid)
            raise ConflictError(self.get_serializer(lapsi_obj).data, status_code=status.HTTP_200_OK)

    def copy_huoltajuussuhteet(self, saved_object):
        for lapsi in saved_object.henkilo.lapsi.all():
            huoltajuussuhteet_qs = lapsi.huoltajuussuhteet.all()
            # If other lapsi has huoltajuussuhteet, copy them
            if huoltajuussuhteet_qs:
                for huoltajuussuhde in huoltajuussuhteet_qs:
                    Huoltajuussuhde(lapsi=saved_object,
                                    huoltaja=huoltajuussuhde.huoltaja,
                                    voimassa_kytkin=huoltajuussuhde.voimassa_kytkin,
                                    changed_by=self.request.user).save()
                # huoltajuussuhteet copied, no need to loop through other lapset
                break

    def _assign_permissions_for_lapsi_obj(self, lapsi, paos_oikeus, toimipaikka_oid):
        if lapsi.paos_kytkin and paos_oikeus:
            tallentaja_organisaatio_oid = paos_oikeus.tallentaja_organisaatio.organisaatio_oid
            assign_vakajarjestaja_lapsi_paos_permissions(lapsi.oma_organisaatio.organisaatio_oid,
                                                         lapsi.paos_organisaatio.organisaatio_oid,
                                                         tallentaja_organisaatio_oid, lapsi)
            if toimipaikka_oid:
                assign_toimipaikka_lapsi_paos_permissions(toimipaikka_oid, tallentaja_organisaatio_oid, lapsi)
        elif lapsi.vakatoimija:
            assign_permissions_for_non_paos_lapsi(lapsi, lapsi.vakatoimija.organisaatio_oid,
                                                  toimipaikka_oid=toimipaikka_oid)

        assign_lapsi_henkilo_permissions(lapsi, user=self.request.user, toimipaikka_oid=toimipaikka_oid)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        oma_organisaatio = validated_data.get('oma_organisaatio')
        paos_organisaatio = validated_data.get('paos_organisaatio')
        paos_oikeus = None
        if paos_organisaatio:
            """
            This is a "PAOS-lapsi"
            - oma_organisaatio must have permission to add this lapsi to PAOS-toimipaikka (under paos-organisaatio)
            - user must have tallentaja-permission in oma_organisaatio (vakajarjestaja-level) or palvelukayttaja.
            """
            paos_organisaatio_oid = paos_organisaatio.organisaatio_oid
            paos_toimipaikka = None
            paos_oikeus = check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(oma_organisaatio,
                                                                                              paos_organisaatio)
            throw_if_not_tallentaja_permissions(paos_organisaatio_oid, paos_toimipaikka, user, oma_organisaatio)

        try:
            with transaction.atomic():
                # This can be performed only after all permission checks are done!
                self.return_lapsi_if_already_created(validated_data, toimipaikka_oid, paos_oikeus)
                saved_object = serializer.save(changed_by=user)

                self._assign_permissions_for_lapsi_obj(saved_object, paos_oikeus, toimipaikka_oid)
                self.copy_huoltajuussuhteet(saved_object)
                delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)
        except ValidationError as validation_error:
            validation_error_message = str(validation_error.detail)
            if 'LA009' in validation_error_message or 'LA010' in validation_error_message:
                # If same Lapsi was created twice in a short period of time, it is possible that Lapsi is
                # already created and IntegrityError is thrown, so check uniqueness again
                self.return_lapsi_if_already_created(validated_data, toimipaikka_oid, paos_oikeus)
            raise validation_error

    def perform_update(self, serializer):
        user = self.request.user
        lapsi_obj = self.get_object()

        validated_data = serializer.validated_data

        check_if_immutable_object_is_changed(lapsi_obj, validated_data, 'henkilo')
        check_if_immutable_object_is_changed(lapsi_obj, validated_data, 'vakatoimija')
        check_if_immutable_object_is_changed(lapsi_obj, validated_data, 'oma_organisaatio')
        check_if_immutable_object_is_changed(lapsi_obj, validated_data, 'paos_organisaatio')

        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        if Huoltajuussuhde.objects.filter(lapsi__id=instance.id).filter(maksutiedot__isnull=False).exists():
            raise ValidationError({'errors': [ErrorMessages.LA003.value]})

        instance_id = instance.id

        with transaction.atomic():
            try:
                Huoltajuussuhde.objects.filter(lapsi__id=instance_id).delete()
                instance.delete()
            except ProtectedError:
                raise ValidationError({'errors': [ErrorMessages.LA004.value]})

            delete_cache_keys_related_model('henkilo', instance.henkilo.id)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['lapsi'])
class VarhaiskasvatuspaatosViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki varhaiskasvatuspäätökset.

    create:
        Luo yksi uusi varhaiskasvatuspäätös.

    delete:
        Poista yksi varhaiskasvatuspäätös.

    retrieve:
        Nouda yksittäinen varhaiskasvatuspäätös.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä varhaiskasvatuspaatos-tietueesta.

    update:
        Päivitä yhden varhaiskasvatuspäätöksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatuspaatosFilter
    queryset = Varhaiskasvatuspaatos.objects.all().order_by('id')
    serializer_class = VarhaiskasvatuspaatosSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        lapsi = validated_data['lapsi']
        toimipaikka_oid = validated_data.get('toimipaikka') and validated_data.get('toimipaikka').organisaatio_oid

        if validated_data['vuorohoito_kytkin']:
            validated_data['paivittainen_vaka_kytkin'] = None
            validated_data['kokopaivainen_vaka_kytkin'] = None
        timediff = validated_data['alkamis_pvm'] - validated_data['hakemus_pvm']
        if timediff.days <= 14:
            validated_data['pikakasittely_kytkin'] = True

        check_overlapping_varhaiskasvatuspaatos(validated_data)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('lapsi', lapsi.id)
            if lapsi.paos_kytkin:
                paos_oikeus = check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(lapsi.oma_organisaatio, lapsi.paos_organisaatio)
                if not user_has_tallentaja_permission_in_organization(paos_oikeus.tallentaja_organisaatio.organisaatio_oid, user):
                    raise PermissionDenied({'errors': [ErrorMessages.PE003.value]})
                oma_organisaatio_oid = lapsi.oma_organisaatio.organisaatio_oid
                paos_organisaatio_oid = lapsi.paos_organisaatio.organisaatio_oid
                tallentaja_organisaatio_oid = paos_oikeus.tallentaja_organisaatio.organisaatio_oid
                assign_vakajarjestaja_vakatiedot_paos_permissions(oma_organisaatio_oid, paos_organisaatio_oid, tallentaja_organisaatio_oid,
                                                                  Varhaiskasvatuspaatos, saved_object)
                if toimipaikka_oid:
                    assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_oid, tallentaja_organisaatio_oid,
                                                                   Varhaiskasvatuspaatos, saved_object)
            else:
                if lapsi.vakatoimija:
                    assign_object_level_permissions(lapsi.vakatoimija.organisaatio_oid, Varhaiskasvatuspaatos, saved_object)
                else:
                    # This Lapsi is still missing vakatoimija-field, so we need to assign user specific permissions
                    # so that Varhaiskasvatussuhde can be created
                    assign_perm('view_varhaiskasvatuspaatos', user, saved_object)
                    assign_perm('change_varhaiskasvatuspaatos', user, saved_object)
                    assign_perm('delete_varhaiskasvatuspaatos', user, saved_object)
                if toimipaikka_oid:
                    assign_object_level_permissions(toimipaikka_oid, Varhaiskasvatuspaatos, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        instance = self.get_object()
        varhaiskasvatussuhteet = instance.varhaiskasvatussuhteet.all()

        for varhaiskasvatussuhde_obj in varhaiskasvatussuhteet:
            self.validate_paivamaarat_varhaiskasvatussuhteet(validated_data['alkamis_pvm'],
                                                             varhaiskasvatussuhde_obj.alkamis_pvm,
                                                             {'alkamis_pvm': [ErrorMessages.VP002.value]})

        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            for varhaiskasvatussuhde_obj in varhaiskasvatussuhteet:
                self.validate_paivamaarat_varhaiskasvatussuhteet(varhaiskasvatussuhde_obj.paattymis_pvm,
                                                                 validated_data['paattymis_pvm'],
                                                                 {'paattymis_pvm': [ErrorMessages.VP003.value]})

        timediff = validated_data['alkamis_pvm'] - validated_data['hakemus_pvm']
        if timediff.days <= 14:
            validated_data['pikakasittely_kytkin'] = True
        else:
            validated_data['pikakasittely_kytkin'] = False

        check_overlapping_varhaiskasvatuspaatos(validated_data, instance.id)

        saved_object = serializer.save(changed_by=user)
        """
        No need to delete the related-lapsi cache, since user cannot change the lapsi-relation.
        """
        self.delete_list_of_toimipaikan_lapset_cache(self.get_toimipaikka_ids(saved_object))
        self.delete_vakajarjestaja_yhteenveto_cache(saved_object)

    def perform_destroy(self, instance):
        lapsi_id = instance.lapsi.id
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({'errors': [ErrorMessages.VP004.value]})
        delete_cache_keys_related_model('lapsi', lapsi_id)
        """
        No need to delete toimipaikan_lapset or vakajarjestaja_yhteenveto caches.
        For this object to be deleted, the vakasuhteet must have been first deleted.
        """

    def get_toimipaikka_ids(self, vakapaatos_obj):
        toimipaikka_id_list = []
        for varhaiskasvatussuhde in vakapaatos_obj.varhaiskasvatussuhteet.all():
            toimipaikka_id = varhaiskasvatussuhde.toimipaikka.id
            if toimipaikka_id not in toimipaikka_id_list:
                toimipaikka_id_list.append(toimipaikka_id)
        return toimipaikka_id_list

    def delete_list_of_toimipaikan_lapset_cache(self, toimipaikka_id_list):
        for toimipaikka_id in toimipaikka_id_list:
            delete_toimipaikan_lapset_cache(str(toimipaikka_id))

    def delete_vakajarjestaja_yhteenveto_cache(self, vakapaatos_obj):
        vakasuhde = vakapaatos_obj.varhaiskasvatussuhteet.all().first()
        if vakasuhde is not None:
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakasuhde.toimipaikka.vakajarjestaja.id))

    def validate_paivamaarat_varhaiskasvatussuhteet(self, alkamis_pvm, paattymis_pvm, error_text):
        if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm, can_be_same=True):
            raise ValidationError(error_text)


@auditlogclass
@request_log_viewset_decorator_factory(target_path=['varhaiskasvatuspaatos', 'lapsi'])
class VarhaiskasvatussuhdeViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        Nouda kaikki varhaiskasvatussuhteet.

    create:
        Luo yksi uusi varhaiskasvatussuhde.

    delete:
        Poista yksi varhaiskasvatussuhde.

    retrieve:
        Nouda yksittäinen varhaiskasvatussuhde.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä varhaiskasvatussuhde-tietueesta.

    update:
        Päivitä yhden varhaiskasvatussuhteen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.all().order_by('id')
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def validate_lapsi_not_under_different_vakajarjestaja(self, lapsi_obj, new_vakajarjestaja_obj):
        """
        Make sure lapsi will not end up under two different vakajarjestajat. Without this validation a virkailija
        with permissions to two different vakajarjestajat could potentially add one and same lapsi to two
        different vakajarjestajat/toimipaikat.
        """
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi_obj)
        vakajarjestajat = VakaJarjestaja.objects.filter(toimipaikat__varhaiskasvatussuhteet__in=vakasuhteet).distinct()
        if vakajarjestajat.count() > 1:
            logger.error('Lapsi under multiple vakajarjestajat. Lapsi-id: {}'.format(lapsi_obj.id))
        if vakajarjestajat and new_vakajarjestaja_obj not in vakajarjestajat:
            raise ValidationError({'errors': [ErrorMessages.VS001.value]})

    def assign_paos_lapsi_permissions(self, lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                      toimipaikka_organisaatio_oid, tallentaja_organisaatio_oid):
        oma_organisaatio_oid = lapsi_obj.oma_organisaatio.organisaatio_oid
        paos_organisaatio_oid = lapsi_obj.paos_organisaatio.organisaatio_oid
        assign_vakajarjestaja_lapsi_paos_permissions(oma_organisaatio_oid,
                                                     paos_organisaatio_oid,
                                                     tallentaja_organisaatio_oid,
                                                     lapsi_obj)
        assign_vakajarjestaja_vakatiedot_paos_permissions(oma_organisaatio_oid,
                                                          paos_organisaatio_oid,
                                                          tallentaja_organisaatio_oid,
                                                          Varhaiskasvatuspaatos,
                                                          varhaiskasvatuspaatos_obj)
        assign_vakajarjestaja_vakatiedot_paos_permissions(oma_organisaatio_oid,
                                                          paos_organisaatio_oid,
                                                          tallentaja_organisaatio_oid,
                                                          Varhaiskasvatussuhde,
                                                          varhaiskasvatussuhde_obj)
        assign_toimipaikka_lapsi_paos_permissions(toimipaikka_organisaatio_oid,
                                                  tallentaja_organisaatio_oid,
                                                  lapsi_obj)
        assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_organisaatio_oid,
                                                       tallentaja_organisaatio_oid,
                                                       Varhaiskasvatuspaatos,
                                                       varhaiskasvatuspaatos_obj)
        assign_toimipaikka_vakatiedot_paos_permissions(toimipaikka_organisaatio_oid,
                                                       tallentaja_organisaatio_oid,
                                                       Varhaiskasvatussuhde,
                                                       varhaiskasvatussuhde_obj)

    def assign_non_paos_lapsi_permissions(self, lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                          vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid):
        """
        Add group-level permissions (vakajarjestaja & toimipaikka)
        """
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Varhaiskasvatussuhde, varhaiskasvatussuhde_obj)
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_obj)
        assign_permissions_for_non_paos_lapsi(lapsi_obj, vakajarjestaja_organisaatio_oid,
                                              toimipaikka_oid=toimipaikka_organisaatio_oid)
        if toimipaikka_organisaatio_oid:
            """
            TODO: Add these to every case after dummy-toimipaikat are removed.
            """
            assign_object_level_permissions(toimipaikka_organisaatio_oid, Varhaiskasvatussuhde, varhaiskasvatussuhde_obj)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_obj)

        # Remove user specific permissions from Varhaiskasvatuspaatos object, since they might have been assigned if
        # Lapsi is still missing vakatoimija-field
        user = self.request.user
        remove_perm('view_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)
        remove_perm('change_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)
        remove_perm('delete_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data['toimipaikka']
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid
        lapsi_obj = validated_data['varhaiskasvatuspaatos'].lapsi

        check_overlapping_varhaiskasvatussuhde(validated_data)

        self.validate_lapsi_not_under_different_vakajarjestaja(lapsi_obj, vakajarjestaja_obj)

        is_paos_lapsi = lapsi_obj.paos_kytkin
        toimipaikka_added_to_org_palvelu = toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka_obj)
        toimipaikka_organisaatio_oid = ''
        if not toimipaikka_added_to_org_palvelu:
            """
            TODO: Remove this when dummy-toimipaikat are removed.
            User needs tallentaja-permissions on vakajarjestaja-level.
            """
            if vakajarjestaja_organisaatio_oid == '':
                logger.error('Missing organisaatio_oid for vakajarjestaja: ' + str(vakajarjestaja_obj.id))
                raise ValidationError({'errors': [ErrorMessages.VS002.value]})
        else:
            toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
            check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user, lapsi_obj.oma_organisaatio)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            delete_cache_keys_related_model('varhaiskasvatuspaatos', saved_object.varhaiskasvatuspaatos.id)
            delete_toimipaikan_lapset_cache(str(saved_object.toimipaikka.id))
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))

            varhaiskasvatussuhde_obj = saved_object
            varhaiskasvatuspaatos_obj = varhaiskasvatussuhde_obj.varhaiskasvatuspaatos

            if is_paos_lapsi:
                paos_oikeus = check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(lapsi_obj.oma_organisaatio, lapsi_obj.paos_organisaatio)
                tallentaja_organisaatio_oid = paos_oikeus.tallentaja_organisaatio.organisaatio_oid
                self.assign_paos_lapsi_permissions(lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                                   toimipaikka_organisaatio_oid, tallentaja_organisaatio_oid)
                cache.delete('vakajarjestaja_yhteenveto_' + str(lapsi_obj.oma_organisaatio.id))
            else:
                # Not PAOS-lapsi (i.e. normal case)
                try:
                    self.assign_non_paos_lapsi_permissions(lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                                           vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
                except Group.DoesNotExist:
                    logger.error('Missing Group for toimija {} and toimipaikka {}'
                                 .format(vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid))
                    raise CustomServerErrorException

            assign_vakasuhde_henkilo_permissions(varhaiskasvatussuhde_obj)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        instance = self.get_object()
        toimipaikka_obj = instance.toimipaikka
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

        if 'varhaiskasvatuspaatos' in validated_data and instance.varhaiskasvatuspaatos != validated_data['varhaiskasvatuspaatos']:
            raise ValidationError({'varhaiskasvatuspaatos': [ErrorMessages.VS003.value]})
        if 'toimipaikka' in validated_data and instance.toimipaikka != validated_data['toimipaikka']:
            raise ValidationError({'toimipaikka': [ErrorMessages.VS004.value]})

        check_overlapping_varhaiskasvatussuhde(validated_data, instance.id)

        saved_object = serializer.save(changed_by=user)
        """
        No need to delete the related-object caches. User cannot change toimipaikka or varhaiskasvatuspaatos.
        """
        delete_toimipaikan_lapset_cache(str(saved_object.toimipaikka.id))
        cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))
        lapsi_obj = saved_object.varhaiskasvatuspaatos.lapsi
        if lapsi_obj.paos_kytkin:
            cache.delete('vakajarjestaja_yhteenveto_' + str(lapsi_obj.oma_organisaatio.id))

    def perform_destroy(self, instance):
        delete_toimipaikan_lapset_cache(str(instance.toimipaikka.id))
        cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))
        delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
        delete_cache_keys_related_model('varhaiskasvatuspaatos', instance.varhaiskasvatuspaatos.id)
        lapsi_obj = instance.varhaiskasvatuspaatos.lapsi
        if lapsi_obj.paos_kytkin:
            cache.delete('vakajarjestaja_yhteenveto_' + str(lapsi_obj.oma_organisaatio.id))
        instance.delete()


@auditlogclass
@request_log_viewset_decorator_factory()
class MaksutietoViewSet(IncreasedModifyThrottleMixin, ObjectByTunnisteMixin, ModelViewSet):
    """
    list:
        hae maksutiedot

    retrieve:
        hae yksittäinen maksutieto

    create:
        luo maksutieto

    update:
        päivitä maksutiedon kentät

    partial_update:
        päivitä yksittäinen tieto maksutiedosta

    delete:
        poista maksutieto
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.MaksutietoFilter
    # Only query distinct results, as related object filters can return the same object multiple times
    queryset = Maksutieto.objects.all().distinct().order_by('id')
    serializer_class = None
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def get_serializer_class(self):
        request = self.request
        if request.method == 'POST':
            return MaksutietoPostSerializer
        else:
            return MaksutietoGetUpdateSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path, object_id=self.get_object().id)

    def validate_user_data(self, data):
        # data validations
        paattymis_pvm_filter = Q()

        if not data['yksityinen_jarjestaja']:
            if 'perheen_koko' not in data:
                raise ValidationError({'perheen_koko': [ErrorMessages.MA001.value]})

        alkamis_pvm_filter = (Q(huoltajuussuhteet__lapsi=data['lapsi']) &
                              (Q(paattymis_pvm=None) | Q(paattymis_pvm__gte=data['alkamis_pvm']))
                              )

        if 'paattymis_pvm' in data and data['paattymis_pvm'] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(data['alkamis_pvm'], data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI004.value]})
            paattymis_pvm_filter = (Q(alkamis_pvm__lte=data['paattymis_pvm']))

        if not data['huoltajat'] or len(data['huoltajat']) == 0:
            raise ValidationError({'huoltajat': [ErrorMessages.MA002.value]})

        vtj_huoltajuudet = self.fetch_and_match_huoltajuudet(data)
        if vtj_huoltajuudet.count() == 0:
            raise ValidationError({'huoltajat': [ErrorMessages.MA003.value]})

        samanaikaiset_maksutiedot = Maksutieto.objects.filter(Q(alkamis_pvm_filter & paattymis_pvm_filter)).distinct().count()
        if samanaikaiset_maksutiedot >= 2:
            raise ValidationError({'errors': [ErrorMessages.MA004.value]})

        return vtj_huoltajuudet

    def validate_yksityinen_maksutieto(self, validated_data, lapsi):
        """
        If maksutieto is yksityinen, palveluseteli_arvo and perheen_koko are not stored.
        :param lapsi: lapsi object
        :param validated_data: serializer.validated_data
        :return:
        """
        if lapsi.yksityinen_kytkin:
            validated_data['yksityinen_jarjestaja'] = True
            validated_data['palveluseteli_arvo'] = None
            validated_data['perheen_koko'] = None

    def validate_maksun_peruste(self, validated_data):
        """
        If maksun peruste is mp01, asiakasmaksu and palveluseteli_arvo are not stored
        :param validated_data: serializer.validated_data
        :return:
        """
        if validated_data['maksun_peruste_koodi'].lower() == 'mp01':
            validated_data['asiakasmaksu'] = 0
            validated_data['palveluseteli_arvo'] = 0.00

    def validate_start_and_end_dates(self, vakapaatokset, start_date, end_date, lapsi):
        """
        Validate the dates for the maksutieto:
        :param vakapaatokset: vakapaatokset of lapsi
        :param start_date: must be after the earliest vakapaatos start
        :param end_date: if given, must be before the latest vakapaatos end
        :param lapsi: lapsi object
        """
        earliest_alkamis_pvm = vakapaatokset.earliest('alkamis_pvm').alkamis_pvm
        latest_paattymis_pvm = vakapaatokset.latest('paattymis_pvm').paattymis_pvm

        if start_date is not None and validators.validate_paivamaara1_before_paivamaara2(start_date, earliest_alkamis_pvm, can_be_same=False):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.MA005.value]})

        if all((v.paattymis_pvm is not None) for v in vakapaatokset):
            if start_date is not None and not validators.validate_paivamaara1_after_paivamaara2(latest_paattymis_pvm, start_date, can_be_same=True):
                raise ValidationError({'alkamis_pvm': [ErrorMessages.MA006.value]})

        """
        While it is possible to leave out the end date, it must fall within vakapaatokset if given.
        Make this check only if all vakapaatokset have a paattymis_pvm.
        """
        if end_date is not None:
            if all((v.paattymis_pvm is not None) for v in vakapaatokset):
                if not validators.validate_paivamaara1_after_paivamaara2(latest_paattymis_pvm, end_date, can_be_same=True):
                    raise ValidationError({'paattymis_pvm': [ErrorMessages.MA007.value]})

        if lapsi.yksityinen_kytkin and end_date and end_date < datetime.date(2020, 9, 1):
            raise ValidationError({'paattymis_pvm': [ErrorMessages.MA014.value]})

    def fetch_and_match_huoltajuudet(self, data):
        queryset_filter = Q()

        # get VTJ_huoltajat from database
        vtj_huoltajuudet = (Huoltajuussuhde.objects
                            .filter(lapsi=data['lapsi'])
                            .filter(voimassa_kytkin=True)
                            )

        # validate VTJ_huoltaja to be one of the persons in the data

        for user_huoltaja in data['huoltajat']:
            etunimi_q = Q()
            etunimet_list = user_huoltaja['etunimet'].split()
            for etunimi in etunimet_list:
                etunimi_q = Q(huoltaja__henkilo__etunimet__search=etunimi) | etunimi_q
            if 'henkilo_oid' in user_huoltaja:
                henkilo_filter = ((etunimi_q |
                                  Q(huoltaja__henkilo__sukunimi__iexact=user_huoltaja['sukunimi'])) &
                                  Q(huoltaja__henkilo__henkilo_oid=user_huoltaja['henkilo_oid'])
                                  )
            else:
                validators.validate_henkilotunnus(user_huoltaja['henkilotunnus'])
                henkilotunnus = hash_string(user_huoltaja['henkilotunnus'])
                henkilo_filter = ((etunimi_q |
                                  Q(huoltaja__henkilo__sukunimi__iexact=user_huoltaja['sukunimi'])) &
                                  Q(huoltaja__henkilo__henkilotunnus_unique_hash=henkilotunnus)
                                  )
            queryset_filter = (queryset_filter | henkilo_filter)

        return vtj_huoltajuudet.filter(queryset_filter)

    def get_maksutieto(self, saved_data, lapsi, huoltajat, inserted_huoltajat_count):
        return {
            'url': self.request.build_absolute_uri(reverse('maksutieto-detail', args=[saved_data.id])),
            'id': saved_data.id,
            'huoltajat': huoltajat,
            'lapsi': self.request.build_absolute_uri(reverse('lapsi-detail', args=[lapsi.id])),
            'lapsi_tunniste': lapsi.tunniste,
            'maksun_peruste_koodi': saved_data.maksun_peruste_koodi,
            'palveluseteli_arvo': saved_data.palveluseteli_arvo,
            'asiakasmaksu': saved_data.asiakasmaksu,
            'perheen_koko': saved_data.perheen_koko,
            'alkamis_pvm': saved_data.alkamis_pvm,
            'paattymis_pvm': saved_data.paattymis_pvm,
            'tallennetut_huoltajat_count': len(huoltajat),
            'ei_tallennetut_huoltajat_count': inserted_huoltajat_count - len(huoltajat),
            'lahdejarjestelma': saved_data.lahdejarjestelma,
            'tunniste': saved_data.tunniste
        }

    def process_post_maksutieto_response(self, huoltajat, inserted_huoltaja_data):
        for huoltaja in huoltajat:
            """
            Loop for each found huoltaja in our DB, and compare if its 'henkilotunnus' is the same as inserted one.
            If a match is found -> return henkilotunnus.
            If a match is not found -> remove henkilotunnus-attribute from response.
            """
            henkilotunnus_found = False
            henkilotunnus = decrypt_henkilotunnus(huoltaja['henkilotunnus'])
            for inserted_huoltaja in inserted_huoltaja_data:
                for key, value in inserted_huoltaja.items():
                    if key == 'henkilotunnus' and value == henkilotunnus:
                        henkilotunnus_found = True
                        break
                if henkilotunnus_found:
                    break

            if henkilotunnus_found:
                huoltaja['henkilotunnus'] = henkilotunnus
            else:
                huoltaja.pop('henkilotunnus')

    def assign_permissions_for_maksutieto_obj(self, lapsi, vakajarjestaja_organisaatio_oid, toimipaikka_qs, saved_object):
        """
        Add group-level permissions (vakajarjestaja & toimipaikka)
        In case of PAOS only oma_organisaatio (kunta/kuntayhtyma) has permissions to add, edit and delete
        """
        if lapsi.paos_kytkin:
            oma_organisaatio_oid = lapsi.oma_organisaatio.organisaatio_oid
            assign_object_level_permissions(oma_organisaatio_oid, Maksutieto, saved_object)

        else:
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Maksutieto, saved_object)
            for toimipaikka in toimipaikka_qs:
                if toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka):
                    assign_object_level_permissions(toimipaikka.organisaatio_oid, Maksutieto, saved_object)

    def create(self, request, *args, **kwargs):
        user = self.request.user
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        lapsi = serializer.validated_data['lapsi']
        serializer.validated_data['yksityinen_jarjestaja'] = False

        vakapaatokset = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).order_by('-alkamis_pvm')
        vakapaatos = vakapaatokset.first()
        if not vakapaatos:
            raise ValidationError({'errors': [ErrorMessages.MA008.value]})

        self.validate_yksityinen_maksutieto(serializer.validated_data, lapsi)

        """
        In order to be able to add maksutieto to lapsi, we need to know the organizations
        (toimipaikat + vakajarjestaja) where the lapsi is at daycare.
        We need this info for permissions.
        """
        toimipaikka_qs = Toimipaikka.objects.filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__id=lapsi.id)
        if not toimipaikka_qs:
            raise ValidationError({'errors': [ErrorMessages.MA009.value]})
        vakajarjestaja = toimipaikka_qs[0].vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja.organisaatio_oid

        if lapsi.paos_kytkin:
            if not user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, lapsi.oma_organisaatio.organisaatio_oid):
                raise PermissionDenied({'errors': [ErrorMessages.MA010.value]})
        else:
            if not user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, vakajarjestaja_organisaatio_oid, toimipaikka_qs):
                raise PermissionDenied({'errors': [ErrorMessages.MA010.value]})

        data = dict(serializer.validated_data)
        vtj_huoltajuudet = self.validate_user_data(data)

        self.validate_maksun_peruste(serializer.validated_data)

        # remove fields not directly in database
        serializer.validated_data.pop('huoltajat')
        serializer.validated_data.pop('lapsi')

        self.validate_start_and_end_dates(vakapaatokset, serializer.validated_data['alkamis_pvm'],
                                          serializer.validated_data.get('paattymis_pvm', None), lapsi)

        """
        Save maksutieto
        """
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))
            self.assign_permissions_for_maksutieto_obj(lapsi, vakajarjestaja_organisaatio_oid, toimipaikka_qs, saved_object)

        # make changes to huoltajuussuhteet
        [huoltajuussuhde.maksutiedot.add(saved_object.id) for huoltajuussuhde in vtj_huoltajuudet]

        henkilo_attributes = ['henkilotunnus', 'henkilo_oid', 'etunimet', 'sukunimi']
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=vtj_huoltajuudet).values(*henkilo_attributes)
        self.process_post_maksutieto_response(huoltajat, data['huoltajat'])

        # return saved object and related information
        return_maksutieto_to_user = self.get_maksutieto(saved_object, lapsi, huoltajat, len(data['huoltajat']))

        headers = self.get_success_headers(saved_object)
        return Response(return_maksutieto_to_user, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        maksutieto_obj = self.get_object()
        data = serializer.validated_data
        paattymis_pvm_q = Q()

        if 'paattymis_pvm' in data and data['paattymis_pvm'] is not None:
            if validators.validate_paivamaara1_after_paivamaara2(data['alkamis_pvm'], data['paattymis_pvm'],
                                                                 can_be_same=False):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI004.value]})
            paattymis_pvm_q = Q(alkamis_pvm__lte=data['paattymis_pvm'])

        lapsi_objects = Lapsi.objects.filter(huoltajuussuhteet__maksutiedot__id=maksutieto_obj.id).distinct()
        if len(lapsi_objects) != 1:
            logger.error('Error getting lapsi for maksutieto ' + str(maksutieto_obj.id))
            raise CustomServerErrorException
        lapsi_object = lapsi_objects[0]

        vakapaatokset = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi_object).order_by('-alkamis_pvm')
        if not vakapaatokset.exists():
            raise ValidationError({'errors': [ErrorMessages.MA008.value]})
        if not Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__in=vakapaatokset).exists():
            raise ValidationError({'errors': [ErrorMessages.MA009.value]})

        self.validate_start_and_end_dates(vakapaatokset, data.get('alkamis_pvm', None),
                                          data.get('paattymis_pvm', None), lapsi_object)

        samanaikaiset_maksutiedot = Maksutieto.objects.filter(
            Q(huoltajuussuhteet__lapsi=lapsi_object) &
            ~Q(id=maksutieto_obj.id) &
            paattymis_pvm_q &
            (Q(paattymis_pvm=None) | Q(paattymis_pvm__gte=maksutieto_obj.alkamis_pvm))
        ).distinct().count()

        if samanaikaiset_maksutiedot >= 2:
            raise ValidationError({'paattymis_pvm': [ErrorMessages.MA004.value]})

        serializer.save(changed_by=user)

        toimipaikka_obj = (Toimipaikka.objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi_object)
                           .first())
        if toimipaikka_obj:
            vakajarjestaja = toimipaikka_obj.vakajarjestaja
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        lapsi_objects = Lapsi.objects.filter(huoltajuussuhteet__maksutiedot=instance).distinct()
        if len(lapsi_objects) != 1:
            logger.error('Error getting lapsi when deleting maksutieto ' + str(instance.id))
            raise CustomServerErrorException
        lapsi_object = lapsi_objects[0]

        self.perform_destroy(instance)

        toimipaikka_obj = (Toimipaikka
                           .objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi_object)
                           .first())
        if toimipaikka_obj:
            vakajarjestaja = toimipaikka_obj.vakajarjestaja
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))

        return Response(status=status.HTTP_204_NO_CONTENT)


@auditlogclass
@request_log_viewset_decorator_factory()
class PaosToimintaViewSet(IncreasedModifyThrottleMixin, GenericViewSet, ListModelMixin, RetrieveModelMixin,
                          CreateModelMixin, DestroyModelMixin):
    """
    list:
        hae palveluseteli- ja ostopalvelutoiminnat

    retrieve:
        hae yksittäinen palveluseteli- ja ostopalvelutoiminta

    create:
        luo palveluseteli- ja ostopalvelutoiminta

    delete:
        poista palveluseteli- ja ostopalvelutoiminta
    """
    filter_backends = (DjangoFilterBackend, )
    filterset_class = filters.PaosToimintaFilter
    queryset = PaosToiminta.objects.filter(voimassa_kytkin=True).order_by('id')
    serializer_class = PaosToimintaSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def get_paos_toiminta_is_active_q(self, validated_data):
        paos_toiminta_is_active_q = Q()

        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            if validated_data['oma_organisaatio'] == validated_data['paos_organisaatio']:
                raise ValidationError({'oma_organisaatio': [ErrorMessages.PT001.value]})

            paos_toiminta_is_active_q = (Q(oma_organisaatio=validated_data['paos_organisaatio']) &
                                         Q(paos_toimipaikka__vakajarjestaja=validated_data['oma_organisaatio']))

        elif 'paos_toimipaikka' in validated_data and validated_data['paos_toimipaikka'] is not None:
            if validated_data['paos_toimipaikka'].vakajarjestaja == validated_data['oma_organisaatio']:
                raise ValidationError({'paos_toimipaikka': [ErrorMessages.PT002.value]})

            paos_toiminta_is_active_q = (Q(oma_organisaatio=validated_data['paos_toimipaikka'].vakajarjestaja) &
                                         Q(paos_organisaatio=validated_data['oma_organisaatio']))

            toimipaikka_jarjestamismuoto_koodit = validated_data['paos_toimipaikka'].jarjestamismuoto_koodi
            toimipaikka_jarjestamismuoto_koodit = [jarjestamismuoto_koodi.lower() for jarjestamismuoto_koodi in toimipaikka_jarjestamismuoto_koodit]
            toimipaikka_jarjestamismuoto_koodit_set = set(toimipaikka_jarjestamismuoto_koodit)
            paos_jarjestamismuoto_koodit_set = set(['jm02', 'jm03'])
            if len(toimipaikka_jarjestamismuoto_koodit_set.intersection(paos_jarjestamismuoto_koodit_set)) == 0:
                raise ValidationError({'paos_toimipaikka': [ErrorMessages.PT003.value]})

        return paos_toiminta_is_active_q

    def get_default_tallentaja_organisaatio(self, validated_data):
        oma_organisaatio = validated_data['oma_organisaatio']
        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            paos_organisaatio = validated_data['paos_organisaatio']
            return paos_organisaatio
        return oma_organisaatio

    def get_non_tallentaja_organisation(self, tallentaja_organisaatio, jarjestaja_kunta_organisaatio, tuottaja_organisaatio):
        if jarjestaja_kunta_organisaatio != tallentaja_organisaatio:
            return jarjestaja_kunta_organisaatio
        return tuottaja_organisaatio

    def get_jarjestaja_kunta_organisaatio(self, validated_data):
        if 'paos_toimipaikka' in validated_data and validated_data['paos_toimipaikka'] is not None:
            return validated_data['oma_organisaatio']
        return validated_data['paos_organisaatio']

    def get_tuottaja_organisaatio(self, validated_data):
        if 'paos_toimipaikka' in validated_data and validated_data['paos_toimipaikka'] is not None:
            return validated_data['paos_toimipaikka'].vakajarjestaja
        return validated_data['oma_organisaatio']

    def get_existing_paos_toiminta_obj(self, validated_data):
        if 'paos_toimipaikka' in validated_data:
            paos_toiminta_query = (Q(oma_organisaatio=validated_data['oma_organisaatio']) &
                                   Q(paos_toimipaikka=validated_data['paos_toimipaikka']))
        else:
            paos_toiminta_query = (Q(oma_organisaatio=validated_data['oma_organisaatio']) &
                                   Q(paos_organisaatio=validated_data['paos_organisaatio']))
        return PaosToiminta.objects.filter(paos_toiminta_query).first()

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        check_if_user_has_paakayttaja_permissions(validated_data['oma_organisaatio'].organisaatio_oid, user)
        paos_toiminta_is_active_q = self.get_paos_toiminta_is_active_q(validated_data)
        paos_toiminta_is_active = PaosToiminta.objects.filter(Q(voimassa_kytkin=True) & Q(paos_toiminta_is_active_q))
        jarjestaja_kunta_organisaatio = self.get_jarjestaja_kunta_organisaatio(validated_data)
        tuottaja_organisaatio = self.get_tuottaja_organisaatio(validated_data)
        serializer.instance = self.get_existing_paos_toiminta_obj(validated_data)

        with transaction.atomic():
            try:
                if not serializer.instance:
                    saved_object = serializer.save(changed_by=user)
                    VARDA_PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
                    group_name = Group.objects.filter(name=VARDA_PAAKAYTTAJA + '_' + validated_data['oma_organisaatio'].organisaatio_oid)
                    assign_perm('view_paostoiminta', group_name, saved_object)
                    assign_perm('delete_paostoiminta', group_name, saved_object)
                else:
                    if serializer.instance.voimassa_kytkin:
                        # This will cause IntegrityError to be raised on save
                        serializer.instance = None
                    else:
                        serializer.instance.voimassa_kytkin = True
                    serializer.save(changed_by=user)

                paos_oikeus_old = PaosOikeus.objects.filter(
                    Q(jarjestaja_kunta_organisaatio=jarjestaja_kunta_organisaatio, tuottaja_organisaatio=tuottaja_organisaatio)
                ).first()  # Either None or the actual paos-oikeus obj

                if paos_oikeus_old:
                    if not paos_oikeus_old.voimassa_kytkin and paos_toiminta_is_active.exists():
                        paos_oikeus_old.voimassa_kytkin = True
                        paos_oikeus_old.changed_by = user
                        paos_oikeus_old.save()
                    grant_or_deny_access_to_paos_toimipaikka(True, jarjestaja_kunta_organisaatio, tuottaja_organisaatio)
                elif not paos_oikeus_old:
                    # Only one half is accepted so no toimipaikka permissions will be granted here
                    tallentaja_organisaatio = self.get_default_tallentaja_organisaatio(validated_data)
                    paos_oikeus_new = PaosOikeus.objects.create(
                        jarjestaja_kunta_organisaatio=jarjestaja_kunta_organisaatio,
                        tuottaja_organisaatio=tuottaja_organisaatio,
                        voimassa_kytkin=False,
                        tallentaja_organisaatio=tallentaja_organisaatio,
                        changed_by=user
                    )
                    non_tallentaja_organisation = self.get_non_tallentaja_organisation(tallentaja_organisaatio, jarjestaja_kunta_organisaatio, tuottaja_organisaatio)
                    group_name = Group.objects.filter(name=VARDA_PAAKAYTTAJA + '_' + non_tallentaja_organisation.organisaatio_oid)
                    assign_perm('view_paosoikeus', group_name, paos_oikeus_new)
                    # set permission for kunta to change
                    group_name = Group.objects.filter(name=VARDA_PAAKAYTTAJA + '_' + tallentaja_organisaatio.organisaatio_oid)
                    assign_perm('view_paosoikeus', group_name, paos_oikeus_new)
                    assign_perm('change_paosoikeus', group_name, paos_oikeus_new)

            except IntegrityError as e:
                if 'oma_organisaatio_paos_organisaatio_unique_constraint' in str(e):
                    msg = {'errors': [ErrorMessages.PT004.value]}
                    raise ValidationError(msg)
                elif 'oma_organisaatio_paos_toimipaikka_unique_constraint' in str(e):
                    msg = {'errors': [ErrorMessages.PT005.value]}
                    raise ValidationError(msg)
                else:
                    logger.error('IntegrityError at PaosToimintaViewSet: {}'.format(e))
                    raise CustomServerErrorException

    def perform_destroy(self, instance):
        """
        Make voimassa_kytkin false when organisation permissions is deleted or when last toimipaikka permission is deleted
        """
        paos_oikeus_object = None
        is_delete = False  # If toimipaikka permissions are removed instance should also be deleted

        with transaction.atomic():
            if instance.paos_organisaatio is not None:
                paos_oikeus_object = PaosOikeus.objects.filter(
                    Q(jarjestaja_kunta_organisaatio=instance.paos_organisaatio, tuottaja_organisaatio=instance.oma_organisaatio)
                ).first()
                # Remove view access to all toimipaikka where tuottaja has not added any children
                grant_or_deny_access_to_paos_toimipaikka(False, paos_oikeus_object.jarjestaja_kunta_organisaatio, paos_oikeus_object.tuottaja_organisaatio)
                is_delete = True
            elif instance.paos_toimipaikka is not None:
                # Remove view access to this toimipaikka if tuottaja has not added any children there
                if not VakaJarjestaja.objects.filter(paos_lapsi_oma_organisaatio__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka=instance.paos_toimipaikka).exists():
                    permission_groups.remove_object_level_permissions(instance.oma_organisaatio.organisaatio_oid, Toimipaikka, instance.paos_toimipaikka, paos_kytkin=True)
                    is_delete = True
                paos_toimipaikka_count = PaosToiminta.objects.filter(
                    Q(voimassa_kytkin=True) &
                    Q(oma_organisaatio=instance.oma_organisaatio) &
                    Q(paos_toimipaikka__vakajarjestaja=instance.paos_toimipaikka.vakajarjestaja)
                ).count()
                if paos_toimipaikka_count == 1:  # Last toimipaikka permission is being removed
                    paos_oikeus_object = PaosOikeus.objects.filter(
                        Q(jarjestaja_kunta_organisaatio=instance.oma_organisaatio, tuottaja_organisaatio=instance.paos_toimipaikka.vakajarjestaja)
                    ).first()

            instance.voimassa_kytkin = False
            instance.delete() if is_delete else instance.save()
            if paos_oikeus_object:
                paos_oikeus_object.voimassa_kytkin = False
                paos_oikeus_object.save()  # we cannot use update since we need to catch the pre_save signal


@auditlogclass
@request_log_viewset_decorator_factory()
class PaosOikeusViewSet(IncreasedModifyThrottleMixin, GenericViewSet, UpdateModelMixin, ListModelMixin,
                        RetrieveModelMixin):
    """
    list:
        hae organisaatioiden väliset palveluseteli- ja ostopalveluoikeudet

    retrieve:
        hae yksittäinen palveluseteli- ja ostopalveluoikeus

    update:
        päivitä organisaatioiden välillä oleva tallentaja

    partial_update:
        päivitä organisaatioiden välillä oleva tallentaja
    """
    filter_backends = (DjangoFilterBackend, )
    filterset_class = filters.PaosOikeusFilter
    queryset = PaosOikeus.objects.all().order_by('id')
    serializer_class = PaosOikeusSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_update(self, serializer):
        user = self.request.user
        paos_oikeus_obj = self.get_object()
        validated_data = serializer.validated_data

        if (validated_data['tallentaja_organisaatio'] != paos_oikeus_obj.jarjestaja_kunta_organisaatio and
                validated_data['tallentaja_organisaatio'] != paos_oikeus_obj.tuottaja_organisaatio):
            raise ValidationError({'tallentaja_organisaatio': [ErrorMessages.PO001.value]}, code='invalid')

        # do not allow unnecessary updates
        if paos_oikeus_obj.tallentaja_organisaatio == validated_data['tallentaja_organisaatio']:
            raise ValidationError({'tallentaja_organisaatio': [ErrorMessages.PO002.value]}, code='invalid')

        with transaction.atomic():
            serializer.save(changed_by=user)


"""
Nested viewsets, e.g. /api/v1/vakajarjestajat/33/toimipaikat/
"""


@auditlogclass
class NestedVakajarjestajaYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan yhteenvetotiedot
    """
    queryset = VakaJarjestaja.objects.all()
    serializer_class = VakaJarjestajaYhteenvetoSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    today = None
    vakajarjestaja_id = None
    swagger_schema = IntegerIdSchema

    def get_active_filter(self, prefix):
        return (Q(**{prefix + 'alkamis_pvm__lte': self.today}) &
                (Q(**{prefix + 'paattymis_pvm__isnull': True}) | Q(**{prefix + 'paattymis_pvm__gte': self.today})))

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        self.today = datetime.datetime.now()

        self.kwargs['pk'] = self.kwargs['vakajarjestaja_pk']
        self.vakajarjestaja_id = self.kwargs['pk']
        if not self.vakajarjestaja_id.isdigit():
            raise Http404
        vakajarjestaja_obj = self.get_object()
        data = cache.get('vakajarjestaja_yhteenveto_' + self.vakajarjestaja_id)
        if data is None:
            data = {
                'vakajarjestaja_nimi': vakajarjestaja_obj.nimi,
                'lapset_lkm': self.get_lapset_lkm(),
                'lapset_vakapaatos_voimassaoleva': self.get_vakapaatos_voimassaoleva(),
                'lapset_vakasuhde_voimassaoleva': self.get_vakasuhde_voimassaoleva(),
                'lapset_vuorohoidossa': self.get_vuorohoito_lapset(),
                'lapset_palveluseteli_ja_ostopalvelu': self.get_paos_lapset(),
                'lapset_maksutieto_voimassaoleva': self.get_maksutieto_voimassaoleva(),
                'toimipaikat_voimassaolevat': self.get_active_toimipaikat(),
                'toimipaikat_paattyneet': self.get_closed_toimipaikat(),
                'toimintapainotukset_maara': self.get_toimipaikkojen_toimintapainotukset(),
                'kielipainotukset_maara': self.get_toimipaikkojen_kielipainotukset(),
                'tyontekijat_lkm': self.get_tyontekija_count(),
                'palvelussuhteet_voimassaoleva': self.get_active_palvelussuhde_count(),
                'palvelussuhteet_maaraaikaiset': self.get_active_palvelussuhde_maaraaikainen_count(),
                'varhaiskasvatusalan_tutkinnot': self.get_vaka_tutkinto_count(),
                'tyoskentelypaikat_kelpoiset': self.get_kelpoinen_tyoskentelypaikka_count(),
                'taydennyskoulutukset_kuluva_vuosi': self.get_taydennyskoulutus_count_this_year(),
                'tilapainen_henkilosto_maara_kuluva_vuosi': self.get_tilapainen_henkilosto_maara_this_year(),
                'tilapainen_henkilosto_tunnit_kuluva_vuosi': self.get_tilapainen_henkilosto_tunnit_this_year()
            }
            cache.set('vakajarjestaja_yhteenveto_' + self.vakajarjestaja_id, data, 8 * 60 * 60)

        serializer = self.get_serializer(data, many=False)
        return Response(serializer.data)

    def get_lapset_lkm(self):
        """
        Return the number of unique lapset (having an active vakasuhde) in all toimipaikat under the vakajarjestaja.
        """
        organisation_filter = Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                        (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                         Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))

        return (Lapsi.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_vakapaatos_voimassaoleva(self):
        organisation_filter = Q(varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id)
        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (Varhaiskasvatuspaatos.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_vakasuhde_voimassaoleva(self):
        organisation_filter = Q(toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (Varhaiskasvatussuhde.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_vuorohoito_lapset(self):
        """
        Return the number of unique lapset (having an active vakasuhde AND vuorohoito_kytkin=True) in all toimipaikat under the vakajarjestaja.
        """
        organisation_filter = Q(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id) &
                                Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False))

        vuorohoito_filter = Q(varhaiskasvatuspaatokset__vuorohoito_kytkin=True)

        date_filter = Q(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                        (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                         Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))

        return (Lapsi.objects
                .filter(organisation_filter &
                        vuorohoito_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_paos_lapset(self):
        """
        Return the number of unique lapset (having an active vakasuhde) in Palveluseteli or Ostopalvelu under the vakajarjestaja.
        """
        organisation_filter = Q(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id) |
                                Q(oma_organisaatio=self.vakajarjestaja_id) |
                                Q(paos_organisaatio=self.vakajarjestaja_id) &
                                Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False))

        jarjestamismuoto_filter = Q(Q(varhaiskasvatuspaatokset__jarjestamismuoto_koodi__iexact="JM02") |
                                    Q(varhaiskasvatuspaatokset__jarjestamismuoto_koodi__iexact="JM03"))

        date_filter = Q(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                        (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                        Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))

        return (Lapsi.objects
                .filter(organisation_filter &
                        jarjestamismuoto_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_maksutieto_voimassaoleva(self):
        """
        Returns the number of unique active maksutieto objects
        """

        # in paos cases only children in oma_organisaatio are counted
        organisation_filter = Q((Q(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id) &
                                Q(huoltajuussuhteet__lapsi__paos_kytkin=False)) |
                                (Q(huoltajuussuhteet__lapsi__oma_organisaatio__id=self.vakajarjestaja_id) &
                                Q(huoltajuussuhteet__lapsi__paos_kytkin=True)) &
                                Q(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False))

        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (Maksutieto.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_active_toimipaikat(self):
        organisation_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (Toimipaikka.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_closed_toimipaikat(self):
        organisation_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(paattymis_pvm__lt=self.today)

        return (Toimipaikka.objects
                .filter(organisation_filter,
                        date_filter)
                .distinct()
                .count()
                )

    def get_toimipaikkojen_toimintapainotukset(self):
        """
        Return the number of active toimintapainotukset in all toimipaikat under the vakajarjestaja.
        """
        organisation_filter = Q(toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (ToiminnallinenPainotus.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_toimipaikkojen_kielipainotukset(self):
        """
        Return the number of active kielipainotukset in all toimipaikat under the vakajarjestaja.
        """
        organisation_filter = Q(toimipaikka__vakajarjestaja__id=self.vakajarjestaja_id)

        date_filter = Q(Q(alkamis_pvm__lte=self.today) &
                        (Q(paattymis_pvm__isnull=True) |
                         Q(paattymis_pvm__gte=self.today)))

        return (KieliPainotus.objects
                .filter(organisation_filter &
                        date_filter)
                .distinct()
                .count()
                )

    def get_tyontekija_count(self):
        """
        :return: number of tyontekijat
        """
        tyontekija_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)
        return Tyontekija.objects.filter(tyontekija_filter).count()

    def get_active_palvelussuhde_count(self):
        """
        :return: number of active palvelussuhteet
        """
        date_filter = self.get_active_filter('')
        vakajarjestaja_filter = Q(tyontekija__vakajarjestaja__id=self.vakajarjestaja_id)
        return Palvelussuhde.objects.filter(date_filter & vakajarjestaja_filter).distinct().count()

    def get_active_palvelussuhde_maaraaikainen_count(self):
        """
        :return: number of active palvelussuhteet that have tyosuhde_koodi = 2 (maaraaikainen)
        """
        date_filter = self.get_active_filter('')
        vakajarjestaja_filter = Q(tyontekija__vakajarjestaja_id=self.vakajarjestaja_id)
        tyosuhde_filter = Q(tyosuhde_koodi=2)
        return Palvelussuhde.objects.filter(date_filter & vakajarjestaja_filter & tyosuhde_filter).distinct().count()

    def get_taydennyskoulutus_count_this_year(self):
        """
        :return: number of taydennyskoulutukset this year
        """
        suoritus_pvm_filter = Q(suoritus_pvm__year=self.today.year)
        vakajarjestaja_filter = Q(tyontekijat__vakajarjestaja__id=self.vakajarjestaja_id)
        return Taydennyskoulutus.objects.filter(suoritus_pvm_filter & vakajarjestaja_filter).distinct().count()

    def get_kelpoinen_tyoskentelypaikka_count(self):
        """
        :return: number of tyoskentelypaikat with kelpoisuus_kytkin=True
        """
        kelpoisuus_filter = Q(kelpoisuus_kytkin=True)
        vakajarjestaja_filter = Q(palvelussuhde__tyontekija__vakajarjestaja__id=self.vakajarjestaja_id)
        return Tyoskentelypaikka.objects.filter(kelpoisuus_filter & vakajarjestaja_filter).distinct().count()

    def get_vaka_tutkinto_count(self):
        """
        :return: number of valid tutkinnot
        """
        tutkinto_koodi_filter = ~Q(tutkinto_koodi='003')
        vakajarjestaja_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)
        return Tutkinto.objects.filter(tutkinto_koodi_filter & vakajarjestaja_filter).distinct().count()

    def get_tilapainen_henkilosto_maara_this_year(self):
        """
        :return: total amount of tilapainen henkilosto this year
        """
        kuukausi_filter = Q(kuukausi__year=self.today.year)
        vakajarjestaja_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)
        return (TilapainenHenkilosto.objects
                .filter(kuukausi_filter & vakajarjestaja_filter)
                .aggregate(sum=Sum('tyontekijamaara')))['sum'] or 0

    def get_tilapainen_henkilosto_tunnit_this_year(self):
        """
        :return: total amount of tilapainen henkilosto hours this year
        """
        kuukausi_filter = Q(kuukausi__year=self.today.year)
        vakajarjestaja_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)
        return (TilapainenHenkilosto.objects
                .filter(kuukausi_filter & vakajarjestaja_filter)
                .aggregate(sum=Sum('tuntimaara')))['sum'] or 0


@auditlogclass
class NestedVarhaiskasvatussuhdeViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        nouda tietyn varhaiskasvatuspaatoksen kaikki varhaiskasvatussuhteet
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = Varhaiskasvatuspaatos

    def get_varhaiskasvatuspaatos(self, request, varhaiskasvatuspaatos_pk=None):
        varhaiskasvatuspaatos = get_object_or_404(Varhaiskasvatuspaatos.objects.all(), pk=varhaiskasvatuspaatos_pk)
        user = request.user
        if user.has_perm('view_varhaiskasvatuspaatos', varhaiskasvatuspaatos):
            return varhaiskasvatuspaatos
        else:
            raise Http404

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['varhaiskasvatuspaatos_pk'].isdigit():
            raise Http404

        self.get_varhaiskasvatuspaatos(request, varhaiskasvatuspaatos_pk=kwargs['varhaiskasvatuspaatos_pk'])
        self.queryset = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos=kwargs['varhaiskasvatuspaatos_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


@auditlogclass
class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vaka-järjestäjän kaikki toimipaikat.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = VakaJarjestaja

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm('view_vakajarjestaja', vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404

        vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=kwargs['vakajarjestaja_pk'])
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj)
        qs_own_toimipaikat = Q(vakajarjestaja=kwargs['vakajarjestaja_pk'])
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        toimipaikka_filter = qs_own_toimipaikat | qs_paos_toimipaikat

        self.queryset = Toimipaikka.objects.filter(toimipaikka_filter).order_by('nimi')

        return cached_list_response(self, request.user, request.get_full_path(), order_by='nimi')


@auditlogclass
class NestedToiminnallinenPainotusViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki toiminnalliset painotukset.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.ToiminnallinenPainotusFilter
    queryset = ToiminnallinenPainotus.objects.none()
    serializer_class = ToiminnallinenPainotusSerializer
    permission_classes = (ToimipaikkaPermissions, )
    swagger_schema = IntegerIdSchema
    swagger_path_model = Toimipaikka

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404
        get_toimipaikka_or_404(request.user, toimipaikka_pk=kwargs['toimipaikka_pk'])

        self.queryset = ToiminnallinenPainotus.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')
        return super(NestedToiminnallinenPainotusViewSet, self).list(request, *args, **kwargs)


@auditlogclass
class NestedKieliPainotusViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki kielipainotukset.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.KieliPainotusFilter
    queryset = KieliPainotus.objects.none()
    serializer_class = KieliPainotusSerializer
    permission_classes = (ToimipaikkaPermissions, )
    swagger_schema = IntegerIdSchema
    swagger_path_model = Toimipaikka

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404
        get_toimipaikka_or_404(request.user, toimipaikka_pk=kwargs['toimipaikka_pk'])

        self.queryset = KieliPainotus.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')
        return super(NestedKieliPainotusViewSet, self).list(request, *args, **kwargs)


@auditlogclass
class NestedVarhaiskasvatussuhdeToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki varhaiskasvatussuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = Toimipaikka

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404

        get_toimipaikka_or_404(request.user, toimipaikka_pk=kwargs['toimipaikka_pk'])
        self.queryset = Varhaiskasvatussuhde.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


@auditlogclass
class NestedVarhaiskasvatuspaatosViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki varhaiskasvatuspäätökset.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatuspaatosFilter
    queryset = Varhaiskasvatuspaatos.objects.none()
    serializer_class = VarhaiskasvatuspaatosSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = Lapsi

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm('view_lapsi', lapsi):
            return lapsi
        else:
            raise Http404

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        self.queryset = Varhaiskasvatuspaatos.objects.filter(lapsi=kwargs['lapsi_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


@auditlogclass
class NestedLapsiKoosteViewSet(ObjectByTunnisteMixin, GenericViewSet, ListModelMixin):
    """
    list:
        Nouda kooste tietyn lapsen tiedoista.
    """
    queryset = Lapsi.objects.all().order_by('id')
    serializer_class = LapsiKoosteSerializer
    permission_classes = (CustomModelPermissions, CustomObjectPermissions,)
    swagger_schema = IntegerIdSchema

    def list(self, request, *args, **kwargs):
        self.kwargs['pk'] = self.kwargs['lapsi_pk']

        user = request.user
        is_superuser_or_oph_staff = user.is_superuser or is_oph_staff(user)

        lapsi = self.get_object()
        lapsi_data = {
            'id': lapsi.id,
            'yksityinen_kytkin': lapsi.yksityinen_kytkin,
            'oma_organisaatio': lapsi.oma_organisaatio,
            'paos_organisaatio': lapsi.paos_organisaatio,
            'henkilo': lapsi.henkilo,
            'lahdejarjestelma': lapsi.lahdejarjestelma,
            'tunniste': lapsi.tunniste,
        }

        paos_organisaatio_oid = None
        if lapsi.vakatoimija:
            oma_organisaatio_oid = lapsi.vakatoimija.organisaatio_oid
        elif lapsi.oma_organisaatio and lapsi.paos_organisaatio:
            oma_organisaatio_oid = lapsi.oma_organisaatio.organisaatio_oid
            paos_organisaatio_oid = lapsi.paos_organisaatio.organisaatio_oid
        else:
            oma_organisaatio_oid = lapsi.varhaiskasvatuspaatokset.values_list(
                'varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__organisaatio_oid', flat=True).first()

        # Get vakapaatokset
        vakapaatos_filter = Q(lapsi=lapsi)
        vakatiedot_organization_groups_qs = user_permission_groups_in_organizations(user, (oma_organisaatio_oid, paos_organisaatio_oid,),
                                                                                    (Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                                                                                     Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                                     Z4_CasKayttoOikeudet.KATSELIJA,))
        if not is_superuser_or_oph_staff and not vakatiedot_organization_groups_qs.exists():
            vakapaatos_filter &= Q(id__in=get_object_ids_for_user_by_model(user, 'varhaiskasvatuspaatos'))

        vakapaatokset = Varhaiskasvatuspaatos.objects.filter(vakapaatos_filter).distinct().order_by('-alkamis_pvm')
        lapsi_data['varhaiskasvatuspaatokset'] = vakapaatokset

        # Get vakasuhteet
        vakasuhde_filter = Q(varhaiskasvatuspaatos__lapsi=lapsi)
        if not is_superuser_or_oph_staff and not vakatiedot_organization_groups_qs.exists():
            vakasuhde_filter &= Q(id__in=get_object_ids_for_user_by_model(user, 'varhaiskasvatussuhde'))

        vakasuhteet = Varhaiskasvatussuhde.objects.filter(vakasuhde_filter).distinct().order_by('-alkamis_pvm')
        lapsi_data['varhaiskasvatussuhteet'] = vakasuhteet

        # Get maksutiedot
        maksutieto_filter = Q(huoltajuussuhteet__lapsi=lapsi)
        huoltajatiedot_organization_groups_qs = user_permission_groups_in_organization(user, oma_organisaatio_oid,
                                                                                       (Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                                                                                        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
                                                                                        Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA))
        if not is_superuser_or_oph_staff and not huoltajatiedot_organization_groups_qs.exists():
            maksutieto_filter &= Q(id__in=get_object_ids_for_user_by_model(user, 'maksutieto'))

        maksutiedot = Maksutieto.objects.filter(maksutieto_filter).distinct().order_by('-alkamis_pvm')
        lapsi_data['maksutiedot'] = maksutiedot

        serializer = self.get_serializer(lapsi_data, many=False)
        return Response(serializer.data)


@auditlogclass
class NestedLapsenVarhaiskasvatussuhdeViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki varhaiskasvatussuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = Lapsi

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm('view_lapsi', lapsi):
            return lapsi
        else:
            raise Http404

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        varhaiskasvatuspaatos_ids = Varhaiskasvatuspaatos.objects.filter(lapsi=kwargs['lapsi_pk']).values('id')
        self.queryset = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos_id__in=varhaiskasvatuspaatos_ids).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


@auditlogclass
class NestedLapsiMaksutietoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki maksutiedot.
    """
    filter_backends = (ObjectPermissionsFilter, DjangoFilterBackend)
    filterset_class = filters.MaksutietoFilter
    queryset = Maksutieto.objects.none()
    serializer_class = MaksutietoGetUpdateSerializer
    permission_classes = (CustomModelPermissions,)
    swagger_schema = IntegerIdSchema
    swagger_path_model = Lapsi

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm('view_lapsi', lapsi):
            return lapsi
        else:
            raise Http404

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        queryset = self.filter_queryset(Maksutieto.objects.filter(huoltajuussuhteet__lapsi=kwargs['lapsi_pk']).distinct().order_by('id'))

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@auditlogclass
class NestedVakajarjestajaPaosToimijatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan paos-järjestäjät
    """
    filter_backends = (ObjectPermissionsFilter,)
    filterset_class = None
    queryset = VakaJarjestaja.objects.none()
    serializer_class = PaosToimijatSerializer
    permission_classes = (CustomModelPermissions,)
    today = datetime.datetime.now()
    swagger_schema = IntegerIdSchema

    def get_vakajarjestaja(self, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = self.request.user
        if user.has_perm('view_vakajarjestaja', vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        if not self.kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404

        vakajarjestaja_obj = self.get_vakajarjestaja(vakajarjestaja_pk=self.kwargs['vakajarjestaja_pk'])

        paos_toiminnat = PaosToiminta.objects.filter(
            Q(voimassa_kytkin=True) &
            Q(oma_organisaatio=vakajarjestaja_obj, paos_organisaatio__isnull=False)
        ).order_by('id')

        page = self.paginate_queryset(paos_toiminnat)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(paos_toiminnat, many=True)
        return Response(serializer.data)


@auditlogclass
class NestedVakajarjestajaPaosToimipaikatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan paos-järjestäjän toimipaikat

    filter:
        toimipaikka_nimi: suodata toimipaikan nimen perusteella
        organisaatio_oid: suodata toimipaikan organisaatio_oid:n perusteella
        toimija_nimi: suodata toimijan nimen perusteella
    """
    filter_backends = (ObjectPermissionsFilter, )
    filterset_class = None
    queryset = VakaJarjestaja.objects.none()
    serializer_class = PaosToimipaikatSerializer
    permission_classes = (CustomModelPermissions,)
    today = datetime.datetime.now()
    swagger_schema = IntegerIdSchema

    def get_vakajarjestaja(self, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = self.request.user
        if user.has_perm('view_vakajarjestaja', vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        if not self.kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404

        query_params = self.request.query_params
        toimipaikka_nimi_filter = query_params.get('toimipaikka_nimi')
        organisaatio_oid_filter = query_params.get('organisaatio_oid')
        toimija_nimi_filter = query_params.get('toimija_nimi')

        vakajarjestaja_obj = self.get_vakajarjestaja(vakajarjestaja_pk=self.kwargs['vakajarjestaja_pk'])
        paos_toiminta_qs = PaosToiminta.objects.filter(
            Q(voimassa_kytkin=True) &
            Q(oma_organisaatio=vakajarjestaja_obj, paos_toimipaikka__isnull=False)
        ).select_related('paos_toimipaikka', 'paos_toimipaikka__vakajarjestaja')

        # Subquery, see the end of page: https://code.djangoproject.com/ticket/24218
        paos_toiminnat = paos_toiminta_qs.filter(
            pk__in=Subquery(
                paos_toiminta_qs.distinct('paos_toimipaikka__id').values('pk')
            )
        ).order_by('paos_toimipaikka__nimi')

        if toimipaikka_nimi_filter is not None:
            paos_toiminnat = paos_toiminnat.filter(paos_toimipaikka__nimi__icontains=toimipaikka_nimi_filter)
        if organisaatio_oid_filter is not None:
            paos_toiminnat = paos_toiminnat.filter(paos_toimipaikka__organisaatio_oid=organisaatio_oid_filter)
        if toimija_nimi_filter is not None:
            paos_toiminnat = paos_toiminnat.filter(paos_toimipaikka__vakajarjestaja__nimi__icontains=toimija_nimi_filter)

        page = self.paginate_queryset(paos_toiminnat)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(paos_toiminnat, many=True)
        return Response(serializer.data)


@auditlogclass
class HenkilohakuLapset(GenericViewSet, ListModelMixin):
    """
    Henkilöhaku rajapinta

    Haettaessa hetulla hetun täytyy olla utf-8 enkoodatusta tekstistä sha256 hashatyssä hexadesimaali muodossa. Parametrit:
        search = henkilön nimi
        filter_status = objektin tila, voi olla 'kaikki', 'voimassaolevat' tai 'paattyneet'
        filter_object = objekti, voi olla 'vakapaatokset', 'vakasuhteet' tai 'maksutiedot'
    """
    serializer_class = HenkilohakuLapsetSerializer
    queryset = Lapsi.objects.none()
    filter_backends = None
    permission_classes = (CustomModelPermissions,)
    search_fields = ('henkilo__etunimet', 'henkilo__sukunimi', '=henkilo__henkilotunnus_unique_hash', '=henkilo__henkilo_oid', )
    tz = pytz.timezone('Europe/Helsinki')
    today = datetime.datetime.now(tz=tz)

    def get_toimipaikka_ids(self):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        vakajarjestaja_obj = get_object_or_404(VakaJarjestaja, pk=vakajarjestaja_id)
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=False)
        qs_own_toimipaikat = Q(vakajarjestaja=vakajarjestaja_obj)
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        return (Toimipaikka
                .objects
                .filter(qs_own_toimipaikat | qs_paos_toimipaikat)
                .values_list('id', flat=True))

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['list_of_toimipaikka_ids'] = self.get_toimipaikka_ids()
        return context

    def set_filter_backends(self, request):
        """
        Do not check for object-level permissions from OPH-admins. Otherwise the query timeouts.
        """
        cas_user_obj_found = True
        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(user=request.user)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            cas_user_obj_found = False

        if cas_user_obj_found and cas_user_obj.approved_oph_staff:
            self.filter_backends = (SearchFilter, )
        else:
            self.filter_backends = (ObjectPermissionsFilter, SearchFilter, )

    def list(self, request, *args, **kwargs):
        """
        Only for throwing not found so swagger doesn't throw tartum.
        """
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit() or not get_object_or_404(VakaJarjestaja, pk=vakajarjestaja_id):
            raise NotFound
        self.set_filter_backends(request)
        return super(HenkilohakuLapset, self).list(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        list_of_toimipaikka_ids = self.get_toimipaikka_ids()
        query = Lapsi.objects.all()
        query_filter = self.get_lapsi_query(list_of_toimipaikka_ids)
        return (self.add_order_by(query.filter(query_filter))
                .prefetch_related('huoltajuussuhteet__maksutiedot',
                                  Prefetch('varhaiskasvatuspaatokset__varhaiskasvatussuhteet',
                                           Varhaiskasvatussuhde.objects.select_related('toimipaikka'))
                                  )
                .select_related('henkilo')
                ).distinct()

    def filter_status_generic(self, query, filter_status):
        if filter_status == 'voimassaolevat':
            query = query.filter(
                Q(alkamis_pvm__lte=self.today) &
                (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=self.today)))
        elif filter_status == 'paattyneet':
            query = query.filter(Q(paattymis_pvm__lt=self.today))
        return query

    def get_lapsi_query(self, list_of_toimipaikka_ids):
        varhaiskasvatuspaatokset_query = (Varhaiskasvatuspaatos
                                          .objects
                                          .filter(varhaiskasvatussuhteet__toimipaikka__id__in=list_of_toimipaikka_ids))

        varhaiskasvatussuhteet_query = (Varhaiskasvatussuhde
                                        .objects
                                        .filter(toimipaikka__id__in=list_of_toimipaikka_ids))

        maksutiedot_query = None

        query_params = self.request.query_params
        filter_status = query_params.get('filter_status', "")
        filter_object = query_params.get('filter_object', "")

        if filter_status != "" and filter_object != "":

            # Vakapaatokset
            if filter_object == 'vakapaatokset':
                varhaiskasvatuspaatokset_query = self.filter_status_generic(varhaiskasvatuspaatokset_query,
                                                                            filter_status)

            # Vakasuhteet
            if filter_object == 'vakasuhteet':
                varhaiskasvatussuhteet_query = self.filter_status_generic(varhaiskasvatussuhteet_query, filter_status)

            # Maksutiedot
            if filter_object == 'maksutiedot':
                maksutiedot_query = (Maksutieto
                                     .objects
                                     .filter(**{'huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset'
                                                '__varhaiskasvatussuhteet__toimipaikka__id__in':
                                                list_of_toimipaikka_ids}))
                maksutiedot_query = self.filter_status_generic(maksutiedot_query, filter_status)

        self.kwargs['varhaiskasvatuspaatokset_query'] = varhaiskasvatuspaatokset_query
        self.kwargs['varhaiskasvatussuhteet_query'] = varhaiskasvatussuhteet_query
        self.kwargs['maksutiedot_query'] = maksutiedot_query

        lapsi_filter = (Q(varhaiskasvatuspaatokset__in=varhaiskasvatuspaatokset_query) &
                        Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__in=varhaiskasvatussuhteet_query))

        if maksutiedot_query is not None:
            lapsi_filter = lapsi_filter & Q(huoltajuussuhteet__maksutiedot__in=maksutiedot_query)

        return lapsi_filter

    def add_order_by(self, query):
        return query.order_by('henkilo__sukunimi', 'henkilo__etunimet')
