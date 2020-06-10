import datetime

from django.conf import settings

from varda.cache import get_localisation_cache, set_localisation_cache
from varda.clients.lokalisointipalvelu_client import get_lokalisointi


if settings.PRODUCTION_ENV:
    # 30 minutes in production
    CACHE_INVALIDATION_SECONDS = 30 * 60
else:
    # 5 minutes in QA and testing environments
    CACHE_INVALIDATION_SECONDS = 5 * 60


def get_localisation_data(category, locale):
    cache_data = get_localisation_cache(category, locale)
    if cache_data:
        created_datetime = cache_data['created']
        now = datetime.datetime.now()
        time_in_cache = now - created_datetime

        new_data = None
        if time_in_cache.total_seconds() > CACHE_INVALIDATION_SECONDS:
            # If data has been in cache longer than CACHE_INVALIDATION_SECONDS, fetch it again
            new_data = _get_data_from_lokalisointipalvelu(category, locale)

            if not new_data:
                # Request failed or empty response, reset cache timestamp and try again in CACHE_INVALIDATION_SECONDS
                set_localisation_cache(category, locale, cache_data['data'])

        # Use new_data if got any, else use old data
        data = new_data if new_data else cache_data['data']
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
