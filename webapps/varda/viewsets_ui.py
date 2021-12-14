import datetime

from operator import itemgetter

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from guardian.shortcuts import get_objects_for_user
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda import filters
from varda.cache import create_cache_key, get_object_ids_user_has_permissions
from varda.cas.varda_permissions import IsVardaPaakayttaja
from varda.custom_swagger import ActionPaginationSwaggerAutoSchema
from varda.filters import TyontekijahakuUiFilter
from varda.misc_queries import get_paos_toimipaikat
from varda.misc_viewsets import ExtraKwargsFilterBackend
from varda.models import (Toimipaikka, VakaJarjestaja, PaosToiminta, PaosOikeus, Lapsi, Henkilo,
                          Tyontekija, Z4_CasKayttoOikeudet)
from varda.pagination import ChangeablePageSizePagination, ChangeablePageSizePaginationLarge
from varda.permissions import (CustomModelPermissions, get_taydennyskoulutus_tyontekija_group_organisaatio_oids,
                               get_toimipaikat_group_has_access, get_organisaatio_oids_from_groups,
                               HenkilostohakuPermissions, LapsihakuPermissions, auditlog, auditlogclass,
                               user_permission_groups_in_organization,
                               get_tyontekija_filters_for_taydennyskoulutus_groups,
                               user_has_vakajarjestaja_level_permission, is_oph_staff, parse_toimipaikka_id_list)
from varda.serializers import PaosToimipaikkaSerializer, PaosVakaJarjestajaSerializer
from varda.serializers_ui import (VakaJarjestajaUiSerializer, ToimipaikkaUiSerializer, UiLapsiSerializer,
                                  TyontekijaHenkiloUiSerializer, LapsihakuHenkiloUiSerializer,
                                  UiTyontekijaSerializer)


def parse_vakajarjestaja(user, vakajarjestaja_id):
    if not vakajarjestaja_id.isdigit():
        raise Http404
    vakajarjestaja_qs = VakaJarjestaja.objects.filter(pk=vakajarjestaja_id)
    if not vakajarjestaja_qs.exists() or not user.has_perm('view_vakajarjestaja', vakajarjestaja_qs.first()):
        raise Http404

    return vakajarjestaja_qs.first()


@auditlogclass
class UiVakajarjestajatViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda vakajarjestajien nimet
    """
    serializer_class = VakaJarjestajaUiSerializer
    queryset = VakaJarjestaja.objects.none()

    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_superuser:
            queryset = VakaJarjestaja.objects.all().order_by('nimi')
        else:
            model_name = 'vakajarjestaja'
            content_type = ContentType.objects.get(model=model_name)
            vakajarjestaja_ids = get_object_ids_user_has_permissions(user, model_name, content_type)
            queryset = VakaJarjestaja.objects.filter(id__in=vakajarjestaja_ids).order_by('nimi')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @auditlog
    @action(methods=['get'], detail=True, url_path='tyontekija-list', url_name='tyontekija_list',
            serializer_class=TyontekijaHenkiloUiSerializer,
            queryset=Henkilo.objects.all(),
            filter_backends=[SearchFilter, DjangoFilterBackend],
            pagination_class=ChangeablePageSizePagination,
            permission_classes=[HenkilostohakuPermissions],
            )
    @swagger_auto_schema(auto_schema=ActionPaginationSwaggerAutoSchema,
                         responses={status.HTTP_200_OK: TyontekijaHenkiloUiSerializer(many=True)})
    def tyontekija_list(self, request, pk=None):
        # Putting these to keyword arguments raises exception
        self.filterset_class = TyontekijahakuUiFilter
        self.search_fields = ['etunimet', 'sukunimi', '=henkilotunnus_unique_hash', '=henkilo_oid']
        user = request.user
        self.queryset = self.queryset.filter(tyontekijat__vakajarjestaja=pk).order_by('sukunimi', 'etunimet').distinct()
        if not user.is_superuser:
            organisaatio_oids = get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user)
            filter_condition = (Q(tyontekijat__vakajarjestaja__organisaatio_oid__in=organisaatio_oids) |
                                Q(tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid__in=organisaatio_oids))
            # user with tyontekija toimipaikka permissions might have object level permissions to tyontekijat without tyoskentelypaikka
            if get_toimipaikat_group_has_access(user, pk, 'HENKILOSTO_TYONTEKIJA_').exists():
                tyontekijat_object_level_permission = get_objects_for_user(user, 'view_tyontekija', klass=Tyontekija, accept_global_perms=False)
                filter_condition = filter_condition | Q(tyontekijat__in=tyontekijat_object_level_permission)
            self.queryset = self.queryset.filter(filter_condition)
        return super().list(request, pk=pk)

    @auditlog
    @action(methods=['get'], detail=True, url_path='lapsi-list', url_name='lapsi_list',
            serializer_class=LapsihakuHenkiloUiSerializer,
            queryset=Henkilo.objects.all(),
            filter_backends=[SearchFilter],
            pagination_class=ChangeablePageSizePagination,
            permission_classes=[LapsihakuPermissions],
            )
    @swagger_auto_schema(auto_schema=ActionPaginationSwaggerAutoSchema,
                         responses={status.HTTP_200_OK: LapsihakuHenkiloUiSerializer(many=True)})
    def lapsi_list(self, request, pk=None):
        """
        Query-parametrit:
            *  toimipaikka_id = int
            *  toimipaikka_oid = str
            *  voimassa_pvm = iso date string esim. "2020-01-01"
        """
        # Putting these to keyword arguments raises exception
        self.search_fields = ['etunimet', 'sukunimi', '=henkilotunnus_unique_hash', '=henkilo_oid']

        filter_condition = self.get_lapsi_list_filter_conditions(pk, request.query_params, 'lapsi__')
        self.queryset = self.queryset.filter(filter_condition).order_by('sukunimi', 'etunimet').distinct()
        return super().list(request, pk=pk)

    def _prefix_Q(self, prefix):
        def decorate_q(*args, **kwargs):
            prefixed_kwargs = {prefix + key: value for key, value in kwargs.items()}
            return Q(*args, **prefixed_kwargs)
        return decorate_q

    def get_lapsi_list_filter_conditions(self, vakajarjestaja_id, query_params, prefix='', permission_context=None):
        """
        This needs to be done manually since django-filter (or more precisely feature in django queryset filtering)
        chains qs.filter() which causes lapsi table to be joined multiple times to henkilo. Doing that makes these
        conditions OR isntead of AND causing weird results in paos cases where same lapsi can be found multiple times.
        https://code.djangoproject.com/ticket/18437
        :param vakajarjestaja_id: ID for Vakajarjestaja
        :param query_params:
        :param prefix: prefix for
        :param permission_context: Context
        :return: None
        """
        prefixed_Q = self._prefix_Q(prefix)
        # This is the condition that causes django filter not being useful here
        filter_condition = (prefixed_Q(vakatoimija=vakajarjestaja_id) |
                            prefixed_Q(oma_organisaatio=vakajarjestaja_id) |
                            prefixed_Q(paos_organisaatio=vakajarjestaja_id))
        if toimipaikka_id := query_params.get('toimipaikka_id'):
            filter_condition &= prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__id=toimipaikka_id)
        if toimipaikka_oid := query_params.get('toimipaikka_oid'):
            filter_condition &= prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid=toimipaikka_oid)
        if voimassa_pvm := query_params.get('voimassa_pvm'):
            filter_condition &= (prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm__lte=voimassa_pvm) &
                                 (prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__gte=voimassa_pvm) |
                                  prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True)))
        if not permission_context:
            permission_context = self._get_lapsi_permission_context()
        is_superuser, vakajarjestaja_oid, user_organisaatio_oids = itemgetter('is_superuser', 'vakajarjestaja_oid', 'user_organisaatio_oids')(permission_context)
        if not is_superuser and vakajarjestaja_oid not in user_organisaatio_oids:
            toimipaikka_oids = permission_context['toimipaikka_oids']
            # Check toimipaikka level. Since object level permissions for lapset without toimipaikka are not set
            # we don't check it here.
            filter_condition &= prefixed_Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid__in=toimipaikka_oids)
        return filter_condition

    def get_serializer_context(self):
        context = super(UiVakajarjestajatViewSet, self).get_serializer_context()
        if self.action == 'lapsi_list':
            context = {**context, **self._get_lapsi_permission_context()}
        return context

    def _get_lapsi_permission_context(self):
        context = {}
        user = self.request.user
        vakajarjestaja_pk = self.kwargs['pk']
        vakajarjestaja_oid = VakaJarjestaja.objects.filter(pk=vakajarjestaja_pk).values_list('organisaatio_oid', flat=True).first()
        group_name_prefixes = ['VARDA-TALLENTAJA_', 'VARDA-KATSELIJA_', 'HUOLTAJATIETO_']
        user_organisaatio_oids = [] if user.is_superuser else get_organisaatio_oids_from_groups(user, *group_name_prefixes)
        toimipaikka_oids = None
        if not user.is_superuser and vakajarjestaja_oid not in user_organisaatio_oids:
            toimipaikka_oids = get_toimipaikat_group_has_access(user, vakajarjestaja_pk, *group_name_prefixes).values_list('organisaatio_oid', flat=True)
        context.update({
            'is_superuser': user.is_superuser,
            'vakajarjestaja_oid': vakajarjestaja_oid,
            'user_organisaatio_oids': user_organisaatio_oids,
            'toimipaikka_oids': toimipaikka_oids,
        })
        return context


@auditlogclass
class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vakajärjestäjän kaikki toimipaikat.
    filter:
        voimassaolo=str (voimassa/paattynyt)
    """
    filter_backends = (DjangoFilterBackend, SearchFilter,)
    search_fields = ('nimi', '=organisaatio_oid', '=id',)
    filterset_class = filters.ToimipaikkaFilter
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaUiSerializer
    permission_classes = (CustomModelPermissions,)
    pagination_class = ChangeablePageSizePaginationLarge

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_obj = None
        self.vakajarjestaja_oid = ''

    def get_toimipaikka_ids_user_has_view_permissions(self):
        model_name = 'toimipaikka'
        content_type = ContentType.objects.get(model=model_name)
        return get_object_ids_user_has_permissions(self.request.user, model_name, content_type)

    def get_queryset(self):
        paos_toimipaikat = get_paos_toimipaikat(self.vakajarjestaja_obj, is_only_active_paostoiminta_included=False)
        qs_own_toimipaikat = Q(vakajarjestaja=self.vakajarjestaja_id)
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        toimipaikka_filter = qs_own_toimipaikat | qs_paos_toimipaikat

        # Filter toimipaikat based on permissions
        user = self.request.user
        has_vakajarjestaja_level_permission = user_has_vakajarjestaja_level_permission(user, self.vakajarjestaja_oid,
                                                                                       'view_toimipaikka')
        if not user.is_superuser and not has_vakajarjestaja_level_permission:
            # Get only toimipaikat user has object level permissions to
            toimipaikka_ids_user_has_view_permissions = self.get_toimipaikka_ids_user_has_view_permissions()
            toimipaikka_filter = toimipaikka_filter & Q(id__in=toimipaikka_ids_user_has_view_permissions)

        return (Toimipaikka.objects.filter(toimipaikka_filter)
                .values('id', 'nimi', 'organisaatio_oid', 'hallinnointijarjestelma', 'vakajarjestaja__id',
                        'vakajarjestaja__nimi', 'vakajarjestaja__organisaatio_oid',)
                .order_by('nimi'))

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'vakajarjestaja_pk': self.kwargs.get('vakajarjestaja_pk', None)
        }

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm('view_vakajarjestaja', vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm('view_toimipaikka', toimipaikka):
            return toimipaikka
        else:
            raise Http404

    def list(self, request, *args, **kwargs):
        self.vakajarjestaja_id = kwargs.get('vakajarjestaja_pk', None)
        if not self.vakajarjestaja_id.isdigit():
            raise Http404

        self.vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=self.vakajarjestaja_id)
        self.vakajarjestaja_oid = self.vakajarjestaja_obj.organisaatio_oid

        return super(NestedToimipaikkaViewSet, self).list(request, args, kwargs)

    @auditlog
    @action(methods=['get'], detail=True, url_path='paos-jarjestajat', url_name='paos_jarjestajat')
    @swagger_auto_schema(auto_schema=ActionPaginationSwaggerAutoSchema,
                         responses={status.HTTP_200_OK: VakaJarjestajaUiSerializer(many=True)})
    def paos_jarjestajat(self, request, vakajarjestaja_pk=None, pk=None):
        """
        Nouda vakajärjestäjän paos-järjestäjät annettuun toimipaikkaan

        Hakee ne paos toimintaa järjestävät kunnat joiden puolesta annettu toimija hoitaa tallennustehtäviä annettuun
        paos-toimipaikkaan.
        """
        vakajarjestaja = self.get_vakajarjestaja(request, vakajarjestaja_pk)
        toimipaikka = self.get_toimipaikka(request, pk)
        kunta_qs = PaosToiminta.objects.filter(paos_toimipaikka=toimipaikka,
                                               voimassa_kytkin=True).values_list('oma_organisaatio_id', flat=True)
        jarjestaja_id_qs = (PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio__in=kunta_qs,
                                                      tallentaja_organisaatio=vakajarjestaja,
                                                      voimassa_kytkin=True)
                            .values_list('jarjestaja_kunta_organisaatio', flat=True)
                            )
        jarjestaja_qs = VakaJarjestaja.objects.filter(id__in=jarjestaja_id_qs).order_by('id')
        page = self.paginate_queryset(jarjestaja_qs)
        serializer = VakaJarjestajaUiSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)


@auditlogclass
class NestedAllToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta varda pääkäyttäjille paos-toimipaikkojen hakuun (jm02 ja jm03).
    """
    queryset = Toimipaikka.objects.all()
    permission_classes = (IsVardaPaakayttaja, )
    serializer_class = PaosToimipaikkaSerializer
    filter_backends = (SearchFilter, )
    search_fields = ['nimi', 'nimi_sv']

    def list(self, request, *args, **kwargs):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit() or not get_object_or_404(VakaJarjestaja, pk=vakajarjestaja_id):
            raise Http404
        return super(NestedAllToimipaikkaViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit():
            vakajarjestaja_id = None
        # Return only paos toimipaikat
        return Toimipaikka.objects.filter(Q(vakajarjestaja__pk=vakajarjestaja_id) &
                                          ~Q(nimi__istartswith='Palveluseteli ja ostopalvelu ') &
                                          (Q(jarjestamismuoto_koodi__icontains='jm02') |
                                           Q(jarjestamismuoto_koodi__icontains='jm03'))).order_by('id')


@auditlogclass
class AllVakajarjestajaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta yksityisten ja kunnallisen toimijan tarvitsemien varhaiskasvatustoimijoiden hakuun.
    Query-parametrit:
    *  tyyppi = 'yksityinen' tai 'kunnallinen'
    *  search = str
    """
    queryset = VakaJarjestaja.objects.all().order_by('id')
    permission_classes = (IsVardaPaakayttaja, )
    serializer_class = PaosVakaJarjestajaSerializer
    filter_backends = (DjangoFilterBackend, )
    filterset_class = filters.UiAllVakajarjestajaFilter


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
    """
    filter_backends = (SearchFilter,)
    queryset = Lapsi.objects.none()
    search_fields = ('henkilo__etunimet',
                     'henkilo__sukunimi',
                     '=henkilo__henkilotunnus_unique_hash',
                     '=henkilo__henkilo_oid',
                     '=id',
                     '=tunniste',
                     '=varhaiskasvatuspaatokset__id',
                     '=varhaiskasvatuspaatokset__tunniste',
                     '=varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id',
                     '=varhaiskasvatuspaatokset__varhaiskasvatussuhteet__tunniste',
                     '=huoltajuussuhteet__maksutiedot__id',
                     '=huoltajuussuhteet__maksutiedot__tunniste')
    serializer_class = UiLapsiSerializer
    permission_classes = (CustomModelPermissions,)
    pagination_class = ChangeablePageSizePagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_oid = ''
        self.toimipaikka_id_list = []

    def get_lapsi_object_ids_user_has_view_permissions(self):
        model_name = 'lapsi'
        content_type = ContentType.objects.get(model=model_name)
        return get_object_ids_user_has_permissions(self.request.user, model_name, content_type)

    def apply_filters(self, vakasuhde_filter):
        query_params = self.request.query_params
        rajaus = query_params.get('rajaus', None)
        voimassaolo = query_params.get('voimassaolo', None)
        alkamis_pvm = query_params.get('alkamis_pvm', None)
        paattymis_pvm = query_params.get('paattymis_pvm', None)

        if not rajaus or not voimassaolo or not alkamis_pvm or not paattymis_pvm:
            return vakasuhde_filter

        rajaus = str.lower(rajaus)
        voimassaolo = str.lower(voimassaolo)

        try:
            alkamis_pvm = datetime.datetime.strptime(alkamis_pvm, '%Y-%m-%d').date()
            paattymis_pvm = datetime.datetime.strptime(paattymis_pvm, '%Y-%m-%d').date()
        except ValueError:
            raise Http404

        if rajaus == 'vakasuhteet':
            prefix = 'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__'
        elif rajaus == 'vakapaatokset':
            prefix = 'varhaiskasvatuspaatokset__'
        elif rajaus == 'maksutiedot':
            prefix = 'huoltajuussuhteet__maksutiedot__'
        else:
            return vakasuhde_filter

        if voimassaolo == 'alkanut':
            vakasuhde_filter = (vakasuhde_filter & Q(**{prefix + 'alkamis_pvm__gte': alkamis_pvm}) &
                                Q(**{prefix + 'alkamis_pvm__lte': paattymis_pvm}))
        elif voimassaolo == 'paattynyt':
            vakasuhde_filter = (vakasuhde_filter & Q(**{prefix + 'paattymis_pvm__gte': alkamis_pvm}) &
                                Q(**{prefix + 'paattymis_pvm__lte': paattymis_pvm}))
        elif voimassaolo == 'voimassa':
            # First set of brackets enables multiline so we need double for query: x and (y or z)
            vakasuhde_filter = (vakasuhde_filter & Q(**{prefix + 'alkamis_pvm__lte': alkamis_pvm}) &
                                ((Q(**{prefix + 'paattymis_pvm__gte': paattymis_pvm})) |
                                Q(**{prefix + 'paattymis_pvm__isnull': True})))

        return vakasuhde_filter

    def get_queryset(self):
        if len(self.toimipaikka_id_list) > 0:
            # If paos-lapsi, return only the ones that are linked to this vakajarjestaja
            lapsi_filter = (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__id__in=self.toimipaikka_id_list) &
                            (Q(oma_organisaatio=self.vakajarjestaja_id) | Q(paos_organisaatio=self.vakajarjestaja_id) |
                             Q(vakatoimija=self.vakajarjestaja_id)))
        else:
            lapsi_filter = (Q(vakatoimija=self.vakajarjestaja_id) | Q(oma_organisaatio=self.vakajarjestaja_id) |
                            Q(paos_organisaatio=self.vakajarjestaja_id))

        lapsi_organization_groups_qs = user_permission_groups_in_organization(self.request.user, self.vakajarjestaja_oid,
                                                                              [Z4_CasKayttoOikeudet.KATSELIJA,
                                                                               Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                               Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
                                                                               Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA])
        # Get all children for superuser and vakajarjestaja level permissions
        if not self.request.user.is_superuser and not lapsi_organization_groups_qs.exists():
            lapsi_object_ids_user_has_view_permissions = self.get_lapsi_object_ids_user_has_view_permissions()
            lapsi_filter = (lapsi_filter & Q(id__in=lapsi_object_ids_user_has_view_permissions))

        lapsi_filter = self.apply_filters(lapsi_filter)

        return Lapsi.objects.filter(lapsi_filter).order_by('henkilo__sukunimi', 'henkilo__etunimet')

    def get_lapset_in_toimipaikat_queryset(self):
        return (self.filter_queryset(self.get_queryset())
                .distinct('henkilo__sukunimi', 'henkilo__etunimet', 'id'))

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        user = request.user

        vakajarjestaja_obj = parse_vakajarjestaja(user, kwargs['vakajarjestaja_pk'])
        self.vakajarjestaja_id = vakajarjestaja_obj.id
        self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid

        required_permission_groups = (Z4_CasKayttoOikeudet.KATSELIJA, Z4_CasKayttoOikeudet.TALLENTAJA,
                                      Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA,
                                      Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,)
        self.toimipaikka_id_list = parse_toimipaikka_id_list(user, request.query_params.get('toimipaikat', ''),
                                                             required_permission_groups, include_paos=True)

        """
        We can differentiate results based on e.g. user-id, and this is needed since queryset
        can be different for one toimipaikka, depending on user permissions.
        """
        toimipaikka_cache_key = create_cache_key(user.id, request.get_full_path())
        queryset = cache.get(toimipaikka_cache_key)
        if queryset is None:
            # Set toimipaikan_lapset-cache for all request toimipaikat
            for toimipaikka_id in self.toimipaikka_id_list:
                key_for_list_of_all_toimipaikka_cache_keys = 'toimipaikan_lapset_' + toimipaikka_id
                list_of_all_toimipaikka_cache_keys = cache.get(key_for_list_of_all_toimipaikka_cache_keys)
                if list_of_all_toimipaikka_cache_keys is None:
                    list_of_all_toimipaikka_cache_keys = []
                if toimipaikka_cache_key not in list_of_all_toimipaikka_cache_keys:
                    list_of_all_toimipaikka_cache_keys.append(toimipaikka_cache_key)
                cache.set(key_for_list_of_all_toimipaikka_cache_keys, list_of_all_toimipaikka_cache_keys, 8 * 60 * 60)

            queryset = self.get_lapset_in_toimipaikat_queryset()
            cache.set(toimipaikka_cache_key, queryset, 8 * 60 * 60)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Pagination is disabled
        serializer = self.get_serializer(queryset.distinct(), many=True)
        return Response(serializer.data)


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
    filter_backends = (ExtraKwargsFilterBackend, SearchFilter,)
    filterset_class = filters.UiTyontekijaFilter
    search_fields = ('henkilo__etunimet',
                     'henkilo__sukunimi',
                     '=henkilo__henkilotunnus_unique_hash',
                     '=henkilo__henkilo_oid',
                     '=id',
                     '=tunniste',
                     '=palvelussuhteet__id',
                     '=palvelussuhteet__tunniste',
                     '=palvelussuhteet__tyoskentelypaikat__id',
                     '=palvelussuhteet__tyoskentelypaikat__tunniste',
                     '=palvelussuhteet__pidemmatpoissaolot__id',
                     '=palvelussuhteet__pidemmatpoissaolot__tunniste',
                     '=taydennyskoulutukset__id',
                     '=taydennyskoulutukset__tunniste')
    serializer_class = UiTyontekijaSerializer
    permission_classes = (HenkilostohakuPermissions,)
    queryset = Tyontekija.objects.none()
    pagination_class = ChangeablePageSizePagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_id = None
        self.vakajarjestaja_oid = ''
        self.has_vakajarjestaja_tyontekija_permissions = False

    def get_tyontekija_ids_user_has_view_permissions(self):
        model_name = 'tyontekija'
        content_type = ContentType.objects.get(model=model_name)
        return get_object_ids_user_has_permissions(self.request.user, model_name, content_type)

    def get_queryset(self):
        tyontekija_filter = Q(vakajarjestaja__id=self.vakajarjestaja_id)

        tyontekija_organization_groups_qs = user_permission_groups_in_organization(self.request.user, self.vakajarjestaja_oid,
                                                                                   [Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                                                                    Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA])

        user = self.request.user
        is_superuser_or_oph_staff = user.is_superuser or is_oph_staff(user)
        self.has_vakajarjestaja_tyontekija_permissions = is_superuser_or_oph_staff or tyontekija_organization_groups_qs.exists()

        taydennyskoulutus_organization_groups_qs = user_permission_groups_in_organization(self.request.user, self.vakajarjestaja_oid,
                                                                                          [Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                                                                                           Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA])

        # Get all tyontekijat for superuser, oph user, and vakajarjestaja level permissions
        if not self.has_vakajarjestaja_tyontekija_permissions and not taydennyskoulutus_organization_groups_qs.exists():
            # Get only tyontekijat user has object permissions to, or tyontekijat that belong to user's
            # taydennyskoulutus groups
            tyontekija_ids_user_has_view_permissions = self.get_tyontekija_ids_user_has_view_permissions()
            tyontekija_taydennyskoulutus_filters, organisaatio_oids = get_tyontekija_filters_for_taydennyskoulutus_groups(self.request.user)
            tyontekija_filter = (tyontekija_filter & (Q(id__in=tyontekija_ids_user_has_view_permissions) | tyontekija_taydennyskoulutus_filters))

        return Tyontekija.objects.filter(tyontekija_filter).order_by('henkilo__sukunimi', 'henkilo__etunimet')

    def get_filterset_kwargs(self):
        return {'has_vakajarjestaja_tyontekija_permissions': self.has_vakajarjestaja_tyontekija_permissions}

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        user = self.request.user

        vakajarjestaja_obj = parse_vakajarjestaja(user, kwargs['vakajarjestaja_pk'])
        self.vakajarjestaja_id = vakajarjestaja_obj.id
        self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid

        return super(UiNestedTyontekijaViewSet, self).list(request, args, kwargs)
