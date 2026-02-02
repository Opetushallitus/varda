import datetime

from django.conf import settings
from django.db import transaction
from django.db.models import Exists, F, OuterRef, Prefetch, Q, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda import filters
from varda.cache import get_object_ids_user_has_permissions, get_queryset_count_cache_key
from varda.cas.varda_permissions import IsVardaPaakayttaja
from varda.custom_swagger import ActionPaginationSwaggerAutoSchema
from varda.filters import CustomParametersFilterBackend, CustomParameter
from varda.kayttooikeuspalvelu import set_active_groups_for_user
from varda.misc_queries import get_active_filter, get_paos_toimipaikat, get_queryset_count
from varda.misc_viewsets import ExtraKwargsFilterBackend, parse_query_parameter
from varda.models import (
    PidempiPoissaolo,
    Toimipaikka,
    Organisaatio,
    PaosToiminta,
    PaosOikeus,
    Lapsi,
    Henkilo,
    Tyontekija,
    Z4_CasKayttoOikeudet,
)
from varda.pagination import (
    UiHenkiloBasicNameOrderingCursorPagination,
    UiHenkiloNameOrderingCursorPagination,
    UiNestedToimipaikkaNameOrderingCursorPagination,
)
from varda.permissions import (
    activate_all_permissions_decorator,
    CustomModelPermissions,
    get_taydennyskoulutus_tyontekija_group_organisaatio_oids,
    HenkilostohakuPermissions,
    LapsihakuPermissions,
    TYONTEKIJA_GROUPS,
    user_belongs_to_correct_groups,
    user_permission_groups_in_organization,
    get_tyontekija_filters_for_taydennyskoulutus_groups,
    is_oph_staff,
    VAKA_GROUPS,
)
from varda.request_logging import auditlog, auditlogclass, request_log_viewset_decorator_factory
from varda.serializers import PaosToimipaikkaSerializer, PaosOrganisaatioSerializer
from varda.serializers_ui import (
    ActiveOrganisaatioSerializer,
    OrganisaatioUiSerializer,
    ToimipaikkaUiSerializer,
    UiLapsiSerializer,
    TyontekijaHenkiloUiSerializer,
    LapsihakuHenkiloUiSerializer,
    UiTyontekijaSerializer,
)


def parse_vakajarjestaja(user, vakajarjestaja_id, permission_group_list):
    if not vakajarjestaja_id.isdigit():
        raise Http404
    vakajarjestaja = Organisaatio.objects.using(settings.READER_DB).filter(pk=vakajarjestaja_id).first()
    if (
        not vakajarjestaja
        or not user.has_perm("view_organisaatio", vakajarjestaja)
        or not user_belongs_to_correct_groups(
            user, vakajarjestaja, permission_groups=permission_group_list, accept_toimipaikka_permission=True
        )
    ):
        raise Http404

    return vakajarjestaja


@auditlogclass
class UiVakajarjestajatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda vakajarjestajien nimet
    """

    serializer_class = OrganisaatioUiSerializer
    queryset = Organisaatio.objects.none()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_oid = None

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page

    @activate_all_permissions_decorator
    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser:
            queryset = Organisaatio.objects.using(settings.READER_DB).all().order_by("nimi")
        else:
            vakajarjestaja_ids = get_object_ids_user_has_permissions(user, Organisaatio)
            queryset = Organisaatio.objects.using(settings.READER_DB).filter(id__in=vakajarjestaja_ids).order_by("nimi")
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @auditlog
    @action(
        methods=["get"],
        detail=True,
        url_path="tyontekija-list",
        url_name="tyontekija_list",
        serializer_class=TyontekijaHenkiloUiSerializer,
        queryset=Henkilo.objects.using(settings.READER_DB).all(),
        filter_backends=[SearchFilter, DjangoFilterBackend],
        pagination_class=UiHenkiloBasicNameOrderingCursorPagination,
        permission_classes=[HenkilostohakuPermissions],
    )
    @swagger_auto_schema(
        auto_schema=ActionPaginationSwaggerAutoSchema,
        responses={status.HTTP_200_OK: TyontekijaHenkiloUiSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("toimipaikka_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("toimipaikka_oid", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("voimassa_pvm", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("kiertava_tyontekija_kytkin", openapi.IN_QUERY, type=openapi.TYPE_BOOLEAN),
        ],
    )
    def tyontekija_list(self, request, pk=None):
        # Putting this to keyword arguments raises exception
        self.search_fields = ["etunimet", "sukunimi", "=henkilotunnus_unique_hash", "=henkilo_oid"]

        vakajarjestaja = parse_vakajarjestaja(self.request.user, pk, TYONTEKIJA_GROUPS)
        self.vakajarjestaja_oid = vakajarjestaja.organisaatio_oid

        # Use subquery to fetch the required Henkilo objects, and to filter the related Tyontekija objects
        tyontekija_filter = self.get_tyontekija_filters(pk)
        tyontekija_id_subquery = Tyontekija.objects.using(settings.READER_DB).filter(tyontekija_filter).distinct().values("id")
        self.queryset = (
            self.queryset.filter(tyontekijat__id__in=Subquery(tyontekija_id_subquery))
            .prefetch_related(
                Prefetch(
                    "tyontekijat",
                    queryset=Tyontekija.objects.using(settings.READER_DB)
                    .filter(id__in=Subquery(tyontekija_id_subquery))
                    .distinct(),
                )
            )
            .order_by("sukunimi", "etunimet")
            .distinct()
        )
        return super().list(request, pk=pk)

    def get_tyontekija_filters(self, vakajarjestaja_id):
        user = self.request.user

        filter_condition = Q(vakajarjestaja=vakajarjestaja_id)

        if not self._has_organisaatio_level_henkilosto_permissions():
            # No organisaatio level permissions, get results based on object permissions
            tyontekija_id_list = get_object_ids_user_has_permissions(user, Tyontekija)
            taydennyskoulutus_filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(user)
            filter_condition &= Q(id__in=tyontekija_id_list) | taydennyskoulutus_filters

        query_params = self.request.query_params
        if toimipaikka_id := query_params.get("toimipaikka_id", None):
            filter_condition &= Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__id=toimipaikka_id)
        if toimipaikka_oid := query_params.get("toimipaikka_oid", None):
            filter_condition &= Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid=toimipaikka_oid)
        if (kiertava_tyontekija_kytkin := parse_query_parameter(query_params, "kiertava_tyontekija_kytkin", bool)) is not None:
            filter_condition &= Q(palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=kiertava_tyontekija_kytkin)
        if (voimassa_pvm := parse_query_parameter(query_params, "voimassa_pvm", datetime.date)) is not None:
            filter_condition &= (
                get_active_filter(voimassa_pvm, prefix="palvelussuhteet")
                & get_active_filter(voimassa_pvm, prefix="palvelussuhteet__tyoskentelypaikat")
                & ~Exists(
                    PidempiPoissaolo.objects.using(settings.READER_DB).filter(
                        get_active_filter(voimassa_pvm), palvelussuhde=OuterRef("palvelussuhteet")
                    )
                )
            )

        return filter_condition

    @auditlog
    @action(
        methods=["get"],
        detail=True,
        url_path="lapsi-list",
        url_name="lapsi_list",
        serializer_class=LapsihakuHenkiloUiSerializer,
        queryset=Henkilo.objects.using(settings.READER_DB).all(),
        filter_backends=[SearchFilter],
        pagination_class=UiHenkiloBasicNameOrderingCursorPagination,
        permission_classes=[LapsihakuPermissions],
    )
    @swagger_auto_schema(
        auto_schema=ActionPaginationSwaggerAutoSchema,
        responses={status.HTTP_200_OK: LapsihakuHenkiloUiSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter("toimipaikka_id", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("toimipaikka_oid", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("voimassa_pvm", openapi.IN_QUERY, type=openapi.TYPE_STRING),
        ],
    )
    def lapsi_list(self, request, pk=None):
        # Putting this to keyword arguments raises exception
        self.search_fields = ["etunimet", "sukunimi", "=henkilotunnus_unique_hash", "=henkilo_oid"]

        vakajarjestaja = parse_vakajarjestaja(self.request.user, pk, VAKA_GROUPS)
        self.vakajarjestaja_oid = vakajarjestaja.organisaatio_oid

        # Use subquery to fetch the required Henkilo objects, and to filter the related Lapsi objects
        lapsi_filter = self.get_lapsi_filter(pk)
        lapsi_id_subquery = Lapsi.objects.using(settings.READER_DB).filter(lapsi_filter).distinct().values("id")
        prefetch_lapsi = Prefetch(
            "lapsi", queryset=Lapsi.objects.using(settings.READER_DB).filter(id__in=Subquery(lapsi_id_subquery)).distinct()
        )
        self.queryset = (
            self.queryset.filter(lapsi__id__in=Subquery(lapsi_id_subquery))
            .prefetch_related(prefetch_lapsi)
            .order_by("sukunimi", "etunimet")
            .distinct()
        )
        return super().list(request, pk=pk)

    def get_lapsi_filter(self, vakajarjestaja_id):
        user = self.request.user

        filter_condition = (
            Q(vakatoimija=vakajarjestaja_id) | Q(oma_organisaatio=vakajarjestaja_id) | Q(paos_organisaatio=vakajarjestaja_id)
        )

        if not self._has_organisaatio_level_vaka_permissions():
            # No organisaatio level permissions, get results based on object permissions
            lapsi_id_list = get_object_ids_user_has_permissions(user, Lapsi)
            filter_condition &= Q(id__in=lapsi_id_list)

        query_params = self.request.query_params
        if toimipaikka_id := query_params.get("toimipaikka_id", None):
            filter_condition &= Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__id=toimipaikka_id)
        if toimipaikka_oid := query_params.get("toimipaikka_oid", None):
            filter_condition &= Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid=toimipaikka_oid)
        if (voimassa_pvm := parse_query_parameter(query_params, "voimassa_pvm", datetime.date)) is not None:
            filter_condition &= get_active_filter(voimassa_pvm, prefix="varhaiskasvatuspaatokset") & get_active_filter(
                voimassa_pvm, prefix="varhaiskasvatuspaatokset__varhaiskasvatussuhteet"
            )

        return filter_condition

    def _has_organisaatio_level_vaka_permissions(self):
        user = self.request.user
        permission_qs = user_permission_groups_in_organization(
            user,
            self.vakajarjestaja_oid,
            # Huoltajatieto groups do not have permissions to Lapsi objects where organisaatio is paos_organisaatio
            [Z4_CasKayttoOikeudet.PALVELUKAYTTAJA, Z4_CasKayttoOikeudet.TALLENTAJA, Z4_CasKayttoOikeudet.KATSELIJA],
        )
        return user.is_superuser or is_oph_staff(user) or permission_qs.exists()

    def _has_organisaatio_level_henkilosto_permissions(self):
        user = self.request.user
        permission_qs = user_permission_groups_in_organization(
            user,
            self.vakajarjestaja_oid,
            [
                Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
            ],
        )
        return user.is_superuser or is_oph_staff(user) or permission_qs.exists()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        user = self.request.user
        if self.action == "tyontekija_list":
            has_organisaatio_level_permissions = self._has_organisaatio_level_henkilosto_permissions()
            organisaatio_oid_list = (
                [] if has_organisaatio_level_permissions else get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user)
            )
            context = {
                **context,
                "has_organisaatio_level_permissions": has_organisaatio_level_permissions,
                "organisaatio_oid_list": organisaatio_oid_list,
            }
        return context


@auditlogclass
class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vakajärjestäjän kaikki toimipaikat.
    filter:
        voimassaolo=str (voimassa/paattynyt)
    """

    filter_backends = (
        DjangoFilterBackend,
        SearchFilter,
    )
    search_fields = (
        "nimi",
        "=organisaatio_oid",
        "=id",
    )
    filterset_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaUiSerializer
    permission_classes = (CustomModelPermissions,)
    pagination_class = UiNestedToimipaikkaNameOrderingCursorPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_obj = None
        self.vakajarjestaja_oid = ""

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page

    def get_queryset(self):
        if not self.vakajarjestaja_id:
            # Not coming from .list (coming from CustomModelPermissions)
            return Toimipaikka.objects.none()

        paos_toimipaikat = get_paos_toimipaikat(self.vakajarjestaja_obj, is_only_active_paostoiminta_included=False)
        qs_own_toimipaikat = Q(vakajarjestaja=self.vakajarjestaja_id)
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        toimipaikka_filter = qs_own_toimipaikat | qs_paos_toimipaikat

        # Filter toimipaikat based on permissions
        # Only vaka groups have permissions to PAOS Toimipaikka objects
        user = self.request.user
        vaka_group_qs = user_permission_groups_in_organization(self.request.user, self.vakajarjestaja_oid, VAKA_GROUPS)
        if not user.is_superuser and not is_oph_staff(user) and not vaka_group_qs.exists():
            # Get only toimipaikat user has object level permissions to
            toimipaikka_ids_user_has_view_permissions = get_object_ids_user_has_permissions(user, Toimipaikka)
            toimipaikka_filter = toimipaikka_filter & Q(id__in=toimipaikka_ids_user_has_view_permissions)

        return (
            Toimipaikka.objects.using(settings.READER_DB)
            .filter(toimipaikka_filter)
            .values(
                "id",
                "nimi",
                "organisaatio_oid",
                "hallinnointijarjestelma",
                "vakajarjestaja__id",
                "vakajarjestaja__nimi",
                "vakajarjestaja__organisaatio_oid",
            )
            .order_by("nimi")
        )

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            "request": self.request,
            "format": self.format_kwarg,
            "view": self,
            "organisaatio_pk": self.kwargs.get("organisaatio_pk", None),
        }

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(Organisaatio.objects.using(settings.READER_DB).all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm("view_organisaatio", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.using(settings.READER_DB).all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        self.vakajarjestaja_id = kwargs.get("organisaatio_pk", None)
        if not self.vakajarjestaja_id.isdigit():
            raise Http404

        self.vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=self.vakajarjestaja_id)
        self.vakajarjestaja_oid = self.vakajarjestaja_obj.organisaatio_oid

        return super(NestedToimipaikkaViewSet, self).list(request, args, kwargs)

    @auditlog
    @action(methods=["get"], detail=True, url_path="paos-jarjestajat", url_name="paos_jarjestajat")
    @swagger_auto_schema(
        auto_schema=ActionPaginationSwaggerAutoSchema, responses={status.HTTP_200_OK: OrganisaatioUiSerializer(many=True)}
    )
    def paos_jarjestajat(self, request, organisaatio_pk=None, pk=None):
        """
        Nouda vakajärjestäjän paos-järjestäjät annettuun toimipaikkaan

        Hakee ne paos toimintaa järjestävät kunnat joiden puolesta annettu toimija hoitaa tallennustehtäviä annettuun
        paos-toimipaikkaan.
        """
        vakajarjestaja = self.get_vakajarjestaja(request, organisaatio_pk)
        toimipaikka = self.get_toimipaikka(request, pk)
        kunta_qs = (
            PaosToiminta.objects.using(settings.READER_DB)
            .filter(paos_toimipaikka=toimipaikka, voimassa_kytkin=True)
            .values_list("oma_organisaatio_id", flat=True)
        )
        jarjestaja_id_qs = (
            PaosOikeus.objects.using(settings.READER_DB)
            .filter(jarjestaja_kunta_organisaatio__in=kunta_qs, tallentaja_organisaatio=vakajarjestaja, voimassa_kytkin=True)
            .values_list("jarjestaja_kunta_organisaatio", flat=True)
        )
        jarjestaja_qs = Organisaatio.objects.using(settings.READER_DB).filter(id__in=jarjestaja_id_qs).order_by("id")
        page = self.paginate_queryset(jarjestaja_qs)
        serializer = OrganisaatioUiSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)


@auditlogclass
class NestedAllToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta varda pääkäyttäjille paos-toimipaikkojen hakuun (jm02 ja jm03).
    """

    queryset = Toimipaikka.objects.using(settings.READER_DB).all()
    permission_classes = (IsVardaPaakayttaja,)
    serializer_class = PaosToimipaikkaSerializer
    filter_backends = (SearchFilter,)
    search_fields = ["nimi", "nimi_sv"]

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page

    def list(self, request, *args, **kwargs):
        vakajarjestaja_id = self.kwargs.get("organisaatio_pk", None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit() or not get_object_or_404(Organisaatio, pk=vakajarjestaja_id):
            raise Http404
        return super(NestedAllToimipaikkaViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        vakajarjestaja_id = self.kwargs.get("organisaatio_pk", None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit():
            vakajarjestaja_id = None
        # Return only paos toimipaikat
        return (
            Toimipaikka.objects.using(settings.READER_DB)
            .filter(
                Q(vakajarjestaja__pk=vakajarjestaja_id)
                & ~Q(nimi__istartswith="Palveluseteli ja ostopalvelu ")
                & (Q(jarjestamismuoto_koodi__icontains="jm02") | Q(jarjestamismuoto_koodi__icontains="jm03"))
            )
            .order_by("id")
        )


@auditlogclass
class AllVakajarjestajaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta yksityisten ja kunnallisen toimijan tarvitsemien varhaiskasvatustoimijoiden hakuun.
    Query-parametrit:
    *  tyyppi = 'yksityinen' tai 'kunnallinen'
    *  search = str
    """

    queryset = Organisaatio.vakajarjestajat.all().order_by("id")
    permission_classes = (IsVardaPaakayttaja,)
    serializer_class = PaosOrganisaatioSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = filters.UiAllVakajarjestajaFilter

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page


@auditlogclass
class UiNestedLapsiViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tiettyjen toimipaikkojen lapset
    filter:
        Lapsia voi suodattaa etu- ja sukunimien, OID:n tai henkilötunnuksen mukaan, sekä varhaiskasvatussuhteen,
        varhaiskasvatuspäätöksen ja maksutietojen alkamis- ja päättymispäivämäärien perusteella

        Henkilötunnus täytyy olla SHA-256 hash heksadesimaalimuodossa (utf-8 enkoodatusta tekstistä)

        toimipaikat=pilkuilla eroteltu lista toimipaikkojen ID:stä, esim. 1,2,3
        search=str (nimi/hetu/OID)
        rajaus=str (vakasuhteet/vakapaatokset/maksutiedot)
        voimassaolo=str (alkanut/paattynyt/voimassa)
        alkamis_pvm=YYYY-mm-dd
        paattymis_pvm=YYYY-mm-dd
        maksun_peruste=str
        palveluseteli=boolean
        jarjestamismuoto=str
    """

    queryset = Lapsi.objects.none()
    filter_backends = (
        CustomParametersFilterBackend,
        DjangoFilterBackend,
        SearchFilter,
    )
    filterset_class = filters.UiLapsiFilter
    search_fields = (
        "henkilo__etunimet",
        "henkilo__sukunimi",
        "=henkilo__henkilotunnus_unique_hash",
        "=henkilo__henkilo_oid",
        "=id",
        "=tunniste",
        "=varhaiskasvatuspaatokset__id",
        "=varhaiskasvatuspaatokset__tunniste",
        "=varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id",
        "=varhaiskasvatuspaatokset__varhaiskasvatussuhteet__tunniste",
        "=huoltajuussuhteet__maksutiedot__id",
        "=huoltajuussuhteet__maksutiedot__tunniste",
    )
    serializer_class = UiLapsiSerializer
    permission_classes = (CustomModelPermissions,)
    pagination_class = UiHenkiloNameOrderingCursorPagination
    custom_parameters = (
        CustomParameter(
            name="toimipaikat",
            required=False,
            location="query",
            data_type="string",
            description="Comma separated list of toimipaikka IDs",
        ),
        CustomParameter(
            name="rajaus",
            required=False,
            location="query",
            data_type="string",
            description="vakasuhteet/vakapaatokset/maksutiedot",
        ),
        CustomParameter(
            name="voimassaolo", required=False, location="query", data_type="string", description="alkanut/paattynyt/voimassa"
        ),
        CustomParameter(
            name="alkamis_pvm", required=False, location="query", data_type="string", description="ISO Date (YYYY-MM-DD)"
        ),
        CustomParameter(
            name="paattymis_pvm", required=False, location="query", data_type="string", description="ISO Date (YYYY-MM-DD)"
        ),
        CustomParameter(
            name="maksun_peruste",
            required=False,
            location="query",
            data_type="string",
            description="Lapsi must have this maksun peruste koodi",
        ),
        CustomParameter(
            name="palveluseteli",
            required=False,
            location="query",
            data_type="boolean",
            description="Lapsi has maksutieto with palveluseteli",
        ),
        CustomParameter(
            name="jarjestamismuoto",
            required=False,
            location="query",
            data_type="string",
            description="Lapsi must have this jarjestamismuoto koodi",
        ),
        CustomParameter(
            name="toimintamuoto",
            required=False,
            location="query",
            data_type="string",
            description="Related Toimipaikka must have this toimintamuoto koodi",
        ),
        CustomParameter(
            name="aktiiviset",
            required=False,
            location="query",
            data_type="boolean",
            description="Varhaiskasvatuspaatos and Varhaiskasvatussuhde must be active",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_oid = ""

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page

    def get_queryset(self):
        if not self.vakajarjestaja_id:
            # Not coming from .list (coming from CustomModelPermissions)
            return Lapsi.objects.none()

        user = self.request.user

        lapsi_filter = (
            Q(vakatoimija=self.vakajarjestaja_id)
            | Q(oma_organisaatio=self.vakajarjestaja_id)
            | Q(paos_organisaatio=self.vakajarjestaja_id)
        )

        lapsi_organization_groups_qs = user_permission_groups_in_organization(
            user,
            self.vakajarjestaja_oid,
            [Z4_CasKayttoOikeudet.PALVELUKAYTTAJA, Z4_CasKayttoOikeudet.KATSELIJA, Z4_CasKayttoOikeudet.TALLENTAJA],
        )
        # Get all Lapsi objects for superuser, OPH and vakajarjestaja level KATSELIJA/TALLENTAJA permissions
        # Huoltajatieto groups do not have permissions to Lapsi objects where organisaatio is paos_organisaatio
        if not user.is_superuser and not is_oph_staff(user) and not lapsi_organization_groups_qs.exists():
            lapsi_object_ids_user_has_view_permissions = get_object_ids_user_has_permissions(user, Lapsi)
            lapsi_filter &= Q(id__in=lapsi_object_ids_user_has_view_permissions)

        return (
            Lapsi.objects.using(settings.READER_DB)
            .filter(lapsi_filter)
            .annotate(henkilo_sukunimi=F("henkilo__sukunimi"), henkilo_etunimet=F("henkilo__etunimet"))
            .order_by("henkilo__sukunimi", "henkilo__etunimet")
        )

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        user = self.request.user

        vakajarjestaja_obj = parse_vakajarjestaja(user, kwargs["organisaatio_pk"], VAKA_GROUPS)
        self.vakajarjestaja_id = vakajarjestaja_obj.id
        self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid

        return super().list(request, args, kwargs)


@auditlogclass
class UiNestedTyontekijaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tiettyjen toimipaikkojen työntekijät tietyllä vakajärjestäjällä
    filter:
        Työntekijöitä voi rajata toimipaikkojen perusteella, ja kiertävät työntekijät voi hakea antamalla
        vakajärjestäjän ID:n

        Työntekijöitä voi suodattaa etu- ja sukunimien, OID:n tai henkilötunnuksen mukaan,
        sekä palvelussuhteen alkamis- ja päättymispäivämäärien, tehtävänimikkeen, tutkinnon ja työsuhteen perusteella

        Henkilötunnus täytyy olla SHA-256 hash heksadesimaalimuodossa (utf-8 enkoodatusta tekstistä)

        toimipaikat=pilkuilla eroteltu lista toimipaikkojen ID:stä, esim. 1,2,3
        kiertava=true/false
        search=str (nimi/hetu/OID)
        rajaus=str (palvelussuhteet/tyoskentelypaikat/poissaolot/taydennyskoulutukset)
        voimassaolo=str (alkanut/paattynyt/voimassa)
        alkamis_pvm=YYYY-mm-dd
        paattymis_pvm=YYYY-mm-dd
        tehtavanimike=str
        tutkinto=str
        tyosuhde=str
    """

    filter_backends = (
        CustomParametersFilterBackend,
        ExtraKwargsFilterBackend,
        SearchFilter,
    )
    filterset_class = filters.UiTyontekijaFilter
    search_fields = (
        "henkilo__etunimet",
        "henkilo__sukunimi",
        "=henkilo__henkilotunnus_unique_hash",
        "=henkilo__henkilo_oid",
        "=id",
        "=tunniste",
        "=palvelussuhteet__id",
        "=palvelussuhteet__tunniste",
        "=palvelussuhteet__tyoskentelypaikat__id",
        "=palvelussuhteet__tyoskentelypaikat__tunniste",
        "=palvelussuhteet__pidemmatpoissaolot__id",
        "=palvelussuhteet__pidemmatpoissaolot__tunniste",
        "=taydennyskoulutukset__id",
        "=taydennyskoulutukset__tunniste",
    )
    serializer_class = UiTyontekijaSerializer
    permission_classes = (HenkilostohakuPermissions,)
    queryset = Tyontekija.objects.none()
    pagination_class = UiHenkiloNameOrderingCursorPagination
    custom_parameters = (
        CustomParameter(
            name="toimipaikat",
            required=False,
            location="query",
            data_type="string",
            description="Comma separated list of toimipaikka IDs",
        ),
        CustomParameter(
            name="rajaus",
            required=False,
            location="query",
            data_type="string",
            description="palvelussuhteet/tyoskentelypaikat/poissaolot/taydennyskoulutukset",
        ),
        CustomParameter(
            name="voimassaolo", required=False, location="query", data_type="string", description="alkanut/paattynyt/voimassa"
        ),
        CustomParameter(
            name="alkamis_pvm", required=False, location="query", data_type="string", description="ISO Date (YYYY-MM-DD)"
        ),
        CustomParameter(
            name="paattymis_pvm", required=False, location="query", data_type="string", description="ISO Date (YYYY-MM-DD)"
        ),
        CustomParameter(
            name="kiertava",
            required=False,
            location="query",
            data_type="boolean",
            description="Tyontekija has kiertava tyoskentelypaikka",
        ),
        CustomParameter(
            name="tehtavanimike",
            required=False,
            location="query",
            data_type="string",
            description="Tyontekija must have this tehtavanimike koodi",
        ),
        CustomParameter(
            name="tutkinto",
            required=False,
            location="query",
            data_type="string",
            description="Tyontekija must have this tutkinto koodi",
        ),
        CustomParameter(
            name="tyosuhde",
            required=False,
            location="query",
            data_type="string",
            description="Tyontekija must have this tyosuhde koodi",
        ),
        CustomParameter(
            name="aktiiviset",
            required=False,
            location="query",
            data_type="boolean",
            description="Palvelussuhde and Tyoskentelypaikka must be active, no active PidempiPoissaolo",
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_oid = ""
        self.has_vakajarjestaja_tyontekija_permissions = False

    def paginate_queryset(self, queryset):
        paginator = self.paginator
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        if page is not None:
            queryset_count_cache_key = get_queryset_count_cache_key(self.request)
            paginator._queryset_count = get_queryset_count(queryset, queryset_count_cache_key)
        return page

    def get_queryset(self):
        if not self.vakajarjestaja_id:
            # Not coming from .list (coming from CustomModelPermissions)
            return Tyontekija.objects.none()

        tyontekija_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)

        tyontekija_organization_groups_qs = user_permission_groups_in_organization(
            self.request.user,
            self.vakajarjestaja_oid,
            [Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA, Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA],
        )

        user = self.request.user
        is_superuser_or_oph_staff = user.is_superuser or is_oph_staff(user)
        self.has_vakajarjestaja_tyontekija_permissions = is_superuser_or_oph_staff or tyontekija_organization_groups_qs.exists()

        taydennyskoulutus_organization_groups_qs = user_permission_groups_in_organization(
            self.request.user,
            self.vakajarjestaja_oid,
            [
                Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
            ],
        )

        # Get all Tyontekija objects for superuser, OPH and vakajarjestaja level permissions
        if not self.has_vakajarjestaja_tyontekija_permissions and not taydennyskoulutus_organization_groups_qs.exists():
            # Get only Tyontekija objects user has object permissions to, or objects that belong to user's
            # taydennyskoulutus groups
            tyontekija_ids_user_has_view_permissions = get_object_ids_user_has_permissions(user, Tyontekija)
            tyontekija_taydennyskoulutus_filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(
                self.request.user
            )
            tyontekija_filter = tyontekija_filter & (
                Q(id__in=tyontekija_ids_user_has_view_permissions) | tyontekija_taydennyskoulutus_filters
            )

        return (
            Tyontekija.objects.using(settings.READER_DB)
            .filter(tyontekija_filter)
            .annotate(henkilo_sukunimi=F("henkilo__sukunimi"), henkilo_etunimet=F("henkilo__etunimet"))
            .order_by("henkilo__sukunimi", "henkilo__etunimet")
        )

    def get_filterset_kwargs(self):
        return {"has_vakajarjestaja_tyontekija_permissions": self.has_vakajarjestaja_tyontekija_permissions}

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        user = self.request.user

        vakajarjestaja_obj = parse_vakajarjestaja(user, kwargs["organisaatio_pk"], TYONTEKIJA_GROUPS)
        self.vakajarjestaja_id = vakajarjestaja_obj.id
        self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid

        return super().list(request, args, kwargs)


@request_log_viewset_decorator_factory()
class ActiveOrganisaatioViewSet(GenericViewSet, CreateModelMixin):
    """
    create:
        Set active permission groups for User based on Organisaatio selection
    """

    queryset = Organisaatio.objects.none()
    permission_classes = (IsAuthenticated,)
    serializer_class = ActiveOrganisaatioSerializer

    @activate_all_permissions_decorator
    def _get_organisaatio(self, request):
        # request parameter needed for decorator
        serializer = self.get_serializer(data=self.request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        return data.get("organisaatio", None)

    @swagger_auto_schema(responses={status.HTTP_200_OK: ""})
    def create(self, request, *args, **kwargs):
        organisaatio = self._get_organisaatio(request)
        set_active_groups_for_user(self.request.user, organisaatio_obj=organisaatio)
        return Response(status=status.HTTP_200_OK)
