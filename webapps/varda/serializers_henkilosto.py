from operator import itemgetter

from rest_framework import serializers

from varda import related_object_validations, validators
from varda.cache import caching_to_representation
from varda.misc_viewsets import ViewSetValidator
from varda.models import (Henkilo, TilapainenHenkilosto, Tutkinto, Tyontekija, VakaJarjestaja, Palvelussuhde,
                          Tyoskentelypaikka, Toimipaikka, PidempiPoissaolo, TaydennyskoulutusTyontekija,
                          Taydennyskoulutus)
from varda.permissions import (is_correct_taydennyskoulutus_tyontekija_permission,
                               filter_authorized_taydennyskoulutus_tyontekijat)
from varda.related_object_validations import (create_daterange, daterange_overlap,
                                              check_overlapping_tyoskentelypaikka_object,
                                              check_overlapping_palvelussuhde_object,
                                              check_if_admin_mutable_object_is_changed)
from varda.serializers import (HenkiloHLField, VakaJarjestajaPermissionCheckedHLField,
                               PermissionCheckedHLFieldMixin, ToimipaikkaPermissionCheckedHLField)

from varda.serializers_common import OidRelatedField, TunnisteRelatedField
from varda.validators import (validate_dates_within_toimipaikka, validate_paattymispvm_same_or_after_alkamispvm,
                              validate_paivamaara1_after_paivamaara2, validate_paivamaara1_before_paivamaara2,
                              parse_paivamaara, fill_missing_fields_for_validations)

_tyontekija_not_specified_error_message = 'Tyontekija not specified. Use (tyontekija), (henkilo_oid, vakajarjestaja_oid) or (lahdejarjestelma, tunniste).'


class TyontekijaHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        """
        https://medium.com/django-rest-framework/limit-related-data-choices-with-django-rest-framework-c54e96f5815e
        """
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Tyontekija.objects.all().order_by('id')
        else:
            queryset = Tyontekija.objects.none()
        return queryset


class TyontekijaPermissionCheckedHLField(PermissionCheckedHLFieldMixin, TyontekijaHLField):
    check_permission = 'change_tyontekija'


class PalvelussuhdePermissionCheckedHLField(PermissionCheckedHLFieldMixin, serializers.HyperlinkedRelatedField):
    check_permission = 'change_palvelussuhde'

    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Palvelussuhde.objects.all().order_by('id')
        else:
            queryset = Palvelussuhde.objects.none()
        return queryset


class OptionalToimipaikkaMixin(metaclass=serializers.SerializerMetaclass):
    """
    Mixin class to be used with HyperlinkedModelSerializer
    """
    # Only user with toimipaikka permissions need to provide this field
    toimipaikka = ToimipaikkaPermissionCheckedHLField(view_name='toimipaikka-detail', required=False, write_only=True)
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
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


class TyontekijaSerializer(OptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validators.validate_henkilo_oid,
                                  either_required=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)

    class Meta:
        model = Tyontekija
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tyontekija')
    def to_representation(self, instance):
        return super(TyontekijaSerializer, self).to_representation(instance)

    def validate(self, data):
        with ViewSetValidator() as validator:
            henkilo = data.get('henkilo')
            if henkilo and henkilo.lapsi.exists():
                validator.error('henkilo', 'This henkilo is already referenced by lapsi objects')

            # Validate only when updating existing henkilo
            if self.instance:
                instance = self.instance
                if 'henkilo' in data:
                    related_object_validations.check_if_admin_mutable_object_is_changed(self.context['request'].user,
                                                                                        instance,
                                                                                        data,
                                                                                        'henkilo')
                if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                    validator.error('vakajarjestaja', 'Changing of vakajarjestaja is not allowed')

        return data


class TilapainenHenkilostoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)

    class Meta:
        model = TilapainenHenkilosto
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tilapainenhenkilosto')
    def to_representation(self, instance):
        return super(TilapainenHenkilostoSerializer, self).to_representation(instance)

    def validate(self, data):
        with ViewSetValidator() as validator:
            # Validate only when creating tilapainen henkilosto
            if self.context['request'].method == 'POST':
                self.verify_unique_month(data, validator)
                with validator.wrap():
                    self.validate_date_within_vakajarjestaja(data, validator)

            # Validate only when updating existing tilapainen henkilosto
            if self.instance:
                instance = self.instance
                if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                    validator.error('vakajarjestaja', 'Changing of vakajarjestaja is not allowed')
                if 'kuukausi' in data and data['kuukausi'] != instance.kuukausi:
                    validator.error('kuukausi', 'Changing of kuukausi is not allowed')
            return data

    def verify_unique_month(self, data, validator):
        tilapainen_henkilosto_qs = TilapainenHenkilosto.objects.filter(vakajarjestaja=data['vakajarjestaja'],
                                                                       kuukausi__year=data['kuukausi'].year,
                                                                       kuukausi__month=data['kuukausi'].month)
        if tilapainen_henkilosto_qs.exists():
            validator.error('kuukausi', 'tilapainen henkilosto already exists for this month.')

    def validate_date_within_vakajarjestaja(self, data, validator):
        vakajarjestaja = data['vakajarjestaja']
        kuukausi = data['kuukausi']
        if kuukausi < vakajarjestaja.alkamis_pvm:
            validator.error('kuukausi', 'kuukausi is not after vakajarjestaja.alkamis_pvm')
        if vakajarjestaja.paattymis_pvm is not None and kuukausi > vakajarjestaja.paattymis_pvm:
            validator.error('kuukausi', 'kuukausi is not before vakajarjestaja.paattymis_pvm')


class TutkintoSerializer(OptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validators.validate_henkilo_oid,
                                  either_required=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False, write_only=True)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True,
                                         write_only=True)

    class Meta:
        model = Tutkinto
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tutkinto')
    def to_representation(self, instance):
        return super(TutkintoSerializer, self).to_representation(instance)

    def create(self, validated_data):
        validated_data.pop('vakajarjestaja', None)
        validated_data.pop('vakajarjestaja_oid', None)
        return super().create(validated_data)

    def validate(self, data):
        vakajarjestaja = data.get('vakajarjestaja')
        toimipaikka = data.get('toimipaikka')
        henkilo = data.get('henkilo')
        with ViewSetValidator() as validator:
            if not Tyontekija.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=henkilo).exists():
                validator.error('tyontekija', 'Provided vakajarjestaja has not added this henkilo as tyontekija')
            if vakajarjestaja and toimipaikka and vakajarjestaja != toimipaikka.vakajarjestaja:
                validator.error('toimipaikka', 'Provided toimipaikka is not matching provided vakajarjestaja')
        return data


class PalvelussuhdeSerializer(OptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    tyontekija = TyontekijaPermissionCheckedHLField(view_name='tyontekija-detail', required=False)
    tyontekija_tunniste = TunnisteRelatedField(object_type=Tyontekija,
                                               parent_field='tyontekija',
                                               prevalidator=validators.validate_tunniste,
                                               either_required=True)

    class Meta:
        model = Palvelussuhde
        exclude = ('changed_by', 'luonti_pvm')
        read_only_fields = ('muutos_pvm', )

    @caching_to_representation('palvelussuhde')
    def to_representation(self, instance):
        return super(PalvelussuhdeSerializer, self).to_representation(instance)

    def validate(self, data):
        # Validate only when updating existing
        palvelussuhde = self.instance

        # UPDATE
        if palvelussuhde:
            with ViewSetValidator() as validator:
                fill_missing_fields_for_validations(data, palvelussuhde)
                with validator.wrap():
                    validate_paattymispvm_same_or_after_alkamispvm(data)

                if data['paattymis_pvm'] is None and data['tyosuhde_koodi'] == '2':
                    validator.error('paattymis_pvm', 'paattymis_pvm can not be none for tyosuhde_koodi 2')

                self.validate_tutkinto(data['tyontekija'], data['tutkinto_koodi'], validator)
                if 'tyontekija' in data:
                    check_if_admin_mutable_object_is_changed(self.context['request'].user, palvelussuhde, data, 'tyontekija')

                with validator.wrap():
                    check_overlapping_palvelussuhde_object(data, Palvelussuhde, palvelussuhde.id)

        # CREATE
        else:
            with ViewSetValidator() as validator:
                with validator.wrap():
                    if data['tyosuhde_koodi'] == '2' and ('paattymis_pvm' not in data or data['paattymis_pvm'] is None):
                        validator.error('paattymis_pvm', 'paattymis_pvm is required for tyosuhde_koodi 2')
                    validate_paattymispvm_same_or_after_alkamispvm(data)

                self.validate_tutkinto(data['tyontekija'], data['tutkinto_koodi'], validator)

                with validator.wrap():
                    check_overlapping_palvelussuhde_object(data, Palvelussuhde)

        return data

    def validate_tutkinto(self, tyontekija, tutkinto_koodi, validator):
        if tutkinto_koodi == '003':  # Ei tutkintoa
            if tyontekija.henkilo.tutkinnot.exclude(tutkinto_koodi='003').exists():
                validator.error('tutkinto_koodi', 'tyontekija has tutkinnot other than just 003.')
        else:
            if not tyontekija.henkilo.tutkinnot.filter(tutkinto_koodi=tutkinto_koodi).exists():
                validator.error('tutkinto_koodi', 'tyontekija doesn\'t have the given tutkinto.')


class TyoskentelypaikkaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail', required=False)
    palvelussuhde_tunniste = TunnisteRelatedField(object_type=Palvelussuhde,
                                                  parent_field='palvelussuhde',
                                                  prevalidator=validators.validate_tunniste,
                                                  either_required=True)
    toimipaikka = ToimipaikkaPermissionCheckedHLField(required=False, allow_null=True, view_name='toimipaikka-detail')
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      either_required=False)
    kiertava_tyontekija_kytkin = serializers.BooleanField(default=False)

    class Meta:
        model = Tyoskentelypaikka
        exclude = ('changed_by', 'luonti_pvm')
        read_only_fields = ('muutos_pvm', )

    @caching_to_representation('tyoskentelypaikka')
    def to_representation(self, instance):
        return super(TyoskentelypaikkaSerializer, self).to_representation(instance)

    def validate(self, data):
        palvelussuhde = data['palvelussuhde']
        toimipaikka = data['toimipaikka'] if 'toimipaikka' in data else None
        kiertava_tyontekija_kytkin = data['kiertava_tyontekija_kytkin']

        with ViewSetValidator() as validator:
            if kiertava_tyontekija_kytkin and toimipaikka:
                validator.error('kiertava_tyontekija_kytkin', 'toimipaikka can\'t be specified with kiertava_tyontekija_kytkin.')
            validate_dates(data, palvelussuhde, validator)

            with validator.wrap():
                validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator)

            if not kiertava_tyontekija_kytkin:
                with validator.wrap():
                    check_overlapping_tyoskentelypaikka_object(data, Tyoskentelypaikka)

            if toimipaikka:
                with validator.wrap():
                    validate_dates_within_toimipaikka(data, toimipaikka)

            if toimipaikka and toimipaikka.vakajarjestaja_id != palvelussuhde.tyontekija.vakajarjestaja_id:
                validator.error('toimipaikka', 'Toimipaikka must have the same vakajarjestaja as tyontekija')

        return data


def validate_dates(validated_data, palvelussuhde, validator):
    with validator.wrap():
        validators.validate_paattymispvm_same_or_after_alkamispvm(validated_data)

    validate_dates_palvelussuhde(validated_data, palvelussuhde, validator)


def validate_dates_palvelussuhde(data, palvelussuhde, validator):
    if 'paattymis_pvm' in data and data['paattymis_pvm'] is not None:
        if palvelussuhde.paattymis_pvm is not None and not validators.validate_paivamaara1_before_paivamaara2(data['paattymis_pvm'], palvelussuhde.paattymis_pvm, can_be_same=True):
            validator.error('paattymis_pvm', 'paattymis_pvm must be before palvelussuhde paattymis_pvm (or same).')
    if 'alkamis_pvm' in data and data['alkamis_pvm'] is not None:
        if not validators.validate_paivamaara1_after_paivamaara2(data['alkamis_pvm'], palvelussuhde.alkamis_pvm, can_be_same=True):
            validator.error('alkamis_pvm', 'alkamis_pvm must be after palvelussuhde alkamis_pvm (or same).')
        if not validators.validate_paivamaara1_before_paivamaara2(data['alkamis_pvm'], palvelussuhde.paattymis_pvm, can_be_same=False):
            validator.error('alkamis_pvm', 'alkamis_pvm must be before palvelussuhde paattymis_pvm.')


def validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator):
    inverse_kiertava_kytkin = not kiertava_tyontekija_kytkin
    related_palvelussuhde_tyoskentelypaikat = Tyoskentelypaikka.objects.filter(palvelussuhde=palvelussuhde, kiertava_tyontekija_kytkin=inverse_kiertava_kytkin)

    range_this = create_daterange(data['alkamis_pvm'], data.get('paattymis_pvm', None))
    for item in related_palvelussuhde_tyoskentelypaikat:
        range_other = create_daterange(item.alkamis_pvm, item.paattymis_pvm)
        if daterange_overlap(range_this, range_other):
            validator.error('kiertava_tyontekija_kytkin', 'can\'t have different values of kiertava_tyontekija_kytkin on overlapping date ranges')
            break


class TyoskentelypaikkaUpdateSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = serializers.HyperlinkedRelatedField(read_only=True, view_name='palvelussuhde-detail')
    toimipaikka = serializers.HyperlinkedRelatedField(read_only=True, view_name='toimipaikka-detail')

    class Meta:
        model = Tyoskentelypaikka
        exclude = ('changed_by', 'luonti_pvm')
        read_only = ('url', 'palvelussuhde', 'toimipaikka', "kiertava_tyontekija_kytkin", "muutos_pvm",)

    @caching_to_representation('tyoskentelypaikka')
    def to_representation(self, instance):
        return super(TyoskentelypaikkaUpdateSerializer, self).to_representation(instance)

    def validate(self, data):
        tyoskentelypaikka = self.instance
        fill_missing_fields_for_validations(data, tyoskentelypaikka)
        palvelussuhde = data['palvelussuhde']
        toimipaikka = data['toimipaikka']
        kiertava_tyontekija_kytkin = data['kiertava_tyontekija_kytkin']

        with ViewSetValidator() as validator:
            if kiertava_tyontekija_kytkin and toimipaikka:
                validator.error('kiertava_tyontekija_kytkin', 'toimipaikka can\'t be specified with kiertava_tyontekija_kytkin.')

            validate_dates(data, palvelussuhde, validator)

            with validator.wrap():
                validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator)

            if not kiertava_tyontekija_kytkin:
                with validator.wrap():
                    check_overlapping_tyoskentelypaikka_object(data, Tyoskentelypaikka, tyoskentelypaikka.id)

        return data


class PidempiPoissaoloSerializer(OptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail', required=False)
    palvelussuhde_tunniste = TunnisteRelatedField(object_type=Palvelussuhde,
                                                  parent_field='palvelussuhde',
                                                  prevalidator=validators.validate_tunniste,
                                                  either_required=True)
    alkamis_pvm = serializers.DateField(required=True)
    paattymis_pvm = serializers.DateField(required=True)

    class Meta:
        model = PidempiPoissaolo
        exclude = ('changed_by', 'luonti_pvm')
        read_only_fields = ('muutos_pvm', )

    @caching_to_representation('pidempipoissaolo')
    def to_representation(self, instance):
        return super(PidempiPoissaoloSerializer, self).to_representation(instance)

    def validate(self, data):
        if not self.instance:
            with ViewSetValidator() as validator:
                self.validate_dates(data, data['palvelussuhde'], validator)
                with validator.wrap():
                    related_object_validations.check_overlapping_pidempipoissaolo_object(data, PidempiPoissaolo)
        else:
            pidempipoissaolo_obj = self.instance
            fill_missing_fields_for_validations(data, pidempipoissaolo_obj)

            with ViewSetValidator() as validator:
                self.validate_dates(data, pidempipoissaolo_obj.palvelussuhde, validator)

                with validator.wrap():
                    related_object_validations.check_overlapping_pidempipoissaolo_object(data, PidempiPoissaolo, pidempipoissaolo_obj.id)
            related_object_validations.check_if_immutable_object_is_changed(pidempipoissaolo_obj, data, 'palvelussuhde')

        return data

    def validate_dates(self, validated_data, palvelussuhde, validator):
        with validator.wrap():
            validate_paattymispvm_same_or_after_alkamispvm(validated_data)

        self.validate_duration(validated_data, validator)
        self.validate_dates_palvelussuhde(validated_data, palvelussuhde, validator)

    def validate_duration(self, validated_data, validator):
        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            start = parse_paivamaara(validated_data['alkamis_pvm'])
            end = parse_paivamaara(validated_data['paattymis_pvm'])
            if (end - start).days < 60:
                validator.error('paattymis_pvm', 'poissaolo duration must be 60 days or more.')

    def validate_dates_palvelussuhde(self, validated_data, palvelussuhde, validator):
        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            if palvelussuhde.paattymis_pvm is not None and not validate_paivamaara1_before_paivamaara2(validated_data['paattymis_pvm'], palvelussuhde.paattymis_pvm, can_be_same=True):
                validator.error('paattymis_pvm', 'paattymis_pvm must be before palvelussuhde paattymis_pvm (or same).')
        if 'alkamis_pvm' in validated_data and validated_data['alkamis_pvm'] is not None:
            if not validate_paivamaara1_after_paivamaara2(validated_data['alkamis_pvm'], palvelussuhde.alkamis_pvm, can_be_same=True):
                validator.error('alkamis_pvm', 'alkamis_pvm must be after palvelussuhde alkamis_pvm (or same).')
            if not validate_paivamaara1_before_paivamaara2(validated_data['alkamis_pvm'], palvelussuhde.paattymis_pvm, can_be_same=False):
                validator.error('alkamis_pvm', 'alkamis_pvm must be before palvelussuhde paattymis_pvm.')


class PermissionCheckedTaydennyskoulutusTyontekijaListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).update(instance, validated_data)

    def to_internal_value(self, data):
        taydennyskoulutus_tyontekija_dicts = super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).to_internal_value(data)
        with ViewSetValidator() as validator:
            # Validate all provided tyontekijat exist and mutate 'tyontekija' field to data.
            for taydennyskoulutus_tyontekija in taydennyskoulutus_tyontekija_dicts:
                taydennyskoulutus_tyontekija['tyontekija'] = self._find_tyontekija(taydennyskoulutus_tyontekija, validator)
                if validator.messages:
                    break

            if not validator.messages:  # All tyontekijat found so check permissions
                user = self.context['request'].user
                tyontekija_ids = {itemgetter('tyontekija')(taydennyskoulutus_tyontekija_dict).id
                                  for taydennyskoulutus_tyontekija_dict in taydennyskoulutus_tyontekija_dicts
                                  }
                if not is_correct_taydennyskoulutus_tyontekija_permission(user, tyontekija_ids, throws=False):
                    validator.error('tyontekija', _tyontekija_not_specified_error_message)

        return taydennyskoulutus_tyontekija_dicts

    def to_representation(self, data):
        user = self.context['request'].user
        # On listing filter tyontekijat that user has no permissions
        if not user.is_superuser and self.context['view'].action == 'list':
            checked_data, organisaatio_oids = filter_authorized_taydennyskoulutus_tyontekijat(data, user)
            if not organisaatio_oids:
                return []
            return super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).to_representation(checked_data)
        return super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).to_representation(data)

    def _find_tyontekija(self, data, validator):
        henkilo_oid = data.get('henkilo_oid', None)
        vakajarjestaja_oid = data.get('vakajarjestaja_oid', None)
        lahdejarjestelma = data.get('lahdejarjestelma', None)
        tunniste = data.get('tunniste', None)

        tyontekija = data.get('tyontekija', None)

        if (henkilo_oid is not None) == (vakajarjestaja_oid is None):
            validator.error('henkilo_oid', 'Either both henkilo_oid and vakajarjestaja_oid, or neither must be given.')
            return None
        if (lahdejarjestelma is not None) == (tunniste is None):
            validator.error('tunniste', 'Either both lahdejarjestelma and tunniste, or neither must be given.')
            return None

        if henkilo_oid is not None:
            tyontekija = self._find_tyontekija_by_henkilo_oid(validator, henkilo_oid, vakajarjestaja_oid, tyontekija)

        if tunniste is not None:
            tyontekija = self._find_tyontekija_by_tunniste(validator, tunniste, lahdejarjestelma, tyontekija)

        if tyontekija is None:
            validator.error('tyontekija', _tyontekija_not_specified_error_message)

        return tyontekija

    def _find_tyontekija_by_henkilo_oid(self, validator, henkilo_oid, vakajarjestaja_oid, tyontekija=None):
        try:
            tyontekija_by_henkilo_oid = Tyontekija.objects.get(henkilo__henkilo_oid=henkilo_oid, vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
        except Tyontekija.DoesNotExist:
            validator.error('henkilo_oid', 'Couldn\'t find tyontekija matching the given (henkilo_oid, vakajarjestaja_oid).')
            return

        if tyontekija is not None and tyontekija_by_henkilo_oid.id != tyontekija.id:
            validator.error('henkilo_oid', 'henkilo_oid doesn\'t refer to the same tyontekija as url.')
        return tyontekija_by_henkilo_oid

    def _find_tyontekija_by_tunniste(self, validator, tunniste, lahdejarjestelma, tyontekija=None):
        try:
            tyontekija_by_tunniste = Tyontekija.objects.get(tunniste=tunniste, lahdejarjestelma=lahdejarjestelma)
        except Tyontekija.DoesNotExist:
            validator.error('tunniste', 'Couldn\'t find tyontekija matching the given (lahdejarjestelma, tunniste).')
            return

        if tyontekija is not None and tyontekija_by_tunniste.id != tyontekija.id:
            validator.error('tunniste', 'Tunniste doesn\'t refer to the same tyontekija as url or henkilo_oid.')
        return tyontekija_by_tunniste


class NestedTaydennyskoulutusTyontekijaSerializer(serializers.ModelSerializer):
    tyontekija = TyontekijaHLField(required=False, view_name='tyontekija-detail')
    henkilo_oid = serializers.CharField(max_length=50, required=False, validators=[validators.validate_henkilo_oid])
    vakajarjestaja_oid = serializers.CharField(max_length=50, required=False, validators=[validators.validate_organisaatio_oid])
    lahdejarjestelma = serializers.CharField(max_length=2, required=False, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = serializers.CharField(max_length=120, required=False, validators=[validators.validate_tunniste])

    class Meta:
        model = TaydennyskoulutusTyontekija
        list_serializer_class = PermissionCheckedTaydennyskoulutusTyontekijaListSerializer
        exclude = ('id', 'taydennyskoulutus', 'changed_by', 'luonti_pvm', 'muutos_pvm')

    def create(self, data):
        user = self.context['request'].user

        tyontekija = data['tyontekija']
        self._validate_tehtavanimike_koodi(data)

        return TaydennyskoulutusTyontekija.objects.create(tyontekija=tyontekija,
                                                          tehtavanimike_koodi=data['tehtavanimike_koodi'],
                                                          taydennyskoulutus=data['taydennyskoulutus'],
                                                          changed_by=user)

    @caching_to_representation('taydennyskoulutustyontekija')
    def to_representation(self, instance):
        tyontekija = instance.tyontekija

        instance = super(NestedTaydennyskoulutusTyontekijaSerializer, self).to_representation(instance)
        instance['henkilo_oid'] = tyontekija.henkilo.henkilo_oid
        instance['vakajarjestaja_oid'] = tyontekija.vakajarjestaja.organisaatio_oid
        instance['lahdejarjestelma'] = tyontekija.lahdejarjestelma
        instance['tunniste'] = tyontekija.tunniste

        return instance

    def validate(self, data):

        return data

    def _validate_tehtavanimike_koodi(self, data):
        tyontekija = data.get('tyontekija', None)
        tehtavanimike_koodi = data.get('tehtavanimike_koodi', None)

        with ViewSetValidator() as validator:
            if tehtavanimike_koodi is None:
                # This field is required also in PATCH requests so we need to check it manually
                validator.error('tehtavanimike_koodi', 'This field is required.')
                return

            if not Tyontekija.objects.filter(id=tyontekija.id, palvelussuhteet__tyoskentelypaikat__tehtavanimike_koodi=tehtavanimike_koodi).exists():
                validator.error('tehtavanimike_koodi', f'tyontekija with ID {tyontekija.id} doesn\'t have tehtavanimike_koodi {tehtavanimike_koodi}')


class TaydennyskoulutusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    taydennyskoulutus_tyontekijat = NestedTaydennyskoulutusTyontekijaSerializer(required=True, allow_empty=False, many=True, source='taydennyskoulutukset_tyontekijat')

    class Meta:
        model = Taydennyskoulutus
        exclude = ('tyontekijat', 'changed_by', 'luonti_pvm')

    @caching_to_representation('taydennyskoulutus')
    def to_representation(self, instance):
        return super(TaydennyskoulutusSerializer, self).to_representation(instance)

    def create(self, validated_data):
        tyontekijat = validated_data.pop('taydennyskoulutukset_tyontekijat', [])
        taydennyskoulutus = Taydennyskoulutus.objects.create(**validated_data)

        for tyontekija in tyontekijat:
            tyontekija['taydennyskoulutus'] = taydennyskoulutus
            NestedTaydennyskoulutusTyontekijaSerializer(context=self._context).create(tyontekija)

        return taydennyskoulutus

    def validate(self, data):
        with ViewSetValidator() as validator:
            tyontekija_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutukset_tyontekijat']}
            if len(tyontekija_set) != len(data['taydennyskoulutukset_tyontekijat']):
                validator.error('taydennyskoulutus_tyontekijat', 'Duplicates detected.')

        return data


class TaydennyskoulutusUpdateSerializer(serializers.HyperlinkedModelSerializer):
    taydennyskoulutus_tyontekijat = NestedTaydennyskoulutusTyontekijaSerializer(required=False, allow_empty=False, many=True, source='taydennyskoulutukset_tyontekijat')
    taydennyskoulutus_tyontekijat_add = NestedTaydennyskoulutusTyontekijaSerializer(required=False, allow_empty=False, many=True)
    taydennyskoulutus_tyontekijat_remove = NestedTaydennyskoulutusTyontekijaSerializer(required=False, allow_empty=False, many=True)

    class Meta:
        model = Taydennyskoulutus
        exclude = ('tyontekijat', 'changed_by', 'luonti_pvm')

    def validate(self, data):
        instance = self.instance

        with ViewSetValidator() as validator:
            if 'taydennyskoulutukset_tyontekijat' in data and ('taydennyskoulutus_tyontekijat_add' in data or 'taydennyskoulutus_tyontekijat_remove' in data):
                validator.error('taydennyskoulutus_tyontekijat', 'taydennyskoulutus_tyontekijat_add and taydennyskoulutus_tyontekijat_remove fields cannot be used if tyontekijat is provided')

            if 'taydennyskoulutukset_tyontekijat' in data:
                tyontekijat_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutukset_tyontekijat']}
                if len(tyontekijat_set) != len(data['taydennyskoulutukset_tyontekijat']):
                    validator.error('taydennyskoulutus_tyontekijat', 'Duplicates detected.')

        self._validate_tyontekijat_add(instance, data)
        self._validate_tyontekijat_remove(instance, data)

        return super(TaydennyskoulutusUpdateSerializer, self).validate(data)

    def _validate_tyontekijat_add(self, instance, data):
        if 'taydennyskoulutus_tyontekijat_add' in data:
            with ViewSetValidator() as validator:
                tyontekijat_add_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutus_tyontekijat_add']}
                if len(tyontekijat_add_set) != len(data['taydennyskoulutus_tyontekijat_add']):
                    validator.error('taydennyskoulutus_tyontekijat_add', 'Duplicates detected.')
                for tyontekija in data['taydennyskoulutus_tyontekijat_add']:
                    if instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija['tyontekija'].id,
                                                                        tehtavanimike_koodi=tyontekija['tehtavanimike_koodi']).exists():
                        validator.error('taydennyskoulutus_tyontekijat_add', 'Tyontekija cannot have same taydennyskoulutus more than once')

    def _validate_tyontekijat_remove(self, instance, data):
        if 'taydennyskoulutus_tyontekijat_remove' in data:
            with ViewSetValidator() as validator:
                tyontekijat_remove_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutus_tyontekijat_remove']}
                if len(tyontekijat_remove_set) != len(data['taydennyskoulutus_tyontekijat_remove']):
                    validator.error('taydennyskoulutus_tyontekijat_remove', 'Duplicates detected.')
                for tyontekija in data['taydennyskoulutus_tyontekijat_remove']:
                    if not instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija['tyontekija'].id,
                                                                            tehtavanimike_koodi=tyontekija['tehtavanimike_koodi']).exists():
                        validator.error('taydennyskoulutus_tyontekijat_remove', 'Tyontekija must have this taydennyskoulutus')
                if len(tyontekijat_remove_set) == instance.taydennyskoulutukset_tyontekijat.count():
                    validator.error('taydennyskoulutus_tyontekijat_remove', 'Cannot delete all tyontekijat from taydennyskoulutus')

    def update(self, instance, validated_data):
        self._update_tyontekijat(instance, validated_data)

        for field in ['nimi', 'suoritus_pvm', 'koulutuspaivia', 'lahdejarjestelma', 'tunniste']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        instance.save()
        return instance

    def _update_tyontekijat(self, instance, validated_data):
        if 'taydennyskoulutukset_tyontekijat' in validated_data:
            # Remove previous tyontekijat from this taydennyskoulutus
            TaydennyskoulutusTyontekija.objects.filter(taydennyskoulutus=instance).delete()

            tyontekijat = validated_data.pop('taydennyskoulutukset_tyontekijat', [])
            for tyontekija in tyontekijat:
                tyontekija['taydennyskoulutus'] = instance
                NestedTaydennyskoulutusTyontekijaSerializer(context=self._context).create(tyontekija)

        if 'taydennyskoulutus_tyontekijat_add' in validated_data:
            tyontekijat_add = validated_data.pop('taydennyskoulutus_tyontekijat_add', [])
            for tyontekija_add in tyontekijat_add:
                tyontekija_add['taydennyskoulutus'] = instance
                NestedTaydennyskoulutusTyontekijaSerializer(context=self._context).create(tyontekija_add)

        if 'taydennyskoulutus_tyontekijat_remove' in validated_data:
            tyontekijat_remove = validated_data.pop('taydennyskoulutus_tyontekijat_remove', [])
            for tyontekija_remove in tyontekijat_remove:
                TaydennyskoulutusTyontekija.objects.filter(tyontekija=tyontekija_remove['tyontekija'],
                                                           tehtavanimike_koodi=tyontekija_remove['tehtavanimike_koodi']).delete()


class TaydennyskoulutusTyontekijaListSerializer(serializers.ModelSerializer):
    henkilo_etunimet = serializers.CharField(source='henkilo.etunimet')
    henkilo_sukunimi = serializers.CharField(source='henkilo.sukunimi')
    henkilo_oid = serializers.CharField(source='henkilo.henkilo_oid')
    tehtavanimike_koodit = serializers.SerializerMethodField()

    def get_tehtavanimike_koodit(self, instance):
        palvelussuhteet = instance.palvelussuhteet.all()
        return Tyoskentelypaikka.objects.filter(palvelussuhde__in=palvelussuhteet).values_list('tehtavanimike_koodi', flat=True).distinct()

    class Meta:
        model = Tyontekija
        fields = ('henkilo_etunimet', 'henkilo_sukunimi', 'henkilo_oid', 'tehtavanimike_koodit')
