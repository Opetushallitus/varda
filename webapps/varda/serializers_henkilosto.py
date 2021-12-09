import datetime

from drf_yasg.utils import swagger_serializer_method
from rest_framework import serializers

from varda import validators
from varda.cache import caching_to_representation, get_object_ids_for_user_by_model
from varda.enums.error_messages import ErrorMessages
from varda.misc_viewsets import ViewSetValidator
from varda.models import (Henkilo, TilapainenHenkilosto, Tutkinto, Tyontekija, VakaJarjestaja, Palvelussuhde,
                          Tyoskentelypaikka, Toimipaikka, PidempiPoissaolo, TaydennyskoulutusTyontekija,
                          Taydennyskoulutus, Z4_CasKayttoOikeudet)
from varda.permissions import (is_correct_taydennyskoulutus_tyontekija_permission,
                               filter_authorized_taydennyskoulutus_tyontekijat, user_permission_groups_in_organization,
                               is_oph_staff, get_available_tehtavanimike_codes_for_user)
from varda.related_object_validations import (create_date_range, date_range_overlap,
                                              check_if_admin_mutable_object_is_changed, check_overlapping_palvelussuhde,
                                              check_overlapping_tyoskentelypaikka, check_overlapping_pidempi_poissaolo,
                                              check_if_immutable_object_is_changed)
from varda.serializers_common import (OidRelatedField, TunnisteRelatedField, VakaJarjestajaPermissionCheckedHLField,
                                      PermissionCheckedHLFieldMixin, ToimipaikkaPermissionCheckedHLField,
                                      OptionalToimipaikkaMixin, HenkiloPermissionCheckedHLField)
from varda.validators import (validate_paattymispvm_same_or_after_alkamispvm, validate_paivamaara1_after_paivamaara2,
                              parse_paivamaara, fill_missing_fields_for_validations)


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


class TyontekijaOptionalToimipaikkaMixin(OptionalToimipaikkaMixin):
    toimipaikka = ToimipaikkaPermissionCheckedHLField(view_name='toimipaikka-detail', required=False, write_only=True,
                                                      permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA])


class TyontekijaSerializer(TyontekijaOptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloPermissionCheckedHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validators.validate_henkilo_oid,
                                  either_required=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA],
                                                            accept_toimipaikka_permission=True)
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
                validator.error('henkilo', ErrorMessages.TY003.value)

            # Validate only when updating existing henkilo
            if self.instance:
                instance = self.instance
                if 'henkilo' in data:
                    check_if_admin_mutable_object_is_changed(self.context['request'].user, instance, data, 'henkilo')
                if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                    validator.error('vakajarjestaja', ErrorMessages.GE013.value)
            elif toimipaikka := data.get('toimipaikka', None):
                # Only validate in POST
                if toimipaikka.vakajarjestaja != data['vakajarjestaja']:
                    validator.error('toimipaikka', ErrorMessages.MI019.value)

        return data


class TilapainenHenkilostoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA])
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
                self.validate_workers_and_working_hours(data, validator)
                self.validate_date_in_allowed_period(data, validator)
                with validator.wrap():
                    self.validate_date_within_vakajarjestaja(data, validator)

            # Validate only when updating existing tilapainen henkilosto
            if self.instance:
                instance = self.instance
                fill_missing_fields_for_validations(data, instance)
                if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                    validator.error('vakajarjestaja', ErrorMessages.GE013.value)
                if 'kuukausi' in data and data['kuukausi'] != instance.kuukausi:
                    validator.error('kuukausi', ErrorMessages.GE013.value)
                self.validate_workers_and_working_hours(data, validator)
            return data

    def verify_unique_month(self, data, validator):
        tilapainen_henkilosto_qs = TilapainenHenkilosto.objects.filter(vakajarjestaja=data['vakajarjestaja'],
                                                                       kuukausi__year=data['kuukausi'].year,
                                                                       kuukausi__month=data['kuukausi'].month)
        if tilapainen_henkilosto_qs.exists():
            validator.error('kuukausi', ErrorMessages.TH001.value)

    def validate_date_within_vakajarjestaja(self, data, validator):
        vakajarjestaja = data['vakajarjestaja']
        kuukausi = data['kuukausi']
        if kuukausi < self._get_first_day_of_month(vakajarjestaja.alkamis_pvm):
            validator.error('kuukausi', ErrorMessages.TH002.value)
        if vakajarjestaja.paattymis_pvm is not None and kuukausi > self._get_last_day_of_month(vakajarjestaja.paattymis_pvm):
            validator.error('kuukausi', ErrorMessages.TH003.value)

    def validate_workers_and_working_hours(self, data, validator):
        tyontekijat_count = data['tyontekijamaara']
        hours_count = data['tuntimaara']
        if tyontekijat_count == 0 and hours_count != 0:
            validator.error('tuntimaara', ErrorMessages.TH004.value)
        if tyontekijat_count != 0 and hours_count == 0:
            validator.error('tyontekijamaara', ErrorMessages.TH005.value)

        future_limit = self._get_last_day_of_month(datetime.date.today())

        if data['kuukausi'] > future_limit and (tyontekijat_count != 0 or hours_count != 0):
            validator.error('errors', ErrorMessages.TH009.value)

    def validate_date_in_allowed_period(self, data, validator):
        kuukausi = data['kuukausi']

        if kuukausi < datetime.date(year=2020, month=9, day=1):
            validator.error('kuukausi', ErrorMessages.TH008.value)

        today = datetime.date.today()

        # TilapainenHenkilosto can be saved for the current period or in the past
        upper_limit = today.replace(month=6, day=30) if today.month < 7 else today.replace(month=12, day=31)
        if kuukausi > upper_limit:
            validator.error('kuukausi', ErrorMessages.TH007.value)

    def _get_first_day_of_month(self, date):
        return date.replace(day=1)

    def _get_last_day_of_month(self, date):
        if date.month == 12:
            return date.replace(day=31)
        else:
            return date.replace(month=date.month + 1, day=1) - datetime.timedelta(days=1)


class TutkintoSerializer(TyontekijaOptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloPermissionCheckedHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validators.validate_henkilo_oid,
                                  either_required=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA],
                                                            accept_toimipaikka_permission=True)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)

    class Meta:
        model = Tutkinto
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tutkinto')
    def to_representation(self, instance):
        return super(TutkintoSerializer, self).to_representation(instance)

    def validate(self, data):
        with ViewSetValidator() as validator:
            vakajarjestaja = data.get('vakajarjestaja')
            toimipaikka = data.get('toimipaikka')
            henkilo = data.get('henkilo')
            if not Tyontekija.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=henkilo).exists():
                validator.error('tyontekija', ErrorMessages.TU002.value)
            if vakajarjestaja and toimipaikka and vakajarjestaja != toimipaikka.vakajarjestaja:
                validator.error('toimipaikka', ErrorMessages.TU003.value)
        return data


class PalvelussuhdeSerializer(TyontekijaOptionalToimipaikkaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
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
        with ViewSetValidator() as validator:
            if self.instance:
                fill_missing_fields_for_validations(data, self.instance)

                with validator.wrap():
                    check_overlapping_palvelussuhde(data, self.instance.id)

                if 'tyontekija' in data:
                    check_if_admin_mutable_object_is_changed(self.context['request'].user, self.instance, data,
                                                             'tyontekija')
            else:
                if toimipaikka := data.get('toimipaikka', None):
                    if toimipaikka.vakajarjestaja != data['tyontekija'].vakajarjestaja:
                        validator.error('toimipaikka', ErrorMessages.MI019.value)

                with validator.wrap():
                    check_overlapping_palvelussuhde(data)

            self.validate_tutkinto(data['tyontekija'], data['tutkinto_koodi'], validator)

            if data.get('paattymis_pvm') is None and data['tyosuhde_koodi'] == '2':
                validator.error('paattymis_pvm', ErrorMessages.PS003.value)

            with validator.wrap():
                validate_paattymispvm_same_or_after_alkamispvm(data)
                alkamis_pvm = data['alkamis_pvm']
                paattymis_pvm = data.get('paattymis_pvm')
                validators.validate_tyosuhde_koodi(data['tyosuhde_koodi'], alkamis_pvm, paattymis_pvm)
                validators.validate_tyoaika_koodi(data['tyoaika_koodi'], alkamis_pvm, paattymis_pvm)
        return data

    def validate_tutkinto(self, tyontekija, tutkinto_koodi, validator):
        if not tyontekija.henkilo.tutkinnot.filter(tutkinto_koodi=tutkinto_koodi,
                                                   vakajarjestaja=tyontekija.vakajarjestaja).exists():
            validator.error('tutkinto_koodi', ErrorMessages.PS005.value)


class TyoskentelypaikkaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail', required=False)
    palvelussuhde_tunniste = TunnisteRelatedField(object_type=Palvelussuhde,
                                                  parent_field='palvelussuhde',
                                                  prevalidator=validators.validate_tunniste,
                                                  either_required=True)
    toimipaikka = ToimipaikkaPermissionCheckedHLField(required=False, allow_null=True, view_name='toimipaikka-detail',
                                                      permission_groups=[Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA])
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
        instance = self.instance
        if instance:
            fill_missing_fields_for_validations(data, instance)

        palvelussuhde = data['palvelussuhde']
        toimipaikka = data.get('toimipaikka', None)
        kiertava_tyontekija_kytkin = data['kiertava_tyontekija_kytkin']

        with ViewSetValidator() as validator:
            validate_tyoskentelypaikka_general(validator, data, toimipaikka, palvelussuhde, kiertava_tyontekija_kytkin)

            if toimipaikka and toimipaikka.vakajarjestaja_id != palvelussuhde.tyontekija.vakajarjestaja_id:
                validator.error('toimipaikka', ErrorMessages.TA005.value)

        return data


def validate_tyoskentelypaikka_general(validator, data, toimipaikka, palvelussuhde,
                                       kiertava_tyontekija_kytkin, tyoskentelypaikka_id=None):
    if kiertava_tyontekija_kytkin and toimipaikka:
        validator.error('kiertava_tyontekija_kytkin', ErrorMessages.TA004.value)
    if not kiertava_tyontekija_kytkin and not toimipaikka:
        validator.error('toimipaikka', ErrorMessages.TA012.value)

    validate_tyoskentelypaikka_dates(data, palvelussuhde, validator)

    with validator.wrap():
        validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator)
        validators.validate_tehtavanimike_koodi(data['tehtavanimike_koodi'], data['alkamis_pvm'],
                                                data.get('paattymis_pvm'))

    if not kiertava_tyontekija_kytkin:
        with validator.wrap():
            if tyoskentelypaikka_id:
                check_overlapping_tyoskentelypaikka(data, tyoskentelypaikka_id)
            else:
                check_overlapping_tyoskentelypaikka(data)


def validate_tyoskentelypaikka_dates(validated_data, palvelussuhde, validator):
    with validator.wrap():
        validators.validate_paattymispvm_same_or_after_alkamispvm(validated_data)

    tyoskentelypaikka_paattymis_pvm = validated_data.get('paattymis_pvm', None)
    tyoskentelypaikka_alkamis_pvm = validated_data.get('alkamis_pvm', None)
    if tyoskentelypaikka_paattymis_pvm:
        if (palvelussuhde.paattymis_pvm is not None and not validators.validate_paivamaara1_before_paivamaara2(tyoskentelypaikka_paattymis_pvm, palvelussuhde.paattymis_pvm, can_be_same=True)):
            validator.error('paattymis_pvm', ErrorMessages.TA006.value)
        if not validate_paivamaara1_after_paivamaara2(tyoskentelypaikka_paattymis_pvm, '2020-09-01', can_be_same=True):
            validator.error('paattymis_pvm', ErrorMessages.TA007.value)
    elif palvelussuhde.paattymis_pvm:
        validator.error('paattymis_pvm', ErrorMessages.TA013.value)

    if not validators.validate_paivamaara1_after_paivamaara2(tyoskentelypaikka_alkamis_pvm, palvelussuhde.alkamis_pvm, can_be_same=True):
        validator.error('alkamis_pvm', ErrorMessages.TA008.value)
    if not validators.validate_paivamaara1_before_paivamaara2(tyoskentelypaikka_alkamis_pvm, palvelussuhde.paattymis_pvm, can_be_same=True):
        validator.error('alkamis_pvm', ErrorMessages.TA009.value)


def validate_overlapping_kiertavyys(data, palvelussuhde, kiertava_tyontekija_kytkin, validator):
    inverse_kiertava_kytkin = not kiertava_tyontekija_kytkin
    related_palvelussuhde_tyoskentelypaikat = Tyoskentelypaikka.objects.filter(palvelussuhde=palvelussuhde, kiertava_tyontekija_kytkin=inverse_kiertava_kytkin)

    range_this = create_date_range(data['alkamis_pvm'], data.get('paattymis_pvm', None))
    for item in related_palvelussuhde_tyoskentelypaikat:
        range_other = create_date_range(item.alkamis_pvm, item.paattymis_pvm)
        if date_range_overlap(range_this, range_other):
            validator.error('kiertava_tyontekija_kytkin', ErrorMessages.TA010.value)
            break


class TyoskentelypaikkaUpdateSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    palvelussuhde = serializers.HyperlinkedRelatedField(read_only=True, view_name='palvelussuhde-detail')
    palvelussuhde_tunniste = TunnisteRelatedField(object_type=Palvelussuhde,
                                                  parent_field='palvelussuhde',
                                                  prevalidator=validators.validate_tunniste,
                                                  read_only=True)
    toimipaikka = serializers.HyperlinkedRelatedField(read_only=True, view_name='toimipaikka-detail')
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      read_only=True)

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
            validate_tyoskentelypaikka_general(validator, data, toimipaikka, palvelussuhde,
                                               kiertava_tyontekija_kytkin, tyoskentelypaikka_id=tyoskentelypaikka.id)

        return data


class PidempiPoissaoloSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    palvelussuhde = PalvelussuhdePermissionCheckedHLField(view_name='palvelussuhde-detail', required=False)
    palvelussuhde_tunniste = TunnisteRelatedField(object_type=Palvelussuhde,
                                                  parent_field='palvelussuhde',
                                                  prevalidator=validators.validate_tunniste,
                                                  either_required=True)
    alkamis_pvm = serializers.DateField(required=True)
    paattymis_pvm = serializers.DateField(required=True, validators=[validators.validate_pidempi_poissaolo_paattymis_pvm])

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
                self.validate_dates(data, validator)
                with validator.wrap():
                    check_overlapping_pidempi_poissaolo(data)
        else:
            pidempipoissaolo_obj = self.instance
            fill_missing_fields_for_validations(data, pidempipoissaolo_obj)

            with ViewSetValidator() as validator:
                self.validate_dates(data, validator)

                with validator.wrap():
                    check_overlapping_pidempi_poissaolo(data, pidempipoissaolo_obj.id)
            check_if_immutable_object_is_changed(pidempipoissaolo_obj, data, 'palvelussuhde')

        return data

    def validate_dates(self, validated_data, validator):
        with validator.wrap():
            validate_paattymispvm_same_or_after_alkamispvm(validated_data)

        self.validate_duration(validated_data, validator)

    def validate_duration(self, validated_data, validator):
        if 'paattymis_pvm' in validated_data and validated_data['paattymis_pvm'] is not None:
            start = parse_paivamaara(validated_data['alkamis_pvm'])
            end = parse_paivamaara(validated_data['paattymis_pvm'])
            # The day difference of datetime subtraction does not include the start date
            if (end - start).days < 59:
                validator.error('paattymis_pvm', ErrorMessages.PP003.value)


class PermissionCheckedTaydennyskoulutusTyontekijaListSerializer(serializers.ListSerializer):
    def update(self, instance, validated_data):
        super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).update(instance, validated_data)

    def to_internal_value(self, data):
        taydennyskoulutus_tyontekija_dicts = super(PermissionCheckedTaydennyskoulutusTyontekijaListSerializer, self).to_internal_value(data)
        with ViewSetValidator() as validator:
            # Validate all provided tyontekijat exist and mutate 'tyontekija' field to data.
            for index, taydennyskoulutus_tyontekija in enumerate(taydennyskoulutus_tyontekija_dicts):
                taydennyskoulutus_tyontekija['tyontekija'] = self._find_tyontekija(taydennyskoulutus_tyontekija, validator, index)
                if validator.messages:
                    break

            if not validator.messages:
                # All tyontekijat found so check permissions
                user = self.context['request'].user
                if not is_correct_taydennyskoulutus_tyontekija_permission(user, taydennyskoulutus_tyontekija_dicts, throws=False):
                    validator.error('0', ErrorMessages.TK001.value)

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

    def _find_tyontekija(self, data, validator, index):
        henkilo_oid = data.get('henkilo_oid', None)
        vakajarjestaja_oid = data.get('vakajarjestaja_oid', None)
        lahdejarjestelma = data.get('lahdejarjestelma', None)
        tunniste = data.get('tunniste', None)

        tyontekija = data.get('tyontekija', None)

        if (henkilo_oid is not None) == (vakajarjestaja_oid is None):
            validator.error_nested([index, 'henkilo_oid'], ErrorMessages.TK002.value)
            return None
        if (lahdejarjestelma is not None) == (tunniste is None):
            validator.error_nested([index, 'tunniste'], ErrorMessages.TK003.value)
            return None

        if henkilo_oid is not None:
            tyontekija = self._find_tyontekija_by_henkilo_oid(validator, henkilo_oid, vakajarjestaja_oid, index, tyontekija)

        if tunniste is not None:
            tyontekija = self._find_tyontekija_by_tunniste(validator, tunniste, lahdejarjestelma, index, tyontekija)

        if tyontekija is None:
            validator.error_nested([index, 'tyontekija'], ErrorMessages.TK001.value)

        return tyontekija

    def _find_tyontekija_by_henkilo_oid(self, validator, henkilo_oid, vakajarjestaja_oid, index, tyontekija=None):
        try:
            tyontekija_by_henkilo_oid = Tyontekija.objects.get(henkilo__henkilo_oid=henkilo_oid, vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
        except Tyontekija.DoesNotExist:
            validator.error_nested([index, 'henkilo_oid'], ErrorMessages.TK004.value)
            return

        if tyontekija is not None and tyontekija_by_henkilo_oid.id != tyontekija.id:
            validator.error_nested([index, 'henkilo_oid'], ErrorMessages.TK005.value)
        return tyontekija_by_henkilo_oid

    def _find_tyontekija_by_tunniste(self, validator, tunniste, lahdejarjestelma, index, tyontekija=None):
        try:
            tyontekija_by_tunniste = Tyontekija.objects.get(tunniste=tunniste, lahdejarjestelma=lahdejarjestelma)
        except Tyontekija.DoesNotExist:
            validator.error_nested([index, 'tunniste'], ErrorMessages.TK006.value)
            return

        if tyontekija is not None and tyontekija_by_tunniste.id != tyontekija.id:
            validator.error_nested([index, 'tunniste'], ErrorMessages.TK007.value)
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
                validator.error('tehtavanimike_koodi', ErrorMessages.GE001.value)
                return

            if not Tyontekija.objects.filter(id=tyontekija.id, palvelussuhteet__tyoskentelypaikat__tehtavanimike_koodi=tehtavanimike_koodi).exists():
                validator.error('tehtavanimike_koodi', ErrorMessages.TK008.value)


class TaydennyskoulutusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    taydennyskoulutus_tyontekijat = NestedTaydennyskoulutusTyontekijaSerializer(required=True, allow_empty=False, many=True, source='taydennyskoulutukset_tyontekijat')
    taydennyskoulutus_tyontekijat_count = serializers.SerializerMethodField()

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
                validator.error('taydennyskoulutus_tyontekijat', ErrorMessages.TK010.value)

        return data

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_taydennyskoulutus_tyontekijat_count(self, instance):
        return instance.taydennyskoulutukset_tyontekijat.count()


class TaydennyskoulutusUpdateSerializer(serializers.HyperlinkedModelSerializer):
    taydennyskoulutus_tyontekijat = NestedTaydennyskoulutusTyontekijaSerializer(required=False, allow_empty=False, many=True, source='taydennyskoulutukset_tyontekijat')
    taydennyskoulutus_tyontekijat_add = NestedTaydennyskoulutusTyontekijaSerializer(write_only=True, required=False, allow_empty=False, many=True)
    taydennyskoulutus_tyontekijat_remove = NestedTaydennyskoulutusTyontekijaSerializer(write_only=True, required=False, allow_empty=False, many=True)
    taydennyskoulutus_tyontekijat_count = serializers.SerializerMethodField()

    class Meta:
        model = Taydennyskoulutus
        exclude = ('tyontekijat', 'changed_by', 'luonti_pvm')

    def validate(self, data):
        instance = self.instance

        with ViewSetValidator() as validator:
            if 'taydennyskoulutukset_tyontekijat' in data and ('taydennyskoulutus_tyontekijat_add' in data or 'taydennyskoulutus_tyontekijat_remove' in data):
                validator.error('taydennyskoulutus_tyontekijat', ErrorMessages.TK009.value)

            if 'taydennyskoulutukset_tyontekijat' in data:
                tyontekijat_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutukset_tyontekijat']}
                if len(tyontekijat_set) != len(data['taydennyskoulutukset_tyontekijat']):
                    validator.error('taydennyskoulutus_tyontekijat', ErrorMessages.TK010.value)

        is_new_tyontekijat_added = self._validate_tyontekijat_add(instance, data)
        self._validate_tyontekijat_remove(instance, data, is_new_tyontekijat_added)

        return super(TaydennyskoulutusUpdateSerializer, self).validate(data)

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField())
    def get_taydennyskoulutus_tyontekijat_count(self, instance):
        return instance.taydennyskoulutukset_tyontekijat.count()

    def _validate_tyontekijat_add(self, instance, data):
        """
        :return: boolean to signify if new tyontekijat were added in this request
        """
        tyontekijat_add = data.get('taydennyskoulutus_tyontekijat_add', [])
        with ViewSetValidator() as validator:
            tyontekijat_add_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in tyontekijat_add}
            if len(tyontekijat_add_set) != len(tyontekijat_add):
                validator.error('taydennyskoulutus_tyontekijat_add', ErrorMessages.TK010.value)
            for tyontekija in tyontekijat_add:
                if instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija['tyontekija'].id,
                                                                    tehtavanimike_koodi=tyontekija['tehtavanimike_koodi']).exists():
                    validator.error('taydennyskoulutus_tyontekijat_add', ErrorMessages.TK011.value)
        return len(tyontekijat_add) > 0

    def _validate_tyontekijat_remove(self, instance, data, is_new_tyontekijat_added):
        if 'taydennyskoulutus_tyontekijat_remove' in data:
            with ViewSetValidator() as validator:
                tyontekijat_remove_set = {(tyontekija['tyontekija'].id, tyontekija['tehtavanimike_koodi']) for tyontekija in data['taydennyskoulutus_tyontekijat_remove']}
                if len(tyontekijat_remove_set) != len(data['taydennyskoulutus_tyontekijat_remove']):
                    validator.error('taydennyskoulutus_tyontekijat_remove', ErrorMessages.TK010.value)
                for tyontekija in data['taydennyskoulutus_tyontekijat_remove']:
                    if not instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija['tyontekija'].id,
                                                                            tehtavanimike_koodi=tyontekija['tehtavanimike_koodi']).exists():
                        validator.error('taydennyskoulutus_tyontekijat_remove', ErrorMessages.TK012.value)
                if len(tyontekijat_remove_set) == instance.taydennyskoulutukset_tyontekijat.count() and not is_new_tyontekijat_added:
                    validator.error('taydennyskoulutus_tyontekijat_remove', ErrorMessages.TK013.value)

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
            instance.taydennyskoulutukset_tyontekijat.all().delete()

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
                instance.taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija_remove['tyontekija'],
                                                                 tehtavanimike_koodi=tyontekija_remove['tehtavanimike_koodi']).delete()


class TaydennyskoulutusTyontekijaListSerializer(serializers.ModelSerializer):
    henkilo_etunimet = serializers.CharField(source='henkilo.etunimet')
    henkilo_sukunimi = serializers.CharField(source='henkilo.sukunimi')
    henkilo_oid = serializers.CharField(source='henkilo.henkilo_oid')
    tehtavanimike_koodit = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.CharField()))
    def get_tehtavanimike_koodit(self, instance):
        return get_available_tehtavanimike_codes_for_user(self.context['request'].user, instance)

    class Meta:
        model = Tyontekija
        fields = ('henkilo_etunimet', 'henkilo_sukunimi', 'henkilo_oid', 'tehtavanimike_koodit')


class TyontekijaKoosteHenkiloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Henkilo
        fields = ('id', 'etunimet', 'sukunimi', 'henkilo_oid', 'turvakielto',)


class TyontekijaKoosteTyoskentelypaikkaSerializer(serializers.ModelSerializer):
    toimipaikka_nimi = serializers.ReadOnlyField(source='toimipaikka.nimi')
    toimipaikka_oid = serializers.ReadOnlyField(source='toimipaikka.organisaatio_oid')

    class Meta:
        model = Tyoskentelypaikka
        fields = ('id', 'toimipaikka_id', 'toimipaikka_oid', 'toimipaikka_nimi', 'tehtavanimike_koodi',
                  'kelpoisuus_kytkin', 'kiertava_tyontekija_kytkin', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma',
                  'tunniste', 'muutos_pvm')

    def to_representation(self, instance):
        return _get_permission_checked_henkilosto_tyontekija_objects(self, instance)


class TyontekijaKoostePidempiPoissaoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = PidempiPoissaolo
        fields = ('id', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma', 'tunniste', 'muutos_pvm')

    def to_representation(self, instance):
        return _get_permission_checked_henkilosto_tyontekija_objects(self, instance)


def _get_permission_checked_henkilosto_tyontekija_objects(serializer_instance, queryset):
    """
    Override to_representation so we can filter Tyoskentelypaikka and PidempiPoissaolo objects based on user permissions
    :param serializer_instance: serializer instance
    :param queryset: unfiltered list of object instances
    :return: list of objects user actually has permissions to
    """
    if not queryset.exists():
        return []

    user = serializer_instance.context['request'].user
    vakajarjestaja_oid = queryset.first().palvelussuhde.tyontekija.vakajarjestaja.organisaatio_oid

    tyontekija_groups_qs = user_permission_groups_in_organization(user, vakajarjestaja_oid,
                                                                  [Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_KATSELIJA,
                                                                   Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA])
    if not user.is_superuser and not is_oph_staff(user) and not tyontekija_groups_qs.exists():
        model_name = queryset.model.__name__.lower()
        queryset = queryset.filter(id__in=get_object_ids_for_user_by_model(user, model_name))

    filtered_list = []
    for instance in queryset.all():
        filtered_list.append(super(serializer_instance.__class__, serializer_instance).to_representation(instance))
    return filtered_list


class TyontekijaKoostePalvelussuhdeSerializer(serializers.ModelSerializer):
    tyoskentelypaikat = TyontekijaKoosteTyoskentelypaikkaSerializer()
    pidemmatpoissaolot = TyontekijaKoostePidempiPoissaoloSerializer()

    class Meta:
        model = Palvelussuhde
        fields = ('id', 'tyosuhde_koodi', 'tyoaika_koodi', 'tyoaika_viikossa', 'tutkinto_koodi',
                  'alkamis_pvm', 'paattymis_pvm', 'tyoskentelypaikat', 'pidemmatpoissaolot', 'lahdejarjestelma',
                  'tunniste', 'muutos_pvm')


class TyontekijaKoosteTaydennyskoulutusSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='taydennyskoulutus.id')
    nimi = serializers.CharField(source='taydennyskoulutus.nimi')
    suoritus_pvm = serializers.CharField(source='taydennyskoulutus.suoritus_pvm')
    koulutuspaivia = serializers.CharField(source='taydennyskoulutus.koulutuspaivia')
    lahdejarjestelma = serializers.CharField(source='taydennyskoulutus.lahdejarjestelma')
    tunniste = serializers.CharField(source='taydennyskoulutus.tunniste')
    muutos_pvm = serializers.ReadOnlyField(source='taydennyskoulutus.muutos_pvm')

    class Meta:
        model = TaydennyskoulutusTyontekija
        fields = ('id', 'tehtavanimike_koodi', 'nimi', 'suoritus_pvm', 'koulutuspaivia', 'lahdejarjestelma', 'tunniste',
                  'muutos_pvm')


class TyontekijaKoosteTutkintoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutkinto
        fields = ('id', 'tutkinto_koodi')


class TyontekijaKoosteSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='tyontekija.id')
    vakajarjestaja_id = serializers.IntegerField(source='tyontekija.vakajarjestaja.id')
    vakajarjestaja_nimi = serializers.CharField(source='tyontekija.vakajarjestaja.nimi')
    vakajarjestaja_organisaatio_oid = serializers.CharField(source='tyontekija.vakajarjestaja.organisaatio_oid')
    lahdejarjestelma = serializers.CharField(source='tyontekija.lahdejarjestelma')
    tunniste = serializers.CharField(source='tyontekija.tunniste')
    henkilo = TyontekijaKoosteHenkiloSerializer(source='tyontekija.henkilo')
    tutkinnot = TyontekijaKoosteTutkintoSerializer(many=True)
    palvelussuhteet = TyontekijaKoostePalvelussuhdeSerializer(many=True)
    taydennyskoulutukset = TyontekijaKoosteTaydennyskoulutusSerializer(many=True)
