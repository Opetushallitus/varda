import datetime
import logging
from wsgiref.util import FileWrapper

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.postgres.aggregates import ArrayAgg
from django.db import connection, transaction
from django.db.models import (Case, Count, DateField, F, FloatField, IntegerField, OuterRef, Q, Subquery, Sum,
                              Value, When)
from django.db.models.functions import Cast
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.constants import SUCCESSFUL_STATUS_CODE_LIST, YRITYSMUOTO_KUNTA
from varda.custom_swagger import IntegerIdSchema
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.koodistot import Koodistot
from varda.enums.supported_language import SupportedLanguage
from varda.excel_export import (create_excel_report_task, ExcelReportType, generate_filename,
                                get_excel_local_file_path)
from varda.enums.reporting import ReportStatus
from varda.filters import (CustomParameter, CustomParametersFilterBackend, ExcelReportFilter, KelaEtuusmaksatusFilter,
                           RequestSummaryFilter, TiedonsiirtoFilter, TransferOutageReportFilter)
from varda.misc import encrypt_string
from varda.misc_queries import get_related_object_changed_id_qs
from varda.misc_viewsets import ViewSetValidator
from varda.models import (KieliPainotus, Lapsi, Maksutieto, Organisaatio, Palvelussuhde, PaosOikeus, PaosToiminta,
                          ToiminnallinenPainotus, Toimipaikka, Tyontekija, Tyoskentelypaikka,
                          Varhaiskasvatuspaatos, Varhaiskasvatussuhde, YearlyReportSummary, Z2_Code,
                          Z2_Koodisto, Z4_CasKayttoOikeudet, Z6_LastRequest, Z6_RequestLog, Z6_RequestSummary,
                          Z8_ExcelReport)
from varda.pagination import (ChangeablePageSizePagination, ChangeableReportingPageSizePagination, DateCursorPagination,
                              DateReverseCursorPagination, IdCursorPagination, IdReverseCursorPagination,
                              TkCursorPagination)
from varda.permissions import (auditlogclass, get_vakajarjestajat_filter_for_raportit, is_oph_staff,
                               IsCertificateAccess, is_user_permission, RaportitPermissions, ReadAdminOrOPHUser,
                               user_permission_groups_in_organization)
from varda.serializers_reporting import (DuplicateLapsiSerializer, ErrorReportLapsetSerializer,
                                         ErrorReportToimipaikatSerializer, ErrorReportTyontekijatSerializer,
                                         ExcelReportSerializer, KelaEtuusmaksatusAloittaneetSerializer,
                                         KelaEtuusmaksatusKorjaustiedotPoistetutSerializer,
                                         KelaEtuusmaksatusKorjaustiedotSerializer,
                                         KelaEtuusmaksatusLopettaneetSerializer,
                                         KelaEtuusmaksatusMaaraaikaisetSerializer,
                                         LahdejarjestelmaTransferOutageReportSerializer, RequestSummaryGroupSerializer,
                                         RequestSummarySerializer, TiedonsiirtoSerializer,
                                         TiedonsiirtotilastoSerializer, TiedonsiirtoYhteenvetoSerializer,
                                         TkHenkilostotiedotSerializer, TkOrganisaatiotSerializer,
                                         TkVakatiedotSerializer, UserTransferOutageReportSerializer,
                                         YearlyReportingDataSummarySerializer)
from varda.tasks import create_yearly_reporting_summary
from varda.validators import validate_kela_api_datetimefield


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
                                            .values('id', 'varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id').distinct('id'))


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
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = KelaEtuusmaksatusLopettaneetSerializer
    permission_classes = (IsCertificateAccess,)
    pagination_class = ChangeablePageSizePagination

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
            muutos_pvm_lte = now

        return (Varhaiskasvatussuhde.objects.raw('''SELECT DISTINCT ON (vas.id) vas.id, vas.paattymis_pvm,
                                                        he.henkilotunnus, he.kotikunta_koodi
                                                    FROM varda_varhaiskasvatussuhde vas
                                                    INNER JOIN varda_varhaiskasvatuspaatos vap ON vas.varhaiskasvatuspaatos_id = vap.id
                                                    INNER JOIN varda_lapsi la ON vap.lapsi_id = la.id
                                                    INNER JOIN varda_henkilo he ON la.henkilo_id = he.id
                                                    INNER JOIN LATERAL (
                                                        SELECT id, paattymis_pvm
                                                        FROM varda_historicalvarhaiskasvatussuhde
                                                        WHERE history_date < %s AND id = vas.id
                                                        ORDER BY id, history_date DESC LIMIT 1
                                                    ) last_vas ON true
                                                    WHERE vas.muutos_pvm >= %s AND vas.muutos_pvm <= %s
                                                    AND LOWER(vap.jarjestamismuoto_koodi) IN ('jm01', 'jm02', 'jm03')
                                                    AND vap.luonti_pvm >= '2021-01-04'
                                                    AND vap.tilapainen_vaka_kytkin = 'f' AND he.henkilotunnus != ''
                                                    AND last_vas.paattymis_pvm IS NULL
                                                    AND vas.paattymis_pvm IS NOT NULL
                                                    ORDER BY vas.id ASC;''', [muutos_pvm_gte, muutos_pvm_gte, muutos_pvm_lte]))


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
                                            .values('id', 'varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id').distinct('id'))


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
                                            .order_by('id').distinct('id'))


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
    # Making changes here does not affect filters on poistetut and lopettaneet, if you update these check if you need
    # to update poistetut and lopettaneet as well

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
    pagination_class = None
    permission_classes = (permissions.IsAdminUser, )

    def get_vakatoimijat(self, kunnat_filter, voimassa_filter):
        if kunnat_filter is None:
            return Organisaatio.objects.filter(voimassa_filter)
        elif kunnat_filter:
            return Organisaatio.objects.filter(voimassa_filter & Q(yritysmuoto__in=YRITYSMUOTO_KUNTA))
        else:
            return Organisaatio.objects.filter(voimassa_filter & ~Q(yritysmuoto__in=YRITYSMUOTO_KUNTA))

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

    @swagger_auto_schema(responses={status.HTTP_200_OK: TiedonsiirtotilastoSerializer(many=False)})
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
    Return a list of Lapsi/Tyontekija/Toimipaikka objects that have incomplete data.
    Rules are defined in get_error_nested_list function.

    search=str (nimi/hetu (SHA-256 hash as hexadecimal)/OID)
    """
    pagination_class = ChangeablePageSizePagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.vakajarjestaja_oid = None
        self.vakajarjestaja_id = None

    def get_search_filter(self):
        """
        Returns raw SQL to be used in a query:
        search_filter is used to filter specific objects based on column values
        search_filter_parameters is used for filtering
        :return: search_filter, search_parameter_list
        """
        search_param = self.request.query_params.get('search', '').lower()
        search_filter = ''
        search_parameter_list = []
        if search_param and self.queryset.model in (Lapsi, Tyontekija,):
            search_filter = ''' AND (he.etunimet ILIKE CONCAT('%%', %s, '%%') OR
                                he.sukunimi ILIKE CONCAT('%%', %s, '%%') OR
                                he.henkilotunnus_unique_hash = %s OR he.henkilo_oid = %s OR '''
            search_filter += 'la.id::varchar = %s)' if self.queryset.model == Lapsi else 'ty.id::varchar = %s)'
            search_parameter_list = [search_param] * 5
        elif search_param and self.queryset.model == Toimipaikka:
            search_filter = ''' AND (tp.nimi ILIKE CONCAT('%%', %s, '%%') OR tp.organisaatio_oid = %s OR
                                tp.id::varchar = %s)'''
            search_parameter_list = [search_param] * 3
        return search_filter, search_parameter_list

    def get_sql_content(self, error_list_nested):
        """
        Returns raw SQL content to be used in a query:
        annotation_query is used to annotate specific error situations
        filter_query is used to filter out errors without any hits
        parameter_list is a list of parameters for both annotations and filters
        :param error_list_nested: nested error list from get_errors function
        :return: annotation_query, filter_query, parameter_list
        """
        annotation_list = []
        filter_list = []
        parameter_list = []

        for error_list in error_list_nested:
            error_code = error_list[0]
            when_filter = error_list[1]
            filter_parameters = error_list[2]
            id_lookup = error_list[3]

            base_sql = f"STRING_AGG(CASE WHEN {when_filter} THEN ({id_lookup})::varchar ELSE NULL END, ',')"
            annotation_list.append(f'{base_sql} AS {error_code.value["error_code"]}')
            filter_list.append(f'NOT {base_sql} IS NULL')
            parameter_list += filter_parameters

        annotation_query = ', '.join(annotation_list)
        filter_query = ' OR '.join(filter_list)
        return annotation_query, filter_query, parameter_list

    def get_errors(self):
        """
        Desired errors can be filtered with error URL parameter
        (e.g. /api/v1/vakajarjestajat/1/error-report-tyontekijat/?error=TA006)
        """
        error_search_term = self.request.query_params.get('error', None)
        return [error_list for error_list in self.get_error_nested_list()
                if not error_search_term or error_search_term.lower() in error_list[0].value['error_code'].lower()]

    def get_vakajarjestaja_object(self, vakajarjestaja_id):
        vakajarjestaja_obj = get_object_or_404(Organisaatio.objects.all(), pk=vakajarjestaja_id)
        if self.request.user.has_perm('view_organisaatio', vakajarjestaja_obj):
            self.vakajarjestaja_oid = vakajarjestaja_obj.organisaatio_oid
            self.vakajarjestaja_id = vakajarjestaja_id
        else:
            raise Http404()

    def list(self, request, *args, **kwargs):
        self.get_vakajarjestaja_object(kwargs.get('organisaatio_pk', None))
        self.verify_permissions()
        return super(AbstractErrorReportViewSet, self).list(request, *args, **kwargs)

    def get_error_nested_list(self):
        """
        Returns a list of lists containing error related information, e.g.
        [[error_key, filter_condition, parameters[], id_lookup, model_name]]
        error_key is ErrorMessages enum value, which is used to identify the specific error
        filter_condition is raw SQL for filtering specific situations
        parameters[] are used to fill the filter conditions
        id_lookup is raw SQL path to specific id value
        model_name is the name of Model for id_lookup
        :return: list of lists
        """
        raise NotImplementedError('get_error_nested_list')

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
    swagger_path_model = Organisaatio

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

    def get_error_nested_list(self):
        today = datetime.date.today()
        overage_date = today - relativedelta(years=8)

        # [[ErrorMessages, filter condition, parameters[], ID lookup, model name for ID lookup]]
        vakatiedot_error_nested_list = [
            [ErrorMessages.VP002, 'vapa.alkamis_pvm > vasu.alkamis_pvm', [], 'vasu.id',
             Varhaiskasvatussuhde.get_name()],
            [ErrorMessages.VP003, 'vapa.paattymis_pvm < vasu.paattymis_pvm', [], 'vasu.id',
             Varhaiskasvatussuhde.get_name()],
            [ErrorMessages.VS012, '''vapa.paattymis_pvm IS NOT NULL AND vasu.id IS NOT NULL AND
             vasu.paattymis_pvm IS NULL''', [], 'vasu.id', Varhaiskasvatussuhde.get_name()],
            [ErrorMessages.VP012, 'vapa.id IS NULL', [], 'la.id', Lapsi.get_name()],
            [ErrorMessages.VS014, 'vapa.id IS NOT NULL AND vasu.id IS NULL', [], 'vapa.id',
             Varhaiskasvatuspaatos.get_name()],
            [ErrorMessages.VP013, 'vapa.paattymis_pvm IS NULL AND he.syntyma_pvm < %s', [overage_date], 'vapa.id',
             Varhaiskasvatuspaatos.get_name()],
            [ErrorMessages.VS015, '''tp.paattymis_pvm < vasu.paattymis_pvm OR
             (tp.paattymis_pvm < %s AND vasu.paattymis_pvm IS NULL)''', [today], 'vasu.id',
             Varhaiskasvatussuhde.get_name()],
            [ErrorMessages.HE017, "he.henkilotunnus != '' AND he.vtj_yksiloity = FALSE", [], 'la.id', Lapsi.get_name()],
            [ErrorMessages.HE018, "he.henkilotunnus = ''", [], 'la.id', Lapsi.get_name()]
        ]

        # Do not get Maksutieto related errors for Lapsi objects for which vakajarjestaja is paos_organisaatio
        # [[ErrorMessages, filter condition, parameters[], ID lookup, model name for ID lookup]]
        huoltajatiedot_error_nested_list = [
            [ErrorMessages.MA015, '''la.paos_organisaatio_id IS DISTINCT FROM %s AND ma.paattymis_pvm IS NULL AND
             NOT EXISTS(SELECT id FROM varda_varhaiskasvatuspaatos WHERE lapsi_id = la.id AND
              alkamis_pvm <= %s AND (paattymis_pvm IS NULL OR paattymis_pvm >= %s))''',
             [self.vakajarjestaja_id, today, today], 'ma.id', Maksutieto.get_name()],
            [ErrorMessages.MA016, '''la.paos_organisaatio_id IS DISTINCT FROM %s AND ma.paattymis_pvm IS NULL AND
             he.syntyma_pvm < %s''', [self.vakajarjestaja_id, overage_date], 'ma.id', Maksutieto.get_name()]
        ]

        vakatiedot_list = vakatiedot_error_nested_list if self.is_vakatiedot_permissions else []
        huoltajatiedot_list = huoltajatiedot_error_nested_list if self.is_huoltajatiedot_permissions else []
        return [*vakatiedot_list, *huoltajatiedot_list]

    def get_queryset(self):
        errors = self.get_errors()
        if not errors:
            # No errors in filtered query
            return Lapsi.objects.none()

        annotation_query, filter_query, parameter_list = self.get_sql_content(errors)
        search_filter, search_parameter_list = self.get_search_filter()

        # If user has partial permissions, only join required tables
        vakatiedot_join = '''
            LEFT JOIN varda_varhaiskasvatuspaatos vapa ON vapa.lapsi_id = la.id
            LEFT JOIN varda_varhaiskasvatussuhde vasu ON vasu.varhaiskasvatuspaatos_id = vapa.id
            LEFT JOIN varda_toimipaikka tp ON tp.id = vasu.toimipaikka_id
        ''' if self.is_vakatiedot_permissions else ''
        huoltajatiedot_join = '''
            LEFT JOIN varda_huoltajuussuhde hu ON hu.lapsi_id = la.id
            LEFT JOIN varda_maksutietohuoltajuussuhde mahu ON mahu.huoltajuussuhde_id = hu.id
            LEFT JOIN varda_maksutieto ma ON ma.id = mahu.maksutieto_id
        ''' if self.is_huoltajatiedot_permissions else ''
        join_clause = f'{vakatiedot_join} {huoltajatiedot_join}'

        raw_query = f'''
            SELECT la.*, {annotation_query}
            FROM varda_lapsi la
            LEFT JOIN varda_henkilo he ON he.id = la.henkilo_id
            {join_clause}
            WHERE (la.vakatoimija_id = %s OR la.oma_organisaatio_id = %s OR la.paos_organisaatio_id = %s)
                  {search_filter}
            GROUP BY la.id, he.sukunimi
            HAVING {filter_query}
            ORDER BY la.muutos_pvm DESC, he.sukunimi
        '''

        return Lapsi.objects.raw(raw_query, [*parameter_list, self.vakajarjestaja_id, self.vakajarjestaja_id,
                                             self.vakajarjestaja_id, *search_parameter_list, *parameter_list])


@auditlogclass
class ErrorReportTyontekijatViewSet(AbstractErrorReportViewSet):
    serializer_class = ErrorReportTyontekijatSerializer
    queryset = Tyontekija.objects.none()
    swagger_schema = IntegerIdSchema
    swagger_path_model = Organisaatio

    def verify_permissions(self):
        user = self.request.user

        valid_permission_groups = [Z4_CasKayttoOikeudet.PAAKAYTTAJA,
                                   Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                   Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA]
        user_group_qs = user_permission_groups_in_organization(user, self.vakajarjestaja_oid,
                                                               valid_permission_groups)

        if not user.is_superuser and not user_group_qs.exists():
            raise Http404()

    def get_error_nested_list(self):
        today = datetime.date.today()

        # [[ErrorMessages, filter condition, parameters[], ID lookup, model name for ID lookup]]
        return [
            [ErrorMessages.PS008, 'tu.id IS NOT NULL AND pasu.id IS NULL', [], 'ty.id', Tyontekija.get_name()],
            [ErrorMessages.TA014, 'pasu.id IS NOT NULL AND typa.id IS NULL', [], 'pasu.id', Palvelussuhde.get_name()],
            [ErrorMessages.TU004, 'tu.id IS NULL', [], 'ty.id', Tyontekija.get_name()],
            [ErrorMessages.TA008, 'pasu.alkamis_pvm > typa.alkamis_pvm', [], 'typa.id', Tyoskentelypaikka.get_name()],
            [ErrorMessages.TA006, 'pasu.paattymis_pvm < typa.paattymis_pvm', [], 'typa.id', Tyoskentelypaikka.get_name()],
            [ErrorMessages.TA013, '''pasu.paattymis_pvm IS NOT NULL AND typa.id IS NOT NULL AND
             typa.paattymis_pvm IS NULL''', [], 'typa.id', Tyoskentelypaikka.get_name()],
            [ErrorMessages.TA016, '''tp.paattymis_pvm < typa.paattymis_pvm OR
             (tp.paattymis_pvm < %s AND typa.paattymis_pvm IS NULL)''', [today], 'typa.id',
             Tyoskentelypaikka.get_name()],
            [ErrorMessages.HE017, "he.henkilotunnus != '' AND he.vtj_yksiloity = FALSE", [], 'ty.id', Tyontekija.get_name()],
            [ErrorMessages.HE018, "he.henkilotunnus = ''", [], 'ty.id', Tyontekija.get_name()],
            [ErrorMessages.PS009, '''pasu.alkamis_pvm <= %s AND
             (pasu.paattymis_pvm IS NULL OR pasu.paattymis_pvm >= %s) AND typa.id IS NOT NULL AND
             NOT EXISTS(SELECT id FROM varda_tyoskentelypaikka WHERE palvelussuhde_id = pasu.id AND
              alkamis_pvm <= %s AND (paattymis_pvm IS NULL OR paattymis_pvm >= %s)) AND
             NOT EXISTS(SELECT id FROM varda_pidempipoissaolo WHERE palvelussuhde_id = pasu.id AND
              alkamis_pvm <= %s AND (paattymis_pvm IS NULL OR paattymis_pvm >= %s))''',
             [today, today, today, today, today, today], 'pasu.id', Palvelussuhde.get_name()]
        ]

    def get_queryset(self):
        errors = self.get_errors()
        if not errors:
            # No errors in filtered query
            return Tyontekija.objects.none()

        annotation_query, filter_query, parameter_list = self.get_sql_content(errors)
        search_filter, search_parameter_list = self.get_search_filter()

        raw_query = f'''
            SELECT ty.*, {annotation_query}
            FROM varda_tyontekija ty
            LEFT JOIN varda_henkilo he ON he.id = ty.henkilo_id
            LEFT JOIN varda_palvelussuhde pasu ON pasu.tyontekija_id = ty.id
            LEFT JOIN varda_tyoskentelypaikka typa ON typa.palvelussuhde_id = pasu.id
            LEFT JOIN varda_toimipaikka tp ON tp.id = typa.toimipaikka_id
            LEFT JOIN varda_tutkinto tu ON tu.henkilo_id = ty.henkilo_id AND tu.vakajarjestaja_id = ty.vakajarjestaja_id
            WHERE ty.vakajarjestaja_id = %s
                  {search_filter}
            GROUP BY ty.id, he.sukunimi
            HAVING {filter_query}
            ORDER BY ty.muutos_pvm DESC, he.sukunimi
        '''

        return Tyontekija.objects.raw(raw_query, [*parameter_list, self.vakajarjestaja_id, *search_parameter_list,
                                                  *parameter_list])


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

    def get_error_nested_list(self):
        today = datetime.date.today()

        # [[ErrorMessages, filter condition, parameters[], ID lookup, model name for ID lookup]]
        vakatiedot_error_nested_list = [
            [ErrorMessages.TO002, 'tp.paattymis_pvm < topa.paattymis_pvm', [], 'topa.id',
             ToiminnallinenPainotus.get_name()],
            [ErrorMessages.TO003, 'tp.paattymis_pvm IS NOT NULL AND topa.id IS NOT NULL AND topa.paattymis_pvm IS NULL',
             [], 'topa.id', ToiminnallinenPainotus.get_name()],
            [ErrorMessages.TO004, 'tp.toiminnallinenpainotus_kytkin = FALSE AND topa.id IS NOT NULL', [], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.TO005, 'tp.toiminnallinenpainotus_kytkin = TRUE AND topa.id IS NULL', [], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.KP002, 'tp.paattymis_pvm < kipa.paattymis_pvm', [], 'kipa.id', KieliPainotus.get_name()],
            [ErrorMessages.KP003, 'tp.paattymis_pvm IS NOT NULL AND kipa.id IS NOT NULL AND kipa.paattymis_pvm IS NULL',
             [], 'kipa.id', KieliPainotus.get_name()],
            [ErrorMessages.KP004, 'tp.kielipainotus_kytkin = FALSE AND kipa.id IS NOT NULL', [], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.KP005, 'tp.kielipainotus_kytkin = TRUE AND kipa.id IS NULL', [], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.TP020, '''tp.varhaiskasvatuspaikat = 0 AND vasu.alkamis_pvm <= %s AND
             (vasu.paattymis_pvm IS NULL OR vasu.paattymis_pvm >= %s)''', [today, today], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.TP021, '''tp.paattymis_pvm < vasu.paattymis_pvm OR
             (tp.paattymis_pvm < %s AND vasu.id IS NOT NULL AND vasu.paattymis_pvm IS NULL)''', [today], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.TP027, '''tp.alkamis_pvm > kj_code.paattymis_pvm OR
             tp.paattymis_pvm > kj_code.paattymis_pvm OR (tp.paattymis_pvm IS NULL AND kj_code.paattymis_pvm < %s)''',
             [today], 'tp.id', Toimipaikka.get_name()]
        ]

        # [[ErrorMessages, filter condition, parameters[], ID lookup, model name for ID lookup]]
        tyontekijatiedot_error_nested_list = [
            [ErrorMessages.TP022, '''tp.paattymis_pvm < typa.paattymis_pvm OR
             (tp.paattymis_pvm < %s AND typa.id IS NOT NULL AND typa.paattymis_pvm IS NULL)''', [today], 'tp.id',
             Toimipaikka.get_name()],
            [ErrorMessages.TP023, '''typa.id IS NULL AND tp.varhaiskasvatuspaikat != 0 AND tp.alkamis_pvm <= %s AND
             (tp.paattymis_pvm IS NULL OR tp.paattymis_pvm >= %s)''', [today, today], 'tp.id', Toimipaikka.get_name()]
        ]

        vakatiedot_list = vakatiedot_error_nested_list if self.is_vakatiedot_permissions else []
        tyontekijatiedot_list = (tyontekijatiedot_error_nested_list
                                 if self.is_vakatiedot_permissions or self.is_tyontekijatiedot_permissions
                                 else [])
        return [*vakatiedot_list, *tyontekijatiedot_list]

    def get_queryset(self):
        errors = self.get_errors()
        if not errors:
            # No errors in filtered query
            return Toimipaikka.objects.none()

        annotation_query, filter_query, parameter_list = self.get_sql_content(errors)
        search_filter, search_parameter_list = self.get_search_filter()

        # If user has partial permissions, only join required tables
        vakatiedot_join = '''
            LEFT JOIN varda_toiminnallinenpainotus topa ON topa.toimipaikka_id = tp.id
            LEFT JOIN varda_kielipainotus kipa ON kipa.toimipaikka_id = tp.id
            LEFT JOIN varda_varhaiskasvatussuhde vasu ON vasu.toimipaikka_id = tp.id
            LEFT JOIN varda_z2_code kj_code ON kj_code.koodisto_id = %s AND
                LOWER(kj_code.code_value) = LOWER(tp.kasvatusopillinen_jarjestelma_koodi)
        ''' if self.is_vakatiedot_permissions else ''
        tyontekijatiedot_join = '''
            LEFT JOIN varda_tyoskentelypaikka typa ON typa.toimipaikka_id = tp.id
        ''' if self.is_vakatiedot_permissions or self.is_tyontekijatiedot_permissions else ''
        join_clause = f'{vakatiedot_join} {tyontekijatiedot_join}'

        kj_koodisto_id = getattr(Z2_Koodisto.objects
                                 .filter(name=Koodistot.kasvatusopillinen_jarjestelma_koodit.value)
                                 .first(), 'id', None)
        join_parameter_list = [kj_koodisto_id] if self.is_vakatiedot_permissions else []

        raw_query = f'''
            SELECT tp.*, {annotation_query}
            FROM varda_toimipaikka tp
            {join_clause}
            WHERE tp.vakajarjestaja_id = %s
                  {search_filter}
            GROUP BY tp.id
            HAVING {filter_query}
            ORDER BY tp.muutos_pvm DESC, tp.nimi
        '''

        return Toimipaikka.objects.raw(raw_query, [*parameter_list, *join_parameter_list, self.vakajarjestaja_id,
                                                   *search_parameter_list, *parameter_list])


@auditlogclass
class TiedonsiirtoViewSet(GenericViewSet, ListModelMixin):
    serializer_class = TiedonsiirtoSerializer
    filter_backends = (CustomParametersFilterBackend, DjangoFilterBackend,)
    filterset_class = TiedonsiirtoFilter
    permission_classes = (RaportitPermissions,)
    custom_parameters = (CustomParameter(name='vakajarjestajat', required=False, location='query', data_type='string',
                                         description='Comma separated list of vakajarjestaja IDs'),)

    @property
    def pagination_class(self):
        reverse_param = self.request.query_params.get('reverse', 'False')
        if reverse_param in ('true', 'True',):
            return IdReverseCursorPagination
        else:
            return IdCursorPagination

    def get_queryset(self):
        vakajarjestaja_filter = get_vakajarjestajat_filter_for_raportit(self.request)
        queryset = Z6_RequestLog.objects.filter(vakajarjestaja_filter).order_by('-id')
        return queryset


@auditlogclass
class TiedonsiirtoYhteenvetoViewSet(GenericViewSet, ListModelMixin):
    serializer_class = TiedonsiirtoYhteenvetoSerializer
    filter_backends = (CustomParametersFilterBackend, DjangoFilterBackend,)
    filterset_class = TiedonsiirtoFilter
    permission_classes = (RaportitPermissions,)
    custom_parameters = (CustomParameter(name='vakajarjestajat', required=False, location='query', data_type='string',
                                         description='Comma separated list of vakajarjestaja IDs'),)

    @property
    def pagination_class(self):
        reverse_param = self.request.query_params.get('reverse', 'False')
        if reverse_param in ('true', 'True',):
            return DateReverseCursorPagination
        else:
            return DateCursorPagination

    def get_queryset(self):
        vakajarjestaja_filter = get_vakajarjestajat_filter_for_raportit(self.request)
        queryset = (Z6_RequestLog.objects.filter(vakajarjestaja_filter)
                    .values('user__id', 'user__username', 'timestamp__date')
                    .annotate(successful=Count(Case(When(response_code__in=SUCCESSFUL_STATUS_CODE_LIST, then=1),
                                                    output_field=IntegerField())),
                              unsuccessful=Count(Case(When(~Q(response_code__in=SUCCESSFUL_STATUS_CODE_LIST), then=1),
                                                      output_field=IntegerField())),
                              date=Cast('timestamp', DateField()))
                    .order_by('-date'))
        return queryset


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
        if isinstance(user, AnonymousUser):
            # Swagger uses AnonymousUser so in that case return an empty queryset
            return Z8_ExcelReport.objects.none()

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
            excel_report = serializer.save(user=user, password=password, status=ReportStatus.PENDING.value,
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
                                         description='Comma separated list of categories'),
                         CustomParameter(name='group', required=False, location='query', data_type='boolean',
                                         description='Group results for the time window'),)

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
                              id_list=ArrayAgg('id', distinct=True, default=Value([])))
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


class TkBaseViewSet(GenericViewSet, ListModelMixin):
    permission_classes = (IsCertificateAccess,)
    pagination_class = TkCursorPagination
    filter_backends = (CustomParametersFilterBackend,)
    custom_parameters = (CustomParameter(name='datetime_gt', required=False, location='query', data_type='string',
                                         description='ISO DateTime (YYYY-MM-DDTHH:MM:SSZ), '
                                                     'e.g. 2021-01-01T00%3A00%3A00%2B0300'),
                         CustomParameter(name='datetime_lte', required=False, location='query', data_type='string',
                                         description='ISO DateTime (YYYY-MM-DDTHH:MM:SSZ), '
                                                     'e.g. 2021-01-01T00%3A00%3A00Z'),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If datetime_gt parameter was not provided set datetime_gt to year 2000 so all results are fetched
        self.datetime_gt = timezone.now().replace(year=2000)
        # If datetime_lte parameter was not provided set datetime_lte to tomorrow so all results are fetched
        self.datetime_lte = timezone.now() + datetime.timedelta(days=1)

    def initial(self, *args, **kwargs):
        super().initial(*args, **kwargs)

        with ViewSetValidator() as validator:
            for datetime_param in (('datetime_gt', self.request.query_params.get('datetime_gt'),),
                                   ('datetime_lte', self.request.query_params.get('datetime_lte'),),):
                field_name = datetime_param[0]
                if field_value := datetime_param[1]:
                    datetime_format = '%Y-%m-%dT%H:%M:%S.%f%z' if '.' in field_value else '%Y-%m-%dT%H:%M:%S%z'
                    try:
                        setattr(self, field_name, datetime.datetime.strptime(field_value, datetime_format))
                    except ValueError:
                        validator.error(field_name, ErrorMessages.GE020.value)

    @transaction.atomic
    def dispatch(self, request, *args, **kwargs):
        with connection.cursor() as cursor:
            # Increase work_mem temporarily as Tilastokeskus queries have expensive sorts with large page_size or
            # time frame. Sorts are slow if PostgreSQL has to perform them on disk when work_mem is not sufficent.
            # Default work_mem is 4MB.
            # dispatch function is decorated with transaction.atomic so that SET LOCAL only applies here
            # PostgreSQL specific functionality (SET LOCAL work_mem)
            cursor.execute('SET LOCAL work_mem = %s;', ['64MB'])
        return super().dispatch(request, *args, **kwargs)


@auditlogclass
class TkOrganisaatiot(TkBaseViewSet):
    queryset = Organisaatio.objects.none()
    serializer_class = TkOrganisaatiotSerializer

    def get_queryset(self):
        id_qs = get_related_object_changed_id_qs(Organisaatio.get_name(), self.datetime_gt, self.datetime_lte)
        return (Organisaatio.history
                .filter(id__in=Subquery(id_qs), history_date__lte=self.datetime_lte)
                .distinct('id').order_by('id', '-history_date'))


@auditlogclass
class TkVakatiedot(TkBaseViewSet):
    queryset = Lapsi.objects.none()
    serializer_class = TkVakatiedotSerializer

    def get_queryset(self):
        id_qs = get_related_object_changed_id_qs(Lapsi.get_name(), self.datetime_gt, self.datetime_lte)
        return (Lapsi.history
                .filter(id__in=Subquery(id_qs), history_date__lte=self.datetime_lte)
                .distinct('id').order_by('id', '-history_date'))


@auditlogclass
class TkHenkilostotiedot(TkBaseViewSet):
    queryset = Tyontekija.objects.none()
    serializer_class = TkHenkilostotiedotSerializer

    def get_queryset(self):
        id_qs = get_related_object_changed_id_qs(Tyontekija.get_name(), self.datetime_gt, self.datetime_lte)
        return (Tyontekija.history
                .filter(id__in=Subquery(id_qs), history_date__lte=self.datetime_lte)
                .distinct('id').order_by('id', '-history_date'))


class YearlyReportingDataSummaryViewSet(GenericViewSet, CreateModelMixin):
    filter_backends = (DjangoFilterBackend,)
    permission_classes = (RaportitPermissions,)
    queryset = YearlyReportSummary.objects.none()
    serializer_class = YearlyReportingDataSummarySerializer

    def return_vakajarjestaja(self, parameter):
        try:
            parameter = int(parameter)
            return Organisaatio.objects.filter(id=parameter).first()
        except ValueError:
            return Organisaatio.objects.filter(organisaatio_oid=parameter).first()

    def check_user_permissions(self, user, vakajarjestaja_obj, full_query):
        if not user.is_superuser and not is_oph_staff(user):
            if full_query:
                raise ValidationError({'vakajarjestaja': [ErrorMessages.PE003.value]})
            if vakajarjestaja_obj and not is_user_permission(user, Z4_CasKayttoOikeudet.RAPORTTIEN_KATSELIJA + '_' + vakajarjestaja_obj.organisaatio_oid):
                raise ValidationError({'vakajarjestaja': [ErrorMessages.PE003.value]})

    def create(self, request, *args, **kwargs):
        last_year = datetime.date.today().year - 1
        user = self.request.user
        data = self.request.data
        vakajarjestaja = data.get('vakajarjestaja_input')
        tilastovuosi = data.get('tilastovuosi', last_year)
        poiminta_pvm = data.get('poiminta_pvm')
        history_q = False
        timediff = None

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        full_query = True if vakajarjestaja.lower() == 'all' else False
        vakajarjestaja_obj = self.return_vakajarjestaja(vakajarjestaja)

        if not vakajarjestaja_obj and not full_query:
            raise ValidationError({'vakajarjestaja': [ErrorMessages.MI015.value]})

        self.check_user_permissions(user, vakajarjestaja_obj, full_query)

        try:
            tilasto_pvm = datetime.date(int(tilastovuosi), 12, 31)
        except ValueError:
            raise ValidationError({'tilastovuosi': [ErrorMessages.GE010.value]})

        if poiminta_pvm:
            try:
                poiminta_pvm = datetime.datetime.strptime(poiminta_pvm, '%Y-%m-%dT%H:%M:%S%z')
                history_q = True
            except ValueError:
                raise ValidationError({'poiminta_pvm': [ErrorMessages.GE020.value]})

        summary_obj, created = YearlyReportSummary.objects.get_or_create(vakajarjestaja=vakajarjestaja_obj, tilasto_pvm=tilasto_pvm)

        if not created and poiminta_pvm is not None:
            timediff = abs(summary_obj.poiminta_pvm - poiminta_pvm)

        if created or (timediff is not None and timediff > datetime.timedelta(minutes=30)):
            poiminta_pvm = poiminta_pvm or datetime.datetime.now(datetime.timezone.utc)
            clear_fields = [field for field in model_to_dict(summary_obj) if field not in ['id', 'vakajarjestaja', 'tilasto_pvm',
                                                                                           'status', 'poiminta_pvm', 'muutos_pvm',
                                                                                           'luonti_pvm']]
            for field in clear_fields:
                setattr(summary_obj, field, None)
            summary_obj.status = ReportStatus.PENDING.value
            summary_obj.poiminta_pvm = poiminta_pvm
            summary_obj.save()
            vakajarjestaja_id = getattr(vakajarjestaja_obj, 'id', None)
            create_yearly_reporting_summary.delay(vakajarjestaja_id, tilasto_pvm, poiminta_pvm, full_query, history_q)

        serializer = self.get_serializer(model_to_dict(summary_obj))
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, headers=headers)
