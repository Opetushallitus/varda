import datetime

from django.http import Http404
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin

from varda.cache import get_object_ids_user_has_permissions
from varda.custom_swagger import OidIdSchema, TunnisteIdSchema
from varda.enums.error_messages import ErrorMessages
from varda.permissions import is_oph_staff
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
                raise ValidationError(self.messages, code="invalid")

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
                self.error("detail", msg)
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

        if hasattr(view, "get_filterset_kwargs"):
            kwargs.update(view.get_filterset_kwargs())

        return kwargs


class ObjectByTunnisteMixin:
    """
    @DynamicAttrs
    """

    swagger_schema = TunnisteIdSchema
    lookup_value_regex = "[^/]+"

    def get_object(self):
        path_param = self.kwargs[self.lookup_field]

        if not path_param.isdigit():
            params = path_param.split(":", 1)
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

    THROTTLING_MODIFY_HTTP_METHODS = ["post", "put", "patch", "delete"]

    def get_throttles(self):
        if self.request.method.lower() in self.THROTTLING_MODIFY_HTTP_METHODS:
            self.throttle_classes = [BurstRateThrottle, SustainedModifyRateThrottle]
        return super().get_throttles()


def parse_query_parameter(parameters, parameter_name, parameter_type):
    """
    Parse query parameter to Python value, e.g. bool or date
    :param parameters: request query_parameters
    :param parameter_name: name of the parameter
    :param parameter_type: type of the parameter (rest_framework Field)
    :return: parsed value, or None if parameter was not present in query
    """
    query_parameter = parameters.get(parameter_name, None)
    if not query_parameter:
        return None
    if isinstance(query_parameter, str):
        if parameter_type is bool:
            return True if query_parameter.lower() == "true" else False
        elif parameter_type is datetime.date:
            try:
                return datetime.datetime.strptime(query_parameter, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError({parameter_name: [ErrorMessages.GE006.value]})
        elif parameter_type is datetime.datetime:
            try:
                return datetime.datetime.strptime(query_parameter, "%Y-%m-%dT%H:%M:%S%z")
            except ValueError:
                raise ValidationError({parameter_name: [ErrorMessages.GE020.value]})
    return query_parameter


class ParentObjectMixin:
    """
    Mixin that gets parent object for nested views and verifies view permission
    @DynamicAttrs
    """

    parent_model = None
    check_parent_permissions = True

    def _get_object(self, parent_object_id):
        if not isinstance(parent_object_id, int) and not parent_object_id.isdigit():
            raise Http404

        return get_object_or_404(self.parent_model, pk=parent_object_id)

    def get_parent_object(self):
        parent_model_name = self.parent_model.get_name()
        parent_object_id = self.kwargs[f"{parent_model_name}_pk"]

        parent_object = self._get_object(parent_object_id)
        user = self.request.user

        # Verify view-permission if self.check_parent_permissions = True
        if not self.check_parent_permissions or user.has_perm(f"view_{parent_model_name}", parent_object):
            return parent_object
        else:
            raise Http404


class ParentObjectByOidMixin(ParentObjectMixin):
    """
    @DynamicAttrs
    """

    swagger_schema = OidIdSchema
    lookup_value_regex = r"(\d+)|([.\d]{26,})"
    oid_field_name = "organisaatio_oid"

    def _get_object(self, parent_object_id):
        # Lookup can be made with ID or organisaatio_oid
        if not parent_object_id.isdigit():
            parent_qs = self.parent_model.objects.filter(**{self.oid_field_name: parent_object_id})
            if not parent_qs.exists():
                raise Http404
            parent_object_id = parent_qs.first().id

        return super()._get_object(parent_object_id)


class PermissionListMixin(ListModelMixin):
    """
    Mixin that filters list results based on user permissions
    @DynamicAttrs
    """

    def list(self, request, *args, **kwargs):
        user = request.user
        if not user.is_superuser and not is_oph_staff(user):
            # Get permission filtered results for non admin users
            self.queryset = self.queryset.filter(id__in=get_object_ids_user_has_permissions(user, self.queryset.model))
        return super().list(request, *args, **kwargs)
