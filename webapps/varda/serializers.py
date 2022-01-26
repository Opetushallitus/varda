import datetime
import logging

from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from drf_yasg.utils import swagger_serializer_method
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError

from varda import validators
from varda.cache import caching_to_representation
from varda.constants import JARJESTAMISMUODOT_YKSITYINEN, JARJESTAMISMUODOT_PAOS, JARJESTAMISMUODOT_KUNTA
from varda.enums.error_messages import ErrorMessages
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.misc import TemporaryObject, hash_string, decrypt_henkilotunnus
from varda.misc_viewsets import ViewSetValidator
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Maksutieto, Henkilo,
                          Lapsi, Huoltaja, Huoltajuussuhde, PaosOikeus, PaosToiminta, Varhaiskasvatuspaatos,
                          Varhaiskasvatussuhde, Z3_AdditionalCasUserFields, Tyontekija, Z4_CasKayttoOikeudet,
                          MaksutietoHuoltajuussuhde)
from varda.permissions import check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement, is_oph_staff
from varda.related_object_validations import (check_if_immutable_object_is_changed,
                                              check_toimipaikka_and_vakajarjestaja_have_oids,
                                              check_overlapping_toiminnallinen_painotus,
                                              check_overlapping_kielipainotus, check_overlapping_varhaiskasvatuspaatos,
                                              check_overlapping_varhaiskasvatussuhde, check_overlapping_maksutieto)
from varda.serializers_common import (OidRelatedField, TunnisteRelatedField, PermissionCheckedHLFieldMixin,
                                      OptionalToimipaikkaMixin, ToimipaikkaPermissionCheckedHLField,
                                      VakaJarjestajaPermissionCheckedHLField, VakaJarjestajaHLField, HenkiloHLField,
                                      ToimipaikkaHLField, HenkiloPermissionCheckedHLField)
from varda.validators import (fill_missing_fields_for_validations, validate_henkilo_oid, validate_nimi,
                              validate_henkilotunnus_or_oid_needed, validate_organisaatio_oid,
                              validate_instance_uniqueness)


logger = logging.getLogger(__name__)


"""
Admin serializers
"""


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class UpdateHenkiloWithOidSerializer(serializers.Serializer):
    henkilo_oid = serializers.CharField(write_only=True, required=True)
    result = serializers.CharField(read_only=True)

    def validate(self, attrs):
        henkilo_oid = attrs.get('henkilo_oid')
        validate_henkilo_oid(henkilo_oid)
        return attrs


class UpdateOphStaffSerializer(serializers.Serializer):
    virkailija_id = serializers.IntegerField(write_only=True, required=True)
    result = serializers.CharField(read_only=True)

    def validate(self, attrs):
        virkailija_id = attrs.get('virkailija_id')
        if virkailija_id < 1:
            raise serializers.ValidationError({'virkailija_id': [ErrorMessages.AD001.value]})

        try:
            user = User.objects.get(id=virkailija_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({'virkailija_id': [ErrorMessages.AD002.value]})

        try:
            oph_staff_user_obj = Z3_AdditionalCasUserFields.objects.get(user=user)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            raise serializers.ValidationError({'virkailija_id': [ErrorMessages.AD003.value]})

        if not user.groups.filter(name='oph_staff').exists():
            raise serializers.ValidationError({'virkailija_id': [ErrorMessages.AD004.value]})

        oph_staff_user_obj.approved_oph_staff = True
        oph_staff_user_obj.save()

        return attrs


class ClearCacheSerializer(serializers.Serializer):
    clear_cache = serializers.CharField(write_only=True, required=True)
    result = serializers.CharField(read_only=True)

    def validate(self, attrs):
        clear_cache = attrs.get('clear_cache')
        if clear_cache.lower() != 'yes':
            raise serializers.ValidationError({'errors': [ErrorMessages.AD005.value]}, code='invalid')
        return attrs


class PulssiVakajarjestajatSerializer(serializers.Serializer):
    number_of_vakajarjestajat = serializers.IntegerField()


"""
User-specific viewsets below
"""


class ActiveUserKayttooikeusSerializer(serializers.Serializer):
    organisaatio = serializers.CharField()
    kayttooikeus = serializers.CharField()


class ActiveUserHuollettavaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Henkilo
        fields = ('henkilo_oid', 'etunimet', 'kutsumanimi', 'sukunimi')


class ActiveUserSerializer(serializers.ModelSerializer):
    asiointikieli_koodi = serializers.ReadOnlyField()
    henkilo_oid = serializers.ReadOnlyField()
    etunimet = serializers.ReadOnlyField()
    kutsumanimi = serializers.ReadOnlyField()
    sukunimi = serializers.ReadOnlyField()
    huollettava_list = serializers.ReadOnlyField()
    kayttajatyyppi = serializers.SerializerMethodField()
    kayttooikeudet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'email', 'asiointikieli_koodi', 'henkilo_oid', 'etunimet', 'kutsumanimi', 'sukunimi',
                  'huollettava_list', 'kayttajatyyppi', 'kayttooikeudet')

    def to_representation(self, instance):
        data = super(ActiveUserSerializer, self).to_representation(instance)

        additional_cas_user_fields = Z3_AdditionalCasUserFields.objects.filter(user_id=instance.id).first()
        if not additional_cas_user_fields:
            data['asiointikieli_koodi'] = 'fi'
            data['henkilo_oid'] = ''
            return data

        data['asiointikieli_koodi'] = additional_cas_user_fields.asiointikieli_koodi
        henkilo_oid = additional_cas_user_fields.henkilo_oid
        data['henkilo_oid'] = henkilo_oid

        if additional_cas_user_fields.kayttajatyyppi in [Kayttajatyyppi.OPPIJA_CAS.value, Kayttajatyyppi.OPPIJA_CAS_VALTUUDET.value]:
            # Extra info for CAS users
            if henkilo_oid and (henkilo := Henkilo.objects.filter(henkilo_oid=henkilo_oid).first()):
                data['etunimet'] = henkilo.etunimet
                data['kutsumanimi'] = henkilo.kutsumanimi
                data['sukunimi'] = henkilo.sukunimi
            else:
                # No Henkilo object for this user
                data['etunimet'] = additional_cas_user_fields.etunimet
                data['kutsumanimi'] = additional_cas_user_fields.kutsumanimi
                data['sukunimi'] = additional_cas_user_fields.sukunimi

            if huollettava_oid_list := additional_cas_user_fields.huollettava_oid_list:
                data['huollettava_list'] = ActiveUserHuollettavaSerializer(
                    instance=Henkilo.objects.filter(henkilo_oid__in=huollettava_oid_list), many=True
                ).data

        return data

    @swagger_serializer_method(serializer_or_field=serializers.CharField)
    def get_kayttajatyyppi(self, user):
        if user.is_superuser:
            return Kayttajatyyppi.ADMIN.value
        if is_oph_staff(user):
            return Kayttajatyyppi.OPH_STAFF.value
        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(user_id=user.id)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            return ''
        return cas_user_obj.kayttajatyyppi

    @swagger_serializer_method(serializer_or_field=ActiveUserKayttooikeusSerializer(many=True))
    def get_kayttooikeudet(self, user):
        kayttooikeudet = []
        user_groups = user.groups.filter(Q(name__startswith='VARDA-') | Q(name__startswith='HUOLTAJATIETO_') |
                                         Q(name__startswith='HENKILOSTO_') | Q(name__startswith='VARDA_'))
        for user_group in user_groups:
            user_group_name = user_group.name.rsplit('_', maxsplit=1)
            kayttooikeus = user_group_name[0]
            organisaatio_oid = user_group_name[1]
            kayttooikeudet.append({'organisaatio': organisaatio_oid, 'kayttooikeus': kayttooikeus})
        return kayttooikeudet


class AuthTokenSerializer(serializers.Serializer):
    refresh_token = serializers.BooleanField(write_only=True, label=_('Refresh token'))
    token = serializers.CharField(read_only=True)

    def validate(self, attrs):
        refresh = attrs.get('refresh_token')

        if refresh:
            pass
        else:
            raise serializers.ValidationError({'errors': [ErrorMessages.MI001.value]}, code='invalid')

        return attrs


class ExternalPermissionsSerializer(serializers.Serializer):
    """
    We use CamelCase here exceptionally for attribute_names only because
    we want to support easy/quick integration for ONR.
    """
    personOidsForSamePerson = serializers.ListField(write_only=True, required=True)
    organisationOids = serializers.ListField(write_only=True, required=False)
    loggedInUserRoles = serializers.ListField(write_only=True, required=False)
    loggedInUserOid = serializers.CharField(write_only=True, required=True)
    accessAllowed = serializers.BooleanField(read_only=True)
    errorMessage = serializers.CharField(read_only=True)


"""
RelatedField serializers
Show only relevant options in the dropdown menus (where changed_by=user)
"""


class VarhaiskasvatuspaatosHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Varhaiskasvatuspaatos.objects.all().order_by('id')
        else:
            queryset = Varhaiskasvatuspaatos.objects.none()
        return queryset


class VarhaiskasvatuspaatosPermissionCheckedHLField(PermissionCheckedHLFieldMixin, VarhaiskasvatuspaatosHLField):
    check_permission = 'change_varhaiskasvatuspaatos'


class VarhaiskasvatussuhdeHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Varhaiskasvatussuhde.objects.all().order_by('id')
        else:
            queryset = Varhaiskasvatussuhde.objects.none()
        return queryset


class HuoltajaHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Huoltaja.objects.all().order_by('id')
        else:
            queryset = Huoltaja.objects.none()
        return queryset


class LapsiHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Lapsi.objects.all().order_by('id')
        else:
            queryset = Lapsi.objects.none()
        return queryset


class LapsiPermissionCheckedHLField(PermissionCheckedHLFieldMixin, LapsiHLField):
    check_permission = 'change_lapsi'


class MaksutietoHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Maksutieto.objects.all().order_by('id')
        else:
            queryset = Maksutieto.objects.none()
        return queryset


class LapsiOptionalToimipaikkaMixin(OptionalToimipaikkaMixin):
    toimipaikka = ToimipaikkaPermissionCheckedHLField(view_name='toimipaikka-detail', required=False, write_only=True,
                                                      permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                         Z4_CasKayttoOikeudet.PALVELUKAYTTAJA],
                                                      check_paos=True)


class RequiredLahdejarjestelmaMixin(metaclass=serializers.SerializerMetaclass):
    lahdejarjestelma = serializers.CharField(required=True, max_length=2,
                                             validators=[validators.validate_lahdejarjestelma_koodi])

    def validate(self, data):
        data = super().validate(data)
        if self.instance and not self.instance.lahdejarjestelma and not data.get('lahdejarjestelma'):
            # If instance does not have lahdejarjestelma, it is required in update-requests
            raise ValidationError({'lahdejarjestelma': [ErrorMessages.GE001.value]})
        return data


"""
VARDA serializers
"""


class VakaJarjestajaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    kunnallinen_kytkin = serializers.BooleanField(read_only=True)
    # Let's use "_top" to decrease the amount of child relations visible. Otherwise the parent-query becomes quickly unreadable.
    toimipaikat_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='toimipaikka-detail')

    class Meta:
        model = VakaJarjestaja
        exclude = ('ytjkieli', 'integraatio_organisaatio', 'luonti_pvm', 'changed_by',)
        read_only_fields = ('id', 'nimi', 'y_tunnus', 'yritysmuoto', 'kunnallinen_kytkin', 'organisaatio_oid',
                            'kunta_koodi', 'kayntiosoite', 'kayntiosoite_postinumero', 'kayntiosoite_postitoimipaikka',
                            'postiosoite', 'postinumero', 'postitoimipaikka', 'alkamis_pvm', 'paattymis_pvm',
                            'muutos_pvm',)

    @caching_to_representation('vakajarjestaja')
    def to_representation(self, instance):
        return super(VakaJarjestajaSerializer, self).to_representation(instance)


class ToimipaikkaSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                               Z4_CasKayttoOikeudet.PALVELUKAYTTAJA])
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)
    organisaatio_oid = serializers.CharField(read_only=True, allow_blank=True)
    kayntiosoite = serializers.CharField(min_length=3, max_length=100)
    postiosoite = serializers.CharField(min_length=3, max_length=100)
    toiminnallisetpainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='toiminnallinenpainotus-detail')
    kielipainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='kielipainotus-detail')
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')

    class Meta:
        model = Toimipaikka
        exclude = ('nimi_sv', 'luonti_pvm', 'changed_by',)
        read_only_fields = ('hallinnointijarjestelma',)

    @caching_to_representation('toimipaikka')
    def to_representation(self, instance):
        return super(ToimipaikkaSerializer, self).to_representation(instance)

    def validate(self, data):
        data = super().validate(data)
        if self.instance:
            fill_missing_fields_for_validations(data, self.instance)

            check_if_immutable_object_is_changed(self.instance, data, 'vakajarjestaja')

            if self.instance.hallinnointijarjestelma != Hallinnointijarjestelma.VARDA.value:
                raise ValidationError({'hallinnointijarjestelma': [ErrorMessages.TP003.value]})
            if (data['toimintamuoto_koodi'].lower() != self.instance.toimintamuoto_koodi.lower() and
                    self.instance.organisaatio_oid is None):
                raise ValidationError({'toimintamuoto_koodi': [ErrorMessages.TP005.value]})

        unique_name_qs = Toimipaikka.objects.filter(vakajarjestaja=data['vakajarjestaja'], nimi=data['nimi'])
        if self.instance:
            # Exclude current instance
            unique_name_qs = unique_name_qs.exclude(pk=self.instance.pk)
        if unique_name_qs.exists():
            raise serializers.ValidationError({'errors': [ErrorMessages.TP001.value]})

        # Names that collide with temporary toimipaikka are not allowed
        if data['nimi'].lower().startswith('palveluseteli ja ostopalvelu'):
            raise serializers.ValidationError({'nimi': [ErrorMessages.TP006.value]}, code='invalid')
        validators.validate_toimipaikan_nimi(data['nimi'])

        self._validate_dates_within_vakajarjestaja(data)
        self._validate_jarjestamismuoto_codes(data)
        validators.validate_alkamis_pvm_before_paattymis_pvm(data)

        alkamis_pvm = data['alkamis_pvm']
        paattymis_pvm = data.get('paattymis_pvm')
        validators.validate_kasvatusopillinen_jarjestelma_koodi(data['kasvatusopillinen_jarjestelma_koodi'],
                                                                alkamis_pvm, paattymis_pvm)
        validators.validate_toimintamuoto_koodi(data['toimintamuoto_koodi'], alkamis_pvm, paattymis_pvm)

        return data

    def _validate_jarjestamismuoto_codes(self, data):
        jarjestamismuoto_codes_list = [code.lower() for code in data['jarjestamismuoto_koodi']]
        jarjestamismuoto_codes_set = set(jarjestamismuoto_codes_list)

        with ViewSetValidator() as validator:
            if len(jarjestamismuoto_codes_list) != len(jarjestamismuoto_codes_set):
                validator.error('jarjestamismuoto_koodi', ErrorMessages.TP019.value)

            jarjestamismuoto_codes_kunta = set(JARJESTAMISMUODOT_KUNTA + JARJESTAMISMUODOT_PAOS)
            jarjestamismuoto_codes_yksityinen = set(JARJESTAMISMUODOT_YKSITYINEN + JARJESTAMISMUODOT_PAOS)
            vakajarjestaja = data['vakajarjestaja']

            if (vakajarjestaja.kunnallinen_kytkin and
                    not jarjestamismuoto_codes_set.issubset(jarjestamismuoto_codes_kunta)):
                # jarjestamismuoto_koodi field has values that are not allowed for kunnallinen Toimipaikka
                validator.error('jarjestamismuoto_koodi', ErrorMessages.TP017.value)
            elif (not vakajarjestaja.kunnallinen_kytkin and
                  not jarjestamismuoto_codes_set.issubset(jarjestamismuoto_codes_yksityinen)):
                # jarjestamismuoto_koodi field has values that are not allowed for yksityinen Toimipaikka
                validator.error('jarjestamismuoto_koodi', ErrorMessages.TP018.value)

            with validator.wrap():
                for jarjestamismuoto_code in jarjestamismuoto_codes_set:
                    validators.validate_jarjestamismuoto_koodi(jarjestamismuoto_code, data['alkamis_pvm'],
                                                               data.get('paattymis_pvm'))

    def _validate_dates_within_vakajarjestaja(self, data):
        vakajarjestaja = data['vakajarjestaja']
        alkamis_pvm = data['alkamis_pvm']
        paattymis_pvm = data.get('paattymis_pvm', None)

        today = datetime.date.today()
        if vakajarjestaja.paattymis_pvm:
            if validators.validate_paivamaara1_after_paivamaara2(alkamis_pvm, vakajarjestaja.paattymis_pvm,
                                                                 can_be_same=True):
                raise ValidationError({'alkamis_pvm': [ErrorMessages.TP025.value]})
            if vakajarjestaja.paattymis_pvm < today and not paattymis_pvm:
                raise ValidationError({'paattymis_pvm': [ErrorMessages.TP024.value]})
            elif (paattymis_pvm and
                  validators.validate_paivamaara1_after_paivamaara2(paattymis_pvm, vakajarjestaja.paattymis_pvm,
                                                                    can_be_same=True)):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.TP026.value]})


class ToimipaikkaUpdateSerializer(ToimipaikkaSerializer):
    """
    Different PUT/PATCH serializer so that Toimipaikka can be updated with only Toimipaikka permissions
    (no VakaJarjestajaPermissionCheckedHLField)
    """
    vakajarjestaja = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False, read_only=True)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         read_only=True)


class ToiminnallinenPainotusSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    toimipaikka = ToimipaikkaPermissionCheckedHLField(required=False, view_name='toimipaikka-detail',
                                                      permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                         Z4_CasKayttoOikeudet.PALVELUKAYTTAJA])
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      either_required=True,
                                      secondary_field='toimipaikka_tunniste')
    toimipaikka_tunniste = TunnisteRelatedField(object_type=Toimipaikka,
                                                parent_field='toimipaikka',
                                                prevalidator=validators.validate_tunniste,
                                                either_required=True,
                                                secondary_field='toimipaikka_oid')

    class Meta:
        model = ToiminnallinenPainotus
        exclude = ('luonti_pvm', 'changed_by',)

    def validate(self, data):
        data = super().validate(data)
        if self.instance:
            fill_missing_fields_for_validations(data, self.instance)
            check_if_immutable_object_is_changed(self.instance, data, 'toimipaikka')
            check_overlapping_toiminnallinen_painotus(data, self_id=self.instance.id)
        else:
            check_overlapping_toiminnallinen_painotus(data)

        toimipaikka = data['toimipaikka']
        validators.validate_dates_within_toimipaikka(data, toimipaikka)
        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka, toimipaikka.vakajarjestaja.organisaatio_oid,
                                                       toimipaikka.organisaatio_oid)
        validators.validate_alkamis_pvm_before_paattymis_pvm(data)
        validators.validate_toimintapainotus_koodi(data['toimintapainotus_koodi'], data['alkamis_pvm'],
                                                   data.get('paattymis_pvm'))

        return data


class KieliPainotusSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    toimipaikka = ToimipaikkaPermissionCheckedHLField(required=False, view_name='toimipaikka-detail',
                                                      permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                         Z4_CasKayttoOikeudet.PALVELUKAYTTAJA])
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      either_required=True,
                                      secondary_field='toimipaikka_tunniste')
    toimipaikka_tunniste = TunnisteRelatedField(object_type=Toimipaikka,
                                                parent_field='toimipaikka',
                                                prevalidator=validators.validate_tunniste,
                                                either_required=True,
                                                secondary_field='toimipaikka_oid')

    class Meta:
        model = KieliPainotus
        exclude = ('luonti_pvm', 'changed_by',)

    def validate(self, data):
        data = super().validate(data)
        if self.instance:
            fill_missing_fields_for_validations(data, self.instance)
            check_if_immutable_object_is_changed(self.instance, data, 'toimipaikka')
            check_overlapping_kielipainotus(data, self_id=self.instance.id)
        else:
            check_overlapping_kielipainotus(data)

        toimipaikka = data['toimipaikka']
        validators.validate_dates_within_toimipaikka(data, toimipaikka)
        check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka, toimipaikka.vakajarjestaja.organisaatio_oid,
                                                       toimipaikka.organisaatio_oid)
        validators.validate_alkamis_pvm_before_paattymis_pvm(data)

        return data


class HaeHenkiloSerializer(serializers.Serializer):
    henkilo_oid = serializers.CharField(write_only=True, required=False)
    henkilotunnus = serializers.CharField(write_only=True, required=False)

    def validate(self, data):
        validate_henkilotunnus_or_oid_needed(data)
        return data


class HenkiloSerializer(serializers.HyperlinkedModelSerializer):
    """
    If you update this, notice the HenkiloSerializerAdmin below: do you also need to update that?
    """
    id = serializers.IntegerField(read_only=True)
    etunimet = serializers.CharField(required=True)
    kutsumanimi = serializers.CharField(required=True)
    sukunimi = serializers.CharField(required=True)
    henkilo_oid = serializers.CharField(required=False)
    syntyma_pvm = serializers.DateField(read_only=True)
    lapsi = serializers.SerializerMethodField(read_only=True)
    tyontekija = serializers.SerializerMethodField(read_only=True)
    henkilotunnus = serializers.CharField(required=False, write_only=True)
    turvakielto = serializers.BooleanField(read_only=True)

    class Meta:
        model = Henkilo
        exclude = ('henkilotunnus_unique_hash', 'aidinkieli_koodi', 'sukupuoli_koodi', 'katuosoite', 'vtj_yksiloity',
                   'vtj_yksilointi_yritetty', 'postinumero', 'postitoimipaikka', 'kotikunta_koodi', 'luonti_pvm',
                   'muutos_pvm', 'changed_by')

    def validate_etunimet(self, value):
        validate_nimi(value)
        return value

    def validate_kutsumanimi(self, value):
        validate_nimi(value)
        return value

    def validate_sukunimi(self, value):
        validate_nimi(value)
        return value

    def validate(self, data):
        validate_henkilotunnus_or_oid_needed(data)
        return data

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_lapsi(self, obj):
        request = self.context.get('request')
        user = request.user
        lapset = []

        qs = Lapsi.objects.filter(henkilo=obj.pk).order_by('id')

        for lapsi in qs:
            if user.has_perm('view_lapsi', lapsi):
                lapset.append(request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': lapsi.pk})))

        return lapset

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_tyontekija(self, obj):
        request = self.context.get('request')
        user = request.user
        tyontekijat = []

        qs = Tyontekija.objects.filter(henkilo=obj.pk).order_by('id')

        for tyontekija in qs:
            if user.has_perm('view_tyontekija', tyontekija):
                tyontekijat.append(request.build_absolute_uri(reverse('tyontekija-detail',
                                                                      kwargs={'pk': tyontekija.pk})))

        return tyontekijat


class HenkiloSerializerAdmin(HenkiloSerializer):
    id = serializers.IntegerField(read_only=True)
    huoltaja = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_lapsi(self, obj):
        request = self.context.get('request')
        lapset = []

        qs = Lapsi.objects.filter(henkilo=obj.pk).order_by('id')

        for lapsi in qs:
            lapset.append(request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': lapsi.pk})))

        return lapset

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_tyontekija(self, obj):
        request = self.context.get('request')
        tyontekijat = []

        qs = Tyontekija.objects.filter(henkilo=obj.pk).order_by('id')

        for tyontekija in qs:
            tyontekijat.append(request.build_absolute_uri(reverse('tyontekija-detail', kwargs={'pk': tyontekija.pk})))

        return tyontekijat

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_huoltaja(self, obj):
        request = self.context.get('request')
        huoltajat = []

        qs = Huoltaja.objects.filter(henkilo=obj.pk).order_by('id')

        for huoltaja in qs:
            huoltajat.append(request.build_absolute_uri(reverse('huoltaja-detail', kwargs={'pk': huoltaja.pk})))

        return huoltajat


class YksiloimattomatHenkilotSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    vakatoimija_oid = serializers.SerializerMethodField()
    vakatoimija_nimi = serializers.SerializerMethodField()

    class Meta:
        model = Henkilo
        fields = ('id', 'henkilo_oid', 'vakatoimija_oid', 'vakatoimija_nimi')

    def get_vakatoimija_oid(self, instance):
        toimija = self._get_toimija(instance)
        return getattr(toimija, 'organisaatio_oid', None)

    def get_vakatoimija_nimi(self, instance):
        toimija = self._get_toimija(instance)
        return getattr(toimija, 'nimi', None)

    def _get_toimija(self, instance):
        first_lapsi = instance.lapsi.first()
        if first_lapsi is not None:
            return first_lapsi.vakatoimija
        first_tyontekija = instance.tyontekijat.first()
        if first_tyontekija is not None:
            return first_tyontekija.vakajarjestaja
        return None


class NestedMaksutietoHuoltajaListSerializer(serializers.ListSerializer):
    def to_internal_value(self, data):
        self.context['original_count'] = len(data)
        return super().to_internal_value(data)

    def validate(self, data):
        data = super().validate(data)
        lapsi = self.context.get('lapsi', None)

        valid_huoltaja_list = []
        for huoltaja_data in data:
            if not huoltaja_data['huoltaja']:
                # If Huoltaja does not exist, remove it from list
                continue

            if lapsi:
                # Validate that Huoltaja is valid for given Lapsi, otherwise remove from list
                huoltajuussuhde_qs = Huoltajuussuhde.objects.filter(lapsi=lapsi, voimassa_kytkin=True)

                etunimet_filter = Q()
                for etunimi in huoltaja_data['etunimet'].split():
                    etunimet_filter |= Q(huoltaja__henkilo__etunimet__search=etunimi)
                name_filter = etunimet_filter | Q(huoltaja__henkilo__sukunimi__iexact=huoltaja_data['sukunimi'])

                if huoltaja_data.get('henkilo_oid', None):
                    henkilo_filter = Q(huoltaja__henkilo__henkilo_oid=huoltaja_data['henkilo_oid'])
                elif huoltaja_data.get('henkilotunnus', None):
                    validators.validate_henkilotunnus(huoltaja_data['henkilotunnus'])
                    henkilotunnus_hashed = hash_string(huoltaja_data['henkilotunnus'])
                    henkilo_filter = Q(huoltaja__henkilo__henkilotunnus_unique_hash=henkilotunnus_hashed)
                else:
                    henkilo_filter = Q(id__isnull=True)

                if not huoltajuussuhde_qs.filter(name_filter & henkilo_filter).exists():
                    continue

            valid_huoltaja_list.append(huoltaja_data)
        data = valid_huoltaja_list

        # Validate that there are no duplicates
        huoltaja_id_list = [huoltaja['huoltaja'].id for huoltaja in data if huoltaja['huoltaja']]
        huoltaja_id_set = set(huoltaja_id_list)
        if len(huoltaja_id_list) != len(huoltaja_id_set):
            raise ValidationError({'temporary_wrapper': [ErrorMessages.MA017.value]})

        return data


class NestedMaksutietoHuoltajaSerializer(serializers.Serializer):
    henkilotunnus = serializers.CharField(required=False)
    henkilo_oid = serializers.CharField(required=False)
    etunimet = serializers.CharField(required=True)
    sukunimi = serializers.CharField(required=True)

    class Meta:
        list_serializer_class = NestedMaksutietoHuoltajaListSerializer

    def to_internal_value(self, data):
        try:
            data = super().to_internal_value(data)
        except ValidationError as validation_error:
            raise validation_error

        if 'henkilotunnus' in data:
            huoltaja_filter = Q(henkilo__henkilotunnus_unique_hash=hash_string(data['henkilotunnus']))
        elif 'henkilo_oid' in data:
            huoltaja_filter = Q(henkilo__henkilo_oid=data['henkilo_oid'])
        else:
            huoltaja_filter = Q(id__isnull=True)

        data['huoltaja'] = Huoltaja.objects.filter(huoltaja_filter).first()

        return data

    def to_representation(self, instance):
        huoltaja = instance.huoltajuussuhde.huoltaja
        henkilo = huoltaja.henkilo
        data = {'henkilo_oid': henkilo.henkilo_oid, 'etunimet': henkilo.etunimet, 'sukunimi': henkilo.sukunimi}

        if self.context['request'].method in ['POST', 'PUT', 'PATCH']:
            # Return henkilotunnus in POST, PUT and PATCH requests if it was present in the request
            henkilotunnus = decrypt_henkilotunnus(henkilo.henkilotunnus, henkilo_id=henkilo.id)
            if henkilotunnus in self.context.get('henkilotunnus_set', []):
                data['henkilotunnus'] = henkilotunnus

        return data

    def create(self, data):
        user = self.context['request'].user
        huoltajuussuhde_obj = Huoltajuussuhde.objects.get(lapsi=data['lapsi'], huoltaja=data['huoltaja'])
        return MaksutietoHuoltajuussuhde.objects.create(huoltajuussuhde=huoltajuussuhde_obj,
                                                        maksutieto=data['maksutieto'], changed_by=user)

    def validate_etunimet(self, value):
        validate_nimi(value)
        return value

    def validate_sukunimi(self, value):
        validate_nimi(value)
        return value

    def validate(self, data):
        with ViewSetValidator() as validator:
            # These fields are required also in PATCH requests so we need to check them manually
            if 'etunimet' not in data:
                validator.error('etunimet', ErrorMessages.GE001.value)
            if 'sukunimi' not in data:
                validator.error('sukunimi', ErrorMessages.GE001.value)
            with validator.wrap():
                validate_henkilotunnus_or_oid_needed(data)
        return data


def _validate_maksutieto_dates(data, lapsi_obj=None):
    lapsi = data.get('lapsi', None) or lapsi_obj
    alkamis_pvm = data['alkamis_pvm']
    paattymis_pvm = data.get('paattymis_pvm', None)

    validators.validate_paattymispvm_same_or_after_alkamispvm(data)

    vakapaatokset = lapsi.varhaiskasvatuspaatokset.all()
    if vakapaatokset.count() > 0:
        earliest_alkamis_pvm = vakapaatokset.earliest('alkamis_pvm').alkamis_pvm
        latest_paattymis_pvm = vakapaatokset.latest('paattymis_pvm').paattymis_pvm

        if validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, earliest_alkamis_pvm, can_be_same=False):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.MA005.value]})

        if all((v.paattymis_pvm is not None) for v in vakapaatokset):
            if not validators.validate_paivamaara1_after_paivamaara2(latest_paattymis_pvm, alkamis_pvm,
                                                                     can_be_same=True):
                raise ValidationError({'alkamis_pvm': [ErrorMessages.MA006.value]})

        """
        While it is possible to leave out the end date, it must fall within vakapaatokset if given.
        Make this check only if all vakapaatokset have a paattymis_pvm.
        """
        if paattymis_pvm is not None:
            if all((v.paattymis_pvm is not None) for v in vakapaatokset):
                if not validators.validate_paivamaara1_after_paivamaara2(latest_paattymis_pvm, paattymis_pvm,
                                                                         can_be_same=True):
                    raise ValidationError({'paattymis_pvm': [ErrorMessages.MA007.value]})

    if lapsi.yksityinen_kytkin and paattymis_pvm and paattymis_pvm < datetime.date(2020, 9, 1):
        raise ValidationError({'paattymis_pvm': [ErrorMessages.MA014.value]})


def _validate_maksutieto_overlap(data, lapsi_obj=None, maksutieto_id=None):
    # Temporarily assign huoltajuussuhdeet.lapsi value to data so that overlap validation is run correctly
    temp_object = TemporaryObject()
    temp_object.lapsi = data.get('lapsi', None) or lapsi_obj
    data['huoltajuussuhteet'] = temp_object
    check_overlapping_maksutieto(data, self_id=maksutieto_id)
    data.pop('huoltajuussuhteet')


def _get_lapsi_for_maksutieto(maksutieto):
    lapsi = maksutieto.huoltajuussuhteet.all().values('lapsi').distinct()
    if len(lapsi) != 1:
        logger.error('Could not find just one lapsi for maksutieto-id: {}'.format(maksutieto.id))
        raise APIException
    return Lapsi.objects.get(id=lapsi[0].get('lapsi'))


class MaksutietoSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    huoltajat = NestedMaksutietoHuoltajaSerializer(required=True, allow_empty=False, many=True,
                                                   source='maksutiedot_huoltajuussuhteet')
    lapsi = LapsiHLField(required=False, view_name='lapsi-detail')
    lapsi_tunniste = TunnisteRelatedField(object_type=Lapsi,
                                          parent_field='lapsi',
                                          prevalidator=validators.validate_tunniste,
                                          either_required=True,
                                          parent_value_getter=_get_lapsi_for_maksutieto)
    alkamis_pvm = serializers.DateField(required=True, validators=[validators.validate_vaka_date])

    class Meta:
        model = Maksutieto
        exclude = ('luonti_pvm', 'muutos_pvm', 'changed_by', 'yksityinen_jarjestaja',)

    def to_representation(self, instance):
        setattr(instance, 'lapsi', _get_lapsi_for_maksutieto(instance))
        return super().to_representation(instance)


class MaksutietoPostSerializer(MaksutietoSerializer):
    tallennetut_huoltajat_count = serializers.SerializerMethodField(read_only=True)
    ei_tallennetut_huoltajat_count = serializers.SerializerMethodField(read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_huoltajat_count = 0
        self.henkilotunnus_set = set()

    def to_representation(self, instance):
        self.fields['huoltajat'].context['henkilotunnus_set'] = self.henkilotunnus_set
        return super().to_representation(instance)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data['huoltajat'] = data.pop('maksutiedot_huoltajuussuhteet', [])
        return data

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_tallennetut_huoltajat_count(self, instance):
        return self.saved_huoltajat_count

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_ei_tallennetut_huoltajat_count(self, instance):
        return self.fields['huoltajat'].context.get('original_count', 0) - self.saved_huoltajat_count

    def create(self, validated_data):
        huoltajat = validated_data.pop('huoltajat', [])
        lapsi = validated_data.pop('lapsi', None)
        maksutieto = Maksutieto.objects.create(**validated_data)

        for huoltaja in huoltajat:
            self.henkilotunnus_set.add(huoltaja.get('henkilotunnus', None))
            huoltaja['lapsi'] = lapsi
            huoltaja['maksutieto'] = maksutieto
            NestedMaksutietoHuoltajaSerializer(context=self._context).create(huoltaja)

        self.henkilotunnus_set.discard(None)
        return maksutieto

    def validate(self, data):
        data = super().validate(data)

        if not self.context['request'].user.has_perm('view_lapsi', data['lapsi']):
            msg = {'lapsi': [ErrorMessages.GE008.value]}
            raise serializers.ValidationError(msg, code='invalid')

        if not Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=data['lapsi']).exists():
            raise ValidationError({'errors': [ErrorMessages.MA009.value]})

        # Set lapsi object for huoltajat context so that the field can be validated more accurately
        lapsi_obj = _get_lapsi_for_maksutieto(self.instance) if self.instance else data['lapsi']
        self.fields['huoltajat'].context['lapsi'] = lapsi_obj
        data['huoltajat'] = self.fields['huoltajat'].validate(data['huoltajat'])

        self._validate_huoltajat(data['huoltajat'])
        self._validate_yksityinen_lapsi(data)
        self._validate_maksun_peruste(data)
        _validate_maksutieto_dates(data)
        _validate_maksutieto_overlap(data)

        return data

    def _validate_huoltajat(self, huoltajat):
        self.saved_huoltajat_count = len(huoltajat)
        if self.saved_huoltajat_count == 0:
            raise ValidationError({'huoltajat': [ErrorMessages.MA003.value]})
        huoltajat_count = self.fields['huoltajat'].context.get('original_count', 0)
        if huoltajat_count > 7:
            raise serializers.ValidationError({'huoltajat': [ErrorMessages.MA011.value]})

    def _validate_yksityinen_lapsi(self, data):
        if data['lapsi'].yksityinen_kytkin:
            # Yksityinen lapsi, palveluseteli_arvo and perheen_koko are not stored
            data['yksityinen_jarjestaja'] = True
            data['palveluseteli_arvo'] = None
            data['perheen_koko'] = None
        else:
            # Kunnallinen lapsi
            if 'perheen_koko' not in data:
                raise ValidationError({'perheen_koko': [ErrorMessages.MA001.value]})

    def _validate_maksun_peruste(self, data):
        if data['maksun_peruste_koodi'].lower() == 'mp01':
            # If maksun peruste is mp01, asiakasmaksu and palveluseteli_arvo are not stored
            data['asiakasmaksu'] = 0
            data['palveluseteli_arvo'] = 0.00
        validators.validate_maksun_peruste_koodi(data['maksun_peruste_koodi'], data['alkamis_pvm'],
                                                 data.get('paattymis_pvm'))


class MaksutietoGetHuoltajaSerializer(serializers.ModelSerializer):
    henkilo_oid = serializers.CharField(read_only=True)
    etunimet = serializers.CharField(read_only=True)
    sukunimi = serializers.CharField(read_only=True)

    class Meta:
        model = Henkilo
        fields = ('henkilo_oid', 'etunimet', 'sukunimi')


class MaksutietoUpdateSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    huoltajat = NestedMaksutietoHuoltajaSerializer(required=False, allow_empty=False, many=True, source='maksutiedot_huoltajuussuhteet', read_only=True)
    huoltajat_add = NestedMaksutietoHuoltajaSerializer(write_only=True, required=False, allow_empty=False, many=True)
    lapsi = serializers.SerializerMethodField(read_only=True)
    lapsi_tunniste = TunnisteRelatedField(object_type=Lapsi,
                                          parent_field='lapsi',
                                          read_only=True,
                                          prevalidator=validators.validate_tunniste,
                                          parent_value_getter=_get_lapsi_for_maksutieto)
    paattymis_pvm = serializers.DateField(allow_null=True, validators=[validators.validate_vaka_date], required=False)
    tallennetut_huoltajat_count = serializers.SerializerMethodField(read_only=True)
    ei_tallennetut_huoltajat_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Maksutieto
        read_only_fields = ('lapsi', 'lapsi_tunniste', 'alkamis_pvm', 'perheen_koko', 'maksun_peruste_koodi',
                            'palveluseteli_arvo', 'asiakasmaksu',)
        exclude = ('luonti_pvm', 'muutos_pvm', 'changed_by', 'yksityinen_jarjestaja',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saved_huoltajat_count = 0
        self.henkilotunnus_set = set()
        self.lapsi = None

    def to_internal_value(self, data):
        self.lapsi = _get_lapsi_for_maksutieto(self.instance)
        self.fields['huoltajat_add'].context['lapsi'] = self.lapsi

        return super().to_internal_value(data)

    def to_representation(self, instance):
        self.fields['huoltajat_add'].context['henkilotunnus_set'] = self.henkilotunnus_set
        return super().to_representation(instance)

    def update(self, instance, validated_data):
        self._update_huoltajat(instance, validated_data)
        return super().update(instance, validated_data)

    def _update_huoltajat(self, instance, validated_data):
        if 'huoltajat_add' in validated_data and (huoltajat := validated_data.pop('huoltajat_add', [])):
            self.saved_huoltajat_count = len(huoltajat)
            for huoltaja in huoltajat:
                self.henkilotunnus_set.add(huoltaja.get('henkilotunnus', None))
                huoltaja['lapsi'] = self.lapsi
                huoltaja['maksutieto'] = instance
                NestedMaksutietoHuoltajaSerializer(context=self._context).create(huoltaja)
            self.henkilotunnus_set.discard(None)

    @swagger_serializer_method(serializer_or_field=serializers.URLField)
    def get_lapsi(self, instance):
        lapsi = _get_lapsi_for_maksutieto(instance)
        return self.context['request'].build_absolute_uri(reverse('lapsi-detail', args=[lapsi]))

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_tallennetut_huoltajat_count(self, instance):
        return self.saved_huoltajat_count

    @swagger_serializer_method(serializer_or_field=serializers.IntegerField)
    def get_ei_tallennetut_huoltajat_count(self, instance):
        return self.fields['huoltajat_add'].context.get('original_count', 0) - self.saved_huoltajat_count

    def validate(self, data):
        if len(data) == 0:
            raise serializers.ValidationError({'errors': [ErrorMessages.GE014.value]})
        fill_missing_fields_for_validations(data, self.instance)

        _validate_maksutieto_dates(data, lapsi_obj=self.lapsi)
        _validate_maksutieto_overlap(data, lapsi_obj=self.lapsi, maksutieto_id=self.instance.id)
        validators.validate_maksun_peruste_koodi(data['maksun_peruste_koodi'], data['alkamis_pvm'],
                                                 data.get('paattymis_pvm'))

        self._validate_huoltajat_add(self.instance, data)

        existing_huoltaja_count = self.instance.maksutiedot_huoltajuussuhteet.count()
        huoltajat_add_count = self.fields['huoltajat_add'].context.get('original_count', 0)
        if existing_huoltaja_count + huoltajat_add_count > 7:
            raise serializers.ValidationError({'huoltajat_add': [ErrorMessages.MA011.value]})

        return super().validate(data)

    def _validate_huoltajat_add(self, instance, data):
        huoltajat_add = data.get('huoltajat_add', [])
        for huoltaja in huoltajat_add:
            if instance.maksutiedot_huoltajuussuhteet.filter(huoltajuussuhde__huoltaja=huoltaja['huoltaja']).exists():
                raise ValidationError({'huoltajat_add': [ErrorMessages.MA018.value]})


class LapsiSerializer(RequiredLahdejarjestelmaMixin, LapsiOptionalToimipaikkaMixin,
                      serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloPermissionCheckedHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validate_henkilo_oid,
                                  either_required=True)
    vakatoimija = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                         allow_null=True,
                                                         permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                            Z4_CasKayttoOikeudet.PALVELUKAYTTAJA],
                                                         accept_toimipaikka_permission=True)
    vakatoimija_oid = OidRelatedField(object_type=VakaJarjestaja,
                                      parent_field='vakatoimija',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validate_organisaatio_oid)
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi')
    oma_organisaatio = VakaJarjestajaHLField(allow_null=True, required=False, view_name='vakajarjestaja-detail')
    oma_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                           parent_field='oma_organisaatio',
                                           parent_attribute='organisaatio_oid',
                                           prevalidator=validate_organisaatio_oid)
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')
    paos_organisaatio = VakaJarjestajaHLField(allow_null=True, required=False, view_name='vakajarjestaja-detail')
    paos_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                            parent_field='paos_organisaatio',
                                            parent_attribute='organisaatio_oid',
                                            prevalidator=validate_organisaatio_oid)
    paos_kytkin = serializers.BooleanField(read_only=True)
    varhaiskasvatuspaatokset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatuspaatos-detail')

    class Meta:
        model = Lapsi
        exclude = ('luonti_pvm', 'changed_by')

    @caching_to_representation('lapsi')
    def to_representation(self, instance):
        return super(LapsiSerializer, self).to_representation(instance)

    def validate(self, data):
        data = super().validate(data)
        with ViewSetValidator() as validator:
            henkilo = data.get('henkilo')
            if henkilo and henkilo.tyontekijat.exists():
                validator.error('henkilo', ErrorMessages.LA012.value)
            if henkilo and hasattr(henkilo, 'huoltaja'):
                validator.error('henkilo', ErrorMessages.LA013.value)

            if self.instance:
                fill_missing_fields_for_validations(data, self.instance)
                check_if_immutable_object_is_changed(self.instance, data, 'henkilo')
                check_if_immutable_object_is_changed(self.instance, data, 'vakatoimija')
                check_if_immutable_object_is_changed(self.instance, data, 'oma_organisaatio')
                check_if_immutable_object_is_changed(self.instance, data, 'paos_organisaatio')
            elif toimipaikka := data.get('toimipaikka', None):
                # Only validate in POST
                vakajarjestaja = data.get('vakatoimija') or data.get('paos_organisaatio')
                if toimipaikka.vakajarjestaja != vakajarjestaja:
                    validator.error('toimipaikka', ErrorMessages.MI019.value)

            vakatoimija = data.get('vakatoimija')
            oma_organisaatio = data.get('oma_organisaatio')
            paos_organisaatio = data.get('paos_organisaatio')

            if not (vakatoimija or oma_organisaatio or paos_organisaatio):
                validator.error('errors', ErrorMessages.LA005.value)
            if vakatoimija and oma_organisaatio or vakatoimija and paos_organisaatio:
                validator.error('errors', ErrorMessages.LA006.value)

            if oma_organisaatio and not paos_organisaatio or paos_organisaatio and not oma_organisaatio:
                validator.error('errors', ErrorMessages.LA007.value)
            if oma_organisaatio and oma_organisaatio == paos_organisaatio:
                validator.error('errors', ErrorMessages.LA008.value)
        return data


class LapsiSerializerAdmin(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    """
    Do not inherit from LapsiSerializer, it messes up the cache!
    to_representation should not be run twice.
    """
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validate_henkilo_oid,
                                  either_required=True)
    varhaiskasvatuspaatokset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatuspaatos-detail')
    huoltajuussuhteet = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='huoltajuussuhde-detail')
    vakatoimija = VakaJarjestajaHLField(allow_null=True, required=False, view_name='vakajarjestaja-detail')
    vakatoimija_oid = OidRelatedField(object_type=VakaJarjestaja,
                                      parent_field='vakatoimija',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validate_organisaatio_oid)
    oma_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                           parent_field='oma_organisaatio',
                                           parent_attribute='organisaatio_oid',
                                           prevalidator=validate_organisaatio_oid)
    paos_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                            parent_field='paos_organisaatio',
                                            parent_attribute='organisaatio_oid',
                                            prevalidator=validate_organisaatio_oid)

    class Meta:
        model = Lapsi
        exclude = ('luonti_pvm', 'changed_by',)
        read_only_fields = ('oma_organisaatio', 'paos_organisaatio', 'paos_kytkin', 'luonti_pvm', 'changed_by')


class HenkilohakuLapsetToimipaikkaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Toimipaikka
        fields = ('nimi', 'nimi_sv', 'organisaatio_oid',)


class HenkilohakuLapsetSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloSerializer()
    maksutiedot = serializers.SerializerMethodField()
    toimipaikat = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        exclude = ('luonti_pvm', 'changed_by', 'muutos_pvm')

    @swagger_serializer_method(serializer_or_field=serializers.ListField(child=serializers.URLField()))
    def get_maksutiedot(self, lapsi_obj):
        request = self.context.get('request')
        maksutiedot_query = (Maksutieto.objects
                             .filter(huoltajuussuhteet__lapsi=lapsi_obj)
                             .order_by('id')
                             )
        return [request.build_absolute_uri(reverse('maksutieto-detail', kwargs={'pk': maksutieto.pk}))
                for maksutieto
                in get_objects_for_user(request.user, 'view_maksutieto', maksutiedot_query)
                ]

    @swagger_serializer_method(serializer_or_field=HenkilohakuLapsetToimipaikkaSerializer(many=True))
    def get_toimipaikat(self, lapsi_obj):
        request = self.context.get('request')
        view = self.context.get('view')
        list_of_toimipaikka_ids = self.context.get('list_of_toimipaikka_ids')

        varhaiskasvatuspaatokset_query = view.kwargs['varhaiskasvatuspaatokset_query']
        varhaiskasvatussuhteet_query = view.kwargs['varhaiskasvatussuhteet_query']
        maksutiedot_query = view.kwargs['maksutiedot_query']

        toimipaikka_filter = (Q(varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi=lapsi_obj) &
                              Q(varhaiskasvatussuhteet__varhaiskasvatuspaatos__in=varhaiskasvatuspaatokset_query) &
                              Q(varhaiskasvatussuhteet__in=varhaiskasvatussuhteet_query) &
                              Q(id__in=list_of_toimipaikka_ids))

        if maksutiedot_query is not None:
            toimipaikka_filter = toimipaikka_filter & Q(**{'varhaiskasvatussuhteet__varhaiskasvatuspaatos__lapsi'
                                                           '__huoltajuussuhteet__maksutiedot__in': maksutiedot_query})

        toimipaikat_query = (Toimipaikka.objects
                             .filter(toimipaikka_filter)
                             .distinct('id')
                             )
        return HenkilohakuLapsetToimipaikkaSerializer(get_objects_for_user(request.user, 'view_toimipaikka',
                                                                           toimipaikat_query), many=True).data

    @caching_to_representation('henkilohakulapset')
    def to_representation(self, instance):
        return super(HenkilohakuLapsetSerializer, self).to_representation(instance)


class HuoltajaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    henkilo = HenkiloHLField(view_name='henkilo-detail')
    huoltajuussuhteet = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='huoltajuussuhde-detail')

    class Meta:
        model = Huoltaja
        exclude = ('luonti_pvm', 'changed_by',)

    @caching_to_representation('huoltaja')
    def to_representation(self, instance):
        return super(HuoltajaSerializer, self).to_representation(instance)


class HuoltajuussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    lapsi = LapsiHLField(view_name='lapsi-detail')
    huoltaja = HuoltajaHLField(view_name='huoltaja-detail')
    voimassa_kytkin = serializers.BooleanField()
    maksutiedot = MaksutietoHLField(required=False, view_name='maksutieto-detail', many=True)
    muutos_pvm = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Huoltajuussuhde
        exclude = ('luonti_pvm', 'changed_by',)


class VarhaiskasvatuspaatosSerializer(RequiredLahdejarjestelmaMixin, LapsiOptionalToimipaikkaMixin,
                                      serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    lapsi = LapsiPermissionCheckedHLField(required=False, view_name='lapsi-detail')
    lapsi_tunniste = TunnisteRelatedField(object_type=Lapsi,
                                          parent_field='lapsi',
                                          prevalidator=validators.validate_tunniste,
                                          either_required=True)
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    alkamis_pvm = serializers.DateField(validators=[validators.validate_vaka_date])
    hakemus_pvm = serializers.DateField(validators=[validators.validate_vaka_date])
    vuorohoito_kytkin = serializers.BooleanField(required=True)
    tilapainen_vaka_kytkin = serializers.BooleanField(default=False)

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('luonti_pvm', 'changed_by',)
        read_only_fields = ('pikakasittely_kytkin',)

    def validate(self, data):
        data = super().validate(data)
        if self.instance:
            if len(data) == 0:
                raise serializers.ValidationError({'errors': [ErrorMessages.GE014.value]})
            fill_missing_fields_for_validations(data, self.instance)

            check_if_immutable_object_is_changed(self.instance, data, 'lapsi')
            check_if_immutable_object_is_changed(self.instance, data, 'vuorohoito_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'tuntimaara_viikossa', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'paivittainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'kokopaivainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'tilapainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'jarjestamismuoto_koodi', compare_id=False)

            check_overlapping_varhaiskasvatuspaatos(data, self_id=self.instance.id)
        else:
            if toimipaikka := data.get('toimipaikka', None):
                _validate_toimipaikka_with_vakajarjestaja_of_lapsi(toimipaikka, data['lapsi'])
            check_overlapping_varhaiskasvatuspaatos(data)

        validate_instance_uniqueness(Varhaiskasvatuspaatos, data, ErrorMessages.VP015.value,
                                     instance_id=getattr(self.instance, 'id', None),
                                     ignore_fields=('pikakasittely_kytkin',))

        jarjestamismuoto_koodi = data['jarjestamismuoto_koodi'].lower()
        lapsi_obj = data['lapsi']

        self._validate_dates(data)
        self._validate_paos_specific_data(lapsi_obj, jarjestamismuoto_koodi)
        self._validate_jarjestamismuoto(lapsi_obj, jarjestamismuoto_koodi)
        self._validate_vuorohoito(data)
        self._validate_tilapainen_vaka_kytkin(data)
        validators.validate_jarjestamismuoto_koodi(jarjestamismuoto_koodi, data['alkamis_pvm'],
                                                   data.get('paattymis_pvm'))

        return data

    def _validate_paos_specific_data(self, lapsi_obj, jarjestamismuoto_koodi):
        jarjestamismuoto_koodit_paos = ['jm02', 'jm03']
        if lapsi_obj.paos_organisaatio is not None:
            check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(lapsi_obj.oma_organisaatio, lapsi_obj.paos_organisaatio)
            if jarjestamismuoto_koodi not in jarjestamismuoto_koodit_paos:
                msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP005.value]}
                raise serializers.ValidationError(msg, code='invalid')
        elif jarjestamismuoto_koodi in jarjestamismuoto_koodit_paos:
            msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP006.value]}
            raise serializers.ValidationError(msg, code='invalid')

    def _validate_jarjestamismuoto(self, lapsi_obj, jarjestamismuoto_koodi):
        jarjestamismuoto_koodit_kunta = ['jm01']
        jarjestamismuoto_koodit_yksityinen = ['jm04', 'jm05']
        if lapsi_obj.vakatoimija is not None:
            if lapsi_obj.vakatoimija.kunnallinen_kytkin and jarjestamismuoto_koodi not in jarjestamismuoto_koodit_kunta:
                msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP007.value]}
                raise serializers.ValidationError(msg, code='invalid')
            elif not lapsi_obj.vakatoimija.kunnallinen_kytkin and jarjestamismuoto_koodi not in jarjestamismuoto_koodit_yksityinen:
                msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP008.value]}
                raise serializers.ValidationError(msg, code='invalid')

    def _validate_vuorohoito(self, data):
        if not data['vuorohoito_kytkin']:
            msg = {}
            if 'paivittainen_vaka_kytkin' not in data or data['paivittainen_vaka_kytkin'] is None:
                msg['paivittainen_vaka_kytkin'] = [ErrorMessages.VP009.value]
            if 'kokopaivainen_vaka_kytkin' not in data or data['kokopaivainen_vaka_kytkin'] is None:
                msg['kokopaivainen_vaka_kytkin'] = [ErrorMessages.VP010.value]
            if msg:
                raise serializers.ValidationError(msg, code='invalid')

    def _validate_tilapainen_vaka_kytkin(self, data):
        if not data['jarjestamismuoto_koodi'].lower() in JARJESTAMISMUODOT_YKSITYINEN:
            is_patch = self.context['request'].method == 'PATCH'
            if self.initial_data.get('tilapainen_vaka_kytkin', None) is None and not is_patch:
                # Tilapainen vaka_kytkin if required, however not in PATCH
                raise serializers.ValidationError({'tilapainen_vaka_kytkin': [ErrorMessages.VP014.value]})

    def _validate_dates(self, data):
        hakemus_pvm = data['hakemus_pvm']
        alkamis_pvm = data['alkamis_pvm']
        if not validators.validate_paivamaara1_before_paivamaara2(hakemus_pvm, alkamis_pvm, can_be_same=True):
            raise ValidationError({'hakemus_pvm': [ErrorMessages.VP001.value]})
        validators.validate_paattymispvm_same_or_after_alkamispvm(data)

    @caching_to_representation('varhaiskasvatuspaatos')
    def to_representation(self, instance):
        return super(VarhaiskasvatuspaatosSerializer, self).to_representation(instance)


def _validate_toimipaikka_with_vakajarjestaja_of_lapsi(toimipaikka, lapsi):
    """
    Validate that given toimipaikka belongs to VakaJarjestaja that Lapsi is linked to
    (vakatoimija or paos_organisaatio)
    :param toimipaikka: Toimipaikka object instance
    :param lapsi: Lapsi object instance
    """
    vakajarjestaja_id = getattr(lapsi.vakatoimija, 'id', None) or getattr(lapsi.paos_organisaatio, 'id', None)
    if vakajarjestaja_id and toimipaikka.vakajarjestaja.id != vakajarjestaja_id:
        # If Lapsi is still missing vakatoimija-field, vakajarjestaja_id cannot be determined
        raise serializers.ValidationError({'toimipaikka': [ErrorMessages.MI019.value]})


class VarhaiskasvatussuhdeSerializer(RequiredLahdejarjestelmaMixin, serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    varhaiskasvatuspaatos = VarhaiskasvatuspaatosPermissionCheckedHLField(required=False, view_name='varhaiskasvatuspaatos-detail')
    varhaiskasvatuspaatos_tunniste = TunnisteRelatedField(object_type=Varhaiskasvatuspaatos,
                                                          parent_field='varhaiskasvatuspaatos',
                                                          prevalidator=validators.validate_tunniste,
                                                          either_required=True)
    toimipaikka = ToimipaikkaHLField(required=False, view_name='toimipaikka-detail')
    toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validators.validate_organisaatio_oid,
                                      either_required=True,
                                      secondary_field='toimipaikka_tunniste')
    toimipaikka_tunniste = TunnisteRelatedField(object_type=Toimipaikka,
                                                parent_field='toimipaikka',
                                                prevalidator=validators.validate_tunniste,
                                                either_required=True,
                                                secondary_field='toimipaikka_oid')

    class Meta:
        model = Varhaiskasvatussuhde
        exclude = ('luonti_pvm', 'changed_by',)

    def validate(self, data):
        data = super().validate(data)
        instance = self.instance
        if instance:
            fill_missing_fields_for_validations(data, instance)
            check_if_immutable_object_is_changed(self.instance, data, 'varhaiskasvatuspaatos')
            check_if_immutable_object_is_changed(self.instance, data, 'toimipaikka')
            check_overlapping_varhaiskasvatussuhde(data, self_id=instance.id)
        else:
            toimipaikka = data['toimipaikka']
            _validate_toimipaikka_with_vakajarjestaja_of_lapsi(toimipaikka, data['varhaiskasvatuspaatos'].lapsi)
            check_toimipaikka_and_vakajarjestaja_have_oids(toimipaikka, toimipaikka.vakajarjestaja.organisaatio_oid,
                                                           toimipaikka.organisaatio_oid)
            check_overlapping_varhaiskasvatussuhde(data)

        self._validate_jarjestamismuoto(data)
        self._validate_paivamaarat_varhaiskasvatussuhde_toimipaikka(data)
        self._validate_paivamaarat_varhaiskasvatussuhde_varhaiskasvatuspaatos(data)

        return data

    def _validate_jarjestamismuoto(self, data):
        jarjestamismuoto_koodit_kunta = ['jm01']
        jarjestamismuoto_koodit_yksityinen = ['jm04', 'jm05']
        vakapaatos = data['varhaiskasvatuspaatos']
        jarjestamismuoto_koodi = vakapaatos.jarjestamismuoto_koodi.lower()
        toimipaikka = data['toimipaikka']

        if jarjestamismuoto_koodi not in (koodi.lower() for koodi in toimipaikka.jarjestamismuoto_koodi):
            msg = {'varhaiskasvatuspaatos': [ErrorMessages.VS006.value]}
            raise serializers.ValidationError(msg, code='invalid')

        if vakapaatos.lapsi.paos_organisaatio is None:
            # Validate only non-paos-lapset, paos-lapset are validated in VarhaiskasvatuspaatosSerializer
            kunnallinen_kytkin = toimipaikka.vakajarjestaja.kunnallinen_kytkin
            if kunnallinen_kytkin and jarjestamismuoto_koodi not in jarjestamismuoto_koodit_kunta:
                msg = {'varhaiskasvatuspaatos': [ErrorMessages.VS007.value]}
                raise serializers.ValidationError(msg, code='invalid')
            elif not kunnallinen_kytkin and jarjestamismuoto_koodi not in jarjestamismuoto_koodit_yksityinen:
                msg = {'varhaiskasvatuspaatos': [ErrorMessages.VS008.value]}
                raise serializers.ValidationError(msg, code='invalid')

    def _validate_paivamaarat_varhaiskasvatussuhde_toimipaikka(self, data):
        toimipaikka_paattymis_pvm = data['toimipaikka'].paattymis_pvm
        vakasuhde_paattymis_pvm = data.get('paattymis_pvm', None)

        if toimipaikka_paattymis_pvm is not None:
            if not validators.validate_paivamaara1_before_paivamaara2(data['alkamis_pvm'], toimipaikka_paattymis_pvm, can_be_same=True):
                raise ValidationError({'errors': [ErrorMessages.VS009.value]})
            if(vakasuhde_paattymis_pvm is not None and
                    not validators.validate_paivamaara1_before_paivamaara2(vakasuhde_paattymis_pvm, toimipaikka_paattymis_pvm, can_be_same=True)):
                raise ValidationError({'errors': [ErrorMessages.VS010.value]})

    def _validate_paivamaarat_varhaiskasvatussuhde_varhaiskasvatuspaatos(self, data):
        vakapaatos = data['varhaiskasvatuspaatos']
        alkamis_pvm = data['alkamis_pvm']
        paattymis_pvm = data.get('paattymis_pvm', None)

        if not validators.validate_paivamaara1_before_paivamaara2(vakapaatos.alkamis_pvm, alkamis_pvm, can_be_same=True):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.VP002.value]})
        if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, vakapaatos.paattymis_pvm, can_be_same=True):
            raise ValidationError({'alkamis_pvm': [ErrorMessages.VS011.value]})

        validators.validate_paattymispvm_same_or_after_alkamispvm(data)
        if paattymis_pvm:
            if not validators.validate_paivamaara1_before_paivamaara2(paattymis_pvm, vakapaatos.paattymis_pvm, can_be_same=True):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.VP003.value]})
        elif vakapaatos.paattymis_pvm:
            # Raise error if vakapaatos has paattymis_pvm and vakasuhde doesn't have paattymis_pvm (existing or in request)
            raise ValidationError({'paattymis_pvm': [ErrorMessages.VS012.value]})


class PaosToimintaSerializer(serializers.HyperlinkedModelSerializer):
    """
    oma_organisaato:
        Organisaatio jolle haetaan oikeuksia toisesta organisaatiosta

    paos_organisaatio:
        Organisaatio josta palveluseteli/ostopalvelu oikeuksia haetaan (vastapuolen organisaatio)

    paos_toimipaikka:
        Toimipaikka josta palveluseteli/ostopalvelu oikeuksia haetaan (vastapuolen toimipaikka)
    """

    id = serializers.IntegerField(read_only=True)
    oma_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    oma_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                           parent_field='oma_organisaatio',
                                           parent_attribute='organisaatio_oid',
                                           prevalidator=validators.validate_organisaatio_oid,
                                           either_required=True)
    paos_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    paos_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                            parent_field='paos_organisaatio',
                                            parent_attribute='organisaatio_oid',
                                            prevalidator=validators.validate_organisaatio_oid,
                                            either_required=False)
    paos_toimipaikka = ToimipaikkaHLField(view_name='toimipaikka-detail', required=False)
    paos_toimipaikka_oid = OidRelatedField(object_type=Toimipaikka,
                                           parent_field='paos_toimipaikka',
                                           parent_attribute='organisaatio_oid',
                                           prevalidator=validators.validate_organisaatio_oid,
                                           either_required=False)
    voimassa_kytkin = serializers.BooleanField(read_only=True)

    class Meta:
        model = PaosToiminta
        exclude = ('luonti_pvm', 'changed_by',)

    def validate(self, data):
        if ('paos_organisaatio' in data and data['paos_organisaatio'] is not None and
                'paos_toimipaikka' in data and data['paos_toimipaikka'] is not None):
            raise serializers.ValidationError({'errors': [ErrorMessages.PT006.value]}, code='invalid')

        if 'paos_organisaatio' not in data and 'paos_toimipaikka' not in data:
            raise serializers.ValidationError({'errors': [ErrorMessages.PT007.value]}, code='invalid')

        if not self.context['request'].user.has_perm('view_vakajarjestaja', data['oma_organisaatio']):
            raise serializers.ValidationError({'oma_organisaatio': [ErrorMessages.GE008.value]}, code='invalid')

        if ('paos_organisaatio' in data and data['paos_organisaatio'] is not None and
                not data['paos_organisaatio'].kunnallinen_kytkin):
            raise serializers.ValidationError({'paos_organisaatio': [ErrorMessages.PT008.value]}, code='invalid')

        return data


class PaosOikeusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.IntegerField(read_only=True)
    jarjestaja_kunta_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', read_only=True)
    tuottaja_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', read_only=True)
    voimassa_kytkin = serializers.BooleanField(read_only=True)
    tallentaja_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    tallentaja_organisaatio_oid = OidRelatedField(object_type=VakaJarjestaja,
                                                  parent_field='tallentaja_organisaatio',
                                                  parent_attribute='organisaatio_oid',
                                                  prevalidator=validators.validate_organisaatio_oid,
                                                  either_required=True)

    class Meta:
        model = PaosOikeus
        exclude = ('changed_by', 'luonti_pvm')

    def validate(self, data):
        if 'tallentaja_organisaatio' not in data:
            raise serializers.ValidationError({'tallentaja_organisaatio': [ErrorMessages.GE001.value]}, code='invalid')
        return data


"""
Nested serializers
"""


class VakaJarjestajaYhteenvetoSerializer(serializers.Serializer):
    vakajarjestaja_nimi = serializers.CharField(read_only=True)
    lapset_lkm = serializers.IntegerField(read_only=True)
    lapset_vakapaatos_voimassaoleva = serializers.IntegerField(read_only=True)
    lapset_vakasuhde_voimassaoleva = serializers.IntegerField(read_only=True)
    lapset_vuorohoidossa = serializers.IntegerField(read_only=True)
    lapset_palveluseteli_ja_ostopalvelu = serializers.IntegerField(read_only=True)
    lapset_maksutieto_voimassaoleva = serializers.IntegerField(read_only=True)
    toimipaikat_voimassaolevat = serializers.IntegerField(read_only=True)
    toimipaikat_paattyneet = serializers.IntegerField(read_only=True)
    toimintapainotukset_maara = serializers.IntegerField(read_only=True)
    kielipainotukset_maara = serializers.IntegerField(read_only=True)
    tyontekijat_lkm = serializers.IntegerField(read_only=True)
    palvelussuhteet_voimassaoleva = serializers.IntegerField(read_only=True)
    palvelussuhteet_maaraaikaiset = serializers.IntegerField(read_only=True)
    varhaiskasvatusalan_tutkinnot = serializers.IntegerField(read_only=True)
    tyoskentelypaikat_kelpoiset = serializers.IntegerField(read_only=True)
    taydennyskoulutukset_kuluva_vuosi = serializers.IntegerField(read_only=True)
    tilapainen_henkilosto_maara_kuluva_vuosi = serializers.IntegerField(read_only=True, allow_null=True)
    tilapainen_henkilosto_tunnit_kuluva_vuosi = serializers.FloatField(read_only=True, allow_null=True)


class ToimipaikanLapsetKatseluSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    etunimet = serializers.CharField()
    sukunimi = serializers.CharField()
    lapsi_id = serializers.IntegerField()


class LapsiKoosteVarhaiskasvatussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    toimipaikka_nimi = serializers.ReadOnlyField(source='toimipaikka.nimi')

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ('id', 'alkamis_pvm', 'paattymis_pvm', 'toimipaikka', 'toimipaikka_nimi',
                  'varhaiskasvatuspaatos', 'lahdejarjestelma', 'tunniste', 'muutos_pvm',)


class LapsiKoosteHenkiloSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Henkilo
        fields = ('id', 'etunimet', 'kutsumanimi', 'sukunimi', 'henkilo_oid', 'syntyma_pvm', 'turvakielto',)


class LapsiKoosteVarhaiskasvatuspaatosSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Varhaiskasvatuspaatos
        fields = ('id', 'hakemus_pvm', 'alkamis_pvm', 'paattymis_pvm', 'jarjestamismuoto_koodi', 'tuntimaara_viikossa',
                  'paivittainen_vaka_kytkin', 'kokopaivainen_vaka_kytkin', 'vuorohoito_kytkin', 'pikakasittely_kytkin',
                  'tilapainen_vaka_kytkin', 'lahdejarjestelma', 'tunniste', 'muutos_pvm',)


class LapsiKoosteMaksutietoSerializer(serializers.HyperlinkedModelSerializer):
    huoltajat = serializers.SerializerMethodField('get_huoltajat_for_maksutieto')

    @swagger_serializer_method(serializer_or_field=MaksutietoGetHuoltajaSerializer(many=True))
    def get_huoltajat_for_maksutieto(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    class Meta:
        model = Maksutieto
        fields = ('id', 'huoltajat', 'alkamis_pvm', 'paattymis_pvm', 'yksityinen_jarjestaja', 'maksun_peruste_koodi',
                  'asiakasmaksu', 'palveluseteli_arvo', 'perheen_koko', 'lahdejarjestelma', 'tunniste', 'muutos_pvm',)


class LapsiKoosteSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi', allow_null=True)
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi', allow_null=True)
    yksityinen_kytkin = serializers.BooleanField(read_only=True)
    henkilo = LapsiKoosteHenkiloSerializer(many=False)
    varhaiskasvatuspaatokset = LapsiKoosteVarhaiskasvatuspaatosSerializer(many=True)
    varhaiskasvatussuhteet = LapsiKoosteVarhaiskasvatussuhdeSerializer(many=True)
    maksutiedot = LapsiKoosteMaksutietoSerializer(many=True)
    lahdejarjestelma = serializers.ReadOnlyField()
    tunniste = serializers.ReadOnlyField()


class NestedPaosOikeusSerializer(serializers.ModelSerializer):
    tallentaja_organisaatio_oid = serializers.ReadOnlyField(source='tallentaja_organisaatio.organisaatio_oid')
    tallentaja_organisaatio_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PaosOikeus
        fields = ('id', 'tallentaja_organisaatio_id', 'tallentaja_organisaatio_oid', 'voimassa_kytkin')


class PaosToimijatSerializer(serializers.HyperlinkedModelSerializer):
    paos_toiminta_url = serializers.HyperlinkedRelatedField(view_name='paostoiminta-detail', source='id', read_only=True)
    paos_toiminta_id = serializers.IntegerField(source='id', read_only=True)
    vakajarjestaja_url = serializers.HyperlinkedRelatedField(view_name='vakajarjestaja-detail', source='paos_organisaatio.id', read_only=True)
    vakajarjestaja_id = serializers.IntegerField(source='paos_organisaatio.id', read_only=True)
    vakajarjestaja_organisaatio_oid = serializers.ReadOnlyField(source='paos_organisaatio.organisaatio_oid')
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')
    paos_oikeus = serializers.SerializerMethodField('get_paos_oikeus')

    @swagger_serializer_method(serializer_or_field=NestedPaosOikeusSerializer(many=False))
    def get_paos_oikeus(self, instance):
        paos_oikeus = (PaosOikeus.objects.filter(jarjestaja_kunta_organisaatio=instance.paos_organisaatio,
                                                 tuottaja_organisaatio=instance.oma_organisaatio)
                                         .select_related('tallentaja_organisaatio')
                                         .first())
        return NestedPaosOikeusSerializer(paos_oikeus).data

    class Meta:
        model = PaosToiminta
        exclude = ('luonti_pvm', 'muutos_pvm', 'changed_by', 'oma_organisaatio', 'paos_organisaatio', 'paos_toimipaikka')


class PaosToimipaikatSerializer(serializers.HyperlinkedModelSerializer):
    paos_toiminta_url = serializers.HyperlinkedRelatedField(view_name='paostoiminta-detail', source='id', read_only=True)
    paos_toiminta_id = serializers.IntegerField(source='id', read_only=True)
    toimija_url = serializers.HyperlinkedRelatedField(view_name='vakajarjestaja-detail', source='paos_toimipaikka.vakajarjestaja.id', read_only=True)
    toimija_id = serializers.IntegerField(source='paos_toimipaikka.vakajarjestaja.id', read_only=True)
    toimija_organisaatio_oid = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.organisaatio_oid')
    toimija_y_tunnus = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.y_tunnus')
    toimija_nimi = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.nimi')
    toimipaikka_url = serializers.HyperlinkedRelatedField(view_name='toimipaikka-detail', source='paos_toimipaikka.id', read_only=True)
    toimipaikka_id = serializers.IntegerField(source='paos_toimipaikka.id', read_only=True)
    toimipaikka_organisaatio_oid = serializers.ReadOnlyField(source='paos_toimipaikka.organisaatio_oid')
    toimipaikka_nimi = serializers.ReadOnlyField(source='paos_toimipaikka.nimi')
    paos_oikeus = serializers.SerializerMethodField('get_paos_oikeus')

    @swagger_serializer_method(serializer_or_field=NestedPaosOikeusSerializer(many=False))
    def get_paos_oikeus(self, instance):
        paos_oikeus = PaosOikeus.objects.filter(
            jarjestaja_kunta_organisaatio=instance.oma_organisaatio,
            tuottaja_organisaatio=instance.paos_toimipaikka.vakajarjestaja
        ).select_related('tallentaja_organisaatio').first()
        return NestedPaosOikeusSerializer(paos_oikeus).data

    class Meta:
        model = PaosToiminta
        exclude = ('luonti_pvm', 'muutos_pvm', 'changed_by', 'oma_organisaatio', 'paos_organisaatio', 'paos_toimipaikka')


class PaosVakaJarjestajaSerializer(serializers.HyperlinkedModelSerializer):
    kunnallinen_kytkin = serializers.BooleanField(read_only=True)

    class Meta:
        model = VakaJarjestaja
        fields = ('id', 'url', 'nimi', 'y_tunnus', 'organisaatio_oid', 'kunnallinen_kytkin')

    @caching_to_representation('paosallvakajarjestaja')
    def to_representation(self, instance):
        return super(PaosVakaJarjestajaSerializer, self).to_representation(instance)


class PaosToimipaikkaSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Toimipaikka
        fields = ('id', 'url', 'nimi', 'organisaatio_oid')

    @caching_to_representation('paosalltoimipaikka')
    def to_representation(self, instance):
        return super(PaosToimipaikkaSerializer, self).to_representation(instance)


class ToimipaikkaKoosteToiminnallinenPainotusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToiminnallinenPainotus
        fields = ('id', 'toimintapainotus_koodi', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma', 'tunniste',)


class ToimipaikkaKoosteKieliPainotusSerializer(serializers.ModelSerializer):
    class Meta:
        model = KieliPainotus
        fields = ('id', 'kielipainotus_koodi', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma', 'tunniste',)


class ToimipaikkaKoosteSerializer(serializers.ModelSerializer):
    vakajarjestaja_id = serializers.IntegerField(read_only=True, source='vakajarjestaja.id')
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='vakajarjestaja.nimi')
    kielipainotukset = ToimipaikkaKoosteKieliPainotusSerializer(many=True, read_only=True)
    toiminnalliset_painotukset = ToimipaikkaKoosteToiminnallinenPainotusSerializer(source='toiminnallisetpainotukset',
                                                                                   many=True, read_only=True)

    class Meta:
        model = Toimipaikka
        exclude = ('changed_by', 'vakajarjestaja', 'luonti_pvm', 'muutos_pvm',)
