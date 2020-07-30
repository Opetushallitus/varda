from rest_framework import serializers

from varda.misc import get_object_id_from_path


class AbstractCustomRelatedField(serializers.Field):
    """
    A field which can be used to add functionality to an existing field.
    By defining this field AFTER the field named parent_field in a
    serializer, it is possible to override the value of that field
    using this one. The type of the parent field is expected to be
    an object url, and the type of this one an oid string.

    During read the oid of the parent field is available via this one.
    During write (when no value is given inside parent field) the
    value given in this field is translated to an object and written to
    the parent field.

    If a field should be required, set the parent required=False and
    either_required=True here. This field then makes sure that a value
    is provided in at least one of the fields.

    Permission
    """

    _does_not_exist = object()

    def __init__(self,
                 parent_field,
                 prevalidator,
                 either_required=False,
                 required_in_patch=False,
                 **kwargs):
        if type(self) is AbstractCustomRelatedField:
            raise TypeError('AbstractCustomRelatedField must be subclassed')

        self.parent_field = parent_field
        self.prevalidator = prevalidator
        self.either_required = either_required
        self.required_in_patch = required_in_patch

        kwargs['source'] = '*'
        kwargs['required'] = False
        kwargs['allow_null'] = True
        super().__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        val = self.to_internal_value(data).get(self.parent_field, serializers.empty)
        if val is serializers.empty:
            val = self._get_parent_value_id()

        request_is_patch = self.context['request'].method == 'PATCH'
        required_and_in_patch = request_is_patch and self.required_in_patch
        required_and_not_patch = self.either_required and not request_is_patch

        # Check if either of the fields is required, or if the request is PATCH request and the field is required
        if (required_and_not_patch or required_and_in_patch) and val is serializers.empty:
            msg = [f'Either this field or {self.parent_field} field is required', ]
            raise serializers.ValidationError(msg, code='invalid')

        return super().run_validation(data)

    def _get_parent_value_id(self):
        if self.parent.initial_data.get(self.parent_field):
            parent_value = self.parent.initial_data[self.parent_field]
            parent_value_id = get_object_id_from_path(parent_value)

            if parent_value_id is None:
                msg = [f'Could not parse object id from field {self.parent_field}', ]
                raise serializers.ValidationError(msg, code='invalid')

            return parent_value_id
        return serializers.empty

    def to_internal_value(self, value):
        if self.is_value_empty(value):
            # Value is optional: if empty or not given do nothing
            return {}

        # Not sure if this is required, but better be safe?
        if self.read_only:
            msg = ['Field is read-only', ]
            raise serializers.ValidationError(msg, code='invalid')

        # Django validators work too late, so we use our own here
        self.prevalidator(value)

        referenced_object = self.get_referenced_object_by_value(value)
        if referenced_object is None:
            return {}
        else:
            check_permission = getattr(self.parent.fields.fields[self.parent_field], 'check_permission', None)
            if check_permission and not self.context['request'].user.has_perm(check_permission, referenced_object):
                # Masking 403 as object not found
                referenced_object = AbstractCustomRelatedField._does_not_exist
        if referenced_object is AbstractCustomRelatedField._does_not_exist:
            msg = ['Could not find matching object', ]
            raise serializers.ValidationError(msg, code='invalid')

        # If the linked parent field has a value, make sure it equals to the one in this field
        parent_value_id = self._get_parent_value_id()
        if parent_value_id is not serializers.empty and referenced_object.id != parent_value_id:
            msg = [f'Differs from {self.parent_field}', ]
            raise serializers.ValidationError(msg, code='invalid')

        return {
            self.parent_field: referenced_object
        }

    def to_representation(self, obj):
        parent_value = getattr(obj, self.parent_field)
        if parent_value:
            return self.get_value_by_referenced_object(parent_value)
        return None

    def get_referenced_object_by_value(self, value):
        """
        Returns an instance of the target object,
        the instance must have .id, which is compared to the id in the parent field.
        Value is the value given for this field.
        This is not called if the value is empty or None, or prevalidator throws.
        If an object is not found, return _does_not_exist.
        If there is no object, return None.
        For example: "1.23.456" -> henkilö instance
        """
        raise NotImplementedError('get_referenced_object_by_value')

    def get_value_by_referenced_object(self, parent_value):
        """
        Returns the value of the field based on the referenced object.
        For example: henkilö instance -> "1.23.456"
        """
        raise NotImplementedError('get_value_by_referenced_object')

    def is_value_empty(self, value):
        return value is None or value is serializers.empty


class OidRelatedField(AbstractCustomRelatedField):
    """
    parent_field should implement parent_attribute
    object_type should implement .DoesNotExist and .objects.get(parent_attribute=value), which returns .id
    """
    def __init__(self, parent_attribute, object_type, **kwargs):
        self.parent_attribute = parent_attribute
        self.object_type = object_type

        super().__init__(**kwargs)

    def get_referenced_object_by_value(self, value):
        try:
            return self.object_type.objects.get(**{self.parent_attribute: value})
        except self.object_type.DoesNotExist:
            return AbstractCustomRelatedField._does_not_exist

    def get_value_by_referenced_object(self, parent_value):
        return getattr(parent_value, self.parent_attribute)


class TunnisteRelatedField(AbstractCustomRelatedField):
    """
    Similar field to OidRelatedField. Serializer must have lahdejarjestelma-field in addition to this field, related
    object is fetched based on tunniste+lahdejarjestelma.
    If parent_field is set, this field (tunniste) is filled without taking into account if lahdejarjestelma is same
    or different.
    """
    def __init__(self, object_type, **kwargs):
        self.object_type = object_type

        super().__init__(**kwargs)

    def get_referenced_object_by_value(self, tunniste):
        try:
            lahdejarjestelma = self.parent.initial_data.get('lahdejarjestelma', None)
            return self.object_type.objects.get(tunniste=tunniste, lahdejarjestelma=lahdejarjestelma)
        except self.object_type.DoesNotExist:
            return AbstractCustomRelatedField._does_not_exist

    def get_value_by_referenced_object(self, parent_value):
        return parent_value.tunniste
