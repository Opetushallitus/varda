import json
import logging
import re
from functools import wraps
from json import JSONDecodeError

from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import QuerySet
from rest_framework import status
from rest_framework.exceptions import ValidationError

from varda.enums.data_category import DataCategory
from varda.helper_functions import hide_hetu
from varda.misc import path_parse
from varda.models import Z12_DataAccessLog, Z5_AuditLog, Z6_RequestLog
from varda.permissions import get_related_organisaatio_for_user
from varda.validators import validate_lahdejarjestelma_koodi


logger = logging.getLogger(__name__)


def request_log_viewset_decorator_factory(target_path=None, log_anonymous=False):
    def _request_log_viewset_decorator(cls):
        function_name = "dispatch"
        original_function = getattr(cls, function_name, None)

        if not original_function:
            raise AttributeError("This decorator can only be used in a ViewSet.")

        setattr(cls, function_name, _request_log_dispatch_decorator(original_function, target_path, log_anonymous))

        return cls

    return _request_log_viewset_decorator


def _request_log_dispatch_decorator(function, target_path, log_anonymous):
    @wraps(function)
    def decorator(*args, **kwargs):
        viewset = args[0]
        request = args[1]

        # We do not want to log GET requests.
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return function(*args, **kwargs)

        # Parse body and lahdejarjestelma from request
        request_body, lahdejarjestelma = _parse_request_body(request.body)

        response = function(*args, **kwargs)

        # Run this after request has been processed so that user attribute is correctly set
        user = None if request.user.is_anonymous else request.user
        if not user and not log_anonymous:
            # Do not log anonymous requests by default
            return response

        # Run this after request has been processed so that user attribute is correctly set
        vakajarjestaja = _get_vakajarjestaja_for_user(user) if user else None

        # Parse data from response
        response_body = _parse_response_body(response.data)

        request_log_object = Z6_RequestLog(
            request_url=request.path,
            request_method=request.method,
            request_body=request_body,
            lahdejarjestelma=lahdejarjestelma,
            response_code=response.status_code,
            response_body=response_body,
            user=user,
            vakajarjestaja=vakajarjestaja,
            data_category=_get_data_category(request.path),
        )

        # If request is not POST and response is 200 or 400, we can save the request target.
        # It is difficult to determine the target if the request is POST, as the object does not yet exist
        # and might fail due to not having permissions to the target. Only status codes 200 and 400 are safe
        # (for example, if response is 404 or 403, user might not have permissions to the target,
        # in case of 204 the object has already been deleted, and 405 signifies an invalid method).
        target_valid_status_codes = [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        if request.method != "POST" and response.status_code in target_valid_status_codes and target_path is not None:
            target_object = viewset.get_object()
            for attribute in target_path:
                target_object = getattr(target_object, attribute)
                request_log_object.target_model = target_object.__class__.__name__
                request_log_object.target_id = target_object.id

        request_log_object.save()

        return response

    return decorator


def _parse_request_body(request_body):
    """
    Return text representation of request_body, and lahdejarjestelma code if it can be determined from request
    :param request_body: request.body
    :return: (request_body, lahdejarjestelma code)
    """
    lahdejarjestelma = None
    request_body_parsed = ""
    if request_body:
        try:
            request_body_object = json.loads(request_body)
            request_body_parsed = json.dumps(request_body_object, cls=DjangoJSONEncoder)
            lahdejarjestelma = str(request_body_object.get("lahdejarjestelma", ""))
            validate_lahdejarjestelma_koodi(lahdejarjestelma)
        except (JSONDecodeError, UnicodeDecodeError) as decodeError:
            request_body_parsed = request_body.decode("utf-8", "ignore")
            logger.warning(f"{decodeError}, request body: {request_body}")
        except (ValidationError, AttributeError):
            # Error validating lahdejarjestelma code
            lahdejarjestelma = None

    request_body_parsed = hide_hetu(request_body_parsed, hide_date=False)

    return request_body_parsed, lahdejarjestelma


def _parse_response_body(response_data):
    """
    Sometimes Response.data contains QuerySets and other types that JSON encoder does not support
    (at least in Maksutieto POST API), so we need to convert them to JSON readable format.
    :param response_data: Response.data object
    :return: dictionary with simple data types (dict, list, string, integer)
    """
    try:
        response_body = json.dumps(response_data, cls=DjangoJSONEncoder) if response_data else ""
    except TypeError as type_error:
        if "QuerySet" in str(type_error):
            for response_key, response_value in response_data.items():
                if isinstance(response_value, QuerySet):
                    response_data[response_key] = list(response_value)
            return _parse_response_body(response_data)
        else:
            # Unidentified error, return empty response body
            logger.warning(f"{type_error}, respones body: {response_data}")
            response_body = ""

    response_body = hide_hetu(response_body, hide_date=False)

    return response_body


def _get_data_category(request_path):
    if request_path.startswith("/api/henkilosto/"):
        return DataCategory.HENKILOSTO.value
    if re.match(r"^/api/v\d+/.*$", request_path):
        # path starts with /api/v<some number>/
        return DataCategory.VARHAISKASVATUS.value
    return DataCategory.OTHER.value


def _get_vakajarjestaja_for_user(user):
    vakajarjestaja_qs = get_related_organisaatio_for_user(user)
    if not vakajarjestaja_qs.exists() or vakajarjestaja_qs.count() > 1:
        # User has permissions to multiple Vakajarjestaja or has no permissions at all
        logger.warning(f"Could not determine Vakajarjestaja for user: {user}")
        return None

    # A single Organisaatio can be determined for User
    return vakajarjestaja_qs.first()


def save_audit_log(user, url):
    path, query_params = path_parse(url)
    # path max-length is 200 characters
    path = path[:200]
    Z5_AuditLog.objects.create(user=user, successful_get_request_path=path, query_params=query_params)


def auditlog(function):
    """
    Decorator that audit logs successful responses. Used with GenericViewSet methods
    :param function: Function to be executed
    :return: response from provided function
    """

    @wraps(function)  # @action decorator wants function name not to change
    def argument_wrapper(*args, **kwargs):
        generic_view_set_obj = args[0]
        response = function(*args, **kwargs)
        status_code = response.status_code
        if status.is_success(status_code):
            request = generic_view_set_obj.request
            user = request.user
            path = request.get_full_path()
            save_audit_log(user, path)
        return response

    return argument_wrapper


def auditlogclass(cls):
    """
    Class level decorator that adds auditlog decorator to all supported classes that exist in provided class. If action
    is not in supported methods (see supported_methods list) @auditlog decorator needs to be used explicitly for that
    action.
    :param cls: GenericViewSet subclass
    :return: Provided class with decorated methods
    """
    # create, update and destroy are detected from history table on auditlog send process.
    supported_methods = [
        "list",
        "retrieve",
    ]
    existing_methods = [method_name for method_name in supported_methods if getattr(cls, method_name, None)]

    for method_name in existing_methods:
        original_method = getattr(cls, method_name)
        setattr(cls, method_name, auditlog(original_method))
    return cls


def save_data_access_log(user, access_type, henkilo_obj=None, henkilo_id_oid_list=()):
    """
    Create new Z12_DataAccessLog instance for provided User and Henkilo
    :param user: User instance
    :param access_type: DataAccessType value
    :param henkilo_obj: Henkilo instance
    :param henkilo_id_oid_list: list of tuples e.g. [(henkilo_id, henkilo_oid,)]
    """
    organisaatio_qs = get_related_organisaatio_for_user(user)
    if organisaatio_qs.count() != 1:
        logger.error(f"Could not determine related Organisaatio for User with ID {user.id}")
    elif henkilo_obj:
        Z12_DataAccessLog.objects.create(
            henkilo_id=henkilo_obj.id,
            henkilo_oid=henkilo_obj.henkilo_oid,
            user=user,
            organisaatio=organisaatio_qs.first(),
            access_type=access_type,
        )
    elif henkilo_id_oid_list:
        for henkilo_id, henkilo_oid in henkilo_id_oid_list:
            Z12_DataAccessLog.objects.create(
                henkilo_id=henkilo_id,
                henkilo_oid=henkilo_oid,
                user=user,
                organisaatio=organisaatio_qs.first(),
                access_type=access_type,
            )
