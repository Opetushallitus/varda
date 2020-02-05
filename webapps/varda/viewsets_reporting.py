import datetime
import math

from django.db.models import Q
from rest_framework import permissions
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda.enums.ytj import YtjYritysmuoto
from varda.models import (Henkilo, KieliPainotus, Lapsi, Maksutieto, ToiminnallinenPainotus, Toimipaikka,
                          VakaJarjestaja, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z2_Koodisto)
from varda.permissions import CustomReportingViewAccess
from varda.serializers_reporting import KelaRaporttiSerializer, KoodistoSerializer, TiedonsiirtotilastoSerializer

"""
Query-results for reports
"""


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


class KoodistoViewSet(GenericViewSet, ListModelMixin):
    queryset = None
    serializer_class = KoodistoSerializer
    permission_classes = (permissions.IsAuthenticated, )

    def get_queryset(self):
        koodisto = Z2_Koodisto.objects.filter(pk=1)[0]
        koodit = {
            'kunta_koodit': koodisto.kunta_koodit,
            'kieli_koodit': koodisto.kieli_koodit,
            'jarjestamismuoto_koodit': koodisto.jarjestamismuoto_koodit,
            'toimintamuoto_koodit': koodisto.toimintamuoto_koodit,
            'kasvatusopillinen_jarjestelma_koodit': koodisto.kasvatusopillinen_jarjestelma_koodit,
            'toiminnallinen_painotus_koodit': koodisto.toiminnallinen_painotus_koodit,
            'tutkintonimike_koodit': koodisto.tutkintonimike_koodit,
            'tyosuhde_koodit': koodisto.tyosuhde_koodit,
            'tyoaika_koodit': koodisto.tyoaika_koodit,
            'tyotehtava_koodit': koodisto.tyotehtava_koodit,
            'sukupuoli_koodit': koodisto.sukupuoli_koodit,
            'opiskeluoikeuden_tila_koodit': koodisto.opiskeluoikeuden_tila_koodit,
            'tutkinto_koodit': koodisto.tutkinto_koodit
        }
        return koodit

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)


class TiedonsiirtotilastoViewSet(GenericViewSet, ListModelMixin):
    """
    list:
    Nouda raportti tiedonsiirtojen tilanteesta (toimijat, toimipaikat, lapset, päätökset, suhteet, maksutiedot,
    kielipainotukset ja toiminnalliset painotukset) eroteltuna kunnallisesti ja yksityisesti

    filter:
    kunnat palauttaa tiedot kunnallisesta (true) tai yksityisestä varhaiskasvatuksesta (false)
    esim. /?kunnat=true
    """
    queryset = None
    serializer_class = TiedonsiirtotilastoSerializer
    permission_classes = (permissions.IsAdminUser, )

    kunnallinen = [YtjYritysmuoto.KUNTA.name, YtjYritysmuoto.KUNTAYHTYMA.name]

    def get_vakatoimijat(self, kunnat_filter):
        if kunnat_filter is None:
            return VakaJarjestaja.objects.all()
        elif kunnat_filter:
            return VakaJarjestaja.objects.filter(yritysmuoto__in=self.kunnallinen)
        else:
            return VakaJarjestaja.objects.exclude(yritysmuoto__in=self.kunnallinen)

    def get_toimipaikat(self, vakatoimijat):
        return Toimipaikka.objects.filter(vakajarjestaja__in=vakatoimijat)

    """
    Ei oteta toimipaikkojen määrään mukaan ns. dummy-toimipaikkoja
    """
    def get_toimipaikat_ei_dummy_paos(self, vakatoimijat):
        return Toimipaikka.objects.filter(~Q(nimi__icontains='Palveluseteli ja ostopalvelu') &
                                          Q(vakajarjestaja__in=vakatoimijat))

    def get_vakasuhteet(self, toimipaikat):
        return Varhaiskasvatussuhde.objects.filter(toimipaikka__in=toimipaikat)

    def get_vakapaatokset(self, vakasuhteet):
        vakasuhde_id_list = vakasuhteet.values_list('varhaiskasvatuspaatos', flat=True)
        return Varhaiskasvatuspaatos.objects.filter(id__in=vakasuhde_id_list)

    def get_lapset(self, vakapaatokset):
        vakapaatos_id_list = vakapaatokset.values_list('lapsi', flat=True)
        return Lapsi.objects.filter(id__in=vakapaatos_id_list).distinct('henkilo__henkilo_oid')

    def get_maksutiedot(self, kunnat_filter):
        if kunnat_filter is None:
            return Maksutieto.objects.all()
        elif kunnat_filter:
            return Maksutieto.objects.exclude(yksityinen_jarjestaja=True)
        else:
            return Maksutieto.objects.filter(yksityinen_jarjestaja=True)

    def get_kielipainotukset(self, toimipaikat):
        return KieliPainotus.objects.filter(toimipaikka__in=toimipaikat)

    def get_toiminnalliset_painotukset(self, toimipaikat):
        return ToiminnallinenPainotus.objects.filter(toimipaikka__in=toimipaikat)

    def list(self, request, *args, **kwargs):
        kunnat_request = self.request.query_params.get('kunnat', None)

        if isinstance(kunnat_request, str):
            kunnat_request = kunnat_request.lower()

        if kunnat_request == 'true':
            kunnat_filter = True
        elif kunnat_request == 'false':
            kunnat_filter = False
        else:
            kunnat_filter = None

        vakatoimijat = self.get_vakatoimijat(kunnat_filter)
        toimipaikat = self.get_toimipaikat(vakatoimijat)
        vakasuhteet = self.get_vakasuhteet(toimipaikat)
        vakapaatokset = self.get_vakapaatokset(vakasuhteet)

        stats = {
            'vakatoimijat': vakatoimijat.count(),
            'toimipaikat': self.get_toimipaikat_ei_dummy_paos(vakatoimijat).count(),
            'vakasuhteet': vakasuhteet.count(),
            'vakapaatokset': vakapaatokset.count(),
            'lapset': self.get_lapset(vakapaatokset).count(),
            'maksutiedot': self.get_maksutiedot(kunnat_filter).count(),
            'kielipainotukset': self.get_kielipainotukset(toimipaikat).count(),
            'toiminnalliset_painotukset': self.get_toiminnalliset_painotukset(toimipaikat).count()
        }

        serializer = self.get_serializer(stats)
        return Response(serializer.data)


"""
class LapsetRyhmittainViewSet(GenericViewSet, ListModelMixin):

    list:
    Nouda lapset ryhmittain.

    queryset = None
    serializer_class = LapsetRyhmittainSerializer
    permission_classes = (CustomReportingViewAccess, )
    schema = AutoSchema(manual_fields=[
        coreapi.Field("ryhma_id", required=False, location="query", schema=coreschema.Integer(description="Ryhmän uniikki ID VARDA:ssa.", title="ryhma_id")),
        coreapi.Field("oid", required=False, location="query", schema=coreschema.String(description="Oppijanumero.", title="oid"))])

    def get_queryset(self):
        This queryset can be filtered using "ryhma_id" and "oid".

        lapset_ryhmittain = []

        # First filtering (with ryhma_id)
        filter_ryhma_id = self.request.query_params.get('ryhma_id', None)
        if filter_ryhma_id is None or filter_ryhma_id is "":
            ryhmat = Ryhma.objects.all().order_by('id')
        else:
            ryhmat = Ryhma.objects.filter(id=filter_ryhma_id).order_by('id')

        for ryhma in ryhmat:
            ryhma_id = ryhma.id

            # Second filtering (with oid)
            filter_oid = self.request.query_params.get('oid', None)
            if filter_oid is None:
                lapset = Lapsi.objects.filter(varhaiskasvatussuhteet__ryhma=ryhma_id).distinct().order_by('id')
            else:
                lapset = Lapsi.objects.filter(henkilo__oppijanumero=filter_oid).filter(varhaiskasvatussuhteet__ryhma=ryhma_id).distinct().order_by('id')

            for lapsi in lapset:
                lapsen_id = lapsi.id
                henkilo = Henkilo.objects.get(lapsi=lapsen_id)
                lapsen_oppijanumero = henkilo.oppijanumero
                lapsen_tiedot = {"ryhma_id": ryhma_id,
                                 "ryhma_tunnus": ryhma.tunnus,
                                 "ryhma_lisatieto": ryhma.lisatieto,
                                 "ryhma_vuorohoitoryhma": ryhma.vuorohoitoryhma,
                                 "ryhma_avoin_varhaiskasvatus": ryhma.avoin_varhaiskasvatus_koodi,
                                 "ryhma_avoin_varhaiskasvatus_lkm": ryhma.avoin_varhaiskasvatus_lkm,
                                 "ryhma_alkamispaivamaara": ryhma.alkamis_pvm,
                                 "ryhma_paattymispaivamaara": ryhma.paattymis_pvm,
                                 "lapsen_id": lapsen_id,
                                 "oid": lapsen_oppijanumero,
                                 "aidinkieli": henkilo.aidinkieli_koodi,
                                 "sukupuoli": henkilo.sukupuoli_koodi,
                                 "syntymapaivamaara": henkilo.syntyma_pvm,
                                 "kunta": henkilo.kotikunta_koodi}
                lapset_ryhmittain.append(lapsen_tiedot)
        return lapset_ryhmittain

    def list(self, request, *args, **kwargs):
        ryhma_id = self.request.query_params.get('ryhma_id', None)
        if ryhma_id is not None and not ryhma_id.isdigit():
            raise Http404("Not found.")
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
"""
