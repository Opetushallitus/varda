import datetime
import logging

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.db import transaction
from functools import wraps
from hashlib import sha1
from rest_framework.exceptions import NotFound
from varda.misc import intersection, path_parse, hash_string
from varda.pagination import CustomPagination, get_requested_page_and_query_params
from varda.permissions import get_object_ids_user_has_view_permissions

# Get an instance of a logger
logger = logging.getLogger(__name__)


def get_model_name_from_view_name(view_name):
    """
    Get model_name from view_name: e.g. Vaka Jarjestaja List, return -> 'vakajarjestaja'
    Or Vaka Jarjestaja Instance, return -> 'vakajarjestaja'
    Or Nested Toimipaikka List, return -> 'toimipaikka'
    """
    splitted_view_name = view_name.replace(' ', '').lower()
    if splitted_view_name.endswith('instance'):
        return splitted_view_name.split('instance')[0]
    elif splitted_view_name == 'nestedlapsenvarhaiskasvatussuhdelist':
        return 'varhaiskasvatussuhde'
    elif splitted_view_name == 'nestedvarhaiskasvatussuhdetoimipaikkalist':
        return 'varhaiskasvatussuhde'
    elif splitted_view_name.startswith('nested'):
        return splitted_view_name.split('nested')[1][:-4]
    else:
        return splitted_view_name.split('list')[0]


def create_cache_key(id, unique_string):
    """
    An example
    Id: 35  (This can be user-id or object-id)
    Unique string: /api/v1/vakajarjestajat/?nimi=Tester2&y_tunnus=4885680-1
    Return: 4e7defb1af583fb0a89985fe0814aa3c7dd557e4
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

            if model_name == 'henkilohakulapset':
                cache_key_henkilohakulapset = create_cache_key(0, 'henkilohakulapset_list')
                henkilohakulapset_list = cache.get(cache_key_henkilohakulapset)
                if henkilohakulapset_list is None:
                    henkilohakulapset_list = []
                if cache_key not in henkilohakulapset_list:
                    henkilohakulapset_list.append(cache_key)
                cache.set(cache_key_henkilohakulapset, henkilohakulapset_list, cache_invalidation_time)

            return data
        return wrapper
    return true_decorator


def get_object_ids_user_has_permissions(user, model_name, content_type,
                                        cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME):
    """
    Cache-keys:
    - cache_key_objs_user_has_permissions = create_cache_key(user.id, model_name + '_obj_permissions')
    - cache_key_list_of_user_ids :: list of user.ids for this model --> Used for cache invalidation
    """
    cache_key_objs_user_has_permissions = create_cache_key(user.id, model_name + '_obj_permissions')
    object_ids_user_has_permissions = cache.get(cache_key_objs_user_has_permissions)
    if object_ids_user_has_permissions is None:
        object_ids_user_has_permissions = get_object_ids_user_has_view_permissions(user, model_name, content_type)
        cache.set(cache_key_objs_user_has_permissions, object_ids_user_has_permissions, cached_time)

        cache_key_list_of_users_for_this_model = create_cache_key(0, model_name + '_cache_user_list')
        list_of_user_ids_for_this_model = cache.get(cache_key_list_of_users_for_this_model)
        if list_of_user_ids_for_this_model is None:
            list_of_user_ids_for_this_model = []
        if cache_key_objs_user_has_permissions not in list_of_user_ids_for_this_model:
            list_of_user_ids_for_this_model.append(cache_key_objs_user_has_permissions)
        cache.set(cache_key_list_of_users_for_this_model, list_of_user_ids_for_this_model, cached_time)

    return object_ids_user_has_permissions


def get_object_ids_for_user_by_model(user, model_name):
    """
    Return list of IDs for certain model that user has permissions to
    :param user: User object
    :param model_name: Django model name
    :return: List of IDs
    """
    content_type = ContentType.objects.get(model=model_name)
    return get_object_ids_user_has_permissions(user, model_name, content_type)


def get_filtered_object_ids(query_param_dict_has_values, model_name, original_queryset, cached_time, request_full_path):
    """
    Cache-keys:
    - cache_key_filtered_qs = create_cache_key(0, full_path_without_page) :: dummy zero
    - cache_key_list_of_filtered_queries :: list of full_paths for this model --> Used for cache invalidation

    sorted_query_params:: string of list of tuples.
    Dummy zero below, don't matter who makes this filtering.
    """
    request_path = request_full_path.split('?')[0]
    sorted_query_params = str(sorted(query_param_dict_has_values.items(), key=lambda x: x[0]))
    cache_key_filtered_qs = create_cache_key(0, request_path + '_' + sorted_query_params)
    filtered_object_ids = cache.get(cache_key_filtered_qs)
    if filtered_object_ids is None:
        filtered_object_ids = list(original_queryset.values_list('id', flat=True))
        cache.set(cache_key_filtered_qs, filtered_object_ids, cached_time)

        cache_key_list_of_filtered_queries = create_cache_key(0, model_name + '_cache_filtered_queries')
        list_of_filtered_queries = cache.get(cache_key_list_of_filtered_queries)
        if list_of_filtered_queries is None:
            list_of_filtered_queries = []
        if cache_key_filtered_qs not in list_of_filtered_queries:
            list_of_filtered_queries.append(cache_key_filtered_qs)
        cache.set(cache_key_list_of_filtered_queries, list_of_filtered_queries, cached_time)
    return filtered_object_ids


def get_ordered_filtered_object_ids_user_has_permissions(model_cls, filtered_object_ids_user_has_permissions,
                                                         order_by, user_id, cached_time, request_full_path,
                                                         query_param_dict_has_values):
    """
    Cache-keys:
    - cache_key_ordered_filtered_ids_for_user = create_cache_key(user_id, request_path + '_ordered_' + sorted_query_params)
    - ordered_filtered_ids_for_user_cache_keys = create_cache_key(0, model_name + '_ordered_filtered_ids_users')
    """
    model_name = model_cls.__name__.lower()
    request_path = request_full_path.split('?')[0]
    sorted_query_params = str(sorted(query_param_dict_has_values.items(), key=lambda x: x[0]))

    cache_key_ordered_filtered_ids_for_user = create_cache_key(user_id,
                                                               request_path + '_ordered_' + sorted_query_params)
    ordered_filtered_ids_for_user = cache.get(cache_key_ordered_filtered_ids_for_user)
    if ordered_filtered_ids_for_user is None:
        ordered_filtered_ids_for_user = list(
            model_cls
            .objects
            .filter(id__in=filtered_object_ids_user_has_permissions)
            .values_list('id', flat=True)
            .order_by(order_by))
        cache.set(cache_key_ordered_filtered_ids_for_user, ordered_filtered_ids_for_user, cached_time)

        ordered_filtered_ids_for_user_cache_keys = create_cache_key(0, model_name + '_ordered_filtered_ids_users')
        list_of_ordered_filtered_ids_for_user_cache_keys = cache.get(ordered_filtered_ids_for_user_cache_keys)
        if list_of_ordered_filtered_ids_for_user_cache_keys is None:
            list_of_ordered_filtered_ids_for_user_cache_keys = []
        if cache_key_ordered_filtered_ids_for_user not in list_of_ordered_filtered_ids_for_user_cache_keys:
            list_of_ordered_filtered_ids_for_user_cache_keys.append(cache_key_ordered_filtered_ids_for_user)
        cache.set(ordered_filtered_ids_for_user_cache_keys, list_of_ordered_filtered_ids_for_user_cache_keys, cached_time)

    return ordered_filtered_ids_for_user


@transaction.atomic
def get_cached_page_for_non_superuser(original_list_viewset, user, request_full_path,
                                      original_queryset, cached_time, order_by):
    original_list_viewset.pagination_class = CustomPagination
    page_size = original_list_viewset.pagination_class.page_size
    requested_page_and_query_params = get_requested_page_and_query_params(original_list_viewset.request.GET)
    requested_page = requested_page_and_query_params['requested_page']
    query_param_dict_has_values = requested_page_and_query_params['query_params']
    limit = page_size * requested_page
    offset = limit - page_size

    view_name = original_list_viewset.get_view_name()
    nested_viewset = True if view_name.startswith('Nested') else False  # Requires always the filtering below
    model_name = get_model_name_from_view_name(view_name)
    try:
        content_type = ContentType.objects.get(model=model_name)
    except ContentType.DoesNotExist:
        logger.error('No content-type for model: {}'.format(model_name))
        raise NotFound
    model_cls = content_type.model_class()

    object_ids_user_has_permissions = get_object_ids_user_has_permissions(user, model_name, content_type, cached_time)
    if nested_viewset or query_param_dict_has_values:
        """
        User gave query-params and we need to perform additional filtering. Or nested viewset, e.g.
        /api/v1/lapsi/213132/varhaiskasvatussuhteet/ --> We need to perform filtering.
        Let's take the filtered objects' ids in memory (cache).
        Then we can make an intersection of objects where user has permissions, and objects that were filtered.
        """
        filtered_object_ids = get_filtered_object_ids(query_param_dict_has_values, model_name,
                                                      original_queryset, cached_time, request_full_path)
        filtered_object_ids_user_has_permissions = intersection(object_ids_user_has_permissions,
                                                                filtered_object_ids)
    else:
        """
        User didn't specify any filtering/query-params. We want to keep this
        separately so that this query remains as light as possible.
        """
        filtered_object_ids_user_has_permissions = object_ids_user_has_permissions

    if order_by != 'id':
        filtered_object_ids_user_has_permissions = get_ordered_filtered_object_ids_user_has_permissions(
            model_cls, filtered_object_ids_user_has_permissions, order_by,
            user.id, cached_time, request_full_path, query_param_dict_has_values)

    queryset_count = len(filtered_object_ids_user_has_permissions)
    queryset = (model_cls
                .objects
                .filter(id__in=filtered_object_ids_user_has_permissions[offset:limit])
                .order_by(order_by))

    total_pages = int(queryset_count / page_size)
    if queryset_count % page_size != 0:
        total_pages += 1
    if queryset_count and requested_page > total_pages:
        raise NotFound(detail='Invalid page.')

    return original_list_viewset.paginator.paginate_queryset(queryset,
                                                             original_list_viewset.request,
                                                             view=original_list_viewset,
                                                             queryset_total_count=queryset_count,
                                                             page_size=page_size,
                                                             page_number=requested_page)


def cached_list_response(original_list_viewset, user, request_full_path,
                         cached_time=settings.DEFAULT_CACHE_INVALIDATION_TIME, order_by='id'):
    """
    Note: If needed, remember to add new db-tables to varda/apps.py VardaConfig::ready()
    This is needed for cache invalidation.
    """
    original_queryset = original_list_viewset.filter_queryset(original_list_viewset.queryset)
    # Handling oph-staff users through regular object permissions effectively causes all object ids of this type in
    # db  to be fetched to cache.
    additional_details = getattr(user, 'additional_cas_user_fields', None)
    if user.is_superuser or getattr(additional_details, 'approved_oph_staff', False):  # No caching for superuser
        page = original_list_viewset.paginate_queryset(original_queryset)
    else:
        request_full_path, query_params = path_parse(request_full_path)
        page = get_cached_page_for_non_superuser(original_list_viewset, user, request_full_path,
                                                 original_queryset, cached_time, order_by)

    serializer = original_list_viewset.get_serializer(page, many=True)
    serializer_data = serializer.data
    return original_list_viewset.get_paginated_response(serializer_data)


def invalidate_cache(model_name, object_id):
    cache.delete('{}.{}'.format(model_name, object_id))  # cache-value from serializer, e.g. vakajarjestaja.3

    if model_name == 'vakajarjestaja':
        cache.delete('{}.{}'.format('vakajarjestaja-ui', object_id))

    cache_key_list_of_users_for_this_model = create_cache_key(0, model_name + '_cache_user_list')
    list_of_users_for_this_model = cache.get(cache_key_list_of_users_for_this_model)
    if list_of_users_for_this_model:
        cache.delete_many(list_of_users_for_this_model)

    cache_key_list_of_filtered_queries = create_cache_key(0, model_name + '_cache_filtered_queries')
    list_of_filtered_queries = cache.get(cache_key_list_of_filtered_queries)
    if list_of_filtered_queries:
        cache.delete_many(list_of_filtered_queries)

    ordered_filtered_ids_for_user_cache_keys = create_cache_key(0, model_name + '_ordered_filtered_ids_users')
    list_of_ordered_filtered_ids_for_user_cache_keys = cache.get(ordered_filtered_ids_for_user_cache_keys)
    if list_of_ordered_filtered_ids_for_user_cache_keys:
        cache.delete_many(list_of_ordered_filtered_ids_for_user_cache_keys)

    if model_name in ['lapsi', 'henkilo', 'maksutieto']:
        cache_key_henkilohakulapset = create_cache_key(0, 'henkilohakulapset_list')
        henkilohakulapset_list = cache.get(cache_key_henkilohakulapset)
        if henkilohakulapset_list:
            cache.delete_many(henkilohakulapset_list)


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
