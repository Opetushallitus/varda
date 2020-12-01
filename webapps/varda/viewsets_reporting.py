import datetime
import math

from django.db.models import Q
from rest_framework import permissions
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.enums.ytj import YtjYritysmuoto
from varda.models import (Henkilo, KieliPainotus, Lapsi, Maksutieto, PaosOikeus, ToiminnallinenPainotus, Toimipaikka,
                          VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde)
from varda.permissions import CustomReportingViewAccess, auditlogclass
from varda.serializers_reporting import KelaRaporttiSerializer, TiedonsiirtotilastoSerializer

"""
Query-results for reports
"""


@auditlogclass
class KelaRaporttiViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    nouda ne lapset joiden vaka_päätöstä on päivitetty kuukauden
    sisällä tästä päivästä.
    """
    queryset = None
    serializer_class = KelaRaporttiSerializer
    permission_classes = (CustomReportingViewAccess, )

    def get_queryset(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        startdate = now - datetime.timedelta(days=500)
        lapsien_tiedot = []
        vakapaatokset = Varhaiskasvatuspaatos.objects.filter(muutos_pvm__range=[startdate, now]).order_by('id')
        for vakapaatos in vakapaatokset:
            lapsen_id = vakapaatos.lapsi
            henkilo = Henkilo.objects.get(lapsi=lapsen_id)
            ikavuosia = (now.date() - henkilo.syntyma_pvm).days / 365.2425
            vuosia = math.floor(ikavuosia)
            kuukausia = math.floor((ikavuosia - vuosia) * 12)
            ika = '%d vuotta, %d kuukautta' % (vuosia, kuukausia)
            if vakapaatos.paattymis_pvm:
                if (now.date() - vakapaatos.paattymis_pvm).days > 0:
                    varhaiskasvatuksessa = False
                else:
                    varhaiskasvatuksessa = True
            else:
                varhaiskasvatuksessa = True
            lapsen_tiedot = {
                'henkilotunnus': henkilo.henkilotunnus,
                'etunimet': henkilo.etunimet,
                'sukunimi': henkilo.sukunimi,
                'ika': ika,
                'postinumero': henkilo.postinumero,
                'kotikunta_koodi': henkilo.kotikunta_koodi,
                'vaka_paatos_alkamis_pvm': vakapaatos.alkamis_pvm,
                'vaka_paatos_paattymis_pvm': vakapaatos.paattymis_pvm,
                'varhaiskasvatuksessa': varhaiskasvatuksessa,
                'vaka_paatos_muutos_pvm': vakapaatos.muutos_pvm
            }
            lapsien_tiedot.append(lapsen_tiedot)
        return lapsien_tiedot

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


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
