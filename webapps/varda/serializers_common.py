from rest_framework import serializers

from varda.enums.error_messages import ErrorMessages
from varda.misc import get_object_id_from_path
from varda.models import VakaJarjestaja, Toimipaikka, Henkilo
from varda.permissions import user_belongs_to_correct_groups
from varda.validators import validate_organisaatio_oid


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
    """

    _does_not_exist = object()

    def __init__(self,
                 parent_field,
                 prevalidator,
                 either_required=False,
                 secondary_field=None,
                 parent_value_getter=None,
                 required_in_patch=False,
                 **kwargs):
        """
        :param parent_field: name of the parent field (e.g. 'lapsi_tunniste' -> parent field is 'lapsi'
        :param prevalidator: function that validates the input value (e.g. validate OID)
        :param either_required: True, if one of the fields is required, either False
        :param secondary_field: name of a secondary CustomRelatedField (e.g. 'toimipaikka_oid' and 'toimipaikka_tunniste')
        :param parent_value_getter: override function that gets the parent value of CustomRelatedField
                                    (e.g. Lapsi is not directly linked to Maksutieto)
        :param required_in_patch: True if this (or one of the fields) should be required in PATCH-calls
        :param kwargs:
        """
        if type(self) is AbstractCustomRelatedField:
            raise TypeError('AbstractCustomRelatedField must be subclassed')

        self.parent_field = parent_field
        self.prevalidator = prevalidator
        self.either_required = either_required
        self.secondary_field = secondary_field
        self.parent_value_getter = parent_value_getter
        self.required_in_patch = required_in_patch

        kwargs['source'] = '*'
        kwargs['required'] = False
        kwargs['allow_null'] = True
        super().__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        self_value = None if data is serializers.empty else data
        self_object = self.to_internal_value(data).get(self.parent_field, None)
        object_id = None if not self_object else self_object.id

        parent_value = self.parent.initial_data.get(self.parent_field, None)
        parent_value_id = self._get_parent_value_id()

        secondary_value = None
        secondary_value_id = None
        if self.secondary_field:
            secondary_value = self.parent.initial_data.get(self.secondary_field, None)
            secondary_value_id = self._get_secondary_value_id(secondary_value)

        request_is_patch = self.context['request'].method == 'PATCH'
        required_and_in_patch = request_is_patch and self.required_in_patch
        required_and_not_patch = self.either_required and not request_is_patch

        # Check if either of the fields is required, or if the request is PATCH request and the field is required
        if (required_and_not_patch or required_and_in_patch) and not (self_value or parent_value or secondary_value):
            raise serializers.ValidationError([ErrorMessages.RF001.value], code='invalid')

        # If the linked parent field or secondary field have values, make sure they equal to the one in this field
        if (object_id and ((parent_value_id and object_id != parent_value_id) or
                           (secondary_value_id and object_id != secondary_value_id))):
            raise serializers.ValidationError([ErrorMessages.RF004.value], code='invalid')

        return super().run_validation(data)

    def _get_parent_value_id(self):
        if self.parent.initial_data.get(self.parent_field):
            parent_value = self.parent.initial_data[self.parent_field]
            parent_value_id = get_object_id_from_path(parent_value)

            if parent_value_id is None:
                raise serializers.ValidationError([ErrorMessages.RF002.value], code='invalid')

            return parent_value_id
        return None

    def _get_secondary_value_id(self, value):
        secondary_field_object = self.parent.fields.fields.get(self.secondary_field, None)
        secondary_value_id = None
        if secondary_field_object:
            secondary_value_id = secondary_field_object.get_id_as_secondary_field(value)
        return secondary_value_id

    def get_id_as_secondary_field(self, value):
        """
        This function is used to validate a secondary field object, if object can be referenced by three fields
        (e.g. hyperlinked, oid, tunniste)
        :param value: secondary value (oid or tunniste)
        :return: ID of the secondary referenced object or None
        """
        if self.is_value_empty(value):
            return None

        referenced_object = self.get_referenced_object_by_value(value)
        if referenced_object is None or referenced_object is AbstractCustomRelatedField._does_not_exist:
            return None

        return referenced_object.id

    def _run_prevalidator(self, value):
        try:
            self.prevalidator(value)
        except serializers.ValidationError as e:
            if isinstance(e.detail, dict):
                # If raised error is already a dict, move errors to a single list so that error messages are
                # not nested multiple times
                error_list = []
                for error_key, error_value in e.detail.items():
                    error_list = error_list + error_value
                e.detail = error_list
            raise e

    def to_internal_value(self, value):
        if self.is_value_empty(value):
            # Value is optional: if empty or not given do nothing
            return {}

        # Not sure if this is required, but better be safe?
        if self.read_only:
            raise serializers.ValidationError([ErrorMessages.GE015.value], code='invalid')

        # Django validators work too late, so we use our own here
        self._run_prevalidator(value)

        referenced_object = self.get_referenced_object_by_value(value)
        if referenced_object is None:
            return {}
        else:
            parent_field = self.parent.fields.fields[self.parent_field]
            user = self.context['request'].user

            check_permission = getattr(parent_field, 'check_permission', None)
            if ((check_permission and not user.has_perm(check_permission, referenced_object)) or
                    not user_belongs_to_correct_groups(parent_field, user, referenced_object)):
                # Masking 403 as object not found
                referenced_object = AbstractCustomRelatedField._does_not_exist

        if referenced_object is AbstractCustomRelatedField._does_not_exist:
            raise serializers.ValidationError([ErrorMessages.RF003.value], code='invalid')

        return {
            self.parent_field: referenced_object
        }

    def to_representation(self, obj):
        if self.parent_value_getter:
            parent_value = self.parent_value_getter(obj)
        else:
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


class PermissionCheckedHLFieldMixin:
    """
    @DynamicAttrs
    Mixin class for checking hyperlink related field permission.
    Note: This needs to be before HyperlinkedRelatedField in class signature because of inheritance order.
    """
    def get_object(self, view_name, view_args, view_kwargs):
        hlfield_object = super(PermissionCheckedHLFieldMixin, self).get_object(view_name, view_args, view_kwargs)
        user = self.context['request'].user

        if (not user.has_perm(self.check_permission, hlfield_object) or
                not user_belongs_to_correct_groups(self, user, hlfield_object)):
            self.fail('does_not_exist')

        return hlfield_object


class VakaJarjestajaHLField(serializers.HyperlinkedRelatedField):
    """
    https://medium.com/django-rest-framework/limit-related-data-choices-with-django-rest-framework-c54e96f5815e
    """
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = VakaJarjestaja.objects.all().order_by('id')
        else:
            queryset = VakaJarjestaja.objects.none()
        return queryset


class VakaJarjestajaPermissionCheckedHLField(PermissionCheckedHLFieldMixin, VakaJarjestajaHLField):
    check_permission = 'view_vakajarjestaja'
    permission_groups = []
    accept_toimipaikka_permission = False

    def __init__(self, *args, **kwargs):
        self.permission_groups = kwargs.pop('permission_groups', [])
        self.accept_toimipaikka_permission = kwargs.pop('accept_toimipaikka_permission', False)

        super(VakaJarjestajaPermissionCheckedHLField, self).__init__(*args, **kwargs)


class ToimipaikkaHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Toimipaikka.objects.all().order_by('id')
        else:
            queryset = Toimipaikka.objects.none()
        return queryset


class ToimipaikkaPermissionCheckedHLField(PermissionCheckedHLFieldMixin, ToimipaikkaHLField):
    check_permission = 'view_toimipaikka'
    permission_groups = []
    check_paos = False

    def __init__(self, *args, **kwargs):
        self.permission_groups = kwargs.pop('permission_groups', [])
        self.check_paos = kwargs.pop('check_paos', False)
        super(ToimipaikkaPermissionCheckedHLField, self).__init__(*args, **kwargs)


class OptionalToimipaikkaMixin(metaclass=serializers.SerializerMetaclass):
    """
    Mixin class to be used with HyperlinkedModelSerializer
    """
    # Only user with toimipaikka permissions need to provide this field
    toimipaikka = ToimipaikkaPermissionCheckedHLField(view_name='toimipaikka-detail', required=False, write_only=True)
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validate_organisaatio_oid,
                                      either_required=False,
                                      write_only=True)

    def create(self, validated_data):
        """
        NOTE: Since toimipaikka is removed here we need to pick toimipaikka before calling serializer.save()
        :param validated_data: Serializer validated data
        :return: Created object
        """
        validated_data.pop('toimipaikka', None)
        validated_data.pop('toimipaikka_oid', None)
        return super(OptionalToimipaikkaMixin, self).create(validated_data)


class HenkiloHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Henkilo.objects.all().order_by('id')
        else:
            queryset = Henkilo.objects.none()
        return queryset


class HenkiloPermissionCheckedHLField(PermissionCheckedHLFieldMixin, HenkiloHLField):
    check_permission = 'view_henkilo'
