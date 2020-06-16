from rest_framework import serializers

from varda import related_object_validations, validators
from varda.cache import caching_to_representation
from varda.misc_viewsets import ViewSetValidator
from varda.models import (Henkilo, TilapainenHenkilosto, Tutkinto, Tyontekija, VakaJarjestaja, Palvelussuhde,
                          Tyoskentelypaikka, Toimipaikka, PidempiPoissaolo)
from varda.related_object_validations import (create_daterange, daterange_overlap,
                                              check_overlapping_tyoskentelypaikka_object,
                                              check_overlapping_palvelussuhde_object,
                                              check_if_admin_mutable_object_is_changed)
from varda.serializers import (HenkiloHLField, VakaJarjestajaPermissionCheckedHLField,
                               PermissionCheckedHLFieldMixin, ToimipaikkaPermissionCheckedHLField)
from varda.serializers_common import OidRelatedField
from varda.validators import (validate_paattymispvm_after_alkamispvm, validate_paivamaara1_after_paivamaara2,
                              validate_paivamaara1_before_paivamaara2, parse_paivamaara)


class TyontekijaPermissionCheckedHLField(PermissionCheckedHLFieldMixin, serializers.HyperlinkedRelatedField):
    check_permission = 'change_tyontekija'

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


class PalvelussuhdePermissionCheckedHLField(PermissionCheckedHLFieldMixin, serializers.HyperlinkedRelatedField):
    check_permission = 'change_palvelussuhde'

    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Palvelussuhde.objects.all().order_by('id')
        else:
            queryset = Palvelussuhde.objects.none()
        return queryset


class TyontekijaSerializer(serializers.HyperlinkedModelSerializer):
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
                                         check_permission='view_vakajarjestaja',
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
            if self.context['request'].method in ['PUT', 'PATCH']:
                instance = self.context['view'].get_object()
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
                                         check_permission='view_vakajarjestaja',
                                         either_required=True)

    class Meta:
        model = TilapainenHenkilosto
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tilapainen_henkilosto')
    def to_representation(self, instance):
        return super(TilapainenHenkilostoSerializer, self).to_representation(instance)

    def validate(self, data):
        # Validate only when creating tilapainen henkilosto
        if self.context['request'].method == 'POST':
            self.verify_unique_month(data)

        # Validate only when updating existing tilapainen henkilosto
        if self.instance:
            instance = self.instance
            msg = {}
            if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                msg = {'vakajarjestaja': ['Changing of vakajarjestaja is not allowed']}
            if 'kuukausi' in data and data['kuukausi'] != instance.kuukausi:
                msg.update({'kuukausi': ['Changing of kuukausi is not allowed']})
            if msg:
                raise serializers.ValidationError(msg, code='invalid')
        return data

    def verify_unique_month(self, data):
        tilapainen_henkilosto_qs = TilapainenHenkilosto.objects.filter(vakajarjestaja=data['vakajarjestaja'],
                                                                       kuukausi__year=data['kuukausi'].year,
                                                                       kuukausi__month=data['kuukausi'].month)
        if tilapainen_henkilosto_qs.exists():
            raise serializers.ValidationError({'kuukausi': ['tilapainen henkilosto already exists for this month.']},
                                              code='invalid')


class TutkintoSerializer(serializers.HyperlinkedModelSerializer):
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
                                         check_permission='view_vakajarjestaja',
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
        henkilo = data.get('henkilo')
        msg = {}
        if not Tyontekija.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=henkilo).exists():
            msg = {'tyontekija': ['Provided vakajarjestaja has not added this henkilo as tyontekija']}
        if msg:
            raise serializers.ValidationError(msg, code='invalid')
        return data


class PalvelussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    tyontekija = TyontekijaPermissionCheckedHLField(view_name='tyontekija-detail')

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
                with validator.wrap():
                    validate_paattymispvm_after_alkamispvm(data)
                if 'tyontekija' in data:
                    tyontekija = data['tyontekija']
                else:
                    tyontekija = palvelussuhde.tyontekija
                if 'tutkinto_koodi' in data:
                    tutkinto_koodi = data['tutkinto_koodi']
                else:
                    tutkinto_koodi = palvelussuhde.tutkinto_koodi
                self.validate_tutkinto(tyontekija, tutkinto_koodi, validator)
                if 'tyontekija' in data:
                    check_if_admin_mutable_object_is_changed(self.context['request'].user, palvelussuhde, data, 'tyontekija')

                with validator.wrap():
                    check_overlapping_palvelussuhde_object(data, Palvelussuhde, palvelussuhde.id)

        # CREATE
        else:
            with ViewSetValidator() as validator:
                with validator.wrap():
                    validate_paattymispvm_after_alkamispvm(data)

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
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail')
    toimipaikka = ToimipaikkaPermissionCheckedHLField(required=False, allow_null=True, view_name='toimipaikka-detail')
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      check_permission='view_toimipaikka',
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
        if not self.instance:
            palvelussuhde = data['palvelussuhde']
            toimipaikka = data.get('toimipaikka')
            kiertava_tyontekija_kytkin = data.get('kiertava_tyontekija_kytkin')
        else:
            palvelussuhde = data['palvelussuhde'] or self.instance.palvelussuhde
            toimipaikka = data.get('toimipaikka') or self.instance.toimipaikka
            kiertava_tyontekija_kytkin = data.get('kiertava_tyontekija_kytkin') or self.instance.kiertava_tyontekija_kytkin

        with ViewSetValidator() as validator:
            if kiertava_tyontekija_kytkin and toimipaikka:
                validator.error('kiertava_tyontekija_kytkin', 'toimipaikka can\'t be specified with kiertava_tyontekija_kytkin.')
            validate_dates(data, palvelussuhde, validator)

            with validator.wrap():
                validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator)

            if not kiertava_tyontekija_kytkin:
                with validator.wrap():
                    check_overlapping_tyoskentelypaikka_object(data, Tyoskentelypaikka)

            if toimipaikka and toimipaikka.vakajarjestaja_id != palvelussuhde.tyontekija.vakajarjestaja_id:
                validator.error('toimipaikka', 'Toimipaikka must have the same vakajarjestaja as tyontekija')

        return data


def validate_dates(validated_data, palvelussuhde, validator):
    with validator.wrap():
        validators.validate_paattymispvm_after_alkamispvm(validated_data)

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
    class Meta:
        model = Tyoskentelypaikka
        fields = ('tehtavanimike_koodi', 'kelpoisuus_kytkin', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma', 'tunniste')

    @caching_to_representation('tyoskentelypaikka')
    def to_representation(self, instance):
        return super(TyoskentelypaikkaUpdateSerializer, self).to_representation(instance)

    def validate(self, data):
        tyoskentelypaikka = self.instance
        palvelussuhde = tyoskentelypaikka.palvelussuhde
        toimipaikka = data.get('toimipaikka') or tyoskentelypaikka.toimipaikka
        kiertava_tyontekija_kytkin = data.get('kiertava_tyontekija_kytkin') or tyoskentelypaikka.kiertava_tyontekija_kytkin

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


class PidempiPoissaoloSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail')

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
            if 'alkamis_pvm' not in data:
                data['alkamis_pvm'] = pidempipoissaolo_obj.alkamis_pvm
            if 'paattymis_pvm' not in data:
                data['paattymis_pvm'] = pidempipoissaolo_obj.paattymis_pvm
            if 'palvelussuhde' not in data:
                data['palvelussuhde'] = pidempipoissaolo_obj.palvelussuhde

            with ViewSetValidator() as validator:
                self.validate_dates(data, pidempipoissaolo_obj.palvelussuhde, validator)

                with validator.wrap():
                    related_object_validations.check_overlapping_pidempipoissaolo_object(data, PidempiPoissaolo, pidempipoissaolo_obj.id)
            related_object_validations.check_if_immutable_object_is_changed(pidempipoissaolo_obj, data, 'palvelussuhde')

        return data

    def validate_dates(self, validated_data, palvelussuhde, validator):
        with validator.wrap():
            validate_paattymispvm_after_alkamispvm(validated_data)

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
