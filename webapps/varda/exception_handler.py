import logging
import re

from django.db.models import F
from rest_framework import status
from rest_framework.exceptions import ErrorDetail
from rest_framework.views import exception_handler

from varda.enums.error_messages import ErrorMessages, get_error_dict
from varda.enums.koodistot import Koodistot
from varda.models import Z2_CodeTranslation

logger = logging.getLogger(__name__)

STATIC = 'static'
DYNAMIC = 'dynamic'
UNIQUE = 'unique'
OTHER = 'other'
error_templates = {
    status.HTTP_400_BAD_REQUEST: {
        STATIC: {
            'required': ErrorMessages.GE001.value,
            'null': ErrorMessages.GE002.value,
            'blank': ErrorMessages.GE003.value,
            'not_a_list': ErrorMessages.GE004.value,
            'empty': ErrorMessages.GE005.value,
            'invalid_choice': ErrorMessages.GE007.value,
            'does_not_exist': ErrorMessages.GE008.value,
            'no_match': ErrorMessages.GE009.value,
            'incorrect_match': ErrorMessages.GE009.value,
        },
        DYNAMIC: {
            'max_length': [
                (re.compile(r'no more than ([\d.]+) characters'), ErrorMessages.DY001.value),
                (re.compile(r'it should contain no more than (\d+)'), ErrorMessages.DY003.value),
            ],
            'min_length': (re.compile(r'at least ([\d.]+) characters'), ErrorMessages.DY002.value),
            'min_value': (re.compile(r'greater than or equal to ([\d.]+?)[.]'), ErrorMessages.DY004.value),
            'max_value': (re.compile(r'less than or equal to ([\d.]+?)[.]'), ErrorMessages.DY005.value),
            'max_decimal_places': (re.compile(r'no more than ([\d]+) decimal places'), ErrorMessages.DY006.value),
            'max_digits': (re.compile(r'no more than ([\d]+) digits'), ErrorMessages.DY007.value),
            'max_whole_digits': (re.compile(r'no more than ([\d]+) digits'), ErrorMessages.DY009.value),
            'parse_error': [
                (re.compile(r'JSON parse error - (.*)'), ErrorMessages.DY010.value),
                (re.compile(r'Multipart form parse error - (.*)'), ErrorMessages.DY010.value)
            ],
        },
        UNIQUE: {
            'Combination of nimi and vakajarjestaja fields should be unique': ErrorMessages.TP001.value,
        },
        OTHER: {
            'Date has wrong format. Use one of these formats instead: YYYY-MM-DD.': ErrorMessages.GE006.value,
            'A valid integer is required.': ErrorMessages.GE010.value,
            'Must be a valid boolean.': ErrorMessages.GE011.value,
            'A valid number is required.': ErrorMessages.GE012.value,
        }
    },
    status.HTTP_403_FORBIDDEN: {
        STATIC: {
            'not_authenticated': ErrorMessages.PE005.value,
            'permission_denied': ErrorMessages.PE006.value,
            'authentication_failed': ErrorMessages.PE007.value
        }
    },
    status.HTTP_429_TOO_MANY_REQUESTS: {
        DYNAMIC: {
            'throttled': (re.compile(r'available in ([\d]+) second'), ErrorMessages.DY008.value)
        }
    }
}


def varda_exception_handler(exc, context):
    # Get standard response from rest_framework
    response = exception_handler(exc, context)
    if not response:
        return None
    # Catch 400 and 403 responses, transform them to Varda style error messages
    if response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN,
                                status.HTTP_429_TOO_MANY_REQUESTS]:
        """
        response.data is a dict, where key is a field name, and value is usually a list of ErrorDetail objects.
        In some cases value can contain nested dicts in case of nested input errors.
        We want to go through all ErrorDetail objects and find default messages of Django and Django REST framework.
        To achieve consistency, default error messages are transformed to our custom format.
        """
        response.data = _parse_error_messages(response.data, status_code=response.status_code)
    # Catch 404 errors and return generic Varda style error message
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        error_message = ErrorMessages.MI015.value
        _add_error_translations(error_message)
        response.data = {'errors': [error_message]}
    return response


def _parse_error_messages(error_messages, status_code=status.HTTP_400_BAD_REQUEST):
    if isinstance(error_messages, dict):
        # Unify miscellaneous errors
        _unify_misc_errors(error_messages)
        new_error_messages = {}
        # Loop through each key
        for field_name, error_message_item in error_messages.items():
            if isinstance(error_message_item, dict) and 'temporary_wrapper' in error_message_item:
                # Errors raised in ListSerializer may contain temporary_wrapper that needs to be removed
                error_message_item = error_message_item['temporary_wrapper']
            new_error_messages[field_name] = _parse_error_messages(error_message_item, status_code=status_code)
        return new_error_messages
    elif isinstance(error_messages, list):
        if (isinstance(error_messages[0], dict) and
                'error_code' not in error_messages[0] and
                'description' not in error_messages[0]):
            # Parse nested errors, dictionary is not in Varda error message format
            return _parse_error_messages(_parse_nested_errors(error_messages), status_code=status_code)
        else:
            new_error_messages = []
            error_codes = []
            for error_message_index, error_message in enumerate(error_messages):
                if isinstance(error_message, ErrorDetail):
                    # Parse errors coming from Django, not in Varda error message format
                    error_message = _parse_error_message(error_message, status_code)
                if 'error_code' in error_message:
                    # Remove duplicates
                    error_code = error_message['error_code']
                    if error_code in error_codes:
                        continue
                    error_codes.append(error_code)

                    # Add translations
                    _add_error_translations(error_message)

                new_error_messages.append(error_message)
            return new_error_messages


def _unify_misc_errors(error_messages):
    """
    Some general errors are stored in non_field_errors and detail -keys, we want to transfer all of them to errors.
    """
    for key in ['non_field_errors', 'detail']:
        if key in error_messages:
            errors_popped = error_messages.pop(key)
            if not isinstance(errors_popped, list):
                errors_popped = [errors_popped]
            error_messages['errors'] = error_messages.get('errors', []) + errors_popped


def _parse_nested_errors(error_messages):
    """
    Sometimes errors are nested, e.g. {field1: [{}, {inner_field1: [error1, error2]}]}
    We want to display them as {field1: {1: {inner_field1: [error1, error2]}}}
    """
    new_error_messages = {}
    for object_index, object_messages in enumerate(error_messages):
        if object_messages:
            new_error_messages[object_index] = object_messages
    return new_error_messages


def _parse_error_message(message, status_code):
    """
    Transform default Django error message to Varda error message
    :param message: ErrorDetail object
    :return: modified error message
    """
    error_template = error_templates.get(status_code, None)
    # Check if the message is a static message
    new_message = _parse_error_static(message, error_template.get(STATIC, None))
    if new_message:
        return new_message

    # Check if the message is a dynamic message
    new_message = _parse_error_dynamic(message, error_template.get(DYNAMIC, None))
    if new_message:
        return new_message

    # Check messages related to uniqueness
    new_message = _parse_error_unique(message, error_template.get(UNIQUE, None))
    if new_message:
        return new_message

    # Check all other possible messages
    new_message = _parse_error_other(message, error_template.get(OTHER, None))
    if new_message:
        return new_message

    # Return original message if no suitable candidates were found
    logger.warning('Varda error message missing for the following error.\n'
                   f'status code: {status_code}, error code: {message.code}, message: {message}')
    return message


def _parse_error_static(message, error_codes):
    if error_codes:
        return error_codes.get(message.code, None)
    return None


def _parse_error_dynamic(message, error_codes):
    if error_codes:
        error_tuple_list = error_codes.get(message.code, None)

        if error_tuple_list:
            # Some errors have multiple possible variations (e.g. max_length, CharField vs. ArrayField)
            if isinstance(error_tuple_list, tuple):
                error_tuple_list = [error_tuple_list]

            for error_tuple in error_tuple_list:
                regex = error_tuple[0]
                error_dict = error_tuple[1]
                match = regex.search(message)

                if match and match.group(1):
                    variable = match.group(1)
                    formatted_description = error_dict.get('description', '').format(variable)
                    new_error_dict = get_error_dict(error_dict.get('error_code', ''), formatted_description)
                    return new_error_dict
    return None


def _parse_error_unique(message, error_codes):
    if error_codes and message.code == 'unique':
        return error_codes.get(message, None)
    return None


def _parse_error_other(message, error_codes):
    if error_codes:
        return error_codes.get(message, None)
    return None


def _add_error_translations(error_message):
    """
    Get error translations from koodisto and add them to error_message
    e.g. {translations: [{language: 'FI', description: 'Tämä tieto on pakollinen'}]}
    :param error_message: Varda style error message
    """
    error_code = str(error_message['error_code'])
    translations = (Z2_CodeTranslation.objects
                    .filter(code__code_value=error_code, code__koodisto__name=Koodistot.virhe_koodit.value)
                    # Select only language and name so that description annotation does not clash with
                    # model field called description
                    .values('language', 'name')
                    .annotate(description=F('name'))
                    .values('language', 'description'))
    error_message['translations'] = list(translations)
