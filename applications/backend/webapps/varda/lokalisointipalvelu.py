import datetime
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from varda.cache import get_localisation_cache, set_localisation_cache
from varda.clients.lokalisointipalvelu_client import get_lokalisointi
from varda.enums.lokalisointi import Lokalisointi
from varda.enums.supported_language import SupportedLanguage
from varda.models import Z2_Code, Z2_CodeTranslation, Z2_Koodisto


logger = logging.getLogger(__name__)
LOKALISOINTIPALVELU_DICT = {
    Lokalisointi.VIRKAILIJA: "varda-virkailija",
    Lokalisointi.KANSALAINEN: "varda-huoltaja",
    Lokalisointi.JULKINEN: "varda-public",
}


if settings.PRODUCTION_ENV:
    # 30 minutes in production
    CACHE_INVALIDATION_SECONDS = 30 * 60
else:
    # 5 minutes in QA and testing environments
    CACHE_INVALIDATION_SECONDS = 5 * 60


def get_localisation_data(category, locale):
    cache_data = get_localisation_cache(category, locale)
    if cache_data:
        created_datetime = cache_data["created"]
        now = datetime.datetime.now()
        time_in_cache = now - created_datetime

        new_data = None
        if time_in_cache.total_seconds() > CACHE_INVALIDATION_SECONDS:
            # If data has been in cache longer than CACHE_INVALIDATION_SECONDS, fetch it again
            new_data = _get_data_from_lokalisointipalvelu(category, locale)

            if not new_data:
                # Request failed or empty response, reset cache timestamp and try again in CACHE_INVALIDATION_SECONDS
                set_localisation_cache(category, locale, cache_data["data"])

        # Use new_data if got any, else use old data
        data = new_data if new_data else cache_data["data"]
    else:
        # Get localisation data from lokalisointipalvelu if it doesn't exist in cache
        data = _get_data_from_lokalisointipalvelu(category, locale)

    return data


def _get_data_from_lokalisointipalvelu(category, locale):
    data = get_lokalisointi(category, locale)
    if data:
        # If data received (not empty response), set it to cache
        set_localisation_cache(category, locale, data)

    return data


def update_lokalisointi_data():
    """
    Update lokalisointi data that is stored in database.
    Data uses Z2_Koodisto, Z2_Code and Z2_CodeTranslation models as it conforms to the structure of koodisto data.
    """
    for category_key, category in LOKALISOINTIPALVELU_DICT.items():
        # Get all values regardless of locale
        lokalisointi_result_raw = get_lokalisointi(category, None)
        if not lokalisointi_result_raw:
            # Lokalisointipalvelu response was empty, continue to next lokalisointi
            logger.warning("Could not get lokalisointi {} from lokalisointipalvelu".format(category))
            continue

        lokalisointi_result = {}
        for lokalisointi in lokalisointi_result_raw:
            lokalisointi_result[lokalisointi["key"]] = lokalisointi_result.get(lokalisointi["key"], [])
            lokalisointi_result[lokalisointi["key"]].append({"locale": lokalisointi["locale"], "value": lokalisointi["value"]})

        koodisto_obj, koodisto_created = Z2_Koodisto.objects.get_or_create(
            name=category_key.value,
            defaults={
                "name_koodistopalvelu": category,
                "version": 1,
                "update_datetime": timezone.now(),  # Only used when created
            },
        )

        koodisto_changed = False
        new_code_list = []
        for lokalisointi_key, lokalisointi_value in lokalisointi_result.items():
            new_code_list.append(lokalisointi_key)
            code_obj, created = Z2_Code.objects.update_or_create(koodisto=koodisto_obj, code_value=lokalisointi_key)

            new_translation_list = []
            for translation in lokalisointi_value:
                new_translation_list.append(translation["locale"])
                codetranslation_obj, codetranslation_created = Z2_CodeTranslation.objects.get_or_create(
                    code=code_obj, language=translation["locale"], defaults={"name": translation["value"], "description": ""}
                )
                if codetranslation_created:
                    koodisto_changed = True
                elif codetranslation_obj.name != translation["value"] or codetranslation_obj.description != "":
                    # update if there is changes
                    codetranslation_obj.name = translation["value"]
                    codetranslation_obj.description = ""
                    codetranslation_obj.save()
                    koodisto_changed = True

            with transaction.atomic():
                # Check if there are any old translations
                old_translation_qs = Z2_CodeTranslation.objects.filter(Q(code=code_obj) & ~Q(language__in=new_translation_list))
                old_translation_qs.delete()

        if koodisto_changed:
            koodisto_obj.update_datetime = timezone.now()
            koodisto_obj.save()

        with transaction.atomic():
            # Check if there are any old codes
            old_code_qs = Z2_Code.objects.filter(Q(koodisto=koodisto_obj) & ~Q(code_value__in=new_code_list))
            if old_code_qs.exists():
                Z2_CodeTranslation.objects.filter(code__in=old_code_qs).delete()
                old_code_qs.delete()


def get_translation(translation_key, locale=SupportedLanguage.FI.value, category=Lokalisointi.VIRKAILIJA.value):
    if locale.upper() not in SupportedLanguage.list():
        # If locale is not supported, use default locale (FI)
        locale = SupportedLanguage.FI.value

    translation_qs = Z2_CodeTranslation.objects.filter(
        code__code_value__contains=translation_key, language__iexact=locale, code__koodisto__name=category
    )
    return getattr(translation_qs.first(), "name", None) or translation_key
