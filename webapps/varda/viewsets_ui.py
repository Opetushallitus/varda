from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q, F
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import get_objects_for_user
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.cache import create_cache_key, get_object_ids_user_has_permissions
from varda.cas.varda_permissions import IsVardaPaakayttaja
from varda.filters import TyontekijaUiFilter
from varda.lokalisointipalvelu import get_localisation_data
from varda.misc_queries import get_paos_toimipaikat
from varda.models import (Toimipaikka, VakaJarjestaja, Varhaiskasvatussuhde, PaosToiminta, PaosOikeus, Lapsi, Henkilo,
                          Tyontekija)
from varda.pagination import ChangeablePageSizePagination
from varda.permissions import (CustomObjectPermissions, save_audit_log,
                               get_taydennyskoulutus_tyontekija_group_organisaatio_oids,
                               is_toimipaikka_access_for_group)
from varda.serializers import PaosToimipaikkaSerializer, PaosVakaJarjestajaSerializer
from varda.serializers_ui import (VakaJarjestajaUiSerializer, ToimipaikkaUiSerializer, ToimipaikanLapsetUISerializer,
                                  TyontekijaUiSerializer)


class UiVakajarjestajatViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin):
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

    @action(methods=['get'], detail=True, url_path='tyontekija-list', url_name='tyontekija_list',
            serializer_class=TyontekijaUiSerializer,
            queryset=Henkilo.objects.all(),
            filter_backends=[SearchFilter, DjangoFilterBackend],
            pagination_class=ChangeablePageSizePagination
            )
    def tyontekija_list(self, request, pk=None):
        # Putting these to keyword arguments raises exception
        self.filterset_class = TyontekijaUiFilter
        self.search_fields = ['etunimet', 'sukunimi']
        user = request.user
        self.queryset = self.queryset.filter(tyontekijat__vakajarjestaja=pk).order_by('sukunimi', 'etunimet').distinct()
        if not user.is_superuser:
            organisaatio_oids = get_taydennyskoulutus_tyontekija_group_organisaatio_oids(user)
            filter_condition = (Q(tyontekijat__vakajarjestaja__organisaatio_oid__in=organisaatio_oids) |
                                Q(tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid__in=organisaatio_oids))
            # user with tyontekija toimipaikka permissions might have object level permissions to tyontekijat without tyoskentelypaikka
            if is_toimipaikka_access_for_group(user, pk, 'HENKILOSTO_TYONTEKIJA_'):
                tyontekijat_object_level_permission = get_objects_for_user(user, 'view_tyontekija', klass=Tyontekija, accept_global_perms=False)
                filter_condition = filter_condition | Q(tyontekijat__in=tyontekijat_object_level_permission)
            self.queryset = self.queryset.filter(filter_condition)
        return super().list(request, pk=pk)


class NestedToimipaikkaViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn vaka-järjestäjän kaikki toimipaikat. (dropdownia -varten)
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = None
    queryset = Toimipaikka.objects.none()
    serializer_class = ToimipaikkaUiSerializer
    permission_classes = (CustomObjectPermissions, )

    def get_serializer_context(self):
        """
        Extra context provided to the serializer class.
        """
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
            'vakajarjestaja_pk': self.kwargs['vakajarjestaja_pk']
        }

    def get_vakajarjestaja(self, request, vakajarjestaja_pk=None):
        vakajarjestaja = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_pk)
        user = request.user
        if user.has_perm("view_vakajarjestaja", vakajarjestaja):
            return vakajarjestaja
        else:
            raise Http404("Not found.")

    def get_toimipaikka(self, request, toimipaikka_pk=None):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=toimipaikka_pk)
        user = request.user
        if user.has_perm("view_toimipaikka", toimipaikka):
            return toimipaikka
        else:
            raise Http404("Not found.")

    def list(self, request, *args, **kwargs):
        if not kwargs['vakajarjestaja_pk'].isdigit():
            raise Http404("Not found.")

        vakajarjestaja_obj = self.get_vakajarjestaja(request, vakajarjestaja_pk=kwargs['vakajarjestaja_pk'])
        paos_toimipaikat = get_paos_toimipaikat(vakajarjestaja_obj, is_only_active_paostoiminta_included=False)
        qs_own_toimipaikat = Q(vakajarjestaja=kwargs['vakajarjestaja_pk'])
        qs_paos_toimipaikat = Q(id__in=paos_toimipaikat)
        qs_all_toimipaikat = (Toimipaikka
                              .objects
                              .filter(qs_own_toimipaikat | qs_paos_toimipaikat)
                              .values('id', 'nimi', 'organisaatio_oid', 'hallinnointijarjestelma', 'vakajarjestaja__id', 'vakajarjestaja__nimi')
                              .order_by('nimi'))

        save_audit_log(request.user, request.get_full_path())

        serializer = self.get_serializer(qs_all_toimipaikat, many=True)
        return Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='paos-jarjestajat', url_name='paos_jarjestajat')
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
            raise Http404("Not found.")
        return super(NestedAllToimipaikkaViewSet, self).list(request, *args, **kwargs)

    def get_queryset(self, **kwargs):
        vakajarjestaja_id = self.kwargs.get('vakajarjestaja_pk', None)
        if not vakajarjestaja_id or not vakajarjestaja_id.isdigit():
            vakajarjestaja_id = None
        # Return only paos toimipaikat
        return Toimipaikka.objects.filter(vakajarjestaja__pk=vakajarjestaja_id,
                                          jarjestamismuoto_koodi__overlap=['jm02', 'jm03']).order_by('id')


class AllVakajarjestajaViewSet(GenericViewSet, ListModelMixin):
    """
    Rajapinta yksityisten ja kunnallisen toimijan tarvitsemien varhaiskasvatustoimijoiden hakuun.
    Query-parametrit:
    *  tyyppi = 'yksityinen' tai 'kunnallinen'
    """
    queryset = VakaJarjestaja.objects.none()
    permission_classes = (IsVardaPaakayttaja, )
    serializer_class = PaosVakaJarjestajaSerializer
    filter_backends = (SearchFilter, )
    search_fields = ['nimi', '=postitoimipaikka', '=organisaatio_oid', '=y_tunnus']

    def get_queryset(self):
        queryset = VakaJarjestaja.objects.all()
        tyyppi = self.request.query_params.get('tyyppi', None)
        if tyyppi in ['yksityinen', 'kunnallinen']:
            condition = Q(yritysmuoto__in=VakaJarjestaja.get_kuntatyypit())
            queryset = queryset.filter(condition) if tyyppi == 'kunnallinen' else queryset.exclude(condition)
        return queryset.order_by('id')


class NestedToimipaikanLapsetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda tietyn toimipaikan lapset
    filter:
        Lapsia voi suodattaa etu- ja sukunimien, OID:n tai henkilötunnuksen mukaan, sekä varhaiskasvatussuhteen,
        varhaiskasvatuspäätöksen ja maksutietojen alkamis- ja päättymispäivämäärien perusteella

        Henkilötunnus täytyy olla SHA-256 hash heksadesimaalimuodossa (utf-8 enkoodatusta tekstistä)

        search=str (nimi/hetu/OID)
        rajaus=str (vakasuhteet/vakapaatokset/maksutiedot)
        voimassaolo=str (alkanut/paattynyt/voimassa)
        alkamis_pvm=YYYY-mm-dd
        paattymis_pvm=YYYY-mm-dd
    """
    filter_backends = (SearchFilter,)
    queryset = Lapsi.objects.none()
    # Same functionality as viewsets.HenkilohakuLapset
    search_fields = ('varhaiskasvatuspaatos__lapsi__henkilo__etunimet',
                     'varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                     '=varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus_unique_hash',
                     '=varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid',)
    serializer_class = ToimipaikanLapsetUISerializer
    permission_classes = (CustomObjectPermissions,)
    toimipaikka_pk = None

    def get_toimipaikka(self, request):
        toimipaikka = get_object_or_404(Toimipaikka.objects.all(), pk=self.toimipaikka_pk)
        user = request.user
        if not user.has_perm('view_toimipaikka', toimipaikka):
            raise Http404('Not found.')

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
            alkamis_pvm = datetime.strptime(alkamis_pvm, '%Y-%m-%d').date()
            paattymis_pvm = datetime.strptime(paattymis_pvm, '%Y-%m-%d').date()
        except ValueError as e:
            raise Http404(e)

        if rajaus == 'vakasuhteet':
            prefix = ''
        elif rajaus == 'vakapaatokset':
            prefix = 'varhaiskasvatuspaatos__'
        elif rajaus == 'maksutiedot':
            prefix = 'varhaiskasvatuspaatos__lapsi__huoltajuussuhteet__maksutiedot__'
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

    def get_vakasuhteet_in_toimipaikka_queryset(self):
        toimipaikka_filter = Q(toimipaikka__id=self.toimipaikka_pk)
        # Get all children for superuser
        if self.request.user.is_superuser:
            vakasuhde_filter = toimipaikka_filter
        else:
            lapsi_object_ids_user_has_view_permissions = self.get_lapsi_object_ids_user_has_view_permissions()
            vakasuhde_filter = (toimipaikka_filter &
                                Q(varhaiskasvatuspaatos__lapsi__id__in=lapsi_object_ids_user_has_view_permissions))

        vakasuhde_filter = self.apply_filters(vakasuhde_filter)

        return (Varhaiskasvatussuhde.objects
                .select_related('varhaiskasvatuspaatos__lapsi__henkilo').filter(vakasuhde_filter)
                .order_by('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                          'varhaiskasvatuspaatos__lapsi__henkilo__etunimet'))

    def get_vakapaatokset_in_toimipaikka_queryset(self):
        return (self.filter_queryset(self.get_vakasuhteet_in_toimipaikka_queryset())
                .values(etunimet=F('varhaiskasvatuspaatos__lapsi__henkilo__etunimet'),
                        sukunimi=F('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi'),
                        henkilo_oid=F('varhaiskasvatuspaatos__lapsi__henkilo__henkilo_oid'),
                        syntyma_pvm=F('varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm'),
                        oma_organisaatio_nimi=F('varhaiskasvatuspaatos__lapsi__oma_organisaatio__nimi'),
                        paos_organisaatio_nimi=F('varhaiskasvatuspaatos__lapsi__paos_organisaatio__nimi'),
                        lapsi_id=F('varhaiskasvatuspaatos__lapsi__id'))
                .distinct('varhaiskasvatuspaatos__lapsi__henkilo__sukunimi',
                          'varhaiskasvatuspaatos__lapsi__henkilo__etunimet',
                          'varhaiskasvatuspaatos__lapsi__id'))

    @transaction.atomic
    def list(self, request, *args, **kwargs):
        if not kwargs['toimipaikka_pk'].isdigit():
            raise Http404('Not found.')
        self.toimipaikka_pk = kwargs['toimipaikka_pk']
        self.get_toimipaikka(request)

        """
        We can differentiate results based on e.g. user-id, and this is needed since queryset
        can be different for one toimipaikka, depending on user permissions.
        """
        user_id = self.request.user.id
        toimipaikka_cache_key = create_cache_key(user_id, request.get_full_path())
        queryset = cache.get(toimipaikka_cache_key)
        if queryset is None:

            key_for_list_of_all_toimipaikka_cache_keys = 'toimipaikan_lapset_' + self.toimipaikka_pk
            list_of_all_toimipaikka_cache_keys = cache.get(key_for_list_of_all_toimipaikka_cache_keys)
            if list_of_all_toimipaikka_cache_keys is None:
                list_of_all_toimipaikka_cache_keys = []
            if toimipaikka_cache_key not in list_of_all_toimipaikka_cache_keys:
                list_of_all_toimipaikka_cache_keys.append(toimipaikka_cache_key)
            cache.set(key_for_list_of_all_toimipaikka_cache_keys, list_of_all_toimipaikka_cache_keys, 8 * 60 * 60)

            save_audit_log(request.user, request.get_full_path())
            queryset = self.get_vakapaatokset_in_toimipaikka_queryset()
            cache.set(toimipaikka_cache_key, queryset, 8 * 60 * 60)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        # Pagination is disabled
        serializer = self.get_serializer(queryset.distinct(), many=True)
        return Response(serializer.data)


class LocalisationViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Get localisations from lokalisointipalvelu for given category and locale

        parameters:
            category=string (required)
            locale=string
    """
    def get_queryset(self):
        return None

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        category = query_params.get('category', None)
        locale = query_params.get('locale', None)

        if not category:
            raise ValidationError({'category': ['category url parameter is required']})

        data = get_localisation_data(category, locale)

        if not data:
            return Response(status=500)

        return Response(data)
