import re

from django.http import Http404
from django_filters.rest_framework import DjangoFilterBackend
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.renderers import SwaggerUIRenderer
from rest_framework.exceptions import ValidationError


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


class PublicSwaggerRenderer(SwaggerUIRenderer):
    def set_context(self, renderer_context, swagger=None):
        super(PublicSwaggerRenderer, self).set_context(renderer_context, swagger=swagger)
        # Disable Django login feature
        renderer_context['USE_SESSION_AUTH'] = False

    def get_swagger_ui_settings(self):
        settings = super(PublicSwaggerRenderer, self).get_swagger_ui_settings()
        # Disable 'Try it out' feature
        settings['supportedSubmitMethods'] = []
        return settings


class PublicSchemaGenerator(OpenAPISchemaGenerator):
    exclude_url_pattern = re.compile(r'^/api/admin.*$')

    def get_security_definitions(self):
        # Disable all authentication features
        return None

    def should_include_endpoint(self, path, method, view, public):
        should_include = super(PublicSchemaGenerator, self).should_include_endpoint(path, method, view, public)
        return should_include and not self.exclude_url_pattern.fullmatch(path)


class TunnisteIdSchema(SwaggerAutoSchema):
    def get_query_parameters(self):
        query_params = super(TunnisteIdSchema, self).get_query_parameters()
        path_list = self.path.split('/')
        if path_list[-2] == '{id}':
            # Override id path parameter description to include lahdejarjestelma:tunniste option
            model_name = self.view.get_queryset().model.__name__
            query_params.append(
                openapi.Parameter('id', openapi.IN_PATH,
                                  description=f'A unique integer value identifying this {model_name}. Can also be '
                                              'lahdejarjestelma and tunniste pair (lahdejarjestelma:tunniste).',
                                  type=openapi.TYPE_STRING)
            )
        return query_params


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
