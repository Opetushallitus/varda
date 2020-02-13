import logging
import pytz
from datetime import datetime

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q, Count, Prefetch
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import assign_perm, remove_perm
from rest_framework import permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import (NotAuthenticated, NotFound, PermissionDenied, ValidationError)
from rest_framework.filters import SearchFilter
from rest_framework.mixins import (CreateModelMixin, DestroyModelMixin, ListModelMixin, RetrieveModelMixin, UpdateModelMixin)
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_guardian.filters import DjangoObjectPermissionsFilter

from varda import filters, related_object_validations, validators
from varda.cache import cached_list_response, cached_retrieve_response, delete_toimipaikan_lapset_cache,\
    delete_cache_keys_related_model, get_object_ids_user_has_permissions
from varda.clients.oppijanumerorekisteri_client import get_henkilo_data_by_oid, \
    add_henkilo_to_oppijanumerorekisteri, get_henkilo_by_henkilotunnus
from varda.enums.lahdejarjestelma import Lahdejarjestelma
from varda.exceptions.conflict_error import ConflictError
from varda.misc import CustomServerErrorException, decrypt_henkilotunnus, encrypt_henkilotunnus, hash_string
from varda.misc_queries import get_paos_toimipaikat
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Tyontekija,
                          Taydennyskoulutus, Ohjaajasuhde, PaosToiminta, Lapsi, Huoltaja, Huoltajuussuhde, Varhaiskasvatuspaatos,
                          Varhaiskasvatussuhde, Maksutieto, PaosOikeus, Z3_AdditionalCasUserFields, Z4_CasKayttoOikeudet)
from varda.oppijanumerorekisteri import fetch_henkilo_with_oid, update_modified_henkilot_since_datetime, \
    save_henkilo_to_db
from varda.organisaatiopalvelu import check_if_toimipaikka_exists_in_organisaatiopalvelu, \
    create_toimipaikka_in_organisaatiopalvelu
from varda.permission_groups import assign_object_level_permissions, create_permission_groups_for_organisaatio
from varda.permissions import (throw_if_not_tallentaja_permissions,
                               check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement,
                               check_if_user_has_paakayttaja_permissions,
                               CustomObjectPermissions, save_audit_log,
                               user_has_huoltajatieto_tallennus_permissions_to_correct_organization,
                               grant_or_deny_access_to_paos_toimipaikka)
from varda.serializers import (UserSerializer, ExternalPermissionsSerializer, GroupSerializer,
                               UpdateHenkiloWithOidSerializer, UpdateHenkilotChangedSinceSerializer,
                               UpdateOphStaffSerializer, ClearCacheSerializer, ActiveUserSerializer,
                               AuthTokenSerializer, VakaJarjestajaSerializer, ToimipaikkaSerializer,
                               ToiminnallinenPainotusSerializer, KieliPainotusSerializer, HaeHenkiloSerializer,
                               HenkiloSerializer, HenkiloSerializerAdmin, HenkiloOppijanumeroSerializer,
                               TyontekijaSerializer, TaydennyskoulutusSerializer, OhjaajasuhdeSerializer,
                               LapsiSerializer, LapsiSerializerAdmin, HuoltajaSerializer, HuoltajuussuhdeSerializer,
                               MaksutietoPostSerializer, MaksutietoUpdateSerializer, MaksutietoGetSerializer,
                               VarhaiskasvatuspaatosSerializer, VarhaiskasvatuspaatosPutSerializer,
                               VarhaiskasvatuspaatosPatchSerializer, VarhaiskasvatussuhdeSerializer,
                               VakaJarjestajaYhteenvetoSerializer, HenkilohakuLapsetSerializer,
                               PaosToimintaSerializer, PaosToimijatSerializer, PaosToimipaikatSerializer,
                               PaosOikeusSerializer, LapsiKoosteSerializer)
from varda.tasks import update_oph_staff_to_vakajarjestaja_groups
from webapps.api_throttles import (BurstRateThrottle, BurstRateThrottleStrict, SustainedModifyRateThrottle,
                                   SustainedRateThrottleStrict)

# Get an instance of a logger
logger = logging.getLogger(__name__)

THROTTLING_MODIFY_HTTP_METHODS = ['post', 'put', 'patch', 'delete']


class PutModelMixin(object):
    """
    Update a model instance.
    """
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()  # checks permissions
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def perform_update(self, serializer):
        serializer.save()


"""
ADMIN-specific viewsets below
"""


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser, )


class GroupViewSet(viewsets.ModelViewSet):
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


class UpdateHenkilotChangedSince(GenericViewSet, CreateModelMixin):
    """
    create:
        Päivitä henkilöt joiden tiedot muuttuneet Oppijanumerorekisterissä ajanhetken X jälkeen.
    """
    queryset = Henkilo.objects.none()
    serializer_class = UpdateHenkilotChangedSinceSerializer
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
        update_modified_henkilot_since_datetime(serializer.validated_data["date_and_time"])
        return {"result": "Henkilot updated."}


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


class HaeYksiloimattomatHenkilotViewSet(viewsets.ModelViewSet):
    """
    list:
        Nouda yksilöimättömat henkilot.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = filters.HenkiloFilter
    queryset = Henkilo.objects.none()
    serializer_class = HenkiloOppijanumeroSerializer
    permission_classes = (permissions.IsAdminUser, )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(Henkilo.objects.filter(vtj_yksiloity=False, vtj_yksilointi_yritetty=True)).order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


"""
Huoltaja-info currently available only for ADMIN-user.
"""


class HuoltajaViewSet(viewsets.ModelViewSet):
    """
    list:
        Listaa kaikki huoltajat.

    retrieve:
        Hae yksittäinen huoltaja.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = filters.HuoltajaFilter
    queryset = Huoltaja.objects.none()
    serializer_class = HuoltajaSerializer
    permission_classes = (permissions.IsAdminUser, )
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            save_audit_log(user, self.request.get_full_path())
            return Huoltaja.objects.all().order_by('id')
        else:
            return Huoltaja.objects.none()


class NestedHuoltajaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki huoltajat.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = filters.HuoltajaFilter
    queryset = Huoltaja.objects.none()
    serializer_class = HuoltajaSerializer
    permission_classes = (permissions.IsAdminUser, )

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        # Explicit check that given primary key is integer
        # TODO: This should be handled by schema validation. Compare to e.g. /lapset/{id} : A unique integer value identifying this lapsi.
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404("Not found.")

        # checking if lapsi exists and user has permissions
        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        queryset = self.filter_queryset(Huoltaja.objects.filter(huoltajuussuhteet__lapsi__id=kwargs['lapsi_pk'])).order_by('id')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class HuoltajuussuhdeViewSet(viewsets.ModelViewSet):
    """
    list:
        Listaa huoltajuussuhteet.

    retrieve:
        Hae yksittainen huoltajuussuhde.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = None
    queryset = Huoltajuussuhde.objects.none()
    serializer_class = HuoltajuussuhdeSerializer
    permission_classes = (permissions.IsAdminUser, )
    http_method_names = ['get', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            save_audit_log(user, self.request.get_full_path())
            return Huoltajuussuhde.objects.all().order_by('id')
        else:
            return Huoltajuussuhde.objects.none()


class NestedLapsiViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn huoltajan kaikki lapset.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = filters.LapsiFilter
    queryset = Lapsi.objects.none()
    serializer_class = LapsiSerializer
    permission_classes = (permissions.IsAdminUser, )

    def get_huoltaja(self, request, huoltaja_pk=None):
        huoltaja = get_object_or_404(Huoltaja.objects.all(), pk=huoltaja_pk)
        user = request.user
        if user.has_perm("view_huoltaja", huoltaja):
            return huoltaja
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        if not kwargs['huoltaja_pk'].isdigit():
            raise Http404("Not found.")

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


class ActiveUserViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda käyttäjän tiedot.
    """
    queryset = User.objects.none()
    serializer_class = ActiveUserSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def list(self, request, *args, **kwargs):
        user = request.user
        queryset = User.objects.get(id=user.id)
        serializer = self.get_serializer(queryset, many=False)
        return Response(serializer.data)


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


class VakaJarjestajaViewSet(viewsets.ModelViewSet):
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
    filter_class = filters.VakaJarjestajaFilter
    queryset = VakaJarjestaja.objects.all().order_by('id')
    serializer_class = VakaJarjestajaSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(VakaJarjestajaViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_update(self, serializer):
        user = self.request.user
        original_object = self.get_object()
        if not user.has_perm('change_vakajarjestaja', original_object):
            raise PermissionDenied("User does not have permissions to change this object.")
        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete vakajarjestaja. There are objects referencing it that need to be deleted first."})


class ToimipaikkaViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, PutModelMixin, ListModelMixin):
    """
    list:
        Nouda kaikki toimipaikat.

    create:
        Luo yksi uusi toimipaikka.

    retrieve:
        Nouda yksittäinen toimipaikka.

    update:
        Päivitä yhden toimipaikan kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.all().order_by('id')
    serializer_class = ToimipaikkaSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(ToimipaikkaViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        vakajarjestaja_id = validated_data["vakajarjestaja"].id

        related_object_validations.check_if_user_has_add_toimipaikka_permissions_under_vakajarjestaja(vakajarjestaja_id, user)
        validators.validate_toimipaikan_nimi(validated_data["nimi"])

        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})

        if related_object_validations.toimipaikka_is_valid_to_organisaatiopalvelu(toimintamuoto_koodi=validated_data["toimintamuoto_koodi"], nimi=validated_data['nimi']):
            check_if_toimipaikka_exists_in_organisaatiopalvelu(vakajarjestaja_id, validated_data["nimi"])

            """
            Toimipaikka was not found in Organisaatiopalvelu. We can POST it there.
            """
            try:
                with transaction.atomic():
                    # Save first internally so we can catch possible IntegrityError before POSTing to Org.palvelu.
                    serializer.save(changed_by=user)

                    result = create_toimipaikka_in_organisaatiopalvelu(validated_data)
                    if result["toimipaikka_created"]:
                        toimipaikka_organisaatio_oid = result["organisaatio_oid"]
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
                    assign_object_level_permissions(toimipaikka_organisaatio_oid, Toimipaikka, saved_object)
            except IntegrityError as e:
                logger.error('Could not create a toimipaikka in Org.Palvelu. Data: {}. Error: {}.'
                             .format(validated_data, e.__cause__))
                raise ValidationError({"toimipaikka": ["Could not create toimipaikka in Organisaatiopalvelu."]})

        else:
            try:
                with transaction.atomic():
                    saved_object = serializer.save(changed_by=user)
                    cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.vakajarjestaja.id))
                    delete_cache_keys_related_model('vakajarjestaja', saved_object.vakajarjestaja.id)

                    """
                    Perhepaivahoitaja-toimipaikka does not have organisaatio_oid. Let's give permissions on vakajarjestaja-level.
                    """
                    vakajarjestaja_obj = validated_data["vakajarjestaja"]
                    vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid
                    assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Toimipaikka, saved_object)
            except IntegrityError:
                raise ValidationError({"toimipaikka": ["Could not create toimipaikka in Varda."]})

    def perform_update(self, serializer):
        """
        We have explicitly disallowed PATCH-requests to this view. Only PUT allowed.
        """
        user = self.request.user
        url = self.request.path
        validated_data = serializer.validated_data
        toimipaikka_id = url.split("/")[-2]
        toimipaikka_obj = Toimipaikka.objects.get(id=toimipaikka_id)

        if not user.has_perm('change_toimipaikka', toimipaikka_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if validated_data['nimi'] != toimipaikka_obj.nimi:
            raise ValidationError({"nimi": ["It is not allowed to change the name of a toimipaikka."]})
        if Lahdejarjestelma[toimipaikka_obj.lahdejarjestelma] is not Lahdejarjestelma.VARDA:
            raise ValidationError({"lahdejarjestelma": ["This toimipaikka should be modified in organisaatio-service."]})
        if validated_data['vakajarjestaja'] != toimipaikka_obj.vakajarjestaja:
            raise ValidationError({"vakajarjestaja": ["It is not allowed to change the vakajarjestaja where toimipaikka belongs to."]})
        if validated_data['toimintamuoto_koodi'] != toimipaikka_obj.toimintamuoto_koodi:
            raise ValidationError({"toiminatamuoto_koodi": ["It is not allowed to change the toimintamuoto_koodi of a toimipaikka."]})
        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('vakajarjestaja', saved_object.vakajarjestaja.id)
        cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.vakajarjestaja.id))


class ToiminnallinenPainotusViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, PutModelMixin, ListModelMixin, DestroyModelMixin):
    """
    list:
        Nouda kaikki toiminnalliset painotukset.

    create:
        Luo yksi uusi toiminnallinen painotus.

    delete:
        Poista yksi toiminnallinen painotus.

    retrieve:
        Nouda yksittäinen toiminnallinen painotus.

    update:
        Päivitä yhden toiminnallisen painotuksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.ToiminnallinenPainotusFilter
    queryset = ToiminnallinenPainotus.objects.all().order_by('id')
    serializer_class = ToiminnallinenPainotusSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(ToiminnallinenPainotusViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data["toimipaikka"]
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user)

        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})

        related_object_validations.check_overlapping_koodi(validated_data, ToiminnallinenPainotus)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, ToiminnallinenPainotus, saved_object)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, ToiminnallinenPainotus, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        url = self.request.path
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data["toimipaikka"]
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        toiminnallinenpainotus_id = url.split("/")[-2]
        toiminnallinenpainotus_obj = ToiminnallinenPainotus.objects.get(id=toiminnallinenpainotus_id)

        related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        if not user.has_perm('change_toiminnallinenpainotus', toiminnallinenpainotus_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if "alkamis_pvm" in validated_data or "paattymis_pvm" in validated_data:
            alkamis_pvm = validated_data["alkamis_pvm"] if "alkamis_pvm" in validated_data else toiminnallinenpainotus_obj.alkamis_pvm
            paattymis_pvm = validated_data["paattymis_pvm"] if "paattymis_pvm" in validated_data else toiminnallinenpainotus_obj.paattymis_pvm
            if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})
        related_object_validations.check_overlapping_koodi(validated_data, ToiminnallinenPainotus, toiminnallinenpainotus_id)

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if not user.has_perm('delete_toiminnallinenpainotus', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
        cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))
        instance.delete()


class KieliPainotusViewSet(GenericViewSet, CreateModelMixin, RetrieveModelMixin, PutModelMixin, ListModelMixin, DestroyModelMixin):
    """
    list:
        Nouda kaikki kielipainotukset.

    create:
        Luo yksi uusi kielipainotus.

    delete:
        Poista yksi kielipainotus.

    retrieve:
        Nouda yksittäinen kielipainotus.

    update:
        Päivitä yhden kielipainotuksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.KieliPainotusFilter
    queryset = KieliPainotus.objects.all().order_by('id')
    serializer_class = KieliPainotusSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(KieliPainotusViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data["toimipaikka"]
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user)

        if "paattymis_pvm" in validated_data:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})
        related_object_validations.check_overlapping_koodi(validated_data, KieliPainotus)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, KieliPainotus, saved_object)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, KieliPainotus, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        url = self.request.path
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data["toimipaikka"]
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        kielipainotus_id = url.split("/")[-2]
        kielipainotus_obj = KieliPainotus.objects.get(id=kielipainotus_id)

        related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        if not user.has_perm('change_kielipainotus', kielipainotus_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if "alkamis_pvm" in validated_data or "paattymis_pvm" in validated_data:
            alkamis_pvm = validated_data["alkamis_pvm"] if "alkamis_pvm" in validated_data else kielipainotus_obj.alkamis_pvm
            paattymis_pvm = validated_data["paattymis_pvm"] if "paattymis_pvm" in validated_data else kielipainotus_obj.paattymis_pvm
            if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})
        related_object_validations.check_overlapping_koodi(validated_data, KieliPainotus, kielipainotus_id)

        saved_object = serializer.save(changed_by=user)
        delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()
        if not user.has_perm('delete_kielipainotus', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
        cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))
        instance.delete()


class HaeHenkiloViewSet(GenericViewSet, CreateModelMixin):
    """
    create:
        Nouda yksittäinen henkilö joko oppijanumerolla (oid) tai henkilotunnuksella.
    """
    queryset = Henkilo.objects.none()
    serializer_class = HaeHenkiloSerializer
    throttle_classes = (BurstRateThrottleStrict, SustainedRateThrottleStrict)  # We need more strict throttling on henkilo-haku, due to security reasons.
    permission_classes = (CustomObjectPermissions,)

    def get_henkilo(self, query_param, query_param_value):
        try:
            henkilo = Henkilo.objects.get(**{query_param: query_param_value})
        except Henkilo.DoesNotExist:
            raise NotFound(detail="Henkilo was not found.", code=404)
        except Henkilo.MultipleObjectsReturned:  # This should never be possible
            logger.error("Multiple of henkilot was found with " + query_param + ": " + query_param_value)
            raise CustomServerErrorException

        user = self.request.user
        if user.has_perm('view_henkilo', henkilo):
            return henkilo
        else:
            """
            For security reasons give HTTP 404 Not found, instead of 403 Permission denied.
            """
            raise NotFound(detail="Henkilo was not found.", code=404)

    def get_successful_response(self, henkilo):
        serializer = HenkiloSerializer(henkilo, context={'request': self.request})
        headers = self.get_success_headers(serializer.data)
        save_audit_log(self.request.user, self.request.path + "id=" + str(serializer.data["id"]))
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    def create(self, request, *args, **kwargs):  # Function name (create) is misleading! Here we get the henkilo based on henkilotunnus or henkilo_oid.
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "henkilotunnus" in serializer.validated_data:
            henkilotunnus = serializer.validated_data["henkilotunnus"]
            validators.validate_henkilotunnus(henkilotunnus)
            with transaction.atomic():
                henkilo = self.get_henkilo("henkilotunnus_unique_hash", hash_string(henkilotunnus))
                if user.has_perm('varda.view_henkilo', henkilo):  # Explicit permission checking - Very important!
                    return self.get_successful_response(henkilo)
                else:
                    raise NotFound(detail="Henkilo was not found.", code=404)
        else:  # "henkilo_oid" in serializer.validated_data
            henkilo_oid = serializer.validated_data["henkilo_oid"]
            validators.validate_henkilo_oid(henkilo_oid)
            with transaction.atomic():
                henkilo = self.get_henkilo("henkilo_oid", henkilo_oid)
                if user.has_perm('varda.view_henkilo', henkilo):
                    return self.get_successful_response(henkilo)
                else:
                    raise NotFound(detail="Henkilo was not found.", code=404)


class HenkiloViewSet(GenericViewSet, RetrieveModelMixin, CreateModelMixin):
    """
    retrieve:
        Nouda yksittäinen henkilö.

    create:
        Luo yksi uusi henkilö.
    """
    filter_backends = ()
    filter_class = None
    queryset = Henkilo.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(HenkiloViewSet, self).get_throttles()

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
        etunimet_list = etunimet.split(" ")
        etunimet_list_lowercase = [x.lower() for x in etunimet_list]
        henkilo_etunimet_list = henkilo.etunimet.split(" ")
        henkilo_etunimet_list_lowercase = [x.lower() for x in henkilo_etunimet_list]
        if set(etunimet_list_lowercase) & set(henkilo_etunimet_list_lowercase) or sukunimi.lower() == henkilo.sukunimi.lower():
            raise ConflictError(self.get_serializer(henkilo).data, status_code=status.HTTP_200_OK)
        else:
            raise ValidationError({"detail": "Person data does not match with the entered data"})

    def perform_create(self, serializer):
        """
        We need either henkilotunnus or henkilo_oid (in case of "hetuton").
        """
        validated_data = serializer.validated_data
        etunimet = validated_data["etunimet"]
        kutsumanimi = validated_data["kutsumanimi"]
        sukunimi = validated_data["sukunimi"]
        validators.validate_kutsumanimi(etunimet, kutsumanimi)

        henkilotunnus = validated_data.get("henkilotunnus", None)
        henkilo_oid = validated_data.get("henkilo_oid", None)
        if henkilotunnus:
            validators.validate_henkilotunnus(henkilotunnus)

            """
            We are ready to create a new henkilo, let's first create a unique hash so that we are sure every
            henkilotunnus exists in the DB only once, and definately not more often.
            Return HTTP 200 if henkilo already exists in DB.
            After that, let's encrypt henkilotunnus due to security reasons.
            """
            henkilotunnus_unique_hash = hash_string(henkilotunnus)
            henkilotunnus_encrypted = encrypt_henkilotunnus(henkilotunnus)
            self.validate_henkilo_uniqueness_henkilotunnus(henkilotunnus_unique_hash, etunimet, sukunimi)

            # It is possible we get different hetu than user provided
            henkilo_result = get_henkilo_by_henkilotunnus(henkilotunnus, etunimet, kutsumanimi, sukunimi)
            henkilo_data = henkilo_result["result"]
            if henkilo_data and henkilo_data.get("hetu", None):
                self.validate_henkilo_uniqueness_henkilotunnus(hash_string(henkilo_data["hetu"]), etunimet, sukunimi)
                henkilotunnus_unique_hash = hash_string(henkilo_data["hetu"])
                henkilotunnus_encrypted = encrypt_henkilotunnus(henkilo_data["hetu"])
                serializer.validated_data['henkilo_oid'] = henkilo_data.get('oidHenkilo', None)

            serializer.validated_data["henkilotunnus_unique_hash"] = henkilotunnus_unique_hash
            serializer.validated_data["henkilotunnus"] = henkilotunnus_encrypted

        else:  # "henkilo_oid" in validated_data
            validators.validate_henkilo_oid(henkilo_oid)
            self.validate_henkilo_uniqueness_oid(henkilo_oid, etunimet, sukunimi)  # checking we don't have this henkilo already (return HTTP 200 if so)
            henkilo_data = get_henkilo_data_by_oid(henkilo_oid)

        self.validate_henkilo_data(henkilo_data)

        # It is possible we get different oid than user provided
        if henkilo_data and henkilo_data.get("oidHenkilo", None):
            self.validate_henkilo_uniqueness_oid(henkilo_data["oidHenkilo"], etunimet, sukunimi)
            serializer.validated_data["henkilo_oid"] = henkilo_data["oidHenkilo"]

        """
        Save the new henkilo in DB
        """

        user = self.request.user
        group = Group.objects.get(name="vakajarjestaja_view_henkilo")
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            assign_perm('view_henkilo', group, saved_object)

            # Fetch henkilo-data from Oppijanumerorekisteri
            henkilo_id = serializer.data["id"]
            if henkilotunnus and not henkilo_data:
                henkilo_result = add_henkilo_to_oppijanumerorekisteri(etunimet, kutsumanimi, sukunimi, henkilotunnus=henkilotunnus)
                henkilo_data = henkilo_result["result"]
            if henkilo_oid and not henkilo_data:
                # If adding henkilo to varda using oid he should always be fround from ONR. Later adding henkilo with
                # just name data might be possible here when manual yksilointi is functional.
                raise ValidationError({"henkilo_oid": ["Not found"]})
            if henkilo_data is not None:
                save_henkilo_to_db(henkilo_id, henkilo_data)

    def validate_henkilo_data(self, henkilo_data):
        """
        Validate if henkilo is found in Oppijanumerorekisteri and he has been identified as unique.
        """
        if henkilo_data:
            is_hetullinen = henkilo_data.get("hetu", None)
            is_hetuton_yksiloity = (not henkilo_data.get("hetu", None) and
                                    henkilo_data.get("yksiloity", None))
            if not is_hetullinen and not is_hetuton_yksiloity:
                error_msg = "Unfortunately this henkilo cannot be added. Is the henkilo yksiloity?"
                raise ValidationError({"henkilo_oid": [error_msg, ]})


class TyontekijaViewSet(viewsets.ModelViewSet):
    """
    list:
        Nouda kaikki työntekijät.

    create:
        Luo yksi uusi työntekijä.

    delete:
        Poista yksi työntekijä.

    retrieve:
        Nouda yksittäinen työntekijä.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä työntekijästä.

    update:
        Päivitä yhden työntekijän kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.TyontekijaFilter
    queryset = Tyontekija.objects.all().order_by('id')
    serializer_class = TyontekijaSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(TyontekijaViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        related_object_validations.check_if_unique_within_vakajarjestaja(self.request.path, validated_data["henkilo"].id, user)

        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)
            assign_perm('view_tyontekija', user, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        if "henkilo" in validated_data:
            related_object_validations.check_if_user_has_access_to_henkilo(validated_data["henkilo"], user)
            related_object_validations.check_if_henkilo_is_changed(self.request.path, validated_data["henkilo"].id, user)
        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})

        serializer.save(changed_by=user)
        """
        No need to delete the related-henkilo cache. It is not possible to change the identity for henkilo.
        """

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_tyontekija', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete tyontekija. There are objects referencing it that need to be deleted first."})
        delete_cache_keys_related_model('henkilo', instance.henkilo.id)


class TaydennyskoulutusViewSet(viewsets.ModelViewSet):
    """
    list:
        Nouda kaikki täydennyskoulutukset.

    create:
        Luo yksi uusi täydennyskoulutus.

    delete:
        Poista yksi täydennyskoulutus.

    retrieve:
        Nouda yksittäinen täydennyskoulutus.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä täydennyskoulutuksesta.

    update:
        Päivitä yhden täydennyskoulutuksen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.TaydennyskoulutusFilter
    queryset = Taydennyskoulutus.objects.all().order_by('id')
    serializer_class = TaydennyskoulutusSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(TaydennyskoulutusViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        # validated_data = serializer.validated_data
        # related_object_validations.check_if_tyontekija_owned_by_user(validated_data["tyontekija"], user)
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            """
            TODO: Cache-invalidation is not done yet.
            Look example from already created functions.
            Jira: CSCVARDA-1088
            """
            assign_perm('view_taydennyskoulutus', user, saved_object)
        # group = Group.objects.get(name="group_view_taydennyskoulutukset")
        # assign_perm('view_taydennyskoulutus', group, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        # validated_data = serializer.validated_data
        # if "tyontekija" in validated_data:
        #     related_object_validations.check_if_tyontekija_owned_by_user(validated_data["tyontekija"], user)
        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_taydennyskoulutus', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        instance.delete()


class OhjaajasuhdeViewSet(viewsets.ModelViewSet):
    """
    list:
        Nouda kaikki ohjaajasuhteet.

    create:
        Luo yksi uusi ohjaajasuhde.

    delete:
        Poista yksi ohjaajasuhde.

    retrieve:
        Nouda yksittäinen ohjaajasuhde.

    partial_update:
        Päivitä yksi tai useampi kenttä yhdestä ohjaajasuhde-tietueesta.

    update:
        Päivitä yhden ohjaajasuhteen kaikki kentät.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.OhjaajasuhdeFilter
    queryset = Ohjaajasuhde.objects.all().order_by('id')
    serializer_class = OhjaajasuhdeSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(OhjaajasuhdeViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        # related_object_validations.check_if_tyontekija_owned_by_user(validated_data["tyontekija"], user)
        # related_object_validations.check_if_toimipaikka_owned_by_user(validated_data["toimipaikka"].id, user)
        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            assign_perm('view_ohjaajasuhde', user, saved_object)
        # group = Group.objects.get(name="group_view_ohjaajasuhteet")
        # assign_perm('view_ohjaajasuhde', group, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        # if "tyontekija" in validated_data:
        #     related_object_validations.check_if_tyontekija_owned_by_user(validated_data["tyontekija"], user)
        # if "toimipaikka" in validated_data:
        #     related_object_validations.check_if_toimipaikka_owned_by_user(validated_data["toimipaikka"].id, user)
        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm']):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm"]})

        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_ohjaajasuhde', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        instance.delete()


class LapsiViewSet(viewsets.ModelViewSet):
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
    filter_class = filters.LapsiFilter
    queryset = Lapsi.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(LapsiViewSet, self).get_throttles()

    def get_serializer_class(self):
        request = self.request
        if request is not None and request.user.is_superuser:
            return LapsiSerializerAdmin
        return LapsiSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def return_lapsi_if_already_created(self, validated_data):
        user = self.request.user
        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            q_obj = Q(henkilo=validated_data['henkilo'],
                      oma_organisaatio=validated_data['oma_organisaatio'],
                      paos_organisaatio=validated_data['paos_organisaatio'])
        else:
            kayttajatyyppi = (Z3_AdditionalCasUserFields
                              .objects
                              .filter(user=user)
                              .values_list('kayttajatyyppi', flat=True))
            if kayttajatyyppi and kayttajatyyppi[0] == 'PALVELU':
                q_obj = Q(henkilo=validated_data['henkilo'],
                          paos_kytkin=False,
                          changed_by=user)
            else:
                model_name = 'lapsi'
                content_type = ContentType.objects.get(model=model_name)
                lapsi_ids = get_object_ids_user_has_permissions(user, model_name, content_type)
                q_obj = Q(henkilo=validated_data['henkilo'],
                          paos_kytkin=False,
                          id__in=lapsi_ids)

        lapsi_obj = Lapsi.objects.filter(q_obj).first()
        if lapsi_obj:
            raise ConflictError(self.get_serializer(lapsi_obj).data, status_code=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            """
            This is a "PAOS-lapsi"
            - oma_organisaatio must have permission to add this lapsi to PAOS-toimipaikka (under paos-organisaatio)
            - user must have tallentaja-permission in oma_organisaatio (vakajarjestaja-level) or palvelukayttaja.
            """
            oma_organisaatio = validated_data['oma_organisaatio']
            paos_organisaatio = validated_data['paos_organisaatio']
            paos_organisaatio_oid = paos_organisaatio.organisaatio_oid
            paos_toimipaikka = None

            check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(oma_organisaatio, paos_organisaatio)
            throw_if_not_tallentaja_permissions(paos_organisaatio_oid, paos_toimipaikka, user, oma_organisaatio)

        self.return_lapsi_if_already_created(validated_data)

        try:
            with transaction.atomic():
                saved_object = serializer.save(changed_by=user)
                delete_cache_keys_related_model('henkilo', saved_object.henkilo.id)
                assign_perm('view_lapsi', user, saved_object)
                assign_perm('change_lapsi', user, saved_object)
                assign_perm('delete_lapsi', user, saved_object)
        except IntegrityError as e:
            if 'oma_organisaatio_is_not_paos_organisaatio' in str(e):
                raise ValidationError({"detail": "oma_organisaatio cannot be same as paos_organisaatio."})
            else:
                logger.error('IntegrityError at LapsiViewSet: {}'.format(e))
                raise CustomServerErrorException

    def perform_update(self, serializer):
        user = self.request.user
        url = self.request.path
        validated_data = serializer.validated_data
        lapsi_id = url.split("/")[-2]
        lapsi_obj = Lapsi.objects.get(id=lapsi_id)

        if not user.has_perm('change_lapsi', lapsi_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if "henkilo" in validated_data:
            related_object_validations.check_if_henkilo_is_changed(url, validated_data["henkilo"].id, user)

        msg = {}
        if 'oma_organisaatio' in validated_data and validated_data['oma_organisaatio'] != lapsi_obj.oma_organisaatio:
            msg = ({"oma_organisaatio": ["Changing of oma_organisaatio is not allowed"]})
        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] != lapsi_obj.paos_organisaatio:
            msg.update(({'paos_organisaatio': ['Changing of paos_organisaatio is not allowed']}))
        if msg:
            raise ValidationError(msg, code='invalid')

        serializer.save(changed_by=user)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_lapsi', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        if Huoltajuussuhde.objects.filter(lapsi__id=instance.id).filter(maksutiedot__isnull=False).exists():
            raise ValidationError({"detail": "Cannot delete lapsi. There are maksutieto/maksutietoja referencing it that need to be deleted first."})

        instance_id = instance.id

        with transaction.atomic():
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError({"detail": "Cannot delete lapsi. There are objects referencing it that need to be deleted first."})

            Huoltajuussuhde.objects.filter(lapsi__id=instance_id).delete()
            delete_cache_keys_related_model('henkilo', instance.henkilo.id)


class VarhaiskasvatuspaatosViewSet(viewsets.ModelViewSet):
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
    filter_class = filters.VarhaiskasvatuspaatosFilter
    queryset = Varhaiskasvatuspaatos.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(VarhaiskasvatuspaatosViewSet, self).get_throttles()

    def get_serializer_class(self):
        request = self.request
        if request.method == 'PUT':
            return VarhaiskasvatuspaatosPutSerializer
        elif request.method == 'PATCH':
            return VarhaiskasvatuspaatosPatchSerializer
        else:
            return VarhaiskasvatuspaatosSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data

        if not validators.validate_paivamaara1_before_paivamaara2(validated_data['hakemus_pvm'], validated_data['alkamis_pvm'], can_be_same=True):
            raise ValidationError({"hakemus_pvm": ["hakemus_pvm must be before alkamis_pvm (or same)."]})
        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)"]})
        if validated_data["vuorohoito_kytkin"]:
            validated_data["paivittainen_vaka_kytkin"] = None
            validated_data["kokopaivainen_vaka_kytkin"] = None
        timediff = validated_data["alkamis_pvm"] - validated_data["hakemus_pvm"]
        if timediff.days <= 14:
            validated_data["pikakasittely_kytkin"] = True

        related_object_validations.check_overlapping_varhaiskasvatus_object(validated_data, Varhaiskasvatuspaatos)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('lapsi', saved_object.lapsi.id)
            assign_perm('view_varhaiskasvatuspaatos', user, saved_object)
            assign_perm('change_varhaiskasvatuspaatos', user, saved_object)
            assign_perm('delete_varhaiskasvatuspaatos', user, saved_object)

    def perform_update(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        url = self.request.path
        varhaiskasvatuspaatos_id = url.split("/")[-2]
        varhaiskasvatuspaatos_obj = Varhaiskasvatuspaatos.objects.get(id=varhaiskasvatuspaatos_id)
        varhaiskasvatussuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos_id=varhaiskasvatuspaatos_id)

        if not user.has_perm('change_varhaiskasvatuspaatos', varhaiskasvatuspaatos_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        """
        Validations for alkamis_pvm and hakemus_pvm must be done in every PUT/PATCH.
        Therefore include the original value if not included in the PATCH.
        """
        if "alkamis_pvm" not in validated_data:
            validated_data['alkamis_pvm'] = varhaiskasvatuspaatos_obj.alkamis_pvm
        if "hakemus_pvm" not in validated_data:
            validated_data['hakemus_pvm'] = varhaiskasvatuspaatos_obj.hakemus_pvm

        if not validators.validate_paivamaara1_before_paivamaara2(validated_data['hakemus_pvm'], validated_data['alkamis_pvm'], can_be_same=True):
            raise ValidationError({"hakemus_pvm": ["hakemus_pvm must be before alkamis_pvm (or same)."]})

        for varhaiskasvatussuhde_obj in varhaiskasvatussuhteet:
            self.validate_paivamaarat_varhaiskasvatussuhteet(validated_data['alkamis_pvm'], varhaiskasvatussuhde_obj.alkamis_pvm, {"alkamis_pvm": ["varhaiskasvatussuhde.alkamis_pvm must be after varhaiskasvatuspaatos.alkamis_pvm"]})

        if "paattymis_pvm" in validated_data and validated_data["paattymis_pvm"] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)."]})
            for varhaiskasvatussuhde_obj in varhaiskasvatussuhteet:
                self.validate_paivamaarat_varhaiskasvatussuhteet(varhaiskasvatussuhde_obj.paattymis_pvm, validated_data['paattymis_pvm'], {"paattymis_pvm": ["varhaiskasvatuspaatos.paattymis_pvm must be after varhaiskasvatussuhde.paattymis_pvm"]})

        timediff = validated_data["alkamis_pvm"] - validated_data["hakemus_pvm"]
        if timediff.days <= 14:
            validated_data["pikakasittely_kytkin"] = True
        else:
            validated_data["pikakasittely_kytkin"] = False

        related_object_validations.check_overlapping_varhaiskasvatus_object(validated_data, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_id)
        saved_object = serializer.save(changed_by=user)
        """
        No need to delete the related-lapsi cache, since user cannot change the lapsi-relation.
        """
        self.delete_list_of_toimipaikan_lapset_cache(self.get_toimipaikka_ids(saved_object))
        self.delete_vakajarjestaja_yhteenveto_cache(saved_object)

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.has_perm('delete_varhaiskasvatuspaatos', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        lapsi_id = instance.lapsi.id
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError({"detail": "Cannot delete varhaiskasvatuspaatos. There are objects referencing it that need to be deleted first."})
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


class VarhaiskasvatussuhdeViewSet(viewsets.ModelViewSet):
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
    filter_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.all().order_by('id')
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(VarhaiskasvatussuhdeViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def validate_paivamaarat_varhaiskasvatussuhde_toimipaikka(self, validated_data, toimipaikka_paattymis_pvm):
        if toimipaikka_paattymis_pvm is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data["alkamis_pvm"], toimipaikka_paattymis_pvm):
                raise ValidationError({"non_field_errors": ["varhaiskasvatussuhde.alkamis_pvm cannot be same or after toimipaikka.paattymis_pvm."]})
            if("paattymis_pvm" in validated_data and
               validated_data["paattymis_pvm"] is not None and
               not validators.validate_paivamaara1_before_paivamaara2(validated_data["paattymis_pvm"], toimipaikka_paattymis_pvm, can_be_same=True)):
                raise ValidationError({"non_field_errors": ["varhaiskasvatussuhde.paattymis_pvm cannot be after toimipaikka.paattymis_pvm."]})

    def validate_lapsi_not_under_different_vakajarjestaja(self, lapsi_obj, new_vakajarjestaja_obj):
        """
        Make sure lapsi will not end up under two different vakajarjestajat. Without this validation a virkailija
        with permissions to two different vakajarjestajat could potentially add one and same lapsi to two
        different vakajarjestajat/toimipaikat.
        """
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi_obj)
        vakajarjestajat = VakaJarjestaja.objects.filter(toimipaikat__varhaiskasvatussuhteet__in=vakasuhteet).distinct()
        if vakajarjestajat.count() > 1:
            logger.error('Lapsi under multiple vakajarjestajat. Lapsi-id:  {}'.format(lapsi_obj.id))
        if vakajarjestajat and new_vakajarjestaja_obj not in vakajarjestajat:
            raise ValidationError({"non_field_errors": ["this lapsi is already under other vakajarjestaja. Please create a new one."]})

    def assign_paos_lapsi_permissions(self, lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                      vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid):
        """
        Permissions for "oma_organisaatio" (view & modify-permissions by default)
        """
        assign_object_level_permissions(lapsi_obj.oma_organisaatio.organisaatio_oid, Varhaiskasvatussuhde, varhaiskasvatussuhde_obj)
        assign_object_level_permissions(lapsi_obj.oma_organisaatio.organisaatio_oid, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_obj)
        assign_object_level_permissions(lapsi_obj.oma_organisaatio.organisaatio_oid, Lapsi, lapsi_obj)
        group_huoltajatieto_katselu_vaka = Group.objects.get(name='HUOLTAJATIETO_KATSELU_' + lapsi_obj.oma_organisaatio.organisaatio_oid)
        group_huoltajatieto_tallennus_vaka = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_' + lapsi_obj.oma_organisaatio.organisaatio_oid)
        assign_perm('view_lapsi', group_huoltajatieto_katselu_vaka, lapsi_obj)
        assign_perm('view_lapsi', group_huoltajatieto_tallennus_vaka, lapsi_obj)

        """
        Permissions for "paos_organisaatio" (view-permissions by default)
        """
        group_varda_katselija_paos_organization = Group.objects.get(name='VARDA-KATSELIJA_' + vakajarjestaja_organisaatio_oid)
        group_varda_paakayttaja_paos_organization = Group.objects.get(name='VARDA-PAAKAYTTAJA_' + vakajarjestaja_organisaatio_oid)
        group_varda_tallentaja_paos_organization = Group.objects.get(name='VARDA-TALLENTAJA_' + vakajarjestaja_organisaatio_oid)
        group_varda_palvelukayttaja_paos_organization = Group.objects.get(name='VARDA-PALVELUKAYTTAJA_' + vakajarjestaja_organisaatio_oid)
        paos_organization_groups = [group_varda_katselija_paos_organization,
                                    group_varda_paakayttaja_paos_organization,
                                    group_varda_tallentaja_paos_organization,
                                    group_varda_palvelukayttaja_paos_organization]

        for paos_organization_group in paos_organization_groups:
            assign_perm('view_varhaiskasvatussuhde', paos_organization_group, varhaiskasvatussuhde_obj)
            assign_perm('view_varhaiskasvatuspaatos', paos_organization_group, varhaiskasvatuspaatos_obj)
            assign_perm('view_lapsi', paos_organization_group, lapsi_obj)

        if toimipaikka_organisaatio_oid != '':
            group_varda_katselija_toimipaikka = Group.objects.get(name='VARDA-KATSELIJA_' + toimipaikka_organisaatio_oid)
            group_varda_tallentaja_toimipaikka = Group.objects.get(name='VARDA-TALLENTAJA_' + toimipaikka_organisaatio_oid)
            paos_toimipaikka_groups = [group_varda_katselija_toimipaikka, group_varda_tallentaja_toimipaikka]

            for paos_toimipaikka_group in paos_toimipaikka_groups:
                assign_perm('view_varhaiskasvatussuhde', paos_toimipaikka_group, varhaiskasvatussuhde_obj)
                assign_perm('view_varhaiskasvatuspaatos', paos_toimipaikka_group, varhaiskasvatuspaatos_obj)
                assign_perm('view_lapsi', paos_toimipaikka_group, lapsi_obj)

    def assign_non_paos_lapsi_permissions(self, lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                          vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid):
        """
        Add group-level permissions (vakajarjestaja & toimipaikka)
        """
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Varhaiskasvatussuhde, varhaiskasvatussuhde_obj)
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_obj)
        assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Lapsi, lapsi_obj)
        group_huoltajatieto_katselu_vaka = Group.objects.get(name='HUOLTAJATIETO_KATSELU_' + vakajarjestaja_organisaatio_oid)
        group_huoltajatieto_tallennus_vaka = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_' + vakajarjestaja_organisaatio_oid)
        assign_perm('view_lapsi', group_huoltajatieto_katselu_vaka, lapsi_obj)
        assign_perm('view_lapsi', group_huoltajatieto_tallennus_vaka, lapsi_obj)

        if toimipaikka_organisaatio_oid != '':
            """
            TODO: Add these to every case after dummy-toimipaikat are removed.
            """
            assign_object_level_permissions(toimipaikka_organisaatio_oid, Varhaiskasvatussuhde, varhaiskasvatussuhde_obj)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, Varhaiskasvatuspaatos, varhaiskasvatuspaatos_obj)
            assign_object_level_permissions(toimipaikka_organisaatio_oid, Lapsi, lapsi_obj)
            group_huoltajatieto_katselu_toimipaikka = Group.objects.get(name='HUOLTAJATIETO_KATSELU_' + toimipaikka_organisaatio_oid)
            group_huoltajatieto_tallennus_toimipaikka = Group.objects.get(name='HUOLTAJATIETO_TALLENNUS_' + toimipaikka_organisaatio_oid)
            assign_perm('view_lapsi', group_huoltajatieto_katselu_toimipaikka, lapsi_obj)
            assign_perm('view_lapsi', group_huoltajatieto_tallennus_toimipaikka, lapsi_obj)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data['toimipaikka']
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid
        varhaiskasvatuspaatos_obj = validated_data['varhaiskasvatuspaatos']
        lapsi_obj = validated_data['varhaiskasvatuspaatos'].lapsi

        self.validate_paivamaarat_varhaiskasvatussuhde_toimipaikka(validated_data, toimipaikka_obj.paattymis_pvm)
        if not validators.validate_paivamaara1_before_paivamaara2(varhaiskasvatuspaatos_obj.alkamis_pvm, validated_data['alkamis_pvm'], can_be_same=True):
            raise ValidationError({'alkamis_pvm': ['varhaiskasvatussuhde.alkamis_pvm must be after varhaiskasvatuspaatos.alkamis_pvm (or same)']})
        if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], varhaiskasvatuspaatos_obj.paattymis_pvm, can_be_same=True):
            raise ValidationError({'alkamis_pvm': ['varhaiskasvatussuhde.alkamis_pvm must be before varhaiskasvatuspaatos.paattymis_pvm (or same)']})

        if 'paattymis_pvm' in validated_data:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({'paattymis_pvm': ['paattymis_pvm must be after alkamis_pvm (or same)']})
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['paattymis_pvm'], varhaiskasvatuspaatos_obj.paattymis_pvm, can_be_same=True):
                raise ValidationError({'paattymis_pvm': ['varhaiskasvatuspaatos.paattymis_pvm must be after varhaiskasvatussuhde.paattymis_pvm (or same)']})
        related_object_validations.check_overlapping_varhaiskasvatus_object(validated_data, Varhaiskasvatussuhde)
        self.validate_lapsi_not_under_different_vakajarjestaja(lapsi_obj, vakajarjestaja_obj)

        paos_lapsi = lapsi_obj.paos_kytkin
        toimipaikka_added_to_org_palvelu = related_object_validations.toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka_obj)
        toimipaikka_organisaatio_oid = ''
        if not toimipaikka_added_to_org_palvelu:
            """
            TODO: Remove this when dummy-toimipaikat are removed.
            User needs tallentaja-permissions on vakajarjestaja-level.
            """
            if vakajarjestaja_organisaatio_oid == '':
                logger.error('Missing organisaatio_oid for vakajarjestaja: ' + str(vakajarjestaja_obj.id))
                raise ValidationError({'non_field_errors': ['Organisaatio_oid missing for vakajarjestaja.']})
            throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user, lapsi_obj.oma_organisaatio)

        else:
            toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
            related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
            throw_if_not_tallentaja_permissions(vakajarjestaja_organisaatio_oid, toimipaikka_obj, user, lapsi_obj.oma_organisaatio)

        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            delete_cache_keys_related_model('toimipaikka', saved_object.toimipaikka.id)
            delete_cache_keys_related_model('varhaiskasvatuspaatos', saved_object.varhaiskasvatuspaatos.id)
            delete_toimipaikan_lapset_cache(str(saved_object.toimipaikka.id))
            cache.delete('vakajarjestaja_yhteenveto_' + str(saved_object.toimipaikka.vakajarjestaja.id))

            varhaiskasvatussuhde_obj = saved_object
            varhaiskasvatuspaatos_obj = varhaiskasvatussuhde_obj.varhaiskasvatuspaatos

            if paos_lapsi:
                self.assign_paos_lapsi_permissions(lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                                   vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
                cache.delete('vakajarjestaja_yhteenveto_' + str(lapsi_obj.oma_organisaatio.id))

            else:  # Not PAOS-lapsi (i.e. normal case)
                self.assign_non_paos_lapsi_permissions(lapsi_obj, varhaiskasvatussuhde_obj, varhaiskasvatuspaatos_obj,
                                                       vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)

            """
            Finally remove user-level permissions from the vakasuhde/vakapaatos/lapsi objects.
            They are not needed after group-level permissions are added.
            """
            remove_perm('view_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)
            remove_perm('change_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)
            remove_perm('delete_varhaiskasvatuspaatos', user, varhaiskasvatuspaatos_obj)
            remove_perm('view_lapsi', user, lapsi_obj)
            remove_perm('change_lapsi', user, lapsi_obj)
            remove_perm('delete_lapsi', user, lapsi_obj)

    def perform_update(self, serializer):
        user = self.request.user
        url = self.request.path
        validated_data = serializer.validated_data
        toimipaikka_obj = validated_data["toimipaikka"]
        toimipaikka_organisaatio_oid = toimipaikka_obj.organisaatio_oid
        vakajarjestaja_obj = toimipaikka_obj.vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja_obj.organisaatio_oid

        self.validate_paivamaarat_varhaiskasvatussuhde_toimipaikka(validated_data, toimipaikka_obj.paattymis_pvm)

        varhaiskasvatussuhde_id = url.split("/")[-2]
        varhaiskasvatussuhde_obj = Varhaiskasvatussuhde.objects.get(id=varhaiskasvatussuhde_id)
        varhaiskasvatuspaatos_obj = Varhaiskasvatuspaatos.objects.get(id=varhaiskasvatussuhde_obj.varhaiskasvatuspaatos_id)

        related_object_validations.check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka_obj, vakajarjestaja_organisaatio_oid, toimipaikka_organisaatio_oid)
        if not user.has_perm('change_varhaiskasvatussuhde', varhaiskasvatussuhde_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if not validators.validate_paivamaara1_before_paivamaara2(varhaiskasvatuspaatos_obj.alkamis_pvm, validated_data['alkamis_pvm'], can_be_same=True):
            raise ValidationError({"alkamis_pvm": ["varhaiskasvatussuhde.alkamis_pvm must be after varhaiskasvatuspaatos.alkamis_pvm (or same)"]})
        if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], varhaiskasvatuspaatos_obj.paattymis_pvm, can_be_same=True):
            raise ValidationError({"alkamis_pvm": ["varhaiskasvatussuhde.alkamis_pvm must be before varhaiskasvatuspaatos.paattymis_pvm (or same)"]})

        if "varhaiskasvatuspaatos" in validated_data and varhaiskasvatussuhde_obj.varhaiskasvatuspaatos != validated_data["varhaiskasvatuspaatos"]:
            raise ValidationError({"varhaiskasvatuspaatos": ["Changing of varhaiskasvatuspaatos is not allowed"]})
        if "toimipaikka" in validated_data and varhaiskasvatussuhde_obj.toimipaikka != validated_data["toimipaikka"]:
            raise ValidationError({"toimipaikka": ["Changing of toimipaikka is not allowed"]})
        if "paattymis_pvm" in validated_data:
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], validated_data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)"]})
            if not validators.validate_paivamaara1_before_paivamaara2(validated_data['paattymis_pvm'], varhaiskasvatuspaatos_obj.paattymis_pvm, can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["varhaiskasvatuspaatos.paattymis_pvm must be after varhaiskasvatussuhde.paattymis_pvm"]})
        related_object_validations.check_overlapping_varhaiskasvatus_object(validated_data, Varhaiskasvatussuhde, varhaiskasvatussuhde_id)
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
        user = self.request.user
        if not user.has_perm('delete_varhaiskasvatussuhde', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        delete_toimipaikan_lapset_cache(str(instance.toimipaikka.id))
        cache.delete('vakajarjestaja_yhteenveto_' + str(instance.toimipaikka.vakajarjestaja.id))
        delete_cache_keys_related_model('toimipaikka', instance.toimipaikka.id)
        delete_cache_keys_related_model('varhaiskasvatuspaatos', instance.varhaiskasvatuspaatos.id)
        lapsi_obj = instance.varhaiskasvatuspaatos.lapsi
        if lapsi_obj.paos_kytkin:
            cache.delete('vakajarjestaja_yhteenveto_' + str(lapsi_obj.oma_organisaatio.id))
        instance.delete()


class MaksutietoViewSet(viewsets.ModelViewSet):
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
    filter_class = filters.MaksutietoFilter
    queryset = Maksutieto.objects.all().order_by('id')
    serializer_class = None
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(MaksutietoViewSet, self).get_throttles()

    def get_serializer_class(self):
        request = self.request
        if request.method == 'POST':
            return MaksutietoPostSerializer
        elif request.method == 'PUT' or request.method == 'PATCH':
            return MaksutietoUpdateSerializer
        else:
            return MaksutietoGetSerializer

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        save_audit_log(request.user, request.path)
        return super(MaksutietoViewSet, self).retrieve(request, *args, **kwargs)

    def validate_user_data(self, data):
        # data validations
        paattymis_pvm_filter = Q()

        if not data['yksityinen_jarjestaja']:
            if "perheen_koko" not in data:
                raise ValidationError({"perheen_koko": ["perheen_koko field is required"]})

        alkamis_pvm_filter = (Q(huoltajuussuhteet__lapsi=data['lapsi']) &
                              (Q(paattymis_pvm=None) | Q(paattymis_pvm__gte=data['alkamis_pvm']))
                              )

        if "paattymis_pvm" in data and data['paattymis_pvm'] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(data['alkamis_pvm'], data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)"]})
            paattymis_pvm_filter = (Q(alkamis_pvm__lte=data['paattymis_pvm']))

        if not data["huoltajat"] or len(data["huoltajat"]) == 0:
            raise ValidationError({"huoltajat": ["huoltajat field is required"]})

        vtj_huoltajuudet = self.fetch_and_match_huoltajuudet(data)
        if vtj_huoltajuudet.count() == 0:
            raise ValidationError({"huoltajat": ["no matching huoltaja found"]})

        samanaikaiset_maksutiedot = Maksutieto.objects.filter(Q(alkamis_pvm_filter & paattymis_pvm_filter)).distinct().count()
        if samanaikaiset_maksutiedot >= 2:
            raise ValidationError({"maksutieto": ["lapsi already has 2 active maksutieto during that time period"]})

        return vtj_huoltajuudet

    def fetch_and_match_huoltajuudet(self, data):
        queryset_filter = Q()

        # get VTJ_huoltajat from database
        vtj_huoltajuudet = (Huoltajuussuhde.objects
                            .filter(lapsi=data["lapsi"])
                            .filter(voimassa_kytkin=True)
                            )

        # validate VTJ_huoltaja to be one of the persons in the data

        for user_huoltaja in data["huoltajat"]:
            etunimi_q = Q()
            etunimet_list = user_huoltaja["etunimet"].split()
            for etunimi in etunimet_list:
                etunimi_q = Q(huoltaja__henkilo__etunimet__search=etunimi) | etunimi_q
            if "henkilo_oid" in user_huoltaja:
                henkilo_filter = ((etunimi_q |
                                  Q(huoltaja__henkilo__sukunimi__iexact=user_huoltaja["sukunimi"])) &
                                  Q(huoltaja__henkilo__henkilo_oid=user_huoltaja["henkilo_oid"])
                                  )
            else:
                validators.validate_henkilotunnus(user_huoltaja["henkilotunnus"])
                henkilotunnus = hash_string(user_huoltaja["henkilotunnus"])
                henkilo_filter = ((etunimi_q |
                                  Q(huoltaja__henkilo__sukunimi__iexact=user_huoltaja["sukunimi"])) &
                                  Q(huoltaja__henkilo__henkilotunnus_unique_hash=henkilotunnus)
                                  )
            queryset_filter = (queryset_filter | henkilo_filter)

        return vtj_huoltajuudet.filter(queryset_filter)

    def get_maksutieto(self, saved_data, lapsi, huoltajat):
        return {
            "url": self.request.build_absolute_uri(reverse('maksutieto-detail', args=[saved_data.id])),
            "id": saved_data.id,
            "huoltajat": huoltajat,
            "lapsi": self.request.build_absolute_uri(reverse('lapsi-detail', args=[lapsi.id])),
            "maksun_peruste_koodi": saved_data.maksun_peruste_koodi,
            "palveluseteli_arvo": saved_data.palveluseteli_arvo,
            "asiakasmaksu": saved_data.asiakasmaksu,
            "perheen_koko": saved_data.perheen_koko,
            "alkamis_pvm": saved_data.alkamis_pvm,
            "paattymis_pvm": saved_data.paattymis_pvm
        }

    def process_post_maksutieto_response(self, huoltajat, inserted_huoltaja_data):
        for huoltaja in huoltajat:
            """
            Loop for each found huoltaja in our DB, and compare if its 'henkilotunnus' is the same as inserted one.
            If a match is found -> return henkilotunnus.
            If a match is not found -> remove henkilotunnus-attribute from response.
            """
            henkilotunnus_found = False
            henkilotunnus = decrypt_henkilotunnus(huoltaja["henkilotunnus"])
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

    def create(self, request):
        user = self.request.user
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        lapsi = serializer.validated_data['lapsi']
        serializer.validated_data['yksityinen_jarjestaja'] = False

        """
        Check if varhaiskasvatuspaatos is private or public for validations and end-users.
        """
        vakapaatos = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).order_by("-alkamis_pvm").first()
        if not vakapaatos:
            raise ValidationError({"Maksutieto": ["Lapsi has no Varhaiskasvatuspaatos. Add Varhaiskasvatuspaatos before adding maksutieto."]})

        if vakapaatos.jarjestamismuoto_koodi.lower() == "jm04":
            serializer.validated_data['yksityinen_jarjestaja'] = True

        """
        In order to be able to add maksutieto to lapsi, we need to know the organizations
        (toimipaikat + vakajarjestaja) where the lapsi is at daycare.
        We need this info for permissions.
        """
        toimipaikka_qs = Toimipaikka.objects.filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi__id=lapsi.id)
        if not toimipaikka_qs:
            raise ValidationError({"Maksutieto": ["Lapsi has no Varhaiskasvatussuhde. Add Varhaiskasvatussuhde before adding maksutieto."]})
        vakajarjestaja = toimipaikka_qs[0].vakajarjestaja
        vakajarjestaja_organisaatio_oid = vakajarjestaja.organisaatio_oid

        if not user_has_huoltajatieto_tallennus_permissions_to_correct_organization(user, vakajarjestaja_organisaatio_oid, toimipaikka_qs):
            raise PermissionDenied("User does not have permissions to add maksutieto to this lapsi.")

        data = dict(serializer.validated_data)
        vtj_huoltajuudet = self.validate_user_data(data)

        if data['maksun_peruste_koodi'].lower() == "mp01":
            serializer.validated_data['asiakasmaksu'] = 0
            serializer.validated_data['palveluseteli_arvo'] = 0

        # remove fields not directly in database
        serializer.validated_data.pop('huoltajat')
        serializer.validated_data.pop('lapsi')

        # save maksutieto
        with transaction.atomic():
            saved_object = serializer.save(changed_by=user)
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))
            """
            Add group-level permissions (vakajarjestaja & toimipaikka)
            """
            assign_object_level_permissions(vakajarjestaja_organisaatio_oid, Maksutieto, saved_object)
            for toimipaikka in toimipaikka_qs:
                if related_object_validations.toimipaikka_is_valid_to_organisaatiopalvelu(toimipaikka_obj=toimipaikka):
                    assign_object_level_permissions(toimipaikka.organisaatio_oid, Maksutieto, saved_object)

        # make changes to huoltajuussuhteet
        [huoltajuussuhde.maksutiedot.add(saved_object.id) for huoltajuussuhde in vtj_huoltajuudet]

        henkilo_attributes = ['henkilotunnus', 'henkilo_oid', 'etunimet', 'sukunimi']
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=vtj_huoltajuudet).values(*henkilo_attributes)
        self.process_post_maksutieto_response(huoltajat, data["huoltajat"])

        # return saved object and related information
        return_maksutieto_to_user = self.get_maksutieto(saved_object, lapsi, huoltajat)

        headers = self.get_success_headers(saved_object)
        return Response(return_maksutieto_to_user, status=status.HTTP_201_CREATED, headers=headers)

    @transaction.atomic
    def perform_update(self, serializer):
        user = self.request.user
        maksutieto_obj = self.get_object()
        data = serializer.validated_data
        paattymis_pvm_q = Q()

        if not user.has_perm('change_maksutieto', maksutieto_obj):
            raise PermissionDenied("User does not have permissions to change this object.")

        if "paattymis_pvm" in data and data['paattymis_pvm'] is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(maksutieto_obj.alkamis_pvm, data['paattymis_pvm'], can_be_same=True):
                raise ValidationError({"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)"]})
            paattymis_pvm_q = Q(alkamis_pvm__lte=data['paattymis_pvm'])

        lapsi_objects = Lapsi.objects.filter(huoltajuussuhteet__maksutiedot__id=maksutieto_obj.id).distinct()
        if len(lapsi_objects) != 1:
            logger.error("Error getting lapsi for maksutieto " + str(maksutieto_obj.id))
            raise CustomServerErrorException
        lapsi_object = lapsi_objects[0]

        samanaikaiset_maksutiedot = Maksutieto.objects.filter(
            Q(huoltajuussuhteet__lapsi=lapsi_object) &
            ~Q(id=maksutieto_obj.id) &
            paattymis_pvm_q &
            (Q(paattymis_pvm=None) | Q(paattymis_pvm__gte=maksutieto_obj.alkamis_pvm))
        ).distinct().count()

        if samanaikaiset_maksutiedot >= 2:
            raise ValidationError({"paattymis_pvm": ["lapsi already has 2 active maksutieto during that time period"]})

        serializer.save(changed_by=user)

        toimipaikka_obj = (Toimipaikka.objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi_object)
                           .first())
        if toimipaikka_obj:
            vakajarjestaja = toimipaikka_obj.vakajarjestaja
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))

    def destroy(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()

        lapsi_objects = Lapsi.objects.filter(huoltajuussuhteet__maksutiedot=instance).distinct()
        if len(lapsi_objects) != 1:
            logger.error("Error getting lapsi when deleting maksutieto " + str(instance.id))
            raise CustomServerErrorException
        lapsi_object = lapsi_objects[0]

        if not user.has_perm('delete_maksutieto', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")
        self.perform_destroy(instance)

        toimipaikka_obj = (Toimipaikka
                           .objects
                           .filter(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi_object)
                           .first())
        if toimipaikka_obj:
            vakajarjestaja = toimipaikka_obj.vakajarjestaja
            cache.delete('vakajarjestaja_yhteenveto_' + str(vakajarjestaja.id))

        return Response(status=status.HTTP_204_NO_CONTENT)


class PaosToimintaViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, CreateModelMixin, DestroyModelMixin):
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
    filter_class = filters.PaosToimintaFilter
    queryset = PaosToiminta.objects.all().order_by('id')
    serializer_class = PaosToimintaSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(PaosToimintaViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def get_paos_toiminta_is_active_q(self, validated_data):
        paos_toiminta_is_active_q = ''

        if 'paos_organisaatio' in validated_data and validated_data['paos_organisaatio'] is not None:
            if validated_data['oma_organisaatio'] == validated_data['paos_organisaatio']:
                raise ValidationError({'oma_organisaatio': "oma_organisaatio can not be the same as paos_organisaatio"})

            paos_toiminta_is_active_q = (Q(oma_organisaatio=validated_data['paos_organisaatio']) &
                                         Q(paos_toimipaikka__vakajarjestaja=validated_data['oma_organisaatio']))

        elif 'paos_toimipaikka' in validated_data and validated_data['paos_toimipaikka'] is not None:
            if validated_data['paos_toimipaikka'].vakajarjestaja == validated_data['oma_organisaatio']:
                raise ValidationError({'paos_toimipaikka': "paos_toimipaikka can not be in oma_organisaatio"})

            paos_toiminta_is_active_q = (Q(oma_organisaatio=validated_data['paos_toimipaikka'].vakajarjestaja) &
                                         Q(paos_organisaatio=validated_data['oma_organisaatio']))

            toimipaikka_jarjestamismuoto_koodit = validated_data['paos_toimipaikka'].jarjestamismuoto_koodi
            [x.lower() for x in toimipaikka_jarjestamismuoto_koodit]
            toimipaikka_jarjestamismuoto_koodit_set = set(toimipaikka_jarjestamismuoto_koodit)
            paos_jarjestamismuoto_koodit_set = set(['jm02', 'jm03'])
            if len(toimipaikka_jarjestamismuoto_koodit_set.intersection(paos_jarjestamismuoto_koodit_set)) == 0:
                raise ValidationError({'paos_toimipaikka': "jarjestamismuoto_koodi is not jm02 or jm03"})

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

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        check_if_user_has_paakayttaja_permissions(validated_data['oma_organisaatio'].organisaatio_oid, user)
        paos_toiminta_is_active_q = self.get_paos_toiminta_is_active_q(validated_data)
        paos_toiminta_is_active = PaosToiminta.objects.filter(paos_toiminta_is_active_q)
        jarjestaja_kunta_organisaatio = self.get_jarjestaja_kunta_organisaatio(validated_data)
        tuottaja_organisaatio = self.get_tuottaja_organisaatio(validated_data)

        with transaction.atomic():
            try:
                saved_object = serializer.save(changed_by=user)
                VARDA_PAAKAYTTAJA = Z4_CasKayttoOikeudet.PAAKAYTTAJA
                group_name = Group.objects.filter(name=VARDA_PAAKAYTTAJA + '_' + validated_data['oma_organisaatio'].organisaatio_oid)
                assign_perm('view_paostoiminta', group_name, saved_object)
                assign_perm('delete_paostoiminta', group_name, saved_object)

                paos_oikeus_old = PaosOikeus.objects.filter(
                    Q(jarjestaja_kunta_organisaatio=jarjestaja_kunta_organisaatio, tuottaja_organisaatio=tuottaja_organisaatio)
                ).first()  # Either None or the actual paos-oikeus obj

                if paos_oikeus_old and paos_toiminta_is_active.exists() and not paos_oikeus_old.voimassa_kytkin:
                    paos_oikeus_old.voimassa_kytkin = True
                    paos_oikeus_old.changed_by = user
                    paos_oikeus_old.save()
                elif paos_oikeus_old and paos_oikeus_old.voimassa_kytkin:
                    grant_or_deny_access_to_paos_toimipaikka(True, jarjestaja_kunta_organisaatio, tuottaja_organisaatio)
                elif not paos_oikeus_old:
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
                    msg = {'non_field_errors': ['oma_organisaatio and paos_organisaatio pair already exists.']}
                    raise ValidationError(msg)
                elif 'oma_organisaatio_paos_toimipaikka_unique_constraint' in str(e):
                    msg = {'non_field_errors': ['oma_organisaatio and paos_toimipaikka pair already exists.']}
                    raise ValidationError(msg)
                else:
                    logger.error('IntegrityError at PaosToimintaViewSet: {}'.format(e))
                    raise CustomServerErrorException

    def perform_destroy(self, instance):
        """
        Make voimassa_kytkin false when organisation permissions is deleted or when last toimipaikka permission is deleted
        """
        user = self.request.user
        paos_oikeus_object = None

        if not user.has_perm('delete_paostoiminta', instance):
            raise PermissionDenied("User does not have permissions to delete this object.")

        with transaction.atomic():
            if instance.paos_organisaatio is not None:
                paos_oikeus_object = PaosOikeus.objects.filter(
                    Q(jarjestaja_kunta_organisaatio=instance.paos_organisaatio, tuottaja_organisaatio=instance.oma_organisaatio)
                ).first()
            elif instance.paos_toimipaikka is not None:
                paos_toimipaikka_count = PaosToiminta.objects.filter(
                    Q(oma_organisaatio=instance.oma_organisaatio) &
                    Q(paos_toimipaikka__vakajarjestaja=instance.paos_toimipaikka.vakajarjestaja)
                ).count()
                if paos_toimipaikka_count == 1:  # Last toimipaikka permission is being removed
                    paos_oikeus_object = PaosOikeus.objects.filter(
                        Q(jarjestaja_kunta_organisaatio=instance.oma_organisaatio, tuottaja_organisaatio=instance.paos_toimipaikka.vakajarjestaja)
                    ).first()

            instance.delete()
            if paos_oikeus_object:
                paos_oikeus_object.voimassa_kytkin = False
                paos_oikeus_object.save()  # we cannot use update since we need to catch the pre_save signal


class PaosOikeusViewSet(GenericViewSet, UpdateModelMixin, ListModelMixin, RetrieveModelMixin):
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
    filter_class = filters.PaosOikeusFilter
    queryset = PaosOikeus.objects.all().order_by('id')
    serializer_class = PaosOikeusSerializer
    permission_classes = (CustomObjectPermissions,)

    def get_throttles(self):
        if self.request.method.lower() in THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super(PaosOikeusViewSet, self).get_throttles()

    def list(self, request, *args, **kwargs):
        return cached_list_response(self, request.user, request.get_full_path())

    def retrieve(self, request, *args, **kwargs):
        return cached_retrieve_response(self, request.user, request.path)

    def perform_update(self, serializer):
        user = self.request.user
        paos_oikeus_obj = self.get_object()
        validated_data = serializer.validated_data

        if not user.has_perm("change_paosoikeus", paos_oikeus_obj):
            raise PermissionDenied("user does not have permission to change object")

        if (validated_data['tallentaja_organisaatio'] != paos_oikeus_obj.jarjestaja_kunta_organisaatio and
                validated_data['tallentaja_organisaatio'] != paos_oikeus_obj.tuottaja_organisaatio):
            msg = ("tallentaja_organisaatio must be either jarjestaja_kunta_organisaatio or tuottaja_organisaatio")
            raise ValidationError({"tallentaja_organisaatio": msg}, code='invalid')

        # do not allow unnecessary updates
        if paos_oikeus_obj.tallentaja_organisaatio == validated_data['tallentaja_organisaatio']:
            msg = ('tallentaja is already set for vakajarjestaja {}').format(validated_data['tallentaja_organisaatio'])
            raise ValidationError({"tallentaja_organisaatio": msg}, code='invalid')

        with transaction.atomic():
            serializer.save(changed_by=user)
            save_audit_log(user, self.request.get_full_path())


"""
Nested viewsets, e.g. /api/v1/vakajarjestajat/33/toimipaikat/
"""


class NestedVakajarjestajaYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan yhteenvetotiedot
    """
    filter_backends = (DjangoObjectPermissionsFilter, )
    filter_class = None
    queryset = VakaJarjestaja.objects.none()
    serializer_class = VakaJarjestajaYhteenvetoSerializer
    permission_classes = (CustomObjectPermissions,)
    today = datetime.now()

    def get_vakajarjestaja(self, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = self.request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        vakajarjestaja_obj = self.get_vakajarjestaja(vakajarjestaja_pk=kwargs['vakajarjestaja_pk'])
        data = cache.get('vakajarjestaja_yhteenveto_' + kwargs['vakajarjestaja_pk'])
        if data is None:
            save_audit_log(request.user, request.get_full_path())
            data = {
                "vakajarjestaja_nimi": vakajarjestaja_obj.nimi,
                "lapset_lkm": self.get_lapset_lkm(vakajarjestaja_obj.id),
                "lapset_vakapaatos_voimassaoleva": self.get_vakapaatos_voimassaoleva(vakajarjestaja_obj.id),
                "lapset_vakasuhde_voimassaoleva": self.get_vakasuhde_voimassaoleva(vakajarjestaja_obj.id),
                "lapset_vuorohoidossa": self.get_vuorohoito_lapset(vakajarjestaja_obj.id),
                "lapset_palveluseteli_ja_ostopalvelu": self.get_paos_lapset(vakajarjestaja_obj.id),
                "lapset_maksutieto_voimassaoleva": self.get_maksutieto_voimassaoleva(vakajarjestaja_obj.id),
                "toimipaikat_voimassaolevat": self.get_active_toimipaikat(vakajarjestaja_obj.id),
                "toimipaikat_paattyneet": self.get_closed_toimipaikat(vakajarjestaja_obj.id),
                "toimintapainotukset_maara": self.get_toimipaikkojen_toimintapainotukset(vakajarjestaja_obj.id),
                "kielipainotukset_maara": self.get_toimipaikkojen_kielipainotukset(vakajarjestaja_obj.id)
            }
            cache.set('vakajarjestaja_yhteenveto_' + kwargs['vakajarjestaja_pk'], data, 8 * 60 * 60)

        serializer = self.get_serializer(data, many=False)
        return Response(serializer.data)

    def get_lapset_lkm(self, vakajarjestaja_id):
        """
        Return the number of unique lapset (having an active vakasuhde) in all toimipaikat under the vakajarjestaja.
        """
        return (Lapsi.objects
                .filter(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                    (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                     Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))
                .distinct()
                .count()
                )

    def get_vakapaatos_voimassaoleva(self, vakajarjestaja_id):
        return (Varhaiskasvatuspaatos.objects
                .filter(varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .count()
                )

    def get_vakasuhde_voimassaoleva(self, vakajarjestaja_id):
        return (Varhaiskasvatussuhde.objects
                .filter(toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .count()
                )

    def get_vuorohoito_lapset(self, vakajarjestaja_id):
        """
        Return the number of unique lapset (having an active vakasuhde AND vuorohoito_kytkin=True) in all toimipaikat under the vakajarjestaja.
        """
        return (Lapsi.objects
                .filter(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False) &
                        Q(varhaiskasvatuspaatokset__vuorohoito_kytkin=True))
                .filter(
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                    (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                     Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))
                .distinct()
                .count()
                )

    def get_paos_lapset(self, vakajarjestaja_id):
        """
        Return the number of unique lapset (having an active vakasuhde) in Palveluseteli or Ostopalvelu under the vakajarjestaja.

        """
        return (Lapsi.objects
                .filter(Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=vakajarjestaja_id) |
                        Q(oma_organisaatio=vakajarjestaja_id) |
                        Q(paos_organisaatio=vakajarjestaja_id)
                        )
                .filter(
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False) &
                    (Q(varhaiskasvatuspaatokset__jarjestamismuoto_koodi__iexact="JM02") |
                     Q(varhaiskasvatuspaatokset__jarjestamismuoto_koodi__iexact="JM03")))
                .filter(
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=self.today) &
                    (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True) |
                     Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=self.today)))
                .distinct().count()
                )

    def get_maksutieto_voimassaoleva(self, vakajarjestaja_id):
        """
        Returns the number of unique active maksutieto objects
        """
        return (Maksutieto.objects
                .filter(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .distinct().count()
                )

    def get_active_toimipaikat(self, vakajarjestaja_id):
        return (Toimipaikka.objects
                .filter(vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .count()
                )

    def get_closed_toimipaikat(self, vakajarjestaja_id):
        return (Toimipaikka.objects
                .filter(vakajarjestaja__id=vakajarjestaja_id)
                .filter(paattymis_pvm__lt=self.today)
                .count()
                )

    def get_toimipaikkojen_toimintapainotukset(self, vakajarjestaja_id):
        """
        Return the number of active toimintapainotukset in all toimipaikat under the vakajarjestaja.
        """
        return (ToiminnallinenPainotus.objects
                .filter(toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .count()
                )

    def get_toimipaikkojen_kielipainotukset(self, vakajarjestaja_id):
        """
        Return the number of active kielipainotukset in all toimipaikat under the vakajarjestaja.
        """
        return (KieliPainotus.objects
                .filter(toimipaikka__vakajarjestaja__id=vakajarjestaja_id)
                .filter(
                    Q(alkamis_pvm__lte=self.today) &
                    (Q(paattymis_pvm__isnull=True) |
                     Q(paattymis_pvm__gte=self.today)))
                .count()
                )


class NestedTaydennyskoulutusViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        nouda tietyn työntekijän kaikki täydennyskoulutukset
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.TaydennyskoulutusFilter
    queryset = Taydennyskoulutus.objects.none()
    serializer_class = TaydennyskoulutusSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_tyontekija(self, request, tyontekija_pk=None):
        tyontekija = get_object_or_404(Tyontekija.objects.all(), pk=tyontekija_pk)
        user = request.user
        if user.has_perm("view_tyontekija", tyontekija):
            return tyontekija
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['tyontekija_pk'].isdigit():
            raise Http404("Not found.")

        self.get_tyontekija(request, tyontekija_pk=kwargs['tyontekija_pk'])
        self.queryset = Taydennyskoulutus.objects.filter(tyontekija=kwargs['tyontekija_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedVarhaiskasvatussuhdeViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        nouda tietyn varhaiskasvatuspaatoksen kaikki varhaiskasvatussuhteet
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_varhaiskasvatuspaatos(self, request, varhaiskasvatuspaatos_pk=None):
        varhaiskasvatuspaatos = get_object_or_404(Varhaiskasvatuspaatos.objects.all(), pk=varhaiskasvatuspaatos_pk)
        user = request.user
        if user.has_perm("view_varhaiskasvatuspaatos", varhaiskasvatuspaatos):
            return varhaiskasvatuspaatos
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['varhaiskasvatuspaatos_pk'].isdigit():
            raise Http404("Not found.")

        self.get_varhaiskasvatuspaatos(request, varhaiskasvatuspaatos_pk=kwargs['varhaiskasvatuspaatos_pk'])
        self.queryset = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos=kwargs['varhaiskasvatuspaatos_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vaka-järjestäjän kaikki toimipaikat.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=kwargs['vakajarjestaja_pk'])
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj)
        qs_own_toimipaikat = Q(vakajarjestaja=kwargs['vakajarjestaja_pk'])
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        self.queryset = (Toimipaikka
                         .objects
                         .filter(qs_own_toimipaikat | qs_paos_toimipaikat)
                         .order_by('nimi'))

        return cached_list_response(self, request.user, request.get_full_path(), order_by='nimi')


class NestedToiminnallinenPainotusViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki toiminnalliset painotukset.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.ToiminnallinenPainotusFilter
    queryset = ToiminnallinenPainotus.objects.none()
    serializer_class = ToiminnallinenPainotusSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404("Not found.")

        self.get_toimipaikka(request, toimipaikka_pk=kwargs['toimipaikka_pk'])
        self.queryset = ToiminnallinenPainotus.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedKieliPainotusViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki kielipainotukset.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.KieliPainotusFilter
    queryset = KieliPainotus.objects.none()
    serializer_class = KieliPainotusSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404("Not found.")

        self.get_toimipaikka(request, toimipaikka_pk=kwargs['toimipaikka_pk'])
        self.queryset = KieliPainotus.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedOhjaajasuhdeToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki ohjaajasuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.OhjaajasuhdeFilter
    queryset = Ohjaajasuhde.objects.none()
    serializer_class = OhjaajasuhdeSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404("Not found.")

        self.get_toimipaikka(request, toimipaikka_pk=kwargs['toimipaikka_pk'])
        self.queryset = Ohjaajasuhde.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedVarhaiskasvatussuhdeToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan kaikki varhaiskasvatussuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404("Not found.")

        self.get_toimipaikka(request, toimipaikka_pk=kwargs['toimipaikka_pk'])
        self.queryset = Varhaiskasvatussuhde.objects.filter(toimipaikka=kwargs['toimipaikka_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedVarhaiskasvatuspaatosViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki varhaiskasvatuspäätökset.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.VarhaiskasvatuspaatosFilter
    queryset = Varhaiskasvatuspaatos.objects.none()
    serializer_class = VarhaiskasvatuspaatosSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404("Not found.")

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        self.queryset = Varhaiskasvatuspaatos.objects.filter(lapsi=kwargs['lapsi_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedLapsiKoosteViewSet(GenericViewSet):
    """
    list:
        Nouda kooste tietyn lapsen tiedoista.
    """
    filter_backends = (DjangoFilterBackend, )
    filter_class = None
    queryset = Lapsi.objects.none()
    serializer_class = LapsiKoosteSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404("Not found.")

        lapsi = self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        save_audit_log(request.user, request.get_full_path())
        data = {
            "henkilo": self.get_henkilo(lapsi),
            "varhaiskasvatuspaatokset": self.get_vakapaatokset(lapsi.id),
            "varhaiskasvatussuhteet": self.get_vakasuhteet(lapsi.id),
            "maksutiedot": self.get_maksutiedot(lapsi.id)
        }

        serializer = self.get_serializer(data, many=False)
        return Response(serializer.data)

    def get_henkilo(self, lapsi):
        """
        Return henkilo for given lapsi
        """
        return lapsi.henkilo

    def get_vakapaatokset(self, lapsi_id):
        """
        Return vakapaatokset for given lapsi_id
        """
        vakapaatokset = Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi_id).distinct().order_by('-alkamis_pvm')
        if vakapaatokset.count() > 0 and self.request.user.has_perm("view_varhaiskasvatuspaatos", vakapaatokset[0]):
            return vakapaatokset
        else:
            return None

    def get_vakasuhteet(self, lapsi_id):
        """
        Return vakasuhteet for given lapsi_id
        """
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi_id).select_related('toimipaikka').distinct().order_by('-alkamis_pvm')
        if vakasuhteet.count() > 0 and self.request.user.has_perm("view_varhaiskasvatussuhde", vakasuhteet[0]):
            return vakasuhteet
        else:
            return None

    def get_maksutiedot(self, lapsi_id):
        """
        Return maksutiedot for given lapsi_id
        """
        maksutiedot = Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi_id).distinct().order_by('-alkamis_pvm')
        if maksutiedot.count() > 0 and self.request.user.has_perm('view_maksutieto', maksutiedot[0]):
            return maksutiedot
        else:
            return None


class NestedLapsenVarhaiskasvatussuhdeViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki varhaiskasvatussuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.VarhaiskasvatussuhdeFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = VarhaiskasvatussuhdeSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404("Not found.")

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        varhaiskasvatuspaatos_ids = Varhaiskasvatuspaatos.objects.filter(lapsi=kwargs['lapsi_pk']).values('id')
        self.queryset = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos_id__in=varhaiskasvatuspaatos_ids).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class NestedLapsiMaksutietoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn lapsen kaikki maksutiedot.
    """
    filter_backends = (DjangoObjectPermissionsFilter, DjangoFilterBackend)
    filter_class = filters.MaksutietoFilter
    queryset = Maksutieto.objects.none()
    serializer_class = MaksutietoGetSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_lapsi(self, request, lapsi_pk=None):
        lapsi = get_object_or_404(Lapsi.objects.all(), pk=lapsi_pk)
        user = request.user
        if user.has_perm("view_lapsi", lapsi):
            return lapsi
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['lapsi_pk'].isdigit():
            raise Http404("Not found.")

        self.get_lapsi(request, lapsi_pk=kwargs['lapsi_pk'])
        queryset = self.filter_queryset(Maksutieto.objects.filter(huoltajuussuhteet__lapsi=kwargs['lapsi_pk']).distinct().order_by('id'))

        save_audit_log(request.user, request.get_full_path())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class NestedVakajarjestajaPaosToimijatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan paos-järjestäjät
    """
    filter_backends = (DjangoObjectPermissionsFilter,)
    filter_class = None
    queryset = VakaJarjestaja.objects.none()
    serializer_class = PaosToimijatSerializer
    permission_classes = (CustomObjectPermissions,)
    today = datetime.now()

    def get_vakajarjestaja(self, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = self.request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        if not self.kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        vakajarjestaja_obj = self.get_vakajarjestaja(vakajarjestaja_pk=self.kwargs['vakajarjestaja_pk'])

        paos_toiminnat = PaosToiminta.objects.filter(
            Q(oma_organisaatio=vakajarjestaja_obj, paos_organisaatio__isnull=False)
        ).order_by('id')

        page = self.paginate_queryset(paos_toiminnat)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(paos_toiminnat, many=True)
        return Response(serializer.data)


class NestedVakajarjestajaPaosToimipaikatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda varhaiskasvatustoimijan paos-järjestäjän toimipaikat

    filter:
        toimipaikka_nimi: suodata toimipaikan nimen perusteella
        organisaatio_oid: suodata toimipaikan organisaatio_oid:n perusteella
        toimija_nimi: suodata toimijan nimen perusteella
    """
    filter_backends = (DjangoObjectPermissionsFilter, )
    filter_class = None
    queryset = VakaJarjestaja.objects.none()
    serializer_class = PaosToimipaikatSerializer
    permission_classes = (CustomObjectPermissions,)
    today = datetime.now()

    def get_vakajarjestaja(self, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = self.request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        if not self.kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        query_params = self.request.query_params
        toimipaikka_nimi_filter = query_params.get('toimipaikka_nimi')
        organisaatio_oid_filter = query_params.get('organisaatio_oid')
        toimija_nimi_filter = query_params.get('toimija_nimi')

        vakajarjestaja_obj = self.get_vakajarjestaja(vakajarjestaja_pk=self.kwargs['vakajarjestaja_pk'])
        paos_toiminta_qs = PaosToiminta.objects.filter(
            Q(oma_organisaatio=vakajarjestaja_obj, paos_toimipaikka__isnull=False)
        ).select_related('paos_toimipaikka', 'paos_toimipaikka__vakajarjestaja')

        paos_toiminnat = paos_toiminta_qs.distinct('paos_toimipaikka__nimi').order_by('paos_toimipaikka__nimi')
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


class NestedOhjaajasuhdeTyontekijaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn työntekijän kaikki ohjaajasuhteet.
    """
    filter_backends = (DjangoFilterBackend,)
    filter_class = filters.OhjaajasuhdeFilter
    queryset = Ohjaajasuhde.objects.none()
    serializer_class = OhjaajasuhdeSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_tyontekija(self, request, tyontekija_pk=None):
        tyontekija = get_object_or_404(Tyontekija.objects.all(), pk=tyontekija_pk)
        user = request.user
        if user.has_perm("view_tyontekija", tyontekija):
            return tyontekija
        else:
            raise Http404("Not found.")

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['tyontekija_pk'].isdigit():
            raise Http404("Not found.")

        self.get_tyontekija(request, tyontekija_pk=kwargs['tyontekija_pk'])
        self.queryset = Ohjaajasuhde.objects.filter(tyontekija=kwargs['tyontekija_pk']).order_by('id')

        return cached_list_response(self, request.user, request.get_full_path())


class HenkilohakuLapset(GenericViewSet, ListModelMixin):
    """
    Henkilöhaku rajapinta

    Haettaessa hetulla hetun täytyy olla utf-8 enkoodatusta tekstistä sha256 hashatyssä hexadesimaali muodossa. Parametrit:
        search = henkilön nimi
        filter_status = objektin tila, voi olla 'kaikki', 'voimassaolevat', 'paattyneet' tai 'eimaksutietoja'
        filter_object = objekti, voi olla 'vakapaatokset', 'vakasuhteet' tai 'maksutiedot'
    """
    serializer_class = HenkilohakuLapsetSerializer
    queryset = Lapsi.objects.none()
    filter_backends = None
    permission_classes = (CustomObjectPermissions, )
    search_fields = ('henkilo__etunimet', 'henkilo__sukunimi', '=henkilo__henkilotunnus_unique_hash', '=henkilo__henkilo_oid', )
    tz = pytz.timezone('Europe/Helsinki')
    today = datetime.now(tz=tz)

    def get_toimipaikka_ids(self):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        vakajarjestaja_obj = get_object_or_404(VakaJarjestaja, pk=vakajarjestaja_id)
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj)
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
            self.filter_backends = (DjangoObjectPermissionsFilter, SearchFilter, )

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

    def filter_vakapaatokset(self, varhaiskasvatuspaatokset_query, filter_status):
        if filter_status == 'voimassaolevat':
            varhaiskasvatuspaatokset_query = varhaiskasvatuspaatokset_query.filter(
                Q(alkamis_pvm__lte=self.today) &
                (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=self.today))
            )
        elif filter_status == 'paattyneet':
            varhaiskasvatuspaatokset_query = varhaiskasvatuspaatokset_query.filter(Q(paattymis_pvm__lt=self.today))
        return varhaiskasvatuspaatokset_query

    def filter_vakasuhteet(self, varhaiskasvatussuhteet_query, filter_status):
        if filter_status == 'voimassaolevat':
            varhaiskasvatussuhteet_query = varhaiskasvatussuhteet_query.filter(
                Q(alkamis_pvm__lte=self.today) &
                (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=self.today))
            )
        elif filter_status == 'paattyneet':
            varhaiskasvatussuhteet_query = varhaiskasvatussuhteet_query.filter(Q(paattymis_pvm__lt=self.today))
        return varhaiskasvatussuhteet_query

    def get_lapsi_query(self, list_of_toimipaikka_ids):
        varhaiskasvatuspaatokset_query = (Varhaiskasvatuspaatos
                                          .objects
                                          .filter(varhaiskasvatussuhteet__toimipaikka__id__in=list_of_toimipaikka_ids))

        varhaiskasvatussuhteet_query = (Varhaiskasvatussuhde
                                        .objects
                                        .filter(toimipaikka__id__in=list_of_toimipaikka_ids))

        query_params = self.request.query_params
        filter_status = query_params.get('filter_status', "")
        filter_object = query_params.get('filter_object', "")

        if filter_status != "" and filter_object != "":

            # Vakapaatokset
            if filter_object == 'vakapaatokset':
                varhaiskasvatuspaatokset_query = self.filter_vakapaatokset(varhaiskasvatuspaatokset_query, filter_status)

            # Vakasuhteet
            if filter_object == 'vakasuhteet':
                varhaiskasvatussuhteet_query = self.filter_vakasuhteet(varhaiskasvatussuhteet_query, filter_status)

            # Maksutiedot
            if filter_object == 'maksutiedot' and filter_status == 'eimaksutietoja':
                varhaiskasvatuspaatokset_query = varhaiskasvatuspaatokset_query.annotate(
                    maksutiedot_count=Count('lapsi__huoltajuussuhteet__maksutiedot')
                ).filter(maksutiedot_count=0)

        self.kwargs['varhaiskasvatuspaatokset_query'] = varhaiskasvatuspaatokset_query
        self.kwargs['varhaiskasvatussuhteet_query'] = varhaiskasvatussuhteet_query
        return (Q(varhaiskasvatuspaatokset__in=varhaiskasvatuspaatokset_query) &
                Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__in=varhaiskasvatussuhteet_query))

    def add_order_by(self, query):
        return query.order_by('henkilo__sukunimi', 'henkilo__etunimet')
