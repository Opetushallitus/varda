import operator
import re
from datetime import datetime
from functools import reduce

from django.contrib.postgres.aggregates import StringAgg
from django.db.models import Q, Case, When, Subquery, OuterRef, CharField, Value
from django.db.models.functions import Concat
from django.http import Http404
from django_filters import rest_framework as djangofilters
from django_filters.constants import EMPTY_VALUES

from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.koodistot import Koodistot
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Lapsi, Huoltaja,
                          Maksutieto, PaosToiminta, PaosOikeus, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Z2_Code)
from varda.misc import parse_toimipaikka_id_list


class CustomCharFilter(djangofilters.CharFilter):
    """
    Custom CharFilter which can be used to filter the query with EMPTY string,
    e.g. /api/v1/toimipaikat/?oid_tunniste=EMPTY
    returns all "toimipaikat" where oid_tunniste == ""
    """
    empty_value = 'EMPTY'

    def filter(self, qs, value):
        if value != self.empty_value:
            return super(CustomCharFilter, self).filter(qs, value)

        qs = self.get_method(qs)(**{'%s__%s' % (self.field_name, self.lookup_expr): ""})
        return qs.distinct() if self.distinct else qs


class KunnallinenKytkinFilter(djangofilters.BooleanFilter):
    def filter(self, qs, value):
        if value is None:
            return qs
        elif value:
            return qs.filter(yritysmuoto__in=VakaJarjestaja.get_kuntatyypit())
        elif not value:
            return qs.filter(~Q(yritysmuoto__in=VakaJarjestaja.get_kuntatyypit()))


class VakaJarjestajaFieldFilter(djangofilters.CharFilter):
    def filter(self, qs, value):
        if value.isdigit():
            self.field_name += '__id'
            value = int(value)
        elif value:
            self.field_name += '__organisaatio_oid'
        return super().filter(qs, value)


class HenkiloFieldFilter(djangofilters.CharFilter):
    def filter(self, qs, value):
        if value.isdigit():
            return qs.filter(henkilo=int(value))
        elif value:
            return qs.filter(henkilo__henkilo_oid=value)
        else:
            return qs


class NoneDateFromToRangeFilter(djangofilters.DateFromToRangeFilter):
    """
    DateFromToRangeFilter that also returns results with undefined date with keyword _after
    """
    def filter(self, qs, value):
        # Copied from filters.RangeFilter.filter()
        if value:
            if value.start is not None and value.stop is not None:
                self.lookup_expr = 'range'
                value = (value.start, value.stop)
            elif value.start is not None:
                self.lookup_expr = 'gte'
                value = value.start
            elif value.stop is not None:
                self.lookup_expr = 'lte'
                value = value.stop

        # Overrides filters.Filter.filter()
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()
        lookup = f'{self.field_name}__{self.lookup_expr}'
        filter_obj = Q(**{lookup: value})

        # Date value can also be None if the lookup_expr is 'gte' so that dates that are after the value and
        # dates that are not yet set are filtered.
        if self.lookup_expr == 'gte':
            isnull_filter = Q(**{f'{self.field_name}__isnull': True})
            filter_obj = filter_obj | isnull_filter

        qs = self.get_method(qs)(filter_obj)
        return qs


class VakaJarjestajaFilter(djangofilters.FilterSet):
    nimi = djangofilters.CharFilter(field_name='nimi', lookup_expr='icontains')
    y_tunnus = djangofilters.CharFilter(field_name='y_tunnus', lookup_expr='exact')
    organisaatio_oid = CustomCharFilter(field_name='organisaatio_oid', lookup_expr='exact')
    kunta_koodi = djangofilters.CharFilter(field_name='kunta_koodi', lookup_expr='exact')
    sahkopostiosoite = CustomCharFilter(field_name='sahkopostiosoite', lookup_expr='exact')
    tilinumero = djangofilters.CharFilter(field_name='tilinumero', lookup_expr='exact')
    kayntiosoite = djangofilters.CharFilter(field_name='kayntiosoite', lookup_expr='icontains')
    kayntiosoite_postitoimipaikka = djangofilters.CharFilter(field_name='kayntiosoite_postitoimipaikka', lookup_expr='icontains')
    kayntiosoite_postinumero = djangofilters.CharFilter(field_name='kayntiosoite_postinumero', lookup_expr='exact')
    postiosoite = djangofilters.CharFilter(field_name='postiosoite', lookup_expr='icontains')
    postitoimipaikka = djangofilters.CharFilter(field_name='postitoimipaikka', lookup_expr='icontains')
    postinumero = djangofilters.CharFilter(field_name='postinumero', lookup_expr='exact')
    puhelinnumero = CustomCharFilter(field_name='puhelinnumero', lookup_expr='exact')
    ytjkieli = djangofilters.CharFilter(field_name='ytjkieli', lookup_expr='exact')
    kunnallinen_kytkin = KunnallinenKytkinFilter(label='kunnallinen_kytkin')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = VakaJarjestaja
        fields = []


class ToimipaikkaFilter(djangofilters.FilterSet):
    nimi = djangofilters.CharFilter(field_name='nimi', lookup_expr='icontains')
    organisaatio_oid = CustomCharFilter(field_name='organisaatio_oid', lookup_expr='exact')
    kayntiosoite = djangofilters.CharFilter(field_name='kayntiosoite', lookup_expr='icontains')
    kayntiosoite_postitoimipaikka = djangofilters.CharFilter(field_name='kayntiosoite_postitoimipaikka', lookup_expr='icontains')
    kayntiosoite_postinumero = djangofilters.CharFilter(field_name='kayntiosoite_postinumero', lookup_expr='exact')
    postiosoite = djangofilters.CharFilter(field_name='postiosoite', lookup_expr='icontains')
    postitoimipaikka = djangofilters.CharFilter(field_name='postitoimipaikka', lookup_expr='icontains')
    postinumero = djangofilters.CharFilter(field_name='postinumero', lookup_expr='exact')
    puhelinnumero = CustomCharFilter(field_name='puhelinnumero', lookup_expr='exact')
    sahkopostiosoite = CustomCharFilter(field_name='sahkopostiosoite', lookup_expr='exact')
    kasvatusopillinen_jarjestelma_koodi = CustomCharFilter(field_name='kasvatusopillinen_jarjestelma_koodi', lookup_expr='exact')
    toimintamuoto_koodi = CustomCharFilter(field_name='toimintamuoto_koodi', lookup_expr='exact')
    asiointikieli_koodi = djangofilters.BaseCSVFilter(field_name='asiointikieli_koodi', lookup_expr='contains')
    jarjestamismuoto_koodi = djangofilters.BaseCSVFilter(field_name='jarjestamismuoto_koodi', lookup_expr='contains')
    varhaiskasvatuspaikat = djangofilters.NumberFilter(field_name='varhaiskasvatuspaikat', lookup_expr='gte')
    alkamis_pvm = djangofilters.DateFromToRangeFilter(field_name='alkamis_pvm')
    paattymis_pvm = NoneDateFromToRangeFilter(field_name='paattymis_pvm')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = Toimipaikka
        fields = []


class ToiminnallinenPainotusFilter(djangofilters.FilterSet):
    toimintapainotus_koodi = djangofilters.CharFilter(field_name='toimintapainotus_koodi', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = ToiminnallinenPainotus
        fields = []


class KieliPainotusFilter(djangofilters.FilterSet):
    kielipainotus_koodi = djangofilters.CharFilter(field_name='kielipainotus_koodi', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = KieliPainotus
        fields = []


class YksiloimattomatHenkilotFilter(djangofilters.FilterSet):
    henkilotunnus = CustomCharFilter(field_name='henkilotunnus', lookup_expr='exact')
    henkilo_oid = CustomCharFilter(field_name='henkilo_oid', lookup_expr='exact')
    vakatoimija_oid = djangofilters.CharFilter(method='filter_vakatoimija_oid')

    class Meta:
        model = Henkilo
        fields = []

    def filter_vakatoimija_oid(self, queryset, name, value):
        return queryset.filter(Q(lapsi__vakatoimija__organisaatio_oid=value) |
                               Q(tyontekijat__vakajarjestaja__organisaatio_oid=value))


class LapsiFilter(djangofilters.FilterSet):
    paos_kytkin = djangofilters.BooleanFilter(field_name='paos_kytkin', lookup_expr='exact')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = Lapsi
        fields = []


class HuoltajaFilter(djangofilters.FilterSet):
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = Huoltaja
        fields = []


class MaksutietoFilter(djangofilters.FilterSet):
    lapsi = djangofilters.NumberFilter(field_name='huoltajuussuhteet__lapsi__id', lookup_expr='exact', label='lapsi_id')
    maksun_peruste_koodi = djangofilters.CharFilter(field_name='maksun_peruste_koodi', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')

    class Meta:
        model = Maksutieto
        fields = []


class PaosToimintaFilter(djangofilters.FilterSet):
    oma_organisaatio = djangofilters.NumberFilter(field_name='oma_organisaatio', lookup_expr='exact')
    paos_organisaatio = djangofilters.NumberFilter(field_name='paos_organisaatio', lookup_expr='exact')
    paos_toimipaikka = djangofilters.NumberFilter(field_name='paos_toimipaikka', lookup_expr='exact')
    voimassa_kytkin = djangofilters.BooleanFilter(field_name='voimassa_kytkin', lookup_expr='exact')

    class Meta:
        model = PaosToiminta
        fields = []


class PaosOikeusFilter(djangofilters.FilterSet):
    jarjestaja_kunta_organisaatio = djangofilters.NumberFilter(field_name='jarjestaja_kunta_organisaatio', lookup_expr='exact')
    tuottaja_organisaatio = djangofilters.NumberFilter(field_name='tuottaja_organisaatio', lookup_expr='exact')

    class Meta:
        model = PaosOikeus
        fields = []


class VarhaiskasvatuspaatosFilter(djangofilters.FilterSet):
    lapsi = djangofilters.NumberFilter(field_name='lapsi__id', lookup_expr='exact')
    vuorohoito_kytkin = djangofilters.BooleanFilter(field_name='vuorohoito_kytkin', lookup_expr='exact')
    pikakasittely_kytkin = djangofilters.BooleanFilter(field_name='pikakasittely_kytkin', lookup_expr='exact')
    tuntimaara_viikossa = djangofilters.NumberFilter(field_name='tuntimaara_viikossa', lookup_expr='gte')
    paivittainen_vaka_kytkin = djangofilters.BooleanFilter(field_name='paivittainen_vaka_kytkin', lookup_expr='exact')
    kokopaivainen_vaka_kytkin = djangofilters.BooleanFilter(field_name='kokopaivainen_vaka_kytkin', lookup_expr='exact')
    tilapainen_vaka_kytkin = djangofilters.BooleanFilter(field_name='tilapainen_vaka_kytkin', lookup_expr='exact')
    jarjestamismuoto_koodi = djangofilters.CharFilter(field_name='jarjestamismuoto_koodi', lookup_expr='exact')
    hakemus_pvm = djangofilters.DateFilter(field_name='hakemus_pvm', lookup_expr='gte')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = Varhaiskasvatuspaatos
        fields = []


class VarhaiskasvatussuhdeFilter(djangofilters.FilterSet):
    varhaiskasvatuspaatos = djangofilters.NumberFilter(field_name='varhaiskasvatuspaatos__id', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    muutos_pvm = djangofilters.DateTimeFilter(field_name='muutos_pvm', lookup_expr='gte')

    class Meta:
        model = Varhaiskasvatussuhde
        fields = []


class TilapainenHenkilostoFilter(djangofilters.FilterSet):
    vakajarjestaja = VakaJarjestajaFieldFilter(field_name='vakajarjestaja')
    vuosi = djangofilters.NumberFilter(field_name='kuukausi__year', lookup_expr='exact')
    kuukausi = djangofilters.NumberFilter(field_name='kuukausi__month', lookup_expr='exact')

    class Meta:
        model = TilapainenHenkilosto
        fields = []


class TutkintoFilter(djangofilters.FilterSet):
    henkilo = HenkiloFieldFilter(field_name='henkilo')
    tutkinto_koodi = djangofilters.CharFilter(field_name='tutkinto_koodi', lookup_expr='exact')
    vakajarjestaja = VakaJarjestajaFieldFilter(field_name='vakajarjestaja')

    class Meta:
        model = Tutkinto
        fields = []


class PalvelussuhdeFilter(djangofilters.FilterSet):
    tyontekija = djangofilters.NumberFilter(field_name='tyontekija__id', lookup_expr='exact')
    tyosuhde_koodi = djangofilters.CharFilter(field_name='tyosuhde_koodi', lookup_expr='exact')
    tyoaika_koodi = djangofilters.CharFilter(field_name='tyoaika_koodi', lookup_expr='exact')
    tutkinto_koodi = djangofilters.CharFilter(field_name='tutkinto_koodi', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    lahdejarjestelma = djangofilters.CharFilter(field_name='lahdejarjestelma', lookup_expr='exact')
    tunniste = djangofilters.CharFilter(field_name='tunniste', lookup_expr='exact')

    class Meta:
        model = Palvelussuhde
        fields = []


class TyoskentelypaikkaFilter(djangofilters.FilterSet):
    palvelussuhde = djangofilters.NumberFilter(field_name='palvelussuhde__id', lookup_expr='exact')
    toimipaikka = djangofilters.NumberFilter(field_name='toimipaikka__id', lookup_expr='exact')
    tehtavanimike_koodi = djangofilters.CharFilter(field_name='tehtavanimike_koodi', lookup_expr='exact')
    kelpoisuus_kytkin = djangofilters.BooleanFilter(field_name='kelpoisuus_kytkin', lookup_expr='exact')
    kiertava_tyontekija_kytkin = djangofilters.BooleanFilter(field_name='kiertava_tyontekija_kytkin', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    lahdejarjestelma = djangofilters.CharFilter(field_name='lahdejarjestelma', lookup_expr='exact')
    tunniste = djangofilters.CharFilter(field_name='tunniste', lookup_expr='exact')

    class Meta:
        model = Tyoskentelypaikka
        fields = []


class PidempiPoissaoloFilter(djangofilters.FilterSet):
    palvelussuhde = djangofilters.NumberFilter(field_name='palvelussuhde__id', lookup_expr='exact')
    alkamis_pvm = djangofilters.DateFilter(field_name='alkamis_pvm', lookup_expr='gte')
    paattymis_pvm = djangofilters.DateFilter(field_name='paattymis_pvm', lookup_expr='gte')
    lahdejarjestelma = djangofilters.CharFilter(field_name='lahdejarjestelma', lookup_expr='exact')
    tunniste = djangofilters.CharFilter(field_name='tunniste', lookup_expr='exact')

    class Meta:
        model = PidempiPoissaolo
        fields = []


class TaydennyskoulutusFilter(djangofilters.FilterSet):
    tyontekija = djangofilters.NumberFilter(field_name='tyontekijat', lookup_expr='exact', distinct=True)
    henkilo_oid = djangofilters.CharFilter(field_name='tyontekijat__henkilo__henkilo_oid', lookup_expr='exact', distinct=True)
    vakajarjestaja_oid = djangofilters.CharFilter(field_name='tyontekijat__vakajarjestaja__organisaatio_oid', lookup_expr='exact', distinct=True)
    nimi = djangofilters.CharFilter(field_name='nimi', lookup_expr='icontains')
    suoritus_pvm = djangofilters.NumberFilter(field_name='suoritus_pvm', lookup_expr='exact')
    koulutuspaivia = djangofilters.NumberFilter(field_name='koulutuspaivia', lookup_expr='exact')
    lahdejarjestelma = djangofilters.CharFilter(field_name='lahdejarjestelma', lookup_expr='exact')
    tunniste = djangofilters.CharFilter(field_name='tunniste', lookup_expr='exact')

    class Meta:
        model = Taydennyskoulutus
        fields = []


class TaydennyskoulutusTyontekijaListFilter(djangofilters.FilterSet):
    vakajarjestaja_oid = djangofilters.CharFilter(field_name='vakajarjestaja__organisaatio_oid', lookup_expr='exact', distinct=True, label='vakajarjestaja_oid')
    henkilo_oid = djangofilters.CharFilter(field_name='henkilo__henkilo_oid', lookup_expr='exact', label='henkilo_oid')
    toimipaikka_oid = djangofilters.CharFilter(field_name='palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid', lookup_expr='exact', distinct=True, label='toimipaikka_oid')

    class Meta:
        model: TaydennyskoulutusTyontekija
        fields = []


class TyontekijahakuUiFilter(djangofilters.FilterSet):
    toimipaikka_id = djangofilters.NumberFilter(field_name='tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__id', label='toimipaikka_id')
    toimipaikka_oid = djangofilters.CharFilter(field_name='tyontekijat__palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid', label='toimipaikka_oid')
    kiertava_tyontekija_kytkin = djangofilters.BooleanFilter(field_name='tyontekijat__palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin', label='kiertava_tyontekija_kytkin')
    palvelussuhde_voimassa = djangofilters.DateFilter(method='filter_palvelussuhde_voimassa')

    class Meta:
        model: Henkilo
        fields = []

    def filter_palvelussuhde_voimassa(self, queryset, name, value):
        return queryset.filter(Q(tyontekijat__palvelussuhteet__alkamis_pvm__lte=value) &
                               (Q(tyontekijat__palvelussuhteet__paattymis_pvm__gte=value) |
                                Q(tyontekijat__palvelussuhteet__paattymis_pvm__isnull=True)))


class LapsihakuUiFilter(djangofilters.FilterSet):
    # Note LapsihakuLapsetUiSerializer flattens toimipaikat so nested filtering can't be done here
    toimipaikka_id = djangofilters.NumberFilter(field_name='lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__id', label='toimipaikka_id')
    toimipaikka_oid = djangofilters.CharFilter(field_name='lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet__toimipaikka__organisaatio_oid', label='toimipaikka_oid')
    vakapaatos_voimassa = djangofilters.DateFilter(method='filter_vakapaatos_voimassa')

    class Meta:
        model: Henkilo
        fields = []

    def filter_vakapaatos_voimassa(self, queryset, name, value):
        return queryset.filter(Q(lapsi__varhaiskasvatuspaatokset__alkamis_pvm__lte=value) &
                               (Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__gte=value) |
                                Q(lapsi__varhaiskasvatuspaatokset__paattymis_pvm__isnull=True)))


class TyontekijaFilter(djangofilters.FilterSet):
    vakajarjestaja_id = djangofilters.NumberFilter(field_name='vakajarjestaja__id', lookup_expr='exact', label='vakajarjestaja_id')
    vakajarjestaja_oid = djangofilters.CharFilter(field_name='vakajarjestaja__organisaatio_oid', lookup_expr='exact', label='vakajarjestaja_oid')
    henkilo_id = djangofilters.NumberFilter(field_name='henkilo__id', lookup_expr='exact', label='henkilo_id')
    henkilo_oid = djangofilters.CharFilter(field_name='henkilo__henkilo_oid', lookup_expr='exact', label='henkilo_oid')

    class Meta:
        model = Tyontekija
        fields = []


class UiTyontekijaFilter(djangofilters.FilterSet):
    """
    Can't utilize djangofilters provided filters (e.g. CharFilter), because all filters need to be inside a single
    .filter() call. If we had multiple .filter() calls, we might get tyontekija that has selected tehtavanimike in
    other toimipaikka, than the ones selected. For example, user has selected toimipaikat=1,2&tehtavanimike=001, we
    may get tyontekija that has tyoskentelypaikka in toimipaikka=1 with tehtavanimike=002 and in toimipaikka=3 with
    tehtavanimike=001.
    """

    class Meta:
        model = Tyontekija
        fields = []

    def get_rajaus_filters(self):
        query_params = self.request.query_params
        rajaus = query_params.get('rajaus', None)
        voimassaolo = query_params.get('voimassaolo', None)
        alkamis_pvm = query_params.get('alkamis_pvm', None)
        paattymis_pvm = query_params.get('paattymis_pvm', None)
        tehtavanimike_taydennyskoulutus = query_params.get('tehtavanimike_taydennyskoulutus', None)

        # voimassaolo is not required if rajaus is taydennyskoulutukset
        voimassaolo_none_and_required = not voimassaolo and rajaus != 'taydennyskoulutukset'
        if not rajaus or voimassaolo_none_and_required or not alkamis_pvm or not paattymis_pvm:
            return Q()

        rajaus = str.lower(rajaus)

        try:
            alkamis_pvm = datetime.strptime(alkamis_pvm, '%Y-%m-%d').date()
            paattymis_pvm = datetime.strptime(paattymis_pvm, '%Y-%m-%d').date()
        except ValueError:
            raise Http404

        prefixes = {
            'tyoskentelypaikat': 'palvelussuhteet__tyoskentelypaikat__',
            'palvelussuhteet': 'palvelussuhteet__',
            'poissaolot': 'palvelussuhteet__pidemmatpoissaolot__'
        }

        if rajaus in ['tyoskentelypaikat', 'palvelussuhteet', 'poissaolot']:
            prefix = prefixes[rajaus]
        elif rajaus == 'taydennyskoulutukset':
            tyontekija_filter = Q(taydennyskoulutukset__suoritus_pvm__gte=alkamis_pvm,
                                  taydennyskoulutukset__suoritus_pvm__lte=paattymis_pvm)
            if tehtavanimike_taydennyskoulutus:
                tyontekija_filter = (tyontekija_filter &
                                     Q(taydennyskoulutukset_tyontekijat__tehtavanimike_koodi=tehtavanimike_taydennyskoulutus))
            return tyontekija_filter
        else:
            return Q()

        voimassaolo = str.lower(voimassaolo)

        if voimassaolo == 'alkanut':
            return Q(**{prefix + 'alkamis_pvm__gte': alkamis_pvm}) & Q(**{prefix + 'alkamis_pvm__lte': paattymis_pvm})
        elif voimassaolo == 'paattynyt':
            return Q(**{prefix + 'paattymis_pvm__gte': alkamis_pvm}) & Q(**{prefix + 'paattymis_pvm__lte': paattymis_pvm})
        elif voimassaolo == 'voimassa':
            return (Q(**{prefix + 'alkamis_pvm__lte': alkamis_pvm}) &
                    (Q(**{prefix + 'paattymis_pvm__gte': paattymis_pvm}) | Q(**{prefix + 'paattymis_pvm__isnull': True})))

    def apply_kiertava_filter(self, toimipaikka_filter):
        kiertava_arg = self.request.query_params.get('kiertava', '').lower()
        if kiertava_arg == 'true' or kiertava_arg == 'false':
            kiertava_boolean = True if kiertava_arg == 'true' else False
            return toimipaikka_filter | Q(palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=kiertava_boolean)
        return toimipaikka_filter

    def filter_queryset(self, queryset):
        user = self.request.user
        query_params = self.request.query_params

        tyontekija_filter = Q()

        toimipaikka_id_list = parse_toimipaikka_id_list(user, query_params.get('toimipaikat', ''))
        if len(toimipaikka_id_list) > 0:
            tyontekija_filter = Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__id__in=toimipaikka_id_list)
        tyontekija_filter = self.apply_kiertava_filter(tyontekija_filter)

        tehtavanimike_arg = query_params.get('tehtavanimike', None)
        if tehtavanimike_arg:
            tyontekija_filter = tyontekija_filter & Q(palvelussuhteet__tyoskentelypaikat__tehtavanimike_koodi__iexact=tehtavanimike_arg)

        tutkinto_arg = query_params.get('tutkinto', None)
        if tutkinto_arg:
            tyontekija_filter = tyontekija_filter & Q(palvelussuhteet__tutkinto_koodi__iexact=tutkinto_arg)

        # Apply custom filters
        return queryset.filter(tyontekija_filter & self.get_rajaus_filters()).distinct('henkilo__sukunimi',
                                                                                       'henkilo__etunimet',
                                                                                       'id')


class UiAllVakajarjestajaFilter(djangofilters.FilterSet):
    tyyppi = djangofilters.CharFilter(method='filter_tyyppi')
    search = djangofilters.CharFilter(method='filter_search')

    def filter_tyyppi(self, queryset, name, value):
        if value in ['yksityinen', 'kunnallinen']:
            condition = Q(yritysmuoto__in=VakaJarjestaja.get_kuntatyypit())
            queryset = queryset.filter(condition) if value == 'kunnallinen' else queryset.exclude(condition)

        return queryset

    def filter_search(self, queryset, name, value):
        matching_kunta_koodit = (Z2_Code.objects.filter(koodisto__name=Koodistot.kunta_koodit.value,
                                                        translations__name__iexact=value)
                                 .values_list('code_value', flat=True))
        return queryset.filter(Q(nimi__icontains=value) | Q(postitoimipaikka__iexact=value) |
                               Q(organisaatio_oid=value) | Q(y_tunnus=value) | Q(kunta_koodi__in=matching_kunta_koodit))


class KelaEtuusmaksatusAloittaneetFilter(djangofilters.FilterSet):
    kunta_koodi = djangofilters.CharFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi', lookup_expr='exact', label='kotikunta_koodi')
    syntyma_pvm = djangofilters.DateFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm', lookup_expr='gte', label='syntyma_pvm')
    luonti_pvm = djangofilters.DateFilter(field_name='luonti_pvm', lookup_expr='gte', label='luonti_pvm')

    class Meta:
        model: Varhaiskasvatussuhde
        fields = []


class KelaEtuusmaksatusLopettaneetFilter(djangofilters.FilterSet):
    kunta_koodi = djangofilters.CharFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi', lookup_expr='exact', label='kotikunta_koodi')
    syntyma_pvm = djangofilters.DateFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm', lookup_expr='gte', label='syntyma_pvm')
    muutos_pvm = djangofilters.DateFilter(field_name='muutos_pvm', lookup_expr='gte', label='muutos_pvm')

    class Meta:
        model: Varhaiskasvatussuhde
        fields = []


class KelaEtuusmaksatusKorjaustiedotFilter(djangofilters.FilterSet):
    kunta_koodi = djangofilters.CharFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi', lookup_expr='exact', label='kotikunta_koodi')
    syntyma_pvm = djangofilters.DateFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm', lookup_expr='gte', label='syntyma_pvm')
    muutos_pvm = djangofilters.DateFilter(field_name='muutos_pvm', lookup_expr='gte', label='muutos_pvm')

    class Meta:
        model: Varhaiskasvatussuhde
        fields = []


class TiedonsiirtoFilter(djangofilters.FilterSet):
    timestamp = djangofilters.IsoDateTimeFromToRangeFilter()
    request_url = djangofilters.CharFilter(lookup_expr='icontains')
    request_method = djangofilters.CharFilter(lookup_expr='iexact')
    request_body = djangofilters.CharFilter(lookup_expr='icontains')
    response_body = djangofilters.CharFilter(lookup_expr='icontains')
    response_code = djangofilters.NumberFilter(lookup_expr='exact')
    lahdejarjestelma = djangofilters.CharFilter(lookup_expr='exact')
    username = djangofilters.CharFilter(lookup_expr='iexact', field_name='user__username')
    successful = djangofilters.BooleanFilter(method='filter_successful')
    search_target = djangofilters.CharFilter(method='filter_target')

    def filter_successful(self, queryset, name, value):
        if value:
            return queryset.filter(response_code__in=SUCCESSFUL_STATUS_CODE_LIST)
        else:
            return queryset.exclude(response_code__in=SUCCESSFUL_STATUS_CODE_LIST)

    def _get_target_filter_annotation(self, model, search_field_list):
        new_search_field_list = []
        for index, search_field in enumerate(search_field_list):
            new_search_field_list.append(search_field)
            if index != len(search_field_list) - 1:
                new_search_field_list.append(Value(' '))

        return StringAgg(Subquery(
            model.objects.filter(pk=OuterRef('target_id'))
            .annotate(search_field=Concat(*search_field_list, output_field=CharField()))
            .values_list('search_field', flat=True)
        ), delimiter=' ')

    def filter_target(self, queryset, name, value):
        # Clean search value
        value = re.sub(re.compile(r'[ ]{2,}'), ' ', value.strip()).strip()
        if not value:
            return queryset

        search_filter = reduce(operator.and_, (Q(search_target__icontains=search_value)
                                               for search_value in value.split(' ')))

        lapsi_model_name = Lapsi.__name__
        tyontekija_model_name = Tyontekija.__name__
        toimipaikka_model_name = Toimipaikka.__name__

        return (queryset.filter(target_model__isnull=False, target_id__isnull=False)
                .annotate(search_target=Case(
                    When(target_model=lapsi_model_name,
                         then=self._get_target_filter_annotation(Lapsi, ['henkilo__henkilo_oid',
                                                                         'henkilo__etunimet',
                                                                         'henkilo__sukunimi'])),
                    When(target_model=tyontekija_model_name,
                         then=self._get_target_filter_annotation(Tyontekija, ['henkilo__henkilo_oid',
                                                                              'henkilo__etunimet',
                                                                              'henkilo__sukunimi'])),
                    When(target_model=toimipaikka_model_name,
                         then=self._get_target_filter_annotation(Toimipaikka, ['organisaatio_oid', 'nimi'])),
                    output_field=CharField()
                )).filter(search_filter))
