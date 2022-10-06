import datetime
import logging

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from functools import wraps
from hashlib import sha1
from varda.misc import hash_string
from varda.permissions import get_ids_user_has_permissions_by_type


logger = logging.getLogger(__name__)


def create_cache_key(id, unique_string):
    """
    Create cache key
    :param id: This can be user ID or object ID
    :param unique_string: unique string, e.g. /api/v1/vakajarjestajat/?nimi=Tester2&y_tunnus=4885680-1
    :return: hashed cache key, e.g. 4e7defb1af583fb0a89985fe0814aa3c7dd557e4
    """
    return sha1(('%s:%s' % (id, unique_string)).encode('utf-8')).hexdigest()


def caching_to_representation(model_name, cache_invalidation_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    """
    Taken from: https://stackoverflow.com/a/45013836
    """
    def true_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            instance = args[1]
            cache_key = '{}.{}'.format(model_name, instance.id)

            data = cache.get(cache_key)
            if data is not None:
                return data

            data = f(*args, **kwargs)
            cache.set(cache_key, data, cache_invalidation_time)

            return data
        return wrapper
    return true_decorator


def get_object_ids_user_has_permissions(user, model, cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    """
    Cache-keys:
    - cache_key_objs_user_has_permissions = create_cache_key(user.id, model_name + '_obj_permissions')
    - cache_key_list_of_user_ids :: list of user.ids for this model --> Used for cache invalidation
    :param user: User object
    :param model: Django model
    :param cached_time: Time IDs are stored in cache
    :return: List of IDs
    """
    if isinstance(user, AnonymousUser):
        # Swagger uses AnonymousUser so in that case return an empty tuple
        return ()

    model_name = model.get_name()

    cache_key_objs_user_has_permissions = create_cache_key(user.id, model_name + '_obj_permissions')
    object_ids_user_has_permissions = cache.get(cache_key_objs_user_has_permissions)
    if object_ids_user_has_permissions is None:
        object_ids_user_has_permissions = get_ids_user_has_permissions_by_type(user, model)
        cache.set(cache_key_objs_user_has_permissions, object_ids_user_has_permissions, cached_time)

        cache_key_list_of_users_for_this_model = create_cache_key(0, model_name + '_cache_user_list')
        list_of_user_ids_for_this_model = cache.get(cache_key_list_of_users_for_this_model)
        if list_of_user_ids_for_this_model is None:
            list_of_user_ids_for_this_model = []
        if cache_key_objs_user_has_permissions not in list_of_user_ids_for_this_model:
            list_of_user_ids_for_this_model.append(cache_key_objs_user_has_permissions)
        cache.set(cache_key_list_of_users_for_this_model, list_of_user_ids_for_this_model, cached_time)

    return object_ids_user_has_permissions


def invalidate_cache(model_name, object_id):
    cache.delete('{}.{}'.format(model_name, object_id))  # cache-value from serializer, e.g. vakajarjestaja.3

    if model_name == 'organisaatio':
        cache.delete('{}.{}'.format('organisaatio-ui', object_id))

    cache_key_list_of_users_for_this_model = create_cache_key(0, model_name + '_cache_user_list')
    list_of_users_for_this_model = cache.get(cache_key_list_of_users_for_this_model)
    if list_of_users_for_this_model:
        cache.delete_many(list_of_users_for_this_model)


def delete_cache_keys_related_model(model_name, object_id):
    cache.delete('{}.{}'.format(model_name, object_id))  # cache-value from serializer, e.g. vakajarjestaja.3


def delete_toimipaikan_lapset_cache(toimipaikka_id):
    list_of_toimipaikan_lapset_cache_keys = cache.get('toimipaikan_lapset_' + toimipaikka_id)
    if list_of_toimipaikan_lapset_cache_keys:
        cache.delete('toimipaikan_lapset_' + toimipaikka_id)
        cache.delete_many(list_of_toimipaikan_lapset_cache_keys)


def delete_object_ids_user_has_permissions(user_id):
    """
    Here we assume if the model is audit loggable, user has cache keys for that specific model.
    """
    from django.apps import apps
    from django.db import transaction
    cache_keys = []
    with transaction.atomic():
        app_models = apps.get_app_config('varda').get_models()
        for model in app_models:
            if hasattr(model, 'audit_loggable') and model.audit_loggable:
                model_name = model.__name__.lower()
                cache_key_objs_user_has_permissions = create_cache_key(user_id, model_name + '_obj_permissions')
                cache_keys.append(cache_key_objs_user_has_permissions)
        cache.delete_many(cache_keys)


def delete_cached_user_permissions_for_model(user_id, model_name):
    cache_key_objs_user_has_permissions = create_cache_key(user_id, model_name + '_obj_permissions')
    cache.delete(cache_key_objs_user_has_permissions)


def get_koodistot_cache(language):
    return cache.get('koodistot.{}'.format(language.upper()))


def set_koodistot_cache(language, data, cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    cache.set('koodistot.{}'.format(language.upper()), data, cached_time)


def get_localisation_cache(category, locale):
    # keys are hashed to prevent malformed keys in cache
    category = hash_string(category.lower())
    if locale:
        return cache.get('lokalisointi.{0}.{1}'.format(category, locale.lower()))
    else:
        return cache.get('lokalisointi.{}'.format(category))


def set_localisation_cache(category, locale, data, cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    cache_data = {
        'data': data,
        'created': datetime.datetime.now()
    }
    # keys are hashed to prevent malformed keys in cache
    category = hash_string(category.lower())
    if locale:
        cache.set('lokalisointi.{0}.{1}'.format(category, locale.lower()), cache_data, cached_time)
    else:
        cache.set('lokalisointi.{}'.format(category), cache_data, cached_time)


def set_paattymis_pvm_cache(identifier, data, cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    cache.set(f'paattymis_pvm_{identifier}', data, cached_time)


def get_paattymis_pvm_cache(identifier):
    return cache.get(f'paattymis_pvm_{identifier}', None)


def delete_paattymis_pvm_cache(identifier):
    return cache.delete(f'paattymis_pvm_{identifier}')


def set_pulssi_cache(data):
    # Data cached for 10 minutes
    cache.set('varda_pulssi', data, 60 * 10)


def get_pulssi_cache():
    return cache.get('varda_pulssi', None)


def delete_organisaatio_yhteenveto_cache(organisaatio_id):
    cache.delete(f'organisaatio_yhteenveto_{organisaatio_id}')
