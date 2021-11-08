import datetime
import logging
from wsgiref.util import FileWrapper

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.aggregates import StringAgg, ArrayAgg
from django.db import transaction
from django.db.models import (Q, Case, Value, When, OuterRef, Subquery, CharField, F, DateField, Count, IntegerField,
                              Exists, FloatField, Sum)
from django.db.models.functions import Cast
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.koodistot import Koodistot
from varda.enums.supported_language import SupportedLanguage
from varda.enums.ytj import YtjYritysmuoto
from varda.excel_export import (generate_filename, get_excel_local_file_path, ExcelReportStatus,
                                create_excel_report_task, ExcelReportType)
from varda.filters import (TiedonsiirtoFilter, ExcelReportFilter, KelaEtuusmaksatusFilter,
                           CustomParametersFilterBackend, CustomParameter, TransferOutageReportFilter,
                           RequestSummaryFilter)
from varda.misc import encrypt_string
from varda.validators import validate_kela_api_datetimefield
from varda.misc_viewsets import IntegerIdSchema
from varda.models import (KieliPainotus, Lapsi, Maksutieto, PaosOikeus, ToiminnallinenPainotus, Toimipaikka,
                          VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z6_RequestLog,
                          Z4_CasKayttoOikeudet, Tyontekija, Z8_ExcelReport, PaosToiminta, Z2_Code, Z6_LastRequest,
                          Tyoskentelypaikka, Palvelussuhde, Z6_RequestSummary)
from varda.pagination import (ChangeablePageSizePagination, IdCursorPagination, DateCursorPagination,
                              DateReverseCursorPagination, IdReverseCursorPagination,
                              ChangeableReportingPageSizePagination)
from varda.permissions import (user_permission_groups_in_organization, is_oph_staff, ReadAdminOrOPHUser, auditlogclass,
                               get_vakajarjestajat_filter_for_raportit, RaportitPermissions, IsCertificateAccess)
from varda.serializers_reporting import (KelaEtuusmaksatusAloittaneetSerializer, KelaEtuusmaksatusLopettaneetSerializer,
                                         KelaEtuusmaksatusMaaraaikaisetSerializer,
                                         KelaEtuusmaksatusKorjaustiedotSerializer,
                                         KelaEtuusmaksatusKorjaustiedotPoistetutSerializer,
                                         TiedonsiirtotilastoSerializer, ErrorReportLapsetSerializer,
                                         ErrorReportTyontekijatSerializer, TiedonsiirtoSerializer,
                                         TiedonsiirtoYhteenvetoSerializer, ExcelReportSerializer,
                                         DuplicateLapsiSerializer, ErrorReportToimipaikatSerializer,
                                         LahdejarjestelmaTransferOutageReportSerializer,
                                         UserTransferOutageReportSerializer, RequestSummarySerializer,
                                         RequestSummaryGroupSerializer)


logger = logging.getLogger(__name__)


@auditlogclass
class KelaEtuusmaksatusAloittaneetViewset(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat aloittaneet varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: Change the amount of query results per page
        luonti_pvm_gte: Fetch created data after given luonti_pvm_gte
        luonti_pvm_lte: fetch created data from a time window with luonti_pvm_gte
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = KelaEtuusmaksatusFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = KelaEtuusmaksatusAloittaneetSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, luonti_pvm_gte, luonti_pvm_lte):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        luonti_pvm_filter = Q(luonti_pvm__gte=luonti_pvm_gte)

        if luonti_pvm_lte:
            luonti_pvm_filter = luonti_pvm_filter & Q(luonti_pvm__lte=luonti_pvm_lte)

        # paattymis_pvm must be none, vakapaatokset with end date are reported separately
        paattymis_pvm_filter = Q(paattymis_pvm=None)

        return (luonti_pvm_filter &
                common_filters &
                paattymis_pvm_filter)

    def get_queryset(self):
        now = datetime.datetime.now().astimezone()
        luonti_pvm_gte = self.request.query_params.get('luonti_pvm_gte', None)
        luonti_pvm_lte = self.request.query_params.get('luonti_pvm_lte', None)

        if luonti_pvm_lte:
            if not luonti_pvm_gte:
                raise ValidationError({'luonti_pvm_gte': [ErrorMessages.GE021.value]})
            luonti_pvm_gte = validate_kela_api_datetimefield(luonti_pvm_gte, now, 'luonti_pvm_gte')
            luonti_pvm_lte = validate_kela_api_datetimefield(luonti_pvm_lte, now, 'luonti_pvm_lte')
            if luonti_pvm_lte < luonti_pvm_gte:
                raise ValidationError({'luonti_pvm_lte': [ErrorMessages.GE022.value]})
        else:
            luonti_pvm_gte = validate_kela_api_datetimefield(luonti_pvm_gte, now, 'luonti_pvm_gte')

        dataset_filters = self.create_filters_for_data(luonti_pvm_gte, luonti_pvm_lte)

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .filter(dataset_filters)
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'alkamis_pvm').distinct('id'))


@auditlogclass
class KelaEtuusmaksatusLopettaneetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat lopettaneet varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: Change amount of search results per page
        muutos_pvm_gte: Fetch added end date data after given muutos_pvm_gte
        muutos_pvm_lte: Fetch added end date data from a time window with muutos_pvm_gte
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = KelaEtuusmaksatusFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = KelaEtuusmaksatusLopettaneetSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, muutos_pvm_gte, muutos_pvm_lte):
        common_filters = _create_common_kela_filters()

        muutos_pvm_filter = Q(muutos_pvm__gte=muutos_pvm_gte)
        if muutos_pvm_lte:
            muutos_pvm_filter = muutos_pvm_filter & Q(muutos_pvm__lte=muutos_pvm_lte)

        return common_filters & muutos_pvm_filter

    def get_queryset(self):
        now = datetime.datetime.now().astimezone()

        muutos_pvm_gte = self.request.query_params.get('muutos_pvm_gte', None)
        muutos_pvm_lte = self.request.query_params.get('muutos_pvm_lte', None)

        if muutos_pvm_lte:
            if not muutos_pvm_gte:
                raise ValidationError({'muutos_pvm_gte': [ErrorMessages.GE021.value]})
            muutos_pvm_gte = validate_kela_api_datetimefield(muutos_pvm_gte, now, 'muutos_pvm_gte')
            muutos_pvm_lte = validate_kela_api_datetimefield(muutos_pvm_lte, now, 'muutos_pvm_lte')
            if muutos_pvm_lte < muutos_pvm_gte:
                raise ValidationError({'muutos_pvm_lte': [ErrorMessages.GE022.value]})
        else:
            muutos_pvm_gte = validate_kela_api_datetimefield(muutos_pvm_gte, now, 'muutos_pvm_gte')

        dataset_filters = self.create_filters_for_data(muutos_pvm_gte, muutos_pvm_lte)

        # get the status before muutos_pvm
        latest_end_dates = (Varhaiskasvatussuhde.history.filter(Q(id=OuterRef('id')) &
                                                                Q(history_date__lt=muutos_pvm_gte)
                                                                ).order_by('-history_id'))

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'lapsi__henkilo')
                                            .annotate(last_paattymis_pvm=Case(When(Exists(latest_end_dates),
                                                                                   then=Subquery(latest_end_dates.values('paattymis_pvm')[:1])),
                                                                              default=Cast(Value('0001-01-01'), output_field=DateField()),
                                                                              output_field=DateField()))
                                            .filter(dataset_filters &
                                                    Q(last_paattymis_pvm__isnull=True) &
                                                    Q(paattymis_pvm__isnull=False))
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'paattymis_pvm').distinct('id'))


@auditlogclass
class KelaEtuusmaksatusMaaraaikaisetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat aloittaneet määräaikaisessa varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: Change amount of results per page of response
        luonti_pvm_gte: Fetch created data after given luonti_pvm_gte
        luonti_pvm_lte: Fetch created data from a time window with luonti_pvm_gte
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = KelaEtuusmaksatusFilter
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusMaaraaikaisetSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, luonti_pvm_gte, luonti_pvm_lte):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        luonti_pvm_filter = Q(luonti_pvm__gte=luonti_pvm_gte)
        if luonti_pvm_lte:
            luonti_pvm_filter = luonti_pvm_filter & Q(luonti_pvm__lte=luonti_pvm_lte)

        # maaraaikainen must always have an end date and be active after
        paattymis_pvm_date_gte = datetime.datetime(2021, 1, 18)
        paattymis_pvm_filter = Q(paattymis_pvm__gte=paattymis_pvm_date_gte)

        return (luonti_pvm_filter &
                common_filters &
                paattymis_pvm_filter)

    def get_queryset(self):
        now = datetime.datetime.now().astimezone()
        luonti_pvm_gte = self.request.query_params.get('luonti_pvm_gte', None)
        luonti_pvm_lte = self.request.query_params.get('luonti_pvm_lte', None)

        if luonti_pvm_lte:
            if not luonti_pvm_gte:
                raise ValidationError({'luonti_pvm_gte': [ErrorMessages.GE021.value]})
            luonti_pvm_gte = validate_kela_api_datetimefield(luonti_pvm_gte, now, 'luonti_pvm_gte')
            luonti_pvm_lte = validate_kela_api_datetimefield(luonti_pvm_lte, now, 'luonti_pvm_lte')
            if luonti_pvm_lte < luonti_pvm_gte:
                raise ValidationError({'luonti_pvm_lte': [ErrorMessages.GE022.value]})
        else:
            luonti_pvm_gte = validate_kela_api_datetimefield(luonti_pvm_gte, now, 'luonti_pvm_gte')

        dataset_filters = self.create_filters_for_data(luonti_pvm_gte, luonti_pvm_lte)

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .filter(dataset_filters)
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'alkamis_pvm', 'paattymis_pvm')
                                            .distinct('id'))


@auditlogclass
class KelaEtuusmaksatusKorjaustiedotViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset joiden tietoihin on tullut muutoksia viimeisen viikon sisällä.

    params:
        page_size: Change the number of query results per page
        muutos_pvm_gte: Fetch changed data after given muutos_pvm_gte
        muutos_pvm_lte: Fetch changed data from a time window with muutos_pvm_gte
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = KelaEtuusmaksatusFilter
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusKorjaustiedotSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, muutos_pvm_gte, muutos_pvm_lte):
        common_filters = _create_common_kela_filters()

        # Only object that have been changed after given date
        time_window_filter = Q(history_date__gte=muutos_pvm_gte)
        if muutos_pvm_lte:
            time_window_filter = time_window_filter & Q(history_date__lte=muutos_pvm_lte)

        # Must be active at or after
        paattymis_pvm_date_gte = datetime.datetime(2021, 1, 18)
        paattymis_pvm_filter = (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=paattymis_pvm_date_gte))

        history_type_filter = Q(history_type='~')

        return (time_window_filter &
                paattymis_pvm_filter &
                history_type_filter &
                common_filters)

    def get_queryset(self):
        now = datetime.datetime.now().astimezone()
        muutos_pvm_gte = self.request.query_params.get('muutos_pvm_gte', None)
        muutos_pvm_lte = self.request.query_params.get('muutos_pvm_lte', None)

        if muutos_pvm_lte:
            if not muutos_pvm_gte:
                raise ValidationError({'muutos_pvm_gte': [ErrorMessages.GE021.value]})
            muutos_pvm_gte = validate_kela_api_datetimefield(muutos_pvm_gte, now, 'muutos_pvm_gte')
            muutos_pvm_lte = validate_kela_api_datetimefield(muutos_pvm_lte, now, 'muutos_pvm_lte')
            if muutos_pvm_lte < muutos_pvm_gte:
                raise ValidationError({'muutos_pvm_lte': [ErrorMessages.GE022.value]})
        else:
            muutos_pvm_gte = validate_kela_api_datetimefield(muutos_pvm_gte, now, 'muutos_pvm_gte')

        dataset_filters = self.create_filters_for_data(muutos_pvm_gte, muutos_pvm_lte)

        latest_changed_objects = Varhaiskasvatussuhde.history.filter(dataset_filters)
        id_filter = Q(id__in=latest_changed_objects.values('id'))

        muutos_pvm_subquery = Varhaiskasvatussuhde.history.filter(id=OuterRef('id'), history_date__lt=muutos_pvm_gte).order_by('-history_id')

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .annotate(old_alkamis_pvm=(Case(When(alkamis_pvm=Subquery(muutos_pvm_subquery.values('alkamis_pvm')[:1]),
                                                                                 then=Cast(Value('0001-01-01'), output_field=DateField())),
                                                                            default=Subquery(muutos_pvm_subquery.values('alkamis_pvm')[:1]),
                                                                            output_field=DateField())),
                                                      old_paattymis_pvm=(Case(When(paattymis_pvm=Subquery(muutos_pvm_subquery.values('paattymis_pvm')[:1]),
                                                                                   then=Cast(Value('0001-01-01'), output_field=DateField())),
                                                                              default=Subquery(muutos_pvm_subquery.values('paattymis_pvm')[:1]),
                                                                              output_field=DateField()))
                                                      )
                                            .filter(id_filter &
                                                    ~Q(Q(old_alkamis_pvm='0001-01-01') & Q(old_paattymis_pvm='0001-01-01')) &
                                                    ~Q(Q(old_alkamis_pvm='0001-01-01') & Q(old_paattymis_pvm__isnull=True)))
                                            .values('id', 'varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'old_alkamis_pvm', 'old_paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'alkamis_pvm')
                                            .distinct('id'))


@auditlogclass
class KelaEtuusmaksatusKorjaustiedotPoistetutViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset joiden on poistettu viimeisen viikon sisällä.

    params:
        page_size: Change the amount of query results per page
        poisto_pvm_gte: Fetch removed data after given poisto_pvm
        poisto_pvm_lte: Fetch removed data from a time window with poisto_pvm_gte
    """
    filter_backends = (DjangoFilterBackend,)
    filterset_class = None  # This api cannot use filters because of raw query
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusKorjaustiedotPoistetutSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

    def get_queryset(self):
        now = datetime.datetime.now().astimezone()
        poisto_pvm_gte = self.request.query_params.get('poisto_pvm_gte', None)
        poisto_pvm_lte = self.request.query_params.get('poisto_pvm_lte', None)

        if poisto_pvm_lte:
            if not poisto_pvm_gte:
                raise ValidationError({'poisto_pvm_gte': [ErrorMessages.GE021.value]})
            poisto_pvm_gte = validate_kela_api_datetimefield(poisto_pvm_gte, now, 'poisto_pvm_gte')
            poisto_pvm_lte = validate_kela_api_datetimefield(poisto_pvm_lte, now, 'muutos_pvm_lte')
            if poisto_pvm_lte < poisto_pvm_gte:
                raise ValidationError({'poisto_pvm_lte': [ErrorMessages.GE022.value]})
        else:
            poisto_pvm_lte = now
            poisto_pvm_gte = validate_kela_api_datetimefield(poisto_pvm_gte, now, 'poisto_pvm_gte')

        return (Varhaiskasvatussuhde.history.raw("""select DISTINCT ON (vas.id) vas.id, vas.history_id as history_id, vas.alkamis_pvm as alkamis_pvm, vas.paattymis_pvm as paattymis_pvm,
                                                    '0001-01-01' as new_alkamis_pvm, '0001-01-01' as new_paattymis_pvm, he.henkilotunnus as henkilotunnus, he.kotikunta_koodi as kotikunta_koodi
                                                    from varda_historicalvarhaiskasvatussuhde vas
                                                    join (select id, muutos_pvm from varda_historicalvarhaiskasvatussuhde where history_type='+') luonti on luonti.id = vas.id
                                                    join (select DISTINCT ON (id) id, lapsi_id from varda_historicalvarhaiskasvatuspaatos
                                                          where lower(jarjestamismuoto_koodi) in ('jm01', 'jm02', 'jm03') and
                                                          tilapainen_vaka_kytkin='f' and luonti_pvm >= '2021-01-04' order by id) vap on vap.id = vas.varhaiskasvatuspaatos_id
                                                    join (select DISTINCT ON (id) id, henkilo_id from varda_historicallapsi order by id) la on la.id = vap.lapsi_id
                                                    join (select DISTINCT ON (id) id, henkilotunnus, kotikunta_koodi from varda_henkilo where henkilotunnus <> '' order by id) he on he.id = la.henkilo_id
                                                    where vas.history_date >= %s and vas.history_date <= %s and vas.history_type = '-' and (vas.paattymis_pvm is null or vas.paattymis_pvm >= '2021-01-18') and
                                                    vas.muutos_pvm > (luonti.muutos_pvm + interval '10 seconds') order by vas.id""", [poisto_pvm_gte, poisto_pvm_lte]))


def _create_common_kela_filters():
    # Making changes here does not affect filters on poistetut, if you update these check if you need
    # to update poistetut as well

    # Kunnallinen
    jarjestamismuoto_filter = (Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM01') |
                               Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM02') |
                               Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM03'))

    # Tilapäinen varhaiskasvatus
    tilapainen_vaka_filter = Q(varhaiskasvatuspaatos__tilapainen_vaka_kytkin=False)

    # Date from which data is transfered
    luonti_pvm_date = datetime.date(2021, 1, 4)
    luonti_pvm_filter = Q(varhaiskasvatuspaatos__luonti_pvm__date__gte=luonti_pvm_date)

    # Only henkilo with hetu
    hetu_filter = ~Q(varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus__exact='')

    return jarjestamismuoto_filter & luonti_pvm_filter & tilapainen_vaka_filter & hetu_filter


@auditlogclass
class TiedonsiirtotilastoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Nouda raportti tiedonsiirtojen tilanteesta (toimijat, toimipaikat, lapset, päätökset, suhteet, maksutiedot,
        kielipainotukset ja toiminnalliset painotukset) eroteltuna kunnallisesti ja yksityisesti

    filter:
        "kunnat" palauttaa tiedot kunnallisesta (true), yksityisestä varhaiskasvatuksesta (false)
        "voimassa" palauttaa voimassa olevat varhaiskasvatustiedot (alkamis_pvm < now < paattymis_pvm)
        Ilman filttereitä palautetaan tiedot kaikesta varhaiskasvatuksesta

        kunnat=true/false
        voimassa=true
    """
    queryset = None
    serializer_class = TiedonsiirtotilastoSerializer
    permission_classes = (permissions.IsAdminUser, )

    def get_vakatoimijat(self, kunnat_filter, voimassa_filter):
        kunnallinen = [YtjYritysmuoto.KUNTA.name, YtjYritysmuoto.KUNTAYHTYMA.name]
        if kunnat_filter is None:
            return VakaJarjestaja.objects.filter(voimassa_filter)
        elif kunnat_filter:
            return VakaJarjestaja.objects.filter(voimassa_filter & Q(yritysmuoto__in=kunnallinen))
        else:
            return VakaJarjestaja.objects.filter(voimassa_filter & ~Q(yritysmuoto__in=kunnallinen))

    def get_toimipaikat(self, vakatoimijat, voimassa_filter):
        return Toimipaikka.objects.filter(voimassa_filter & Q(vakajarjestaja__in=vakatoimijat))

    # Don't include so called dummy-toimipaikat
    def get_toimipaikat_ei_dummy_paos(self, vakatoimijat, voimassa_filter):
        return Toimipaikka.objects.filter(voimassa_filter & ~Q(nimi__icontains='Palveluseteli ja ostopalvelu') &
                                          Q(vakajarjestaja__in=vakatoimijat))

    def get_vakasuhteet(self, toimipaikat, voimassa_filter):
        return Varhaiskasvatussuhde.objects.filter(voimassa_filter & Q(toimipaikka__in=toimipaikat))

    def get_vakapaatokset(self, vakasuhteet, voimassa_filter, kunnat_filter):
        if kunnat_filter is None:
            vakapaatos_filter = voimassa_filter
        else:
            vakapaatos_id_list = vakasuhteet.values_list('varhaiskasvatuspaatos', flat=True)
            vakapaatos_filter = voimassa_filter & Q(id__in=vakapaatos_id_list)
        return Varhaiskasvatuspaatos.objects.filter(vakapaatos_filter)

    def get_lapset(self, vakapaatokset):
        lapsi_id_list = vakapaatokset.values_list('lapsi', flat=True)
        return Lapsi.objects.filter(id__in=lapsi_id_list).distinct('henkilo__henkilo_oid')

    def get_maksutiedot(self, kunnat_filter, voimassa_filter):
        if kunnat_filter is None:
            return Maksutieto.objects.filter(voimassa_filter)
        elif kunnat_filter:
            return Maksutieto.objects.filter(voimassa_filter & Q(yksityinen_jarjestaja=False))
        else:
            return Maksutieto.objects.filter(voimassa_filter & Q(yksityinen_jarjestaja=True))

    def get_kielipainotukset(self, toimipaikat, voimassa_filter):
        return KieliPainotus.objects.filter(voimassa_filter & Q(toimipaikka__in=toimipaikat))

    def get_toiminnalliset_painotukset(self, toimipaikat, voimassa_filter):
        return ToiminnallinenPainotus.objects.filter(voimassa_filter & Q(toimipaikka__in=toimipaikat))

    def get_paos_oikeudet(self, voimassa_filter):
        if voimassa_filter != Q():
            return PaosOikeus.objects.filter(voimassa_kytkin=True)
        else:
            return PaosOikeus.objects.all()

    def validate_boolean_parameter(self, parameter):
        if isinstance(parameter, str):
            parameter = parameter.lower()

        if parameter == 'true':
            return True
        elif parameter == 'false':
            return False
        else:
            return None

    def list(self, request, *args, **kwargs):
        query_params = self.request.query_params
        kunnat_filter = self.validate_boolean_parameter(query_params.get('kunnat', None))
        if self.validate_boolean_parameter(query_params.get('voimassa', None)):
            today = datetime.date.today()
            voimassa_filter = Q(alkamis_pvm__lte=today) & (Q(paattymis_pvm__gte=today) | Q(paattymis_pvm=None))
        else:
            voimassa_filter = Q()

        vakatoimijat = self.get_vakatoimijat(kunnat_filter, voimassa_filter)
        toimipaikat = self.get_toimipaikat(vakatoimijat, voimassa_filter)
        vakasuhteet = self.get_vakasuhteet(toimipaikat, voimassa_filter)
        vakapaatokset = self.get_vakapaatokset(vakasuhteet, voimassa_filter, kunnat_filter)

        stats = {
            'vakatoimijat': vakatoimijat.count(),
            'toimipaikat': self.get_toimipaikat_ei_dummy_paos(vakatoimijat, voimassa_filter).count(),
            'vakasuhteet': vakasuhteet.count(),
            'vakapaatokset': vakapaatokset.count(),
            'lapset': self.get_lapset(vakapaatokset).count(),
            'maksutiedot': self.get_maksutiedot(kunnat_filter, voimassa_filter).count(),
            'kielipainotukset': self.get_kielipainotukset(toimipaikat, voimassa_filter).count(),
            'toiminnalliset_painotukset': self.get_toiminnalliset_painotukset(toimipaikat, voimassa_filter).count(),
            'paos_oikeudet': None
        }

        if kunnat_filter is None:
            stats['paos_oikeudet'] = self.get_paos_oikeudet(voimassa_filter).count()

        serializer = self.get_serializer(stats)
        return Response(serializer.data)


class AbstractErrorReportViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    Return a list of Lapsi/Tyontekija objects whose data is not completely correct.
    Rules are defined in get_error_tuples function.

    search=str (nimi/hetu (SHA-256 hash as hexadecimal)/OID)
    """
    filter_backends = (SearchFilter, )
    pagination_class = ChangeablePageSizePagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_oid = None
        self.vakajarjestaja_id = None

    @property
    def search_fields(self):
        if self.queryset.model in (Lapsi, Tyontekija,):
            return ('henkilo__etunimet', 'henkilo__sukunimi', '=henkilo__henkilotunnus_unique_hash',
                    '=henkilo__henkilo_oid', '=id',)
        elif self.queryset.model == Toimipaikka:
            return 'nimi', '=organisaatio_oid', '=id'
        return ()

    def get_annotation_for_filter(self, filter_object, id_lookup):
        return StringAgg(Case(When(filter_object, then=Cast(id_lookup, CharField()))), delimiter=',')

    def get_annotations(self):
        """
        Desired errors can be filtered with error URL parameter
        (e.g. /api/v1/vakajarjestajat/1/error-report-tyontekijat/?error=TA006)
        """
        error_search_term = self.request.query_params.get('error', None)
        return {error_key.value['error_code']: error_tuple[0]
                for error_key, error_tuple in self.get_error_tuples().items()
                if not error_search_term or error_search_term.lower() in error_key.value['error_code'].lower()}

    def get_include_filter(self, annotations):
        if not annotations:
            # No matching annotations found using search, do not return any results
            return Q(id=None)

        include_filter = Q()
        for error_name in annotations:
            include_filter = include_filter | ~Q(**{error_name: None})
        return include_filter

    def get_vakajarjestaja_object(self, vakajarjestaja_id):
        vakajarjestaja_obj = get_object_or_404(VakaJarjestaja.objects.all(), pk=vakajarjestaja_id)
        if self.request.user.has_perm('view_vakajarjestaja', vakajarjestaja_obj):
            self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid
            self.vakajarjestaja_id = vakajarjestaja_id
        else:
            raise Http404()

    def list(self, request, *args, **kwargs):
        self.get_vakajarjestaja_object(kwargs.get('vakajarjestaja_pk', None))
        self.verify_permissions()
        return super(AbstractErrorReportViewSet, self).list(request, *args, **kwargs)

    def get_error_tuples(self):
        """
        Returns a dict of tuples e.g. 'error_key': (error_annotation, model_name)
        error_key is ErrorMessages enum value, which is used to identify the specific error
        error_annotation is used in the queryset, model_name is used in the serializer
        :return: dict of error tuples
        """
        raise NotImplementedError('get_error_tuples')

    def verify_permissions(self):
        """
        Verifies that user has correct permissions to view this information.
        """
        raise NotImplementedError('verify_permissions')

    def get_queryset(self):
        raise NotImplementedError('get_queryset')


@auditlogclass
class ErrorReportLapsetViewSet(AbstractErrorReportViewSet):
    serializer_class = ErrorReportLapsetSerializer
    queryset = Lapsi.objects.none()
    swagger_schema = IntegerIdSchema
    swagger_path_model = VakaJarjestaja

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_vakatiedot_permissions = False
        self.is_huoltajatiedot_permissions = False

    def verify_permissions(self):
        user = self.request.user

        valid_permission_groups_vakatiedot = [Z4_CasKayttoOikeudet.PAAKAYTTAJA, Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                                              Z4_CasKayttoOikeudet.TALLENTAJA, Z4_CasKayttoOikeudet.KATSELIJA]
        user_group_vakatiedot_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                                          valid_permission_groups_vakatiedot)
        self.is_vakatiedot_permissions = user.is_superuser or user_group_vakatiedot_qs.exists()

        valid_permission_groups_huoltajatiedot = [Z4_CasKayttoOikeudet.PAAKAYTTAJA,
                                                  Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                                                  Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
                                                  Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA]
        user_group_huoltajatiedot_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                                              valid_permission_groups_huoltajatiedot)
        self.is_huoltajatiedot_permissions = user.is_superuser or user_group_huoltajatiedot_qs.exists()

        if not self.is_vakatiedot_permissions and not self.is_huoltajatiedot_permissions:
            raise Http404()

    def get_error_tuples(self):
        today = datetime.date.today()
        overage_date = today - relativedelta(years=8)

        vakatiedot_error_tuples = {
            ErrorMessages.VP002: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__alkamis_pvm__gt=F('varhaiskasvatuspaatokset__varhaiskasvatussuhteet__alkamis_pvm')),
                    'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id'
                ),
                Varhaiskasvatussuhde.__name__.lower()
            ),
            ErrorMessages.VP003: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__paattymis_pvm__lt=F('varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm')),
                    'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id'
                ),
                Varhaiskasvatussuhde.__name__.lower()
            ),
            ErrorMessages.VS012: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__paattymis_pvm__isnull=False) &
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=False) &
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True),
                    'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id'
                ),
                Varhaiskasvatussuhde.__name__.lower()
            ),
            ErrorMessages.VP012: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__isnull=True),
                    'id'
                ),
                Lapsi.__name__.lower()
            ),
            ErrorMessages.VS014: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__isnull=False) &
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__isnull=True),
                    'varhaiskasvatuspaatokset__id'
                ),
                Varhaiskasvatuspaatos.__name__.lower()
            ),
            ErrorMessages.VP013: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__paattymis_pvm__isnull=True) &
                    Q(henkilo__syntyma_pvm__lt=overage_date),
                    'varhaiskasvatuspaatokset__id'
                ),
                Varhaiskasvatuspaatos.__name__.lower()
            ),
            ErrorMessages.VS015: (
                self.get_annotation_for_filter(
                    Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__paattymis_pvm__lt=F('varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm')) |
                    (Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__paattymis_pvm__lt=today) &
                     Q(varhaiskasvatuspaatokset__varhaiskasvatussuhteet__paattymis_pvm__isnull=True)),
                    'varhaiskasvatuspaatokset__varhaiskasvatussuhteet__id'
                ),
                Varhaiskasvatussuhde.__name__.lower()
            )
        }

        # Do not get Maksutieto related errors for Lapsi objects for which vakajarjestaja is paos_organisaatio
        huoltajatiedot_error_tuples = {
            # Use Subquery to check that Lapsi is not in a list of Lapsi objects that have active varhaiskasvatuspaatos
            ErrorMessages.MA015: (
                self.get_annotation_for_filter(
                    ~Q(paos_organisaatio=self.vakajarjestaja_id) &
                    ~Q(id__in=Subquery(
                        Lapsi.objects.filter(self.get_vakajarjestaja_filter() &
                                             (Q(varhaiskasvatuspaatokset__paattymis_pvm__isnull=True) |
                                              Q(varhaiskasvatuspaatokset__paattymis_pvm__gt=today))).values('id'))) &
                    Q(huoltajuussuhteet__maksutiedot__paattymis_pvm__isnull=True),
                    'huoltajuussuhteet__maksutiedot__id'
                ),
                Maksutieto.__name__.lower()
            ),
            ErrorMessages.MA016: (
                self.get_annotation_for_filter(
                    ~Q(paos_organisaatio=self.vakajarjestaja_id) &
                    Q(huoltajuussuhteet__maksutiedot__paattymis_pvm__isnull=True) &
                    Q(henkilo__syntyma_pvm__lt=overage_date),
                    'huoltajuussuhteet__maksutiedot__id'
                ),
                Maksutieto.__name__.lower()
            )
        }

        vakatiedot_dict = vakatiedot_error_tuples if self.is_vakatiedot_permissions else {}
        huoltajatiedot_dict = huoltajatiedot_error_tuples if self.is_huoltajatiedot_permissions else {}
        return {**vakatiedot_dict, **huoltajatiedot_dict}

    def get_vakajarjestaja_filter(self):
        vakatoimija_filter = Q(vakatoimija=self.vakajarjestaja_id)
        paos_filter = Q(oma_organisaatio=self.vakajarjestaja_id) | Q(paos_organisaatio=self.vakajarjestaja_id)

        return vakatoimija_filter | paos_filter

    def get_queryset(self):
        queryset = Lapsi.objects.filter(self.get_vakajarjestaja_filter())
        queryset = self.filter_queryset(queryset)

        annotations = self.get_annotations()

        return queryset.annotate(**annotations).filter(self.get_include_filter(annotations)).order_by('-muutos_pvm', 'henkilo__sukunimi')


@auditlogclass
class ErrorReportTyontekijatViewSet(AbstractErrorReportViewSet):
    serializer_class = ErrorReportTyontekijatSerializer
    queryset = Tyontekija.objects.none()
    swagger_schema = IntegerIdSchema
    swagger_path_model = VakaJarjestaja

    def verify_permissions(self):
        user = self.request.user

        valid_permission_groups = [Z4_CasKayttoOikeudet.PAAKAYTTAJA,
                                   Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                   Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA]
        user_group_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                               valid_permission_groups)

        if not user.is_superuser and not user_group_qs.exists():
            raise Http404()

    def get_error_tuples(self):
        today = datetime.date.today()
        return {
            ErrorMessages.PS008: (
                self.get_annotation_for_filter(
                    Q(henkilo__tutkinnot__vakajarjestaja=F('vakajarjestaja')) & Q(palvelussuhteet__isnull=True),
                    'id'
                ),
                Tyontekija.__name__.lower()
            ),
            ErrorMessages.TA014: (
                self.get_annotation_for_filter(
                    Q(palvelussuhteet__isnull=False) & Q(palvelussuhteet__tyoskentelypaikat__isnull=True),
                    'palvelussuhteet__id'
                ),
                Palvelussuhde.__name__.lower()
            ),
            ErrorMessages.TU004: (
                self.get_annotation_for_filter(
                    Q(id__in=Subquery(
                        Tyontekija.objects.filter(vakajarjestaja=self.vakajarjestaja_id)
                        .exclude(henkilo__tutkinnot__vakajarjestaja=self.vakajarjestaja_id).values('id'))),
                    'id'
                ),
                Tyontekija.__name__.lower()
            ),
            ErrorMessages.TA008: (
                self.get_annotation_for_filter(
                    Q(palvelussuhteet__alkamis_pvm__gt=F('palvelussuhteet__tyoskentelypaikat__alkamis_pvm')),
                    'palvelussuhteet__tyoskentelypaikat__id'
                ),
                Tyoskentelypaikka.__name__.lower()
            ),
            ErrorMessages.TA006: (
                self.get_annotation_for_filter(
                    Q(palvelussuhteet__paattymis_pvm__lt=F('palvelussuhteet__tyoskentelypaikat__paattymis_pvm')),
                    'palvelussuhteet__tyoskentelypaikat__id'
                ),
                Tyoskentelypaikka.__name__.lower()
            ),
            ErrorMessages.TA013: (
                self.get_annotation_for_filter(
                    Q(palvelussuhteet__paattymis_pvm__isnull=False) &
                    Q(palvelussuhteet__tyoskentelypaikat__isnull=False) &
                    Q(palvelussuhteet__tyoskentelypaikat__paattymis_pvm__isnull=True),
                    'palvelussuhteet__tyoskentelypaikat__id'
                ),
                Tyoskentelypaikka.__name__.lower()
            ),
            ErrorMessages.TA016: (
                self.get_annotation_for_filter(
                    Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__paattymis_pvm__lt=F('palvelussuhteet__tyoskentelypaikat__paattymis_pvm')) |
                    (Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__paattymis_pvm__lt=today) &
                     Q(palvelussuhteet__tyoskentelypaikat__paattymis_pvm__isnull=True)),
                    'palvelussuhteet__tyoskentelypaikat__id'
                ),
                Tyoskentelypaikka.__name__.lower()
            )
        }

    def get_queryset(self):
        queryset = Tyontekija.objects.filter(vakajarjestaja=self.vakajarjestaja_id)
        queryset = self.filter_queryset(queryset)

        annotations = self.get_annotations()
        return queryset.annotate(**annotations).filter(self.get_include_filter(annotations)).order_by('-muutos_pvm', 'henkilo__sukunimi')


@auditlogclass
class ErrorReportToimipaikatViewSet(AbstractErrorReportViewSet):
    serializer_class = ErrorReportToimipaikatSerializer
    queryset = Toimipaikka.objects.none()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_vakatiedot_permissions = False
        self.is_tyontekijatiedot_permissions = False

    def verify_permissions(self):
        user = self.request.user

        valid_permission_groups_vakatiedot = [Z4_CasKayttoOikeudet.PAAKAYTTAJA, Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                                              Z4_CasKayttoOikeudet.TALLENTAJA, Z4_CasKayttoOikeudet.KATSELIJA]
        user_group_vakatiedot_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                                          valid_permission_groups_vakatiedot)
        self.is_vakatiedot_permissions = user.is_superuser or user_group_vakatiedot_qs.exists()

        valid_permission_groups_tyontekijatiedot = [Z4_CasKayttoOikeudet.PAAKAYTTAJA,
                                                    Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                                    Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA]
        user_group_tyontekijatiedot_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                                                valid_permission_groups_tyontekijatiedot)
        self.is_tyontekijatiedot_permissions = user.is_superuser or user_group_tyontekijatiedot_qs.exists()

        if not self.is_vakatiedot_permissions and not self.is_tyontekijatiedot_permissions:
            raise Http404()

    def get_error_tuples(self):
        today = datetime.date.today()

        vakatiedot_error_tuples = {
            ErrorMessages.TO002: (
                self.get_annotation_for_filter(
                    Q(paattymis_pvm__lt=F('toiminnallisetpainotukset__paattymis_pvm')),
                    'toiminnallisetpainotukset__id'
                ),
                ToiminnallinenPainotus.__name__.lower()
            ),
            ErrorMessages.TO003: (
                self.get_annotation_for_filter(
                    Q(paattymis_pvm__isnull=False) &
                    Q(toiminnallisetpainotukset__isnull=False) &
                    Q(toiminnallisetpainotukset__paattymis_pvm__isnull=True),
                    'toiminnallisetpainotukset__id'
                ),
                ToiminnallinenPainotus.__name__.lower()
            ),
            ErrorMessages.TO004: (
                self.get_annotation_for_filter(Q(toiminnallinenpainotus_kytkin=False) &
                                               Q(toiminnallisetpainotukset__isnull=False),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.TO005: (
                self.get_annotation_for_filter(Q(toiminnallinenpainotus_kytkin=True) &
                                               Q(toiminnallisetpainotukset__isnull=True),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.KP002: (
                self.get_annotation_for_filter(
                    Q(paattymis_pvm__lt=F('kielipainotukset__paattymis_pvm')),
                    'kielipainotukset__id'
                ),
                KieliPainotus.__name__.lower()
            ),
            ErrorMessages.KP003: (
                self.get_annotation_for_filter(
                    Q(paattymis_pvm__isnull=False) &
                    Q(kielipainotukset__isnull=False) &
                    Q(kielipainotukset__paattymis_pvm__isnull=True),
                    'kielipainotukset__id'
                ),
                KieliPainotus.__name__.lower()
            ),
            ErrorMessages.KP004: (
                self.get_annotation_for_filter(Q(kielipainotus_kytkin=False) &
                                               Q(kielipainotukset__isnull=False),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.KP005: (
                self.get_annotation_for_filter(Q(kielipainotus_kytkin=True) &
                                               Q(kielipainotukset__isnull=True),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.TP020: (
                self.get_annotation_for_filter(Q(varhaiskasvatuspaikat=0) &
                                               Q(varhaiskasvatussuhteet__alkamis_pvm__lte=today) &
                                               (Q(varhaiskasvatussuhteet__paattymis_pvm__gte=today) |
                                                Q(varhaiskasvatussuhteet__paattymis_pvm__isnull=True)),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.TP021: (
                self.get_annotation_for_filter(Q(paattymis_pvm__lt=F('varhaiskasvatussuhteet__paattymis_pvm')) |
                                               (Q(paattymis_pvm__lt=today) &
                                                Q(varhaiskasvatussuhteet__isnull=False) &
                                                Q(varhaiskasvatussuhteet__paattymis_pvm__isnull=True)),
                                               'id'),
                Toimipaikka.__name__.lower()
            )
        }

        tyontekijatiedot_error_tuples = {
            ErrorMessages.TP022: (
                self.get_annotation_for_filter(Q(paattymis_pvm__lt=F('tyoskentelypaikat__paattymis_pvm')) |
                                               (Q(paattymis_pvm__lt=today) &
                                                Q(tyoskentelypaikat__isnull=False) &
                                                Q(tyoskentelypaikat__paattymis_pvm__isnull=True)),
                                               'id'),
                Toimipaikka.__name__.lower()
            ),
            ErrorMessages.TP023: (
                self.get_annotation_for_filter(Q(tyoskentelypaikat__isnull=True) &
                                               Q(alkamis_pvm__lte=today) &
                                               (Q(paattymis_pvm__gte=today) | Q(paattymis_pvm__isnull=True)),
                                               'id'),
                Toimipaikka.__name__.lower()
            )
        }

        vakatiedot_dict = vakatiedot_error_tuples if self.is_vakatiedot_permissions else {}
        tyontekijatiedot_dict = (tyontekijatiedot_error_tuples
                                 if self.is_vakatiedot_permissions or self.is_tyontekijatiedot_permissions
                                 else {})
        return {**vakatiedot_dict, **tyontekijatiedot_dict}

    def get_queryset(self):
        queryset = Toimipaikka.objects.filter(vakajarjestaja=self.vakajarjestaja_id)
        queryset = self.filter_queryset(queryset)

        annotations = self.get_annotations()
        return queryset.annotate(**annotations).filter(self.get_include_filter(annotations)).order_by('-muutos_pvm', 'nimi')


@auditlogclass
class TiedonsiirtoViewSet(GenericViewSet, ListModelMixin):
    serializer_class = TiedonsiirtoSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TiedonsiirtoFilter
    permission_classes = (RaportitPermissions,)

    vakajarjestaja_filter = None

    @property
    def pagination_class(self):
        reverse_param = self.request.query_params.get('reverse', 'False')
        if reverse_param in ('true', 'True',):
            return IdReverseCursorPagination
        else:
            return IdCursorPagination

    def get_queryset(self):
        queryset = Z6_RequestLog.objects.filter(self.vakajarjestaja_filter).order_by('-id')
        return queryset

    def list(self, request, *args, **kwargs):
        self.vakajarjestaja_filter = get_vakajarjestajat_filter_for_raportit(request)
        return super(TiedonsiirtoViewSet, self).list(request, *args, **kwargs)


@auditlogclass
class TiedonsiirtoYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    serializer_class = TiedonsiirtoYhteenvetoSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = TiedonsiirtoFilter
    permission_classes = (RaportitPermissions,)

    vakajarjestaja_filter = None

    @property
    def pagination_class(self):
        reverse_param = self.request.query_params.get('reverse', 'False')
        if reverse_param in ('true', 'True',):
            return DateReverseCursorPagination
        else:
            return DateCursorPagination

    def get_queryset(self):
        queryset = (Z6_RequestLog.objects.filter(self.vakajarjestaja_filter)
                    .values('user__id', 'user__username', 'timestamp__date')
                    .annotate(successful=Count(Case(When(response_code__in=SUCCESSFUL_STATUS_CODE_LIST, then=1),
                                                    output_field=IntegerField())),
                              unsuccessful=Count(Case(When(~Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST), then=1),
                                                      output_field=IntegerField())),
                              date=Cast('timestamp', DateField()))
                    .order_by('-date'))
        return queryset

    def list(self, request, *args, **kwargs):
        self.vakajarjestaja_filter = get_vakajarjestajat_filter_for_raportit(request)
        return super(TiedonsiirtoYhteenvetoViewSet, self).list(request, *args, **kwargs)


@auditlogclass
class ExcelReportViewSet(GenericViewSet, ListModelMixin, RetrieveModelMixin, CreateModelMixin):
    serializer_class = ExcelReportSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ExcelReportFilter
    permission_classes = (RaportitPermissions,)
    pagination_class = ChangeablePageSizePagination

    def _validate_toimipaikka_belongs_to_vakajarjestaja(self, vakajarjestaja, toimipaikka, accept_paos=False):
        paos_qs = PaosToiminta.objects.filter(Q(oma_organisaatio=vakajarjestaja) & Q(paos_toimipaikka=toimipaikka))
        if ((not toimipaikka.vakajarjestaja == vakajarjestaja and not accept_paos) or
                (not toimipaikka.vakajarjestaja == vakajarjestaja and not paos_qs.exists())):
            # Toimipaikka should be one of vakajarjestaja, or PAOS-toimipaikka of vakajarjestaja
            raise ValidationError({'toimipaikka': [ErrorMessages.ER001.value]})

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or is_oph_staff(user):
            report_filter = Q()
        else:
            report_filter = Q(user=user)
        return Z8_ExcelReport.objects.filter(report_filter).distinct().order_by('-timestamp')

    def perform_create(self, serializer):
        user = self.request.user
        data = serializer.validated_data

        vakajarjestaja = data.get('vakajarjestaja')
        if toimipaikka := data.get('toimipaikka'):
            accept_paos_list = [ExcelReportType.VAKATIEDOT_VOIMASSA.value, ExcelReportType.TOIMIPAIKAT_VOIMASSA.value]
            self._validate_toimipaikka_belongs_to_vakajarjestaja(vakajarjestaja, toimipaikka,
                                                                 accept_paos=data.get('report_type') in accept_paos_list)

        language = (SupportedLanguage.SV.value if data.get('language').upper() == SupportedLanguage.SV.value
                    else SupportedLanguage.FI.value)

        with transaction.atomic():
            filename = generate_filename(data.get('report_type'), language)
            while Z8_ExcelReport.objects.filter(filename=filename).exists():
                # Ensure filename is unique
                filename = generate_filename(data.get('report_type'), language)

            password = encrypt_string(User.objects.make_random_password(length=16))
            excel_report = serializer.save(user=user, password=password, status=ExcelReportStatus.PENDING.value,
                                           filename=filename, language=language)
            transaction.on_commit(lambda: create_excel_report_task.delay(excel_report.id))

    @action(methods=['get'], detail=True, url_path='download', url_name='download')
    def download_report(self, request, pk=None):
        if settings.PRODUCTION_ENV or settings.QA_ENV:
            # In production and QA Excel files are downloaded from S3
            raise Http404

        instance = self.get_object()
        try:
            excel_file = open(get_excel_local_file_path(instance), 'rb')
        except OSError as osException:
            logger.error(f'Error opening Excel file with id {instance.id}: {osException}')
            raise Http404

        response = HttpResponse(FileWrapper(excel_file),
                                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{instance.filename}"'
        excel_file.close()
        return response


@auditlogclass
class DuplicateLapsiViewSet(GenericViewSet, ListModelMixin):
    """
    Temporary ViewSet for fetching information about duplicate Lapsi objects.
    """
    permission_classes = (IsAdminUser,)
    pagination_class = ChangeableReportingPageSizePagination
    serializer_class = DuplicateLapsiSerializer

    def get_queryset(self):
        duplicate_lapsi_qs = (Lapsi.objects.values('henkilo', 'vakatoimija').annotate(count=Count('id'))
                              .filter(vakatoimija__isnull=False, count__gt=1)
                              .order_by('vakatoimija', 'henkilo__sukunimi', 'henkilo__etunimet'))
        return duplicate_lapsi_qs


@auditlogclass
class AbstractTransferOutageReportViewSet(GenericViewSet, ListModelMixin):
    permission_classes = (ReadAdminOrOPHUser,)
    pagination_class = ChangeablePageSizePagination
    filter_backends = (CustomParametersFilterBackend,)
    custom_parameters = (CustomParameter(name='timestamp_before', required=False, location='query', data_type='string',
                                         description='ISO Date (YYYY-MM-DD)'),
                         CustomParameter(name='timestamp_after', required=False, location='query', data_type='string',
                                         description='ISO Date (YYYY-MM-DD)'),)

    def parse_filters(self):
        filters = Q()

        if timestamp_before := self.request.query_params.get('timestamp_before', None):
            try:
                timestamp_before_datetime = datetime.datetime.strptime(timestamp_before, '%Y-%m-%d')
                timestamp_before_datetime += datetime.timedelta(days=1)
                timestamp_before_datetime = timestamp_before_datetime.replace(tzinfo=datetime.timezone.utc)
                filters = Q(last_successful__gt=timestamp_before_datetime)
            except ValueError:
                raise ValidationError({'timestamp_before': [ErrorMessages.GE006.value]})

        if timestamp_after := self.request.query_params.get('timestamp_after', None):
            try:
                timestamp_after_datetime = datetime.datetime.strptime(timestamp_after, '%Y-%m-%d')
                timestamp_after_datetime = timestamp_after_datetime.replace(tzinfo=datetime.timezone.utc)

                if timestamp_before:
                    filters |= Q(last_successful__lt=timestamp_after_datetime)
                else:
                    filters = Q(last_successful__lt=timestamp_after_datetime)
            except ValueError:
                raise ValidationError({'timestamp_after': [ErrorMessages.GE006.value]})
        return filters


@auditlogclass
class UserTransferOutageReportViewSet(AbstractTransferOutageReportViewSet):
    filter_backends = (CustomParametersFilterBackend, DjangoFilterBackend,)
    filterset_class = TransferOutageReportFilter
    serializer_class = UserTransferOutageReportSerializer

    def get_queryset(self):
        request_filters = self.parse_filters()

        return Z6_LastRequest.objects.filter(Q(user__additional_cas_user_fields__kayttajatyyppi=Kayttajatyyppi.PALVELU.value) &
                                             request_filters).order_by('user')


@auditlogclass
class LahdejarjestelmaTransferOutageReportViewSet(AbstractTransferOutageReportViewSet):
    serializer_class = LahdejarjestelmaTransferOutageReportSerializer

    def get_queryset(self):
        request_filters = self.parse_filters()

        lahdejarjestelma_list = (Z2_Code.objects.filter(koodisto__name=Koodistot.lahdejarjestelma_koodit.value)
                                 .values_list('code_value', flat=True))
        active_lahdejarjestelma_list = (Z6_LastRequest.objects.filter(~Q(request_filters) &
                                                                      Q(last_successful__isnull=False))
                                        .values_list('lahdejarjestelma', flat=True).distinct())
        inactive_lahdejarjestelma_set = set(lahdejarjestelma_list).difference(set(active_lahdejarjestelma_list))
        return sorted(list(inactive_lahdejarjestelma_set), key=lambda x: int(x))


@auditlogclass
class RequestSummaryViewSet(GenericViewSet, ListModelMixin):
    permission_classes = (ReadAdminOrOPHUser,)
    pagination_class = ChangeablePageSizePagination
    serializer_class = RequestSummarySerializer
    filter_backends = (CustomParametersFilterBackend, DjangoFilterBackend, SearchFilter,)
    filterset_class = RequestSummaryFilter
    search_fields = ('user__username', 'vakajarjestaja__nimi', '=vakajarjestaja__organisaatio_oid',
                     'request_url_simple',)
    custom_parameters = (CustomParameter(name='categories', required=False, location='query', data_type='string',
                                         description='Comma separated list of categories'),)

    def get_serializer_class(self):
        if self.request.query_params.get('group', '').lower() == 'true':
            return RequestSummaryGroupSerializer
        return RequestSummarySerializer

    def _parse_filters(self):
        category_list = self.request.query_params.get('categories', '').split(',')
        query_filter = Q()
        if 'user' in category_list:
            query_filter |= Q(user__isnull=False)
        if 'vakajarjestaja' in category_list:
            query_filter |= Q(vakajarjestaja__isnull=False)
        if 'lahdejarjestelma' in category_list:
            query_filter |= Q(lahdejarjestelma__isnull=False)
        if 'url' in category_list:
            query_filter |= Q(request_url_simple__isnull=False)
        return query_filter

    def get_queryset(self):
        query_filters = self._parse_filters()

        if self.request.query_params.get('group', '').lower() == 'true':
            return (Z6_RequestSummary.objects
                    .filter(query_filters)
                    .values('user', 'vakajarjestaja', 'lahdejarjestelma', 'request_url_simple')
                    .annotate(successful_sum=Sum('successful_count'), unsuccessful_sum=Sum('unsuccessful_count'),
                              ratio=Cast(F('unsuccessful_sum'), output_field=FloatField()) /
                              Cast(F('successful_sum') + F('unsuccessful_sum'), output_field=FloatField()),
                              id_list=ArrayAgg('id', distinct=True))
                    .values('user__id', 'user__username', 'vakajarjestaja__id', 'vakajarjestaja__nimi',
                            'vakajarjestaja__organisaatio_oid', 'lahdejarjestelma', 'request_url_simple', 'ratio',
                            'successful_sum', 'unsuccessful_sum', 'id_list')
                    .order_by('-ratio', '-unsuccessful_sum'))
        else:
            return (Z6_RequestSummary.objects
                    .filter(query_filters)
                    .annotate(ratio=Cast(F('unsuccessful_count'), output_field=FloatField()) /
                              Cast(F('successful_count') + F('unsuccessful_count'), output_field=FloatField()))
                    .order_by('-ratio', '-unsuccessful_count', '-summary_date'))
