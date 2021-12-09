from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError

from varda.custom_swagger import TunnisteIdSchema
from webapps.api_throttles import SustainedModifyRateThrottle, BurstRateThrottle


class ViewSetValidator:
    """
    Validation functionality specifically for viewsets.
    The functions here are built around an error dictionary.

    All validation errors are added to the dictionary for field-specific key, as an array.
    After all validations are done, there can be multiple fields and errors per field in
    the error dictionary.

    The error dictionary itself is a context manager, making it easy to use and not forget
    to throw the potential validation errors:

         with ViewSetValidator() as validator:
            if condition:
                validator.error('some_field', 'Some message.')
    """
    def __init__(self):
        self.messages = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            if self.messages:
                raise ValidationError(self.messages, code='invalid')

    def error(self, key, message):
        """
        A helper function to add a validation error to the error dictionary.
        The values of the dictionary are expected to be arrays.
        If a key already exists, the error is appended to the list.

        :param key: Dictionary key
        :param message: Validation error text
        """

        arr = self.messages[key] = self.messages.get(key, [])
        arr.append(message)

    def errors(self, detail):
        """
        Like error, but the parameter can be a dict or a list.

        :param detail: errors as dict or list
        """

        if isinstance(detail, list):
            for msg in detail:
                # No key, just use something
                self.error('detail', msg)
        else:
            for key, msgs in detail.items():
                for msg in msgs:
                    self.error(key, msg)

    def error_nested(self, key_list, message):
        """
        A helper function to add a nested validation error to the error dictionary.
        :param key_list: list of nested keys (e.g. ['key1', 'key2'] -> {'key1': {'key2': ['error1']}}
        :param message: Validation error text
        """
        current_dict = self.messages
        for key in key_list[:-1]:
            current_dict[key] = current_dict.get(key, {})
            current_dict = current_dict[key]

        last_key = key_list[-1]
        arr = current_dict[last_key] = current_dict.get(last_key, [])
        arr.append(message)

    def wrap(self):
        """
        Returns a context handler that catches a ValidationError and
        adds its contents to the error dictionary.

            with validator.wrap():
                raise ValidationError('foo')
            with validator.wrap():
                raise ValidationError({'key': 'bar'})
        """

        return ValidationErrorWrapper(self)


class ValidationErrorWrapper:
    def __init__(self, validator):
        self.validator = validator

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is ValidationError:
            self.validator.errors(exc_val.detail)
            return True


class ExtraKwargsFilterBackend(DjangoFilterBackend):
    """
    DjangoFilterBackend that supports passing extra arguments to FilterSet
    https://github.com/carltongibson/django-filter/issues/857#issuecomment-360788150
    """
    def get_filterset_kwargs(self, request, queryset, view):
        kwargs = super(ExtraKwargsFilterBackend, self).get_filterset_kwargs(request, queryset, view)

        if hasattr(view, 'get_filterset_kwargs'):
            kwargs.update(view.get_filterset_kwargs())

        return kwargs


class ObjectByTunnisteMixin:
    """
    @DynamicAttrs
    """
    swagger_schema = TunnisteIdSchema
    lookup_value_regex = '[^/]+'

    def get_object(self):
        path_param = self.kwargs[self.lookup_field]

        if not path_param.isdigit():
            params = path_param.split(':', 1)
            # Check that both lahdejarjestelma and tunniste have been provided and that they are not empty
            if len(params) != 2 or (len(params) == 2 and (not params[0] or not params[1])):
                raise Http404

            model_qs = self.get_queryset().filter(lahdejarjestelma=params[0], tunniste=params[1])
            if not model_qs.exists():
                raise Http404
            self.kwargs[self.lookup_field] = str(model_qs.first().id)

        return super().get_object()


class IncreasedModifyThrottleMixin:
    """
    Mixin that uses different throttle rates for GET and POST/PUT/PATCH/DELETE requests
    @DynamicAttrs
    """
    THROTTLING_MODIFY_HTTP_METHODS = ['post', 'put', 'patch', 'delete']

    def get_throttles(self):
        if self.request.method.lower() in self.THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super().get_throttles()
