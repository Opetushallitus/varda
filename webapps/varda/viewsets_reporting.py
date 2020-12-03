import datetime

from django.db.models import Q, Case, Value, When, OuterRef, Subquery
from django_filters.rest_framework import DjangoFilterBackend
from django.utils.timezone import make_aware
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from varda.enums.error_messages import ErrorMessages
from varda.pagination import ChangeablePageSizePagination
from varda import filters
from varda.serializers_reporting import (KelaEtuusmaksatusAloittaneetSerializer, KelaEtuusmaksatusLopettaneetSerializer,
                                         KelaEtuusmaksatusMaaraaikaisetSerializer, KelaEtuusmaksatusKorjaustiedotSerializer,
                                         KelaEtuusmaksatusKorjaustiedotPoistetutSerializer, TiedonsiirtotilastoSerializer)
from varda.enums.ytj import YtjYritysmuoto
from varda.models import (KieliPainotus, Lapsi, Maksutieto, PaosOikeus, ToiminnallinenPainotus, Toimipaikka,
                          VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde)
from varda.permissions import CustomReportingViewAccess, auditlogclass


"""
Query-results for reports
"""


@auditlogclass
class KelaEtuusmaksatusAloittaneetViewset(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat aloittaneet varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: change the amount of query results per page
        luonti_pvm: fetch data after given luonti_pvm
    """
    filter_class = filters.KelaEtuusmaksatusAloittaneetFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = KelaEtuusmaksatusAloittaneetSerializer
    permission_classes = (CustomReportingViewAccess, )
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, luonti_pvm):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        luonti_pvm_filter = Q(luonti_pvm__date__gte=luonti_pvm)

        # paattymis_pvm must be none, vakapaatokset with end date are reported separately
        paattymis_pvm_filter = Q(paattymis_pvm=None)

        return (luonti_pvm_filter &
                common_filters &
                paattymis_pvm_filter)

    def get_queryset(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        luonti_pvm = self.request.query_params.get('luonti_pvm', None)

        # Limit the amount of objects to the dataset (maximum of 1 year ago)
        if luonti_pvm is not None:
            try:
                luonti_pvm = datetime.datetime.strptime(luonti_pvm, '%Y-%m-%d')
            except ValueError:
                raise ValidationError({'luonti_pvm': [ErrorMessages.GE006.value]})
            if (now.date() - luonti_pvm.date()).days > 365:
                raise ValidationError({'luonti_pvm': [ErrorMessages.GE019.value]})
        else:
            luonti_pvm = now - datetime.timedelta(days=7)

        dataset_filters = self.create_filters_for_data(luonti_pvm)

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .filter(dataset_filters)
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('varhaiskasvatuspaatos__lapsi', 'alkamis_pvm').distinct('varhaiskasvatuspaatos__lapsi'))


@auditlogclass
class KelaEtuusmaksatusLopettaneetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat lopettaneet varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: Change amount of search results per page
        muutos_pvm: Pick starting date for muutos_pvm
    """
    filter_class = filters.KelaEtuusmaksatusLopettaneetFilter
    queryset = Varhaiskasvatussuhde.objects.none()
    serializer_class = KelaEtuusmaksatusLopettaneetSerializer
    permission_classes = (CustomReportingViewAccess, )
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, muutos_pvm):
        common_filters = _create_common_kela_filters()

        muutos_pvm_filter = Q(muutos_pvm__gte=muutos_pvm)

        paattymis_pvm_filter = Q(paattymis_pvm__isnull=True)

        history_type_filter = ~Q(history_type='-')

        return common_filters & muutos_pvm_filter & paattymis_pvm_filter & history_type_filter

    def get_queryset(self):
        muutos_pvm = self.get_muutos_pvm()

        dataset_filters = self.create_filters_for_data(muutos_pvm)

        latest_end_dates = (Varhaiskasvatussuhde.history.filter(dataset_filters)
                                                        .values('id')
                                                        .distinct('id')
                                                        .order_by('id'))

        id_filter = Q(id__in=latest_end_dates)

        return (Varhaiskasvatussuhde.history.select_related('varhaiskasvatuspaatos__lapsi', 'lapsi__henkilo')
                                            .filter(id_filter & Q(paattymis_pvm__isnull=False))
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'paattymis_pvm').distinct('id'))

    def get_muutos_pvm(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        muutos_pvm = self.request.query_params.get('muutos_pvm', None)

        # Limit the amount of objects to the dataset (1 year past)
        if muutos_pvm is not None:
            try:
                muutos_pvm = datetime.datetime.strptime(muutos_pvm, '%Y-%m-%d')
                aware_muutos_pvm = make_aware(muutos_pvm)
            except ValueError:
                raise ValidationError({'muutos_pvm': [ErrorMessages.GE006.value]})
            if (now.date() - muutos_pvm.date()).days > 365:
                raise ValidationError({'muutos_pvm': [ErrorMessages.GE019.value]})
        else:
            aware_muutos_pvm = now - datetime.timedelta(days=7)

        return aware_muutos_pvm


@auditlogclass
class KelaEtuusmaksatusMaaraaikaisetViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset jotka ovat aloittaneet määräaikaisessa varhaiskasvatuksessa viikon
    sisällä tästä päivästä.

    params:
        page_size: Change amount of results per page of response
        luonti_pvm: Change alkamis_pvm of fetched data
    """
    filter_class = filters.KelaEtuusmaksatusAloittaneetFilter
    filter_backends = (DjangoFilterBackend,)
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusMaaraaikaisetSerializer
    permission_classes = (CustomReportingViewAccess, )
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, luonti_pvm):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        luonti_pvm_filter = Q(luonti_pvm__date__gte=luonti_pvm)

        # maaraaikainen must always have an end date
        paattymis_pvm_filter = Q(paattymis_pvm__isnull=False)

        return (luonti_pvm_filter &
                common_filters &
                paattymis_pvm_filter)

    def get_queryset(self):
        now = datetime.datetime.now()
        luonti_pvm = self.request.query_params.get('luonti_pvm', None)

        # Limit the amount of objects to the dataset (1 year past)
        if luonti_pvm is not None:
            try:
                luonti_pvm = datetime.datetime.strptime(luonti_pvm, '%Y-%m-%d')
            except ValueError:
                raise ValidationError({'luonti_pvm': [ErrorMessages.GE006.value]})
            if (now - luonti_pvm).days > 365:
                raise ValidationError({'luonti_pvm': [ErrorMessages.GE019.value]})
        else:
            luonti_pvm = now - datetime.timedelta(days=7)

        dataset_filters = self.create_filters_for_data(luonti_pvm)

        return (Varhaiskasvatussuhde.objects.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .filter(dataset_filters)
                                            .values('varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('varhaiskasvatuspaatos__lapsi', 'alkamis_pvm', 'paattymis_pvm')
                                            .distinct('varhaiskasvatuspaatos__lapsi'))


@auditlogclass
class KelaEtuusmaksatusKorjaustiedotViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset joiden tietoihin on tullut muutoksia viimeisen viikon sisällä.

    params:
        page_size: change the number of query results per page
        muutos_pvm: change starting date for returned changes
    """
    filter_backends = (DjangoFilterBackend,)
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusKorjaustiedotSerializer
    permission_classes = (CustomReportingViewAccess, )
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, aware_muutos_pvm):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        time_window_filter = Q(muutos_pvm__gte=aware_muutos_pvm) & Q(luonti_pvm__lt=aware_muutos_pvm)

        # Must be active at or after
        # TO-DO change filter to 2021-18-01
        paattymis_pvm_date_gte = datetime.datetime(2019, 9, 4)
        paattymis_pvm_filter = (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=paattymis_pvm_date_gte))

        history_type_filter = ~Q(history_type='-')

        return (time_window_filter &
                paattymis_pvm_filter &
                history_type_filter &
                common_filters)

    def get_queryset(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        muutos_pvm = self.request.query_params.get('muutos_pvm', None)

        if muutos_pvm is not None:
            try:
                muutos_pvm = datetime.datetime.strptime(muutos_pvm, '%Y-%m-%d')
                aware_muutos_pvm = make_aware(muutos_pvm)
            except ValueError:
                raise ValidationError({'muutos_pvm': [ErrorMessages.GE006.value]})
            if (now.date() - muutos_pvm.date()).days > 365:
                raise ValidationError({'muutos_pvm': [ErrorMessages.GE019.value]})
        else:
            aware_muutos_pvm = now - datetime.timedelta(days=7)

        dataset_filters = self.create_filters_for_data(aware_muutos_pvm)

        latest_changed_objects = Varhaiskasvatussuhde.history.filter(dataset_filters)
        id_filter = Q(id__in=latest_changed_objects.values('id'))

        history_subquery = Varhaiskasvatussuhde.history.filter(id=OuterRef('id')).order_by('history_id')

        return (Varhaiskasvatussuhde.history.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .annotate(new_alkamis_pvm=(Case(When(alkamis_pvm=Subquery(history_subquery.values('alkamis_pvm')[:1]), then=Value('0001-01-01')), default=Subquery(history_subquery.values('alkamis_pvm')[:1]))),
                                                      new_paattymis_pvm=(Case(When(paattymis_pvm=Subquery(history_subquery.values('paattymis_pvm')[:1]), then=Value('0001-01-01')), default=Subquery(history_subquery.values('paattymis_pvm')[:1])))
                                                      )
                                            .filter(id_filter & ~Q(Q(new_alkamis_pvm='0001-01-01') & Q(new_paattymis_pvm='0001-01-01')))
                                            .values('id', 'varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'new_alkamis_pvm', 'new_paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('id', 'varhaiskasvatuspaatos__lapsi', 'alkamis_pvm').distinct('id'))


@auditlogclass
class KelaEtuusmaksatusKorjaustiedotPoistetutViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset joiden on poistettu viimeisen viikon sisällä.

    params:
        page_size: change the amount of query results per page
        poisto_pvm: get deleted after set poisto_pvm
    """
    filter_backends = (DjangoFilterBackend,)
    queryset = Varhaiskasvatussuhde.history.none()
    serializer_class = KelaEtuusmaksatusKorjaustiedotPoistetutSerializer
    permission_classes = (CustomReportingViewAccess, )
    pagination_class = ChangeablePageSizePagination

    def create_filters_for_data(self, now, poisto_pvm):
        common_filters = _create_common_kela_filters()

        # time window for fetching data
        if poisto_pvm is None:
            poisto_pvm = now - datetime.timedelta(days=7)
        time_window_filter = Q(history_date__gte=poisto_pvm)

        # Must be active at or after
        # TO-DO change filter to 2021-18-01
        paattymis_pvm_date_gte = datetime.datetime(2019, 9, 4)
        paattymis_pvm_filter = (Q(paattymis_pvm__isnull=True) | Q(paattymis_pvm__gte=paattymis_pvm_date_gte))

        # Only deleted objects
        history_filter = Q(history_type='-')

        return (time_window_filter &
                paattymis_pvm_filter &
                history_filter &
                common_filters)

    def get_queryset(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        poisto_pvm = self.request.query_params.get('poisto_pvm', None)

        if poisto_pvm is not None:
            try:
                poisto_pvm = datetime.datetime.strptime(poisto_pvm, '%Y-%m-%d')
            except ValueError:
                raise ValidationError({'poisto_pvm': [ErrorMessages.GE006.value]})
            if (now.date() - poisto_pvm.date()).days > 365:
                raise ValidationError({'poisto_pvm': [ErrorMessages.GE019.value]})
        else:
            poisto_pvm = now - datetime.timedelta(days=7)

        dataset_filters = self.create_filters_for_data(now, poisto_pvm)

        return (Varhaiskasvatussuhde.history.select_related('varhaiskasvatuspaatos__lapsi', 'varhaiskasvatuspaatos__lapsi__henkilo')
                                            .filter(dataset_filters)
                                            .values('id', 'varhaiskasvatuspaatos__lapsi_id', 'alkamis_pvm', 'paattymis_pvm',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus',
                                                    'varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi')
                                            .order_by('varhaiskasvatuspaatos__lapsi', 'alkamis_pvm').distinct('varhaiskasvatuspaatos__lapsi'))


def _create_common_kela_filters():
    # Kunnallinen
    jarjestamismuoto_filter = (Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM01') |
                               Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM02') |
                               Q(varhaiskasvatuspaatos__jarjestamismuoto_koodi__iexact='JM03'))

    # Tilapäinen varhaiskasvatus
    tilapainen_vaka_filter = Q(varhaiskasvatuspaatos__tilapainen_vaka_kytkin=False)

    # Date from which data is transfered
    # TO-DO Change filter to 2021, 1, 4
    luonti_pvm_date = datetime.datetime(2019, 9, 4, tzinfo=datetime.timezone.utc)
    luonti_pvm_filter = Q(varhaiskasvatuspaatos__luonti_pvm__gte=luonti_pvm_date)

    # Only henkilo with hetu
    hetu_filter = Q(varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus__isnull=False)

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
