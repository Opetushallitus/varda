import re
from collections import OrderedDict

from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.renderers import SwaggerUIRenderer
from drf_yasg.utils import no_body, force_serializer_instance, force_real_str
from rest_framework.fields import DictField
from rest_framework.serializers import Serializer, ListSerializer

from varda.misc import TemporaryObject


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


class ReadOnly:
    pass


class WriteOnly:
    pass


class BlankMeta:
    pass


class ReadWriteAutoSchema(SwaggerAutoSchema):
    """
    Custom AutoSchema that handles write_only and read_only field arguments
    https://github.com/axnsan12/drf-yasg/issues/70#issuecomment-592304609
    """
    def get_view_serializer(self):
        serializer = super().get_view_serializer()
        return _convert_serializer(serializer, WriteOnly)

    def get_default_response_serializer(self):
        body_override = self._get_request_body_override()
        if body_override and body_override is not no_body:
            return body_override

        serializer = super().get_view_serializer()
        return _convert_serializer(serializer, ReadOnly)

    def get_response_serializers(self):
        # In case of a @swagger_auto_schema override we need to go through custom responses that have not been converted
        responses = super().get_response_serializers()
        if not responses:
            return responses
        for key, value in responses.items():
            responses[key] = _convert_serializer(value, ReadOnly)
        return responses


def _convert_serializer(serializer, new_class):
    if not isinstance(serializer, Serializer) or isinstance(serializer, ReadOnly) or isinstance(serializer, WriteOnly):
        # Serializer cannot be converted (again)
        return serializer

    class CustomSerializer(new_class, serializer.__class__):
        class Meta(getattr(serializer.__class__, 'Meta', BlankMeta)):
            ref_name = new_class.__name__ + serializer.__class__.__name__

        def get_fields(self):
            new_fields = OrderedDict()
            for fieldName, field in super().get_fields().items():
                if (new_class == ReadOnly and not field.write_only) or (new_class == WriteOnly and not field.read_only):
                    if isinstance(field, ListSerializer) and hasattr(field, 'child'):
                        field.child = _convert_serializer(field.child, new_class)
                    new_fields[fieldName] = _convert_serializer(field, new_class)
            return new_fields

    new_serializer = CustomSerializer(data=serializer.data)
    return new_serializer


class TunnisteIdSchema(ReadWriteAutoSchema):
    param_type = openapi.TYPE_STRING
    param_description = ('A unique integer value identifying this {}. Can also be lahdejarjestelma and '
                         'tunniste pair (lahdejarjestelma:tunniste).')

    def get_query_parameters(self):
        query_params = super().get_query_parameters()
        lookup_regex = re.compile(r'{((.*_)?(id|pk))}')
        match = lookup_regex.search(self.path)
        if match and match.group(1):
            # Override id path parameter description to include lahdejarjestelma:tunniste option
            path_model = getattr(getattr(self.view, 'swagger_path_model', None), '__name__', None)
            parent_model = getattr(getattr(self.view, 'parent_model', None), '__name__', None)
            model_name = path_model or parent_model or self.view.get_queryset().model.__name__
            query_params.append(
                openapi.Parameter(match.group(1), openapi.IN_PATH,
                                  description=self.param_description.format(model_name),
                                  type=self.param_type)
            )
        return query_params


class IntegerIdSchema(TunnisteIdSchema):
    param_type = openapi.TYPE_INTEGER
    param_description = 'A unique integer value identifying this {}.'


class OidIdSchema(TunnisteIdSchema):
    param_description = 'A unique integer or OID value identifying this {}.'


class ActionPaginationSwaggerAutoSchema(ReadWriteAutoSchema):
    """
    https://github.com/axnsan12/drf-yasg/pull/499
    """
    def get_response_schemas(self, response_serializers):
        """Return the :class:`.openapi.Response` objects calculated for this view.
        :param dict response_serializers: response serializers as returned by :meth:`.get_response_serializers`
        :return: a dictionary of status code to :class:`.Response` object
        :rtype: dict[str, openapi.Response]
        """
        responses = OrderedDict()
        for sc, serializer in response_serializers.items():
            if isinstance(serializer, str):
                response = openapi.Response(
                    description=force_real_str(serializer)
                )
            elif not serializer:
                continue
            elif isinstance(serializer, openapi.Response):
                response = serializer
                if hasattr(response, 'schema') and not isinstance(response.schema, openapi.Schema.OR_REF):
                    serializer = force_serializer_instance(response.schema)
                    response.schema = self.serializer_to_schema(serializer)
            elif isinstance(serializer, openapi.Schema.OR_REF):
                response = openapi.Response(
                    description='',
                    schema=serializer,
                )
            else:
                serializer = force_serializer_instance(serializer)

                schema = self.serializer_to_schema(serializer)

                if self.has_list_response():
                    schema = openapi.Schema(type=openapi.TYPE_ARRAY,
                                            items=schema)
                schema = self.get_paginated_response(schema) or schema

                response = openapi.Response(
                    description='',
                    schema=schema,
                )

            responses[str(sc)] = response
        return responses


class CustomSchemaField(DictField):
    """
    Provide custom OpenAPI 2.0 schema for this field in the first positional argument.
    """
    def __init__(self, *args, **kwargs):
        self.Meta = TemporaryObject(swagger_schema_fields=args[0])
        super().__init__(**kwargs)
