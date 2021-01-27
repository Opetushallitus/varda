import json
import logging
import re
from functools import wraps
from json import JSONDecodeError

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet, Q
from rest_framework import status
from rest_framework.exceptions import ValidationError

from varda.misc import hide_hetu
from varda.models import Z6_RequestLog, VakaJarjestaja
from varda.validators import validate_lahdejarjestelma_koodi

logger = logging.getLogger(__name__)


def request_log_viewset_decorator_factory(target_path=None):
    def _request_log_viewset_decorator(cls):
        function_name = 'dispatch'
        original_function = getattr(cls, function_name, None)

        if not original_function:
            raise AttributeError('This decorator can only be used in a ViewSet.')

        setattr(cls, function_name,
                _request_log_dispatch_decorator(original_function, target_path))

        return cls
    return _request_log_viewset_decorator


def _request_log_dispatch_decorator(function, target_path):
    @wraps(function)
    def decorator(*args, **kwargs):
        viewset = args[0]
        request = args[1]

        # We do not want to log GET requests.
        if request.method not in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return function(*args, **kwargs)

        lahdejarjestelma = None
        request_body = ''
        if request.body:
            try:
                request_body_object = json.loads(request.body)
                request_body = json.dumps(request_body_object, cls=DjangoJSONEncoder)
                lahdejarjestelma = str(request_body_object.get('lahdejarjestelma', ''))
                validate_lahdejarjestelma_koodi(lahdejarjestelma)
            except (JSONDecodeError, UnicodeDecodeError) as decodeError:
                request_body = request.body.decode('utf-8', 'ignore')
                logger.warning(f'{decodeError}, request body: {request_body}')
            except (ValidationError, AttributeError):
                # Error validating lahdejarjestelma code
                lahdejarjestelma = None
        request_body = hide_hetu(request_body, hide_date=False)

        response = function(*args, **kwargs)

        if request.user.is_anonymous:
            # Do not log anonymous requests
            return response

        # Run this after request has been processed so that user attribute is correctly set
        vakajarjestaja = _get_user_vakajarjestaja(request.user)

        response_body = _parse_response_body(response.data)
        response_body = hide_hetu(response_body, hide_date=False)

        request_log_object = Z6_RequestLog(request_url=request.path, request_method=request.method,
                                           request_body=request_body, lahdejarjestelma=lahdejarjestelma,
                                           response_code=response.status_code, response_body=response_body,
                                           user=request.user, vakajarjestaja=vakajarjestaja)

        # If request is not POST and response is 200 or 400, we can save the request target.
        # It is difficult to determine the target if the request is POST, as the object does not yet exist
        # and might fail due to not having permissions to the target. Only status codes 200 and 400 are safe
        # (for example, if response is 404 or 403, user might not have permissions to the target,
        # in case of 204 the object has already been deleted, and 405 signifies an invalid method).
        target_valid_status_codes = [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        if request.method != 'POST' and response.status_code in target_valid_status_codes and target_path is not None:
            target_object = viewset.get_object()
            for attribute in target_path:
                target_object = getattr(target_object, attribute)
            request_log_object.target_model = target_object.__class__.__name__
            request_log_object.target_id = target_object.id

        request_log_object.save()

        return response
    return decorator


def _get_user_vakajarjestaja(user):
    """
    Determine which Vakajarjestaja user has permissions to and return it
    :param user: User object
    :return: Vakajarjestaja object if user has permissions to only one Vakajarjestaja, otherwise None
    """
    user_group_names = user.groups.values_list('name', flat=True)

    regex_pattern = re.compile(r'.*_([\d\.]*)')
    organisaatio_oid_set = {match.group(1) for group_name in user_group_names
                            if (match := regex_pattern.fullmatch(group_name)) and match.group(1)}

    # organisaatio_oid might be that of Vakajarjestaja or Toimipaikka
    vakajarjestaja_qs = VakaJarjestaja.objects.filter(Q(organisaatio_oid__in=organisaatio_oid_set) |
                                                      Q(toimipaikat__organisaatio_oid__in=organisaatio_oid_set)).distinct()
    if not vakajarjestaja_qs.exists() or vakajarjestaja_qs.count() > 1:
        # User has permissions to multiple Vakajarjestaja or has no permissions at all
        logger.warning(f'Could not determine Vakajarjestaja for user: {user}')
        return None

    return vakajarjestaja_qs.first()


def _parse_response_body(response_data):
    """
    Sometimes Response.data contains QuerySets and other types that JSON encoder does not support
    (at least in Maksutieto POST API), so we need to convert them to JSON readable format.
    :param response_data: Response.data object
    :return: dictionary with simple data types (dict, list, string, integer)
    """
    try:
        response_body = json.dumps(response_data, cls=DjangoJSONEncoder) if response_data else ''
    except TypeError as typeError:
        if 'QuerySet' in str(typeError):
            for response_key, response_value in response_data.items():
                if isinstance(response_value, QuerySet):
                    response_data[response_key] = list(response_value)
            return _parse_response_body(response_data)
        else:
            # Unidentified error, return empty response body
            logger.warning(f'{typeError}, respones body: {response_data}')
            response_body = ''

    return response_body
