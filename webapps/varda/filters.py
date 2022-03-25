import operator
import re
from datetime import datetime
from functools import reduce

import coreapi
import coreschema
import django_filters.rest_framework as django_filters
from django.contrib.postgres.aggregates import StringAgg
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q, Case, TextField, When, Subquery, OuterRef, CharField, Value
from django.db.models.functions import Cast, Concat, Lower
from django.http import Http404
from django.template import loader
from django_filters.constants import EMPTY_VALUES
from rest_framework.filters import BaseFilterBackend

from varda.constants import SUCCESSFUL_STATUS_CODE_LIST
from varda.enums.koodistot import Koodistot
from varda.models import (Organisaatio, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Lapsi, Huoltaja,
                          Maksutieto, PaosToiminta, PaosOikeus, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          TilapainenHenkilosto, Tutkinto, Tyontekija, Palvelussuhde, Tyoskentelypaikka,
                          PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija, Z2_Code,
                          Z4_CasKayttoOikeudet)
from varda.permissions import parse_toimipaikka_id_list


class CustomParameter:
    def __init__(self, name, data_type, required, location, description):
        self.name = name
        self.data_type = data_type
        self.required = required
        self.location = location
        self.description = description


class CustomParametersFilterBackend(BaseFilterBackend):
    template = 'varda/custom_filters.html'

    def _get_schema(self, data_type, description):
        if data_type == 'integer':
            schema = coreschema.Integer
        elif data_type == 'number':
            schema = coreschema.Number
        elif data_type == 'boolean':
            schema = coreschema.Boolean
        else:
            schema = coreschema.String

        return schema(description=description)

    def filter_queryset(self, request, queryset, view):
        return queryset

    def get_schema_fields(self, view):
        custom_parameters = getattr(view, 'custom_parameters', ())
        schema_fields = []
        for custom_parameter in custom_parameters:
            schema_fields.append(coreapi.Field(name=custom_parameter.name, location=custom_parameter.location,
                                               required=custom_parameter.required,
                                               schema=self._get_schema(custom_parameter.data_type,
                                                                       custom_parameter.description)))
        return schema_fields

    def get_schema_operation_parameters(self, view):
        custom_parameters = getattr(view, 'custom_parameters', ())
        schema_operations = []
        for custom_parameter in custom_parameters:
            schema_operations.append({'name': custom_parameter.name, 'required': custom_parameter.required,
                                      'description': custom_parameter.description, 'in': custom_parameter.location,
                                      'schema': {'type': custom_parameter.data_type}})
        return schema_operations

    def to_html(self, request, queryset, view):
        template = loader.get_template(self.template)
        return template.render({'fields': getattr(view, 'custom_parameters', ())})


class CustomCharFilter(django_filters.CharFilter):
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


class KunnallinenKytkinFilter(django_filters.BooleanFilter):
    def filter(self, qs, value):
        if value is None:
            return qs
        elif value:
            return qs.filter(yritysmuoto__in=Organisaatio.get_kuntatyypit())
        elif not value:
            return qs.filter(~Q(yritysmuoto__in=Organisaatio.get_kuntatyypit()))


class OrganisaatioFieldFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if value.isdigit():
            self.field_name += '__id'
            value = int(value)
        elif value:
            self.field_name += '__organisaatio_oid'
        return super().filter(qs, value)


class HenkiloFieldFilter(django_filters.CharFilter):
    def filter(self, qs, value):
        if value.isdigit():
            return qs.filter(henkilo=int(value))
        elif value:
            return qs.filter(henkilo__henkilo_oid=value)
        else:
            return qs


class CaseInsensitiveContainsFilter(django_filters.BaseCSVFilter):
    def filter(self, qs, value):
        if not isinstance(value, list) and not isinstance(value, tuple):
            return qs

        value = [single_value.lower() for single_value in value]
        field_name = f'i{self.field_name}'
        # Annotate new field that is ArrayField but all items are lowercase
        return (qs.annotate(**{field_name: Cast(Lower(Cast(self.field_name, output_field=TextField())),
                                                output_field=ArrayField(base_field=TextField()))})
                .filter(**{f'{field_name}__contains': value}))


class NoneDateFromToRangeFilter(django_filters.DateFromToRangeFilter):
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


class OrganisaatioFilter(django_filters.FilterSet):
    nimi = django_filters.CharFilter(lookup_expr='icontains')
    y_tunnus = django_filters.CharFilter(lookup_expr='exact')
    organisaatio_oid = CustomCharFilter(lookup_expr='exact')
    kunta_koodi = django_filters.CharFilter(lookup_expr='iexact')
    sahkopostiosoite = CustomCharFilter(lookup_expr='iexact')
    kayntiosoite = django_filters.CharFilter(lookup_expr='icontains')
    kayntiosoite_postitoimipaikka = django_filters.CharFilter(lookup_expr='icontains')
    kayntiosoite_postinumero = django_filters.CharFilter(lookup_expr='exact')
    postiosoite = django_filters.CharFilter(lookup_expr='icontains')
    postitoimipaikka = django_filters.CharFilter(lookup_expr='icontains')
    postinumero = django_filters.CharFilter(lookup_expr='exact')
    puhelinnumero = CustomCharFilter(lookup_expr='exact')
    ytjkieli = django_filters.CharFilter(lookup_expr='iexact')
    kunnallinen_kytkin = KunnallinenKytkinFilter(label='kunnallinen_kytkin')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = Organisaatio
        fields = []


class ToimipaikkaFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(lookup_expr='exact')
    nimi = django_filters.CharFilter(lookup_expr='icontains')
    organisaatio_oid = CustomCharFilter(lookup_expr='exact')
    kayntiosoite = django_filters.CharFilter(lookup_expr='icontains')
    kayntiosoite_postitoimipaikka = django_filters.CharFilter(lookup_expr='icontains')
    kayntiosoite_postinumero = django_filters.CharFilter(lookup_expr='exact')
    postiosoite = django_filters.CharFilter(lookup_expr='icontains')
    postitoimipaikka = django_filters.CharFilter(lookup_expr='icontains')
    postinumero = django_filters.CharFilter(lookup_expr='exact')
    puhelinnumero = CustomCharFilter(lookup_expr='exact')
    sahkopostiosoite = CustomCharFilter(lookup_expr='iexact')
    kasvatusopillinen_jarjestelma_koodi = CustomCharFilter(lookup_expr='iexact')
    toimintamuoto_koodi = CustomCharFilter(lookup_expr='iexact')
    asiointikieli_koodi = CaseInsensitiveContainsFilter()
    jarjestamismuoto_koodi = CaseInsensitiveContainsFilter()
    varhaiskasvatuspaikat = django_filters.NumberFilter(lookup_expr='gte')
    alkamis_pvm = django_filters.DateFromToRangeFilter()
    paattymis_pvm = NoneDateFromToRangeFilter()
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')
    vakajarjestaja = OrganisaatioFieldFilter()

    class Meta:
        model = Toimipaikka
        fields = []


class ToiminnallinenPainotusFilter(django_filters.FilterSet):
    toimintapainotus_koodi = django_filters.CharFilter(lookup_expr='iexact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = ToiminnallinenPainotus
        fields = []


class KieliPainotusFilter(django_filters.FilterSet):
    kielipainotus_koodi = django_filters.CharFilter(lookup_expr='iexact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = KieliPainotus
        fields = []


class YksiloimattomatHenkilotFilter(django_filters.FilterSet):
    henkilotunnus = CustomCharFilter(lookup_expr='iexact')
    henkilo_oid = CustomCharFilter(lookup_expr='exact')
    vakatoimija_oid = django_filters.CharFilter(method='filter_vakatoimija_oid')

    class Meta:
        model = Henkilo
        fields = []

    def filter_vakatoimija_oid(self, queryset, name, value):
        return queryset.filter(Q(lapsi__vakatoimija__organisaatio_oid=value) |
                               Q(tyontekijat__vakajarjestaja__organisaatio_oid=value))


class LapsiFilter(django_filters.FilterSet):
    paos_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = Lapsi
        fields = []


class HuoltajaFilter(django_filters.FilterSet):
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = Huoltaja
        fields = []


class MaksutietoFilter(django_filters.FilterSet):
    lapsi = django_filters.NumberFilter(field_name='huoltajuussuhteet__lapsi__id', lookup_expr='exact', label='lapsi_id')
    maksun_peruste_koodi = django_filters.CharFilter(lookup_expr='iexact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')

    class Meta:
        model = Maksutieto
        fields = []


class PaosToimintaFilter(django_filters.FilterSet):
    oma_organisaatio = OrganisaatioFieldFilter(lookup_expr='exact')
    paos_organisaatio = OrganisaatioFieldFilter(lookup_expr='exact')
    paos_toimipaikka = OrganisaatioFieldFilter(lookup_expr='exact')
    voimassa_kytkin = django_filters.BooleanFilter(lookup_expr='exact')

    class Meta:
        model = PaosToiminta
        fields = []


class PaosOikeusFilter(django_filters.FilterSet):
    jarjestaja_kunta_organisaatio = OrganisaatioFieldFilter(lookup_expr='exact')
    tuottaja_organisaatio = OrganisaatioFieldFilter(lookup_expr='exact')

    class Meta:
        model = PaosOikeus
        fields = []


class VarhaiskasvatuspaatosFilter(django_filters.FilterSet):
    lapsi = django_filters.NumberFilter(field_name='lapsi__id', lookup_expr='exact')
    vuorohoito_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    pikakasittely_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    tuntimaara_viikossa = django_filters.NumberFilter(lookup_expr='gte')
    paivittainen_vaka_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    kokopaivainen_vaka_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    tilapainen_vaka_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    jarjestamismuoto_koodi = django_filters.CharFilter(lookup_expr='iexact')
    hakemus_pvm = django_filters.DateFilter(lookup_expr='gte')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = Varhaiskasvatuspaatos
        fields = []


class VarhaiskasvatussuhdeFilter(django_filters.FilterSet):
    varhaiskasvatuspaatos = django_filters.NumberFilter(field_name='varhaiskasvatuspaatos__id', lookup_expr='exact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    muutos_pvm = django_filters.DateTimeFilter(lookup_expr='gte')

    class Meta:
        model = Varhaiskasvatussuhde
        fields = []


class TilapainenHenkilostoFilter(django_filters.FilterSet):
    vakajarjestaja = OrganisaatioFieldFilter()
    vuosi = django_filters.NumberFilter(field_name='kuukausi__year', lookup_expr='exact')
    kuukausi = django_filters.NumberFilter(field_name='kuukausi__month', lookup_expr='exact')

    class Meta:
        model = TilapainenHenkilosto
        fields = []


class TutkintoFilter(django_filters.FilterSet):
    henkilo = HenkiloFieldFilter()
    tutkinto_koodi = django_filters.CharFilter(lookup_expr='iexact')
    vakajarjestaja = OrganisaatioFieldFilter()

    class Meta:
        model = Tutkinto
        fields = []


class PalvelussuhdeFilter(django_filters.FilterSet):
    tyontekija = django_filters.NumberFilter(field_name='tyontekija__id', lookup_expr='exact')
    tyosuhde_koodi = django_filters.CharFilter(lookup_expr='iexact')
    tyoaika_koodi = django_filters.CharFilter(lookup_expr='iexact')
    tutkinto_koodi = django_filters.CharFilter(lookup_expr='iexact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    tunniste = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Palvelussuhde
        fields = []


class TyoskentelypaikkaFilter(django_filters.FilterSet):
    palvelussuhde = django_filters.NumberFilter(field_name='palvelussuhde__id', lookup_expr='exact')
    toimipaikka = django_filters.NumberFilter(field_name='toimipaikka__id', lookup_expr='exact')
    tehtavanimike_koodi = django_filters.CharFilter(lookup_expr='iexact')
    kelpoisuus_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    kiertava_tyontekija_kytkin = django_filters.BooleanFilter(lookup_expr='exact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    tunniste = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Tyoskentelypaikka
        fields = []


class PidempiPoissaoloFilter(django_filters.FilterSet):
    palvelussuhde = django_filters.NumberFilter(field_name='palvelussuhde__id', lookup_expr='exact')
    alkamis_pvm = django_filters.DateFilter(lookup_expr='gte')
    paattymis_pvm = django_filters.DateFilter(lookup_expr='gte')
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    tunniste = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = PidempiPoissaolo
        fields = []


class TaydennyskoulutusFilter(django_filters.FilterSet):
    tyontekija = django_filters.NumberFilter(field_name='tyontekijat', lookup_expr='exact', distinct=True)
    henkilo_oid = django_filters.CharFilter(field_name='tyontekijat__henkilo__henkilo_oid', lookup_expr='exact', distinct=True)
    vakajarjestaja_oid = django_filters.CharFilter(field_name='tyontekijat__vakajarjestaja__organisaatio_oid', lookup_expr='exact', distinct=True)
    nimi = django_filters.CharFilter(lookup_expr='icontains')
    suoritus_pvm = django_filters.NumberFilter(lookup_expr='exact')
    koulutuspaivia = django_filters.NumberFilter(lookup_expr='exact')
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    tunniste = django_filters.CharFilter(lookup_expr='exact')

    class Meta:
        model = Taydennyskoulutus
        fields = []


class TaydennyskoulutusTyontekijaListFilter(django_filters.FilterSet):
    vakajarjestaja_oid = django_filters.CharFilter(field_name='vakajarjestaja__organisaatio_oid', lookup_expr='exact', distinct=True, label='vakajarjestaja_oid')
    henkilo_oid = django_filters.CharFilter(field_name='henkilo__henkilo_oid', lookup_expr='exact', label='henkilo_oid')
    toimipaikka_oid = django_filters.CharFilter(field_name='palvelussuhteet__tyoskentelypaikat__toimipaikka__organisaatio_oid', lookup_expr='exact', distinct=True, label='toimipaikka_oid')

    class Meta:
        model: TaydennyskoulutusTyontekija
        fields = []


class TyontekijaFilter(django_filters.FilterSet):
    vakajarjestaja_id = django_filters.NumberFilter(field_name='vakajarjestaja__id', lookup_expr='exact', label='vakajarjestaja_id')
    vakajarjestaja_oid = django_filters.CharFilter(field_name='vakajarjestaja__organisaatio_oid', lookup_expr='exact', label='vakajarjestaja_oid')
    henkilo_id = django_filters.NumberFilter(field_name='henkilo__id', lookup_expr='exact', label='henkilo_id')
    henkilo_oid = django_filters.CharFilter(field_name='henkilo__henkilo_oid', lookup_expr='exact', label='henkilo_oid')

    class Meta:
        model = Tyontekija
        fields = []


class UiTyontekijaFilter(django_filters.FilterSet):
    """
    Can't utilize django_filters provided filters (e.g. CharFilter), because all filters need to be inside a single
    .filter() call. If we had multiple .filter() calls, we might get tyontekija that has selected tehtavanimike in
    other toimipaikka, than the ones selected. For example, user has selected toimipaikat=1,2&tehtavanimike=001, we
    may get tyontekija that has tyoskentelypaikka in toimipaikka=1 with tehtavanimike=002 and in toimipaikka=3 with
    tehtavanimike=001.
    """
    class Meta:
        model = Tyontekija
        fields = []

    def __init__(self, *args, **kwargs):
        self.has_vakajarjestaja_tyontekija_permissions = kwargs.pop('has_vakajarjestaja_tyontekija_permissions', False)
        super(UiTyontekijaFilter, self).__init__(*args, **kwargs)

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

    def apply_kiertava_filter(self, tyontekija_filter):
        kiertava_arg = self.request.query_params.get('kiertava', '').lower()
        # Filter by kiertava_kytkin only with vakajarjestaja level permissions
        if self.has_vakajarjestaja_tyontekija_permissions and (kiertava_arg == 'true' or kiertava_arg == 'false'):
            kiertava_boolean = True if kiertava_arg == 'true' else False
            return tyontekija_filter | Q(palvelussuhteet__tyoskentelypaikat__kiertava_tyontekija_kytkin=kiertava_boolean)
        return tyontekija_filter

    def filter_queryset(self, queryset):
        user = self.request.user
        query_params = self.request.query_params

        tyontekija_filter = Q()

        required_permission_groups = (Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                                      Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                                      Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA,
                                      Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,)
        toimipaikka_id_list = parse_toimipaikka_id_list(user, query_params.get('toimipaikat', ''),
                                                        required_permission_groups)
        if len(toimipaikka_id_list) > 0:
            tyontekija_filter = Q(palvelussuhteet__tyoskentelypaikat__toimipaikka__id__in=toimipaikka_id_list)
        tyontekija_filter = self.apply_kiertava_filter(tyontekija_filter)

        tehtavanimike_arg = query_params.get('tehtavanimike', None)
        if tehtavanimike_arg:
            tyontekija_filter = tyontekija_filter & Q(palvelussuhteet__tyoskentelypaikat__tehtavanimike_koodi__iexact=tehtavanimike_arg)

        tutkinto_arg = query_params.get('tutkinto', None)
        if tutkinto_arg:
            tyontekija_filter = tyontekija_filter & Q(palvelussuhteet__tutkinto_koodi__iexact=tutkinto_arg)

        tyosuhde_arg = query_params.get('tyosuhde', None)
        if tyosuhde_arg:
            tyontekija_filter = tyontekija_filter & Q(palvelussuhteet__tyosuhde_koodi__iexact=tyosuhde_arg)

        # Apply custom filters
        return queryset.filter(tyontekija_filter & self.get_rajaus_filters()).distinct('henkilo__sukunimi',
                                                                                       'henkilo__etunimet',
                                                                                       'id')


class UiAllVakajarjestajaFilter(django_filters.FilterSet):
    tyyppi = django_filters.CharFilter(method='filter_tyyppi')
    search = django_filters.CharFilter(method='filter_search')

    def filter_tyyppi(self, queryset, name, value):
        if value in ['yksityinen', 'kunnallinen']:
            condition = Q(yritysmuoto__in=Organisaatio.get_kuntatyypit())
            queryset = queryset.filter(condition) if value == 'kunnallinen' else queryset.exclude(condition)

        return queryset

    def filter_search(self, queryset, name, value):
        matching_kunta_koodit = (Z2_Code.objects.filter(koodisto__name=Koodistot.kunta_koodit.value,
                                                        translations__name__iexact=value)
                                 .values_list('code_value', flat=True))
        return queryset.filter(Q(nimi__icontains=value) | Q(postitoimipaikka__iexact=value) |
                               Q(organisaatio_oid=value) | Q(y_tunnus=value) | Q(kunta_koodi__in=matching_kunta_koodit))


class KelaEtuusmaksatusFilter(django_filters.FilterSet):
    kunta_koodi = django_filters.CharFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi', lookup_expr='exact', label='kotikunta_koodi')
    syntyma_pvm = django_filters.DateFilter(field_name='varhaiskasvatuspaatos__lapsi__henkilo__syntyma_pvm', lookup_expr='gte', label='syntyma_pvm')

    class Meta:
        model: Varhaiskasvatussuhde
        fields = []


class TiedonsiirtoFilter(django_filters.FilterSet):
    timestamp = django_filters.IsoDateTimeFromToRangeFilter()
    request_url = django_filters.CharFilter(lookup_expr='icontains')
    request_method = django_filters.CharFilter(lookup_expr='iexact')
    request_body = django_filters.CharFilter(lookup_expr='icontains')
    response_body = django_filters.CharFilter(lookup_expr='icontains')
    response_code = django_filters.NumberFilter(lookup_expr='exact')
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='exact')
    username = django_filters.CharFilter(lookup_expr='iexact', field_name='user__username')
    successful = django_filters.BooleanFilter(method='filter_successful')
    search_target = django_filters.CharFilter(method='filter_target')

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


class ExcelReportFilter(django_filters.FilterSet):
    vakajarjestaja = OrganisaatioFieldFilter()
    toimipaikka = OrganisaatioFieldFilter()
    user_id = django_filters.NumberFilter(field_name='user__id')
    username = django_filters.NumberFilter(lookup_expr='iexact', field_name='user__username')
    status = django_filters.CharFilter()
    report_type = django_filters.CharFilter()


class TransferOutageReportFilter(django_filters.FilterSet):
    vakajarjestaja = OrganisaatioFieldFilter()
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    username = django_filters.CharFilter(lookup_expr='icontains', field_name='user__username')


class RequestSummaryFilter(django_filters.FilterSet):
    summary_date = django_filters.DateFromToRangeFilter()
    vakajarjestaja = OrganisaatioFieldFilter()
    lahdejarjestelma = django_filters.CharFilter(lookup_expr='iexact')
    username = django_filters.CharFilter(lookup_expr='icontains', field_name='user__username')
    request_url_simple = django_filters.CharFilter(lookup_expr='icontains')
