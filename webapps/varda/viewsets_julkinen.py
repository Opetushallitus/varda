from django.db.models import F, Value, CharField, Q
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from varda import koodistopalvelu
from varda.cache import get_koodistot_cache, set_koodistot_cache
from varda.enums.error_messages import ErrorMessages
from varda.lokalisointipalvelu import get_localisation_data
from varda.models import Z2_Koodisto, Z2_Code
from webapps.api_throttles import PublicAnonThrottle


class KoodistotViewSet(GenericViewSet, ListModelMixin):
    queryset = Z2_Koodisto.objects.all().order_by('name_koodistopalvelu')
    permission_classes = (AllowAny,)
    throttle_classes = (PublicAnonThrottle,)

    def list(self, request, *args, **kwargs):
        """
        filter:
            lang=string
            e.g. /api/julkinen/v1/koodistot/?lang=sv
        """
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

            translation_qs = (codes_with_translation_qs
                              .annotate(name=F('translations__name'), description=F('translations__description'))
                              .values('code_value', 'name', 'description'))
            placeholder_qs = (codes_without_translation_qs
                              .annotate(name=Value('', CharField()), description=Value('', CharField()))
                              .values('code_value', 'name', 'description'))

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
                codes_sorted = sorted(codes_combined, key=lambda item: item['code_value'])

                koodisto_obj['codes'] = codes_sorted
                koodistot_list.append(koodisto_obj)

            set_koodistot_cache(language, koodistot_list)

        return Response(koodistot_list)


class LocalisationViewSet(GenericViewSet, ListModelMixin):
    """
    list:
        Get localisations from lokalisointipalvelu for given category and locale

        parameters:
            category=string (required)
            locale=string
    """
    permission_classes = (AllowAny,)
    throttle_classes = (PublicAnonThrottle,)

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

        return Response(data)
