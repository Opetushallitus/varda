from rest_framework import serializers

from varda.misc import get_object_id_from_path


class OidRelatedField(serializers.Field):
    """
    A field which can be used to add functionality to an existing field.
    By defining this field AFTER the field named parent_field in a
    serializer, it is possible to override the value of that field
    using this one. The type of the parent field is expected to be
    an object url, and the type of this one an oid string.

    During read the oid of the parent field is available via this one.
    During write (when no value is given inside parent field) the
    oid given in this field is translated to an object and written to
    the parent field.

    If a field should be required, set the parent required=False and
    either_required=True here. This field then makes sure that a value
    is provided in at least one of the fields.

    parent_field should implement .organisaatio_oid
    object_type should implement .DoesNotExist and .objects.get(organisaatio_oid=value), which returns .id

    Should something more elaborate be needed change this to an abstract class.
    """
    def __init__(self, parent_field, object_type, prevalidator, either_required=False, **kwargs):
        self.parent_field = parent_field
        self.object_type = object_type
        self.prevalidator = prevalidator
        self.either_required = either_required

        kwargs['source'] = '*'
        kwargs['required'] = False
        kwargs['allow_null'] = True
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        self.field_name = field_name
        super().bind(field_name, parent)

    def run_validation(self, data=serializers.empty):
        val = self.to_internal_value(data).get(self.parent_field, serializers.empty)
        if val is serializers.empty:
            val = self._get_parent_value_id()

        if self.either_required and val is serializers.empty:
            msg = f"Either this field or {self.parent_field} is required"
            raise serializers.ValidationError(msg, code='invalid')

        return super().run_validation(data)

    def _get_parent_value_id(self):
        if self.parent_field in self.parent.initial_data and self.parent.initial_data[self.parent_field] is not None:
            parent_value = self.parent.initial_data[self.parent_field]
            parent_value_id = get_object_id_from_path(parent_value)

            if parent_value_id is None:
                msg = {self.parent_field: [f"Could not parse object id from URL", ]}
                raise serializers.ValidationError(msg, code='invalid')

            return parent_value_id
        return serializers.empty

    def to_internal_value(self, value):
        if value is None or value is serializers.empty:
            # Value is optional: if empty or not given do nothing
            return {}

        # Not sure if this is required, but better be safe?
        if self.read_only:
            msg = {self.field_name: [f"Field is read-only", ]}
            raise serializers.ValidationError(msg, code='invalid')

        # Django validators work too late, so we use our own here
        self.prevalidator(value)

        try:
            referenced_object = self.object_type.objects.get(organisaatio_oid=value)
        except self.object_type.DoesNotExist:
            msg = {self.field_name: [f"Unknown oid", ]}
            raise serializers.ValidationError(msg, code='invalid')

        # If the linked parent field has a value, make sure it equals to the one in this field
        parent_value_id = self._get_parent_value_id()
        if parent_value_id is not serializers.empty and referenced_object.id != parent_value_id:
            msg = {self.parent_field: [f"Differs from {self.parent_field}", ]}
            raise serializers.ValidationError(msg, code='invalid')

        return {
            self.parent_field: referenced_object
        }

    def to_representation(self, obj):
        val = getattr(obj, self.parent_field)
        if val:
            return val.organisaatio_oid
        return None
