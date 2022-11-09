import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import (Avg, Count, DecimalField, Exists, F, Func, OuterRef, Sum, Value, CharField, Q, Case, When,
                              BooleanField)
from django.db.models.functions import Coalesce, Lower
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda import koodistopalvelu
from varda.cache import get_koodistot_cache, get_pulssi_cache, set_koodistot_cache, set_pulssi_cache
from varda.constants import YRITYSMUOTO_KUNTA
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.koodistot import Koodistot
from varda.filters import CustomParametersFilterBackend, CustomParameter
from varda.lokalisointipalvelu import get_localisation_data
from varda.misc_queries import get_active_filter
from varda.misc_viewsets import parse_query_parameter
from varda.models import (Huoltaja, Lapsi, Maksutieto, Organisaatio, PidempiPoissaolo, Taydennyskoulutus,
                          TaydennyskoulutusTyontekija, TilapainenHenkilosto, Toimipaikka, Tyontekija, Tyoskentelypaikka,
                          Varhaiskasvatuspaatos, Z2_Koodisto, Z2_Code)
from varda.serializers_julkinen import LocalisationSerializer, KoodistotSerializer, PulssiSerializer
from webapps.api_throttles import PublicAnonThrottle


class KoodistotViewSet(GenericViewSet, ListModelMixin):
    queryset = Z2_Koodisto.objects.all().order_by('name_koodistopalvelu')
    permission_classes = (AllowAny,)
    throttle_classes = (PublicAnonThrottle,)
    pagination_class = None
    serializer_class = KoodistotSerializer
    filter_backends = (CustomParametersFilterBackend,)
    custom_parameters = (CustomParameter(name='lang', required=False, location='query', data_type='string',
                                         description='Locale code (fi/sv)'),)

    def list(self, request, *args, **kwargs):
        query_params = self.request.query_params
        language = query_params.get('lang', 'FI')
        if language.upper() not in koodistopalvelu.LANGUAGE_CODES:
            # If language doesn't exist, use default (FI)
            language = 'FI'

        koodistot_list = get_koodistot_cache(language)
        if not koodistot_list:
            """
            Codes with and without requested translation need to be fetched separately so that we can set placeholder
            for codes without translation.

            To simplify query, when fetching koodistot from koodistopalvelu, Z2_CodeTranslation instances could be
            created for missing translations.
            """
            codes_with_translation_qs = Z2_Code.objects.filter(translations__language__iexact=language)
            codes_without_translation_qs = Z2_Code.objects.filter(~Q(id__in=codes_with_translation_qs))

            today = datetime.date.today()
            active_annotation = {'active': Case(When(Q(alkamis_pvm__gt=today) | Q(paattymis_pvm__lt=today), then=False),
                                                default=True, output_field=BooleanField())}
            translation_qs = (codes_with_translation_qs
                              .annotate(name=F('translations__name'), description=F('translations__description'),
                                        **active_annotation)
                              .values('code_value', 'name', 'description', 'active', 'alkamis_pvm', 'paattymis_pvm'))
            placeholder_qs = (codes_without_translation_qs
                              .annotate(name=Value('', CharField()), description=Value('', CharField()),
                                        **active_annotation)
                              .values('code_value', 'name', 'description', 'active', 'alkamis_pvm', 'paattymis_pvm'))

            koodistot_list = []
            for koodisto in self.get_queryset():
                koodisto_obj = {
                    'name': koodisto.name_koodistopalvelu,
                    'version': koodisto.version,
                    'update_datetime': koodisto.update_datetime
                }

                codes_translation = translation_qs.filter(koodisto=koodisto)
                codes_placeholder = placeholder_qs.filter(koodisto=koodisto)

                # We need to combine QuerySets as lists so that annotations are not combined
                codes_combined = list(codes_translation) + list(codes_placeholder)
                # Combined list needs to be sorted
                codes_sorted = sorted(codes_combined, key=lambda item: (not item['active'], item['code_value']))

                koodisto_obj['codes'] = codes_sorted
                koodistot_list.append(koodisto_obj)

            set_koodistot_cache(language, koodistot_list)

        return Response(self.get_serializer(koodistot_list, many=True).data)


class LocalisationViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Get localisations from lokalisointipalvelu for given category and locale
    """
    permission_classes = (AllowAny,)
    throttle_classes = (PublicAnonThrottle,)
    pagination_class = None
    serializer_class = LocalisationSerializer
    filter_backends = (CustomParametersFilterBackend,)
    custom_parameters = (CustomParameter(name='category', required=True, location='query', data_type='string',
                                         description='Category name in lokalisointipalvelu'),
                         CustomParameter(name='locale', required=False, location='query', data_type='string',
                                         description='Locale code (fi/sv)'),)

    def get_queryset(self):
        return None

    def list(self, request, *args, **kwargs):
        query_params = request.query_params
        category = query_params.get('category', None)
        locale = query_params.get('locale', None)

        if not category:
            raise ValidationError({'errors': [ErrorMessages.LO001.value]})

        if locale and locale.lower() not in ['fi', 'sv']:
            raise ValidationError({'errors': [ErrorMessages.LO002.value]})

        data = get_localisation_data(category, locale)

        if not data:
            return Response(status=500)

        return Response(self.get_serializer(data, many=True).data)


class PulssiViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Get Varda Pulssi
    """
    permission_classes = (AllowAny,)
    throttle_classes = (PublicAnonThrottle,)
    pagination_class = None
    serializer_class = PulssiSerializer
    filter_backends = (CustomParametersFilterBackend,)
    custom_parameters = (CustomParameter(name='refresh', required=False, location='query', data_type='boolean',
                                         description='Force result refresh in non prod env'),)

    def get_queryset(self):
        return None

    def get_data(self):
        today = timezone.now()
        active_filter = get_active_filter(today)

        # Organisaatio related information
        organisaatio_count = Organisaatio.vakajarjestajat.filter(active_filter).count()
        kunta_count = Organisaatio.vakajarjestajat.filter(active_filter, yritysmuoto__in=YRITYSMUOTO_KUNTA).count()
        yksityinen_count = (Organisaatio.vakajarjestajat
                            .filter(active_filter)
                            .exclude(yritysmuoto__in=YRITYSMUOTO_KUNTA)
                            .count())

        # Toimipaikka related information
        toimipaikka_count = Toimipaikka.objects.filter(active_filter).count()

        # Toimipaikka count by toimintamuoto_koodi
        tm_codes = (Z2_Code.objects
                    .filter(koodisto__name=Koodistot.toimintamuoto_koodit.value)
                    .annotate(code_lower=Lower('code_value'))
                    .values_list('code_lower', flat=True).order_by('code_lower'))
        tm_annotations = {}
        for tm_code in tm_codes:
            tm_annotations[tm_code] = Sum(Case(When(toimintamuoto_koodi__iexact=tm_code, then=1), default=0))
        # Avoid Django's default group by id with 'temp' field
        toimipaikka_by_tm = (Toimipaikka.objects
                             .filter(active_filter)
                             .annotate(temp=Value(0)).values('temp')
                             .annotate(**tm_annotations).values(*tm_codes))[0]

        # Toimipaikka count by jarjestamismuoto_koodi
        jm_codes = (Z2_Code.objects
                    .filter(koodisto__name=Koodistot.jarjestamismuoto_koodit.value)
                    .annotate(code_lower=Lower('code_value'))
                    .values_list('code_lower', flat=True).order_by('code_lower'))
        jm_annotations = {}
        for jm_code in jm_codes:
            jm_annotations[jm_code] = Sum(Case(When(jarjestamismuoto_koodi__icontains=jm_code, then=1), default=0))
        toimipaikka_by_jm = (Toimipaikka.objects
                             .filter(active_filter)
                             .annotate(temp=Value(0)).values('temp')
                             .annotate(**jm_annotations).values(*jm_codes))[0]

        # Toimipaikka count by kasvatusopillinen_jarjestelma_koodi
        kj_codes = (Z2_Code.objects
                    .filter(koodisto__name=Koodistot.kasvatusopillinen_jarjestelma_koodit.value)
                    .annotate(code_lower=Lower('code_value'))
                    .values_list('code_lower', flat=True).order_by('code_lower'))
        kj_annotations = {}
        for kj_code in kj_codes:
            kj_annotations[kj_code] = Sum(Case(When(kasvatusopillinen_jarjestelma_koodi__iexact=kj_code, then=1),
                                               default=0))
        toimipaikka_by_kj = (Toimipaikka.objects
                             .filter(active_filter)
                             .annotate(temp=Value(0)).values('temp')
                             .annotate(**kj_annotations).values(*kj_codes))[0]

        # Toimipaikka count by asiointikieli_koodi
        # PostgreSQL specific functionality (unnest)
        toimipaikka_by_ak = {row['asiointikieli_lower']: row['count'] for row in
                             Toimipaikka.objects
                             .filter(active_filter)
                             .annotate(asiointikieli_lower=Lower(Func(F('asiointikieli_koodi'), function='unnest')))
                             .values('asiointikieli_lower')
                             .annotate(count=Count('id'))
                             .order_by('asiointikieli_lower')}
        # If asiointikieli is not one of predefined, count it to others category
        toimipaikka_by_ak_filtered = {'others': 0}
        for key, value in toimipaikka_by_ak.items():
            if key[0:2] in ['fi', 'sv', 'en', 'se']:
                # One of common languages
                toimipaikka_by_ak_filtered[key] = value
            else:
                # Other language
                toimipaikka_by_ak_filtered['others'] += value

        # Toimipaikka count with active KieliPainotus and ToiminnallinenPainotus
        kp_voimassa_filter = get_active_filter(today, prefix='kielipainotukset')
        toimipaikka_with_kp = Toimipaikka.objects.filter(active_filter & kp_voimassa_filter).distinct('id').count()
        tp_voimassa_filter = get_active_filter(today, prefix='toiminnallisetpainotukset')
        toimipaikka_with_tp = Toimipaikka.objects.filter(active_filter & tp_voimassa_filter).distinct('id').count()

        # Lapsi related information
        lapsi_active_filter = (get_active_filter(today, prefix='varhaiskasvatuspaatokset') &
                               get_active_filter(today, prefix='varhaiskasvatuspaatokset__varhaiskasvatussuhteet'))
        lapsi_count = Lapsi.objects.filter(lapsi_active_filter).distinct('henkilo_id').count()
        lapsi_kunta_count = (Lapsi.objects
                                  .filter(lapsi_active_filter &
                                          (Q(vakatoimija__yritysmuoto__in=YRITYSMUOTO_KUNTA) |
                                           Q(oma_organisaatio__yritysmuoto__in=YRITYSMUOTO_KUNTA)))
                                  .distinct('henkilo_id').count())
        lapsi_yksityinen_count = (Lapsi.objects
                                  .filter(lapsi_active_filter &
                                          ~(Q(vakatoimija__yritysmuoto__in=YRITYSMUOTO_KUNTA) |
                                            Q(oma_organisaatio__yritysmuoto__in=YRITYSMUOTO_KUNTA)))
                                  .distinct('henkilo_id').count())
        vakapaatos_count = Varhaiskasvatuspaatos.objects.filter(active_filter).count()
        paivittainen_count = (Lapsi.objects
                              .filter(lapsi_active_filter, varhaiskasvatuspaatokset__paivittainen_vaka_kytkin=True)
                              .distinct('henkilo_id').count())
        kokopaivainen_count = (Lapsi.objects
                               .filter(lapsi_active_filter, varhaiskasvatuspaatokset__kokopaivainen_vaka_kytkin=True)
                               .distinct('henkilo_id').count())
        vuorohoito_count = (Lapsi.objects
                            .filter(lapsi_active_filter, varhaiskasvatuspaatokset__vuorohoito_kytkin=True)
                            .distinct('henkilo_id').count())

        jm_lapsi_annotations = {}
        for jm_code in jm_codes:
            jm_lapsi_annotations[jm_code] = Count(Case(When(
                varhaiskasvatuspaatokset__jarjestamismuoto_koodi__iexact=jm_code, then=F('henkilo_id'))), distinct=True)
        lapsi_by_jm = (Lapsi.objects
                       .filter(lapsi_active_filter)
                       .annotate(temp=Value(0)).values('temp')
                       .annotate(**jm_lapsi_annotations).values(*jm_codes))[0]

        # Huoltaja related information
        huoltaja_vakapaatos_prefix = 'huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset'
        huoltaja_vakasuhde_prefix = 'huoltajuussuhteet__lapsi__varhaiskasvatuspaatokset__varhaiskasvatussuhteet'
        huoltaja_lapsi_active_filter = (get_active_filter(today, prefix=huoltaja_vakapaatos_prefix) &
                                        get_active_filter(today, prefix=huoltaja_vakasuhde_prefix))
        huoltaja_count = (Huoltaja.objects
                          .filter(huoltaja_lapsi_active_filter, huoltajuussuhteet__voimassa_kytkin=True)
                          .distinct('henkilo_id').count())
        asiakasmaksu_avg = Maksutieto.objects.filter(active_filter).aggregate(avg=Avg('asiakasmaksu'))

        # Tyontekija related information
        tyontekija_active_filter = (get_active_filter(today, prefix='palvelussuhteet') &
                                    get_active_filter(today, prefix='palvelussuhteet__tyoskentelypaikat') &
                                    ~Exists(PidempiPoissaolo.objects
                                            .filter(active_filter, palvelussuhde=OuterRef('palvelussuhteet'))))
        tyontekija_count = Tyontekija.objects.filter(tyontekija_active_filter).distinct('henkilo_id').count()

        # Tyoskentelypaikka count by tehtavanimike_koodi
        tn_codes = (Z2_Code.objects
                    .filter(koodisto__name=Koodistot.tehtavanimike_koodit.value)
                    .annotate(code_lower=Lower('code_value'))
                    .values_list('code_lower', flat=True).order_by('code_lower'))
        tn_annotations = {}
        for tn_code in tn_codes:
            tn_annotations[tn_code] = Sum(Case(When(tehtavanimike_koodi__iexact=tn_code, then=1), default=0))

        tyoskentelypaikka_active_filter = (active_filter & get_active_filter(today, prefix='palvelussuhde') &
                                           ~Exists(PidempiPoissaolo.objects
                                                   .filter(active_filter, palvelussuhde=OuterRef('palvelussuhde'))))
        # Count tehtavanimike_koodi per henkilo_id only once, raw query would probably be faster (SELECT FROM subquery)
        distinct_tp_subquery = (Tyoskentelypaikka.objects
                                .filter(tyoskentelypaikka_active_filter)
                                .distinct('palvelussuhde__tyontekija__henkilo_id', 'tehtavanimike_koodi')
                                .values('id'))
        tyoskentelypaikka_by_tn = (Tyoskentelypaikka.objects
                                   .filter(id__in=distinct_tp_subquery)
                                   .annotate(temp=Value(0)).values('temp')
                                   .annotate(**tn_annotations).values(*tn_codes))[0]

        # Tyontekija count with Tyoskentelypaikka in more than 1 Toimipaikka
        tyontekija_multi_count = (Tyoskentelypaikka.objects
                                  .filter(tyoskentelypaikka_active_filter)
                                  .values('palvelussuhde__tyontekija__henkilo_id')
                                  .annotate(toimipaikka_count=Count('toimipaikka_id', distinct=True),
                                            kiertava_count=Sum(Case(When(kiertava_tyontekija_kytkin=True, then=1),
                                                                    default=0)))
                                  .filter(Q(toimipaikka_count__gt=1) | Q(kiertava_count__gt=0))
                                  .values('palvelussuhde__tyontekija__henkilo_id')
                                  .count())

        # Taydennyskoulutus koulutuspaivia sum
        # Count taydennyskoulutus per henkilo_id only once, raw query would probably be faster (SELECT FROM suqbuery)
        distinct_tt_subquery = (TaydennyskoulutusTyontekija.objects
                                .distinct('tyontekija__henkilo_id', 'taydennyskoulutus_id')
                                .values('id'))
        koulutuspaiva_count = (TaydennyskoulutusTyontekija.objects
                               .filter(id__in=distinct_tt_subquery, taydennyskoulutus__suoritus_pvm__year=today.year)
                               .aggregate(sum=Coalesce(Sum('taydennyskoulutus__koulutuspaivia'), 0.0,
                                                       output_field=DecimalField())))

        taydennyskoulutus_count = Taydennyskoulutus.objects.filter(suoritus_pvm__year=today.year).count()

        # TilapainenHenkilosto tyontekijamaara and tuntimaara sum
        tilapainen_henkilosto_aggregate = (TilapainenHenkilosto.objects
                                           .filter(kuukausi__year=today.year)
                                           .aggregate(tyontekijamaara=Coalesce(Sum('tyontekijamaara'), 0),
                                                      tuntimaara=Coalesce(Sum('tuntimaara'), 0.0,
                                                                          output_field=DecimalField())))

        # Varda UI related data
        user_count = (User.objects
                      .annotate(kayttajatyyppi=F('additional_cas_user_fields__kayttajatyyppi'))
                      .values('kayttajatyyppi')
                      .annotate(count=Count('kayttajatyyppi')))
        user_count_dict = {result['kayttajatyyppi']: result['count'] for result in user_count}
        ui_login_count = user_count_dict.get(Kayttajatyyppi.VIRKAILIJA.value, 0)
        oppija_login_count = user_count_dict.get(Kayttajatyyppi.OPPIJA_CAS.value, 0)
        valtuudet_login_count = user_count_dict.get(Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value, 0)

        # Number of created Varhaiskasvatuspaatos objects with lahdejarjestelma = '1'
        month_ago = today - datetime.timedelta(days=30)
        ui_new_paatos_count = (Varhaiskasvatuspaatos.history
                               .filter(history_type='+', history_date__gte=month_ago, lahdejarjestelma='1')
                               .count())
        ui_new_tyontekija_count = (Tyontekija.history
                                   .filter(history_type='+', history_date__gte=month_ago, lahdejarjestelma='1')
                                   .count())
        ui_new_maksutieto_count = (Maksutieto.history
                                   .filter(history_type='+', history_date__gte=month_ago, lahdejarjestelma='1')
                                   .count())

        data = {
            'organisaatio_count': organisaatio_count, 'kunta_count': kunta_count, 'yksityinen_count': yksityinen_count,
            'toimipaikka_count': toimipaikka_count, 'toimipaikka_by_tm': toimipaikka_by_tm,
            'toimipaikka_by_jm': toimipaikka_by_jm, 'toimipaikka_by_kj': toimipaikka_by_kj,
            'toimipaikka_by_ak': toimipaikka_by_ak_filtered, 'toimipaikka_with_kp': toimipaikka_with_kp,
            'toimipaikka_with_tp': toimipaikka_with_tp, 'lapsi_count': lapsi_count,
            'lapsi_kunta_count': lapsi_kunta_count, 'lapsi_yksityinen_count': lapsi_yksityinen_count,
            'vakapaatos_count': vakapaatos_count, 'paivittainen_count': paivittainen_count,
            'kokopaivainen_count': kokopaivainen_count, 'vuorohoito_count': vuorohoito_count,
            'lapsi_by_jm': lapsi_by_jm, 'huoltaja_count': huoltaja_count, 'asiakasmaksu_avg': asiakasmaksu_avg['avg'],
            'tyontekija_count': tyontekija_count, 'tyoskentelypaikka_by_tn': tyoskentelypaikka_by_tn,
            'tyontekija_multi_count': tyontekija_multi_count, 'taydennyskoulutus_count': taydennyskoulutus_count,
            'koulutuspaiva_count': koulutuspaiva_count['sum'],
            'tilapainen_henkilosto_tyontekijamaara': tilapainen_henkilosto_aggregate['tyontekijamaara'],
            'tilapainen_henkilosto_tuntimaara': tilapainen_henkilosto_aggregate['tuntimaara'],
            'ui_login_count': ui_login_count, 'oppija_login_count': oppija_login_count,
            'valtuudet_login_count': valtuudet_login_count, 'ui_new_paatos_count': ui_new_paatos_count,
            'ui_new_tyontekija_count': ui_new_tyontekija_count,
            'ui_new_maksutieto_count': ui_new_maksutieto_count, 'timestamp': timezone.now()
        }
        set_pulssi_cache(data)
        return data

    @swagger_auto_schema(responses={status.HTTP_200_OK: PulssiSerializer(many=False)})
    def list(self, request, *args, **kwargs):
        # Fetch data again only if it is not cached or refresh query parameter is present in non prod env
        force_refresh = (not settings.PRODUCTION_ENV and
                         parse_query_parameter(request.query_params, 'refresh', bool) is True)
        data = get_pulssi_cache()
        if force_refresh or not data:
            data = self.get_data()
        return Response(data=data)
