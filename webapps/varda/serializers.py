import datetime
import logging

from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import APIException, ValidationError

from varda import validators
from varda.cache import caching_to_representation
from varda.constants import JARJESTAMISMUODOT_YKSITYINEN
from varda.enums.error_messages import ErrorMessages
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.misc import list_of_dicts_has_duplicate_values
from varda.misc_viewsets import ViewSetValidator
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Maksutieto, Henkilo,
                          Lapsi, Huoltaja, Huoltajuussuhde, PaosOikeus, PaosToiminta, Varhaiskasvatuspaatos,
                          Varhaiskasvatussuhde, Z3_AdditionalCasUserFields, Tyontekija, Z4_CasKayttoOikeudet)
from varda.permissions import (check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement,
                               user_belongs_to_correct_groups, is_oph_staff)
from varda.related_object_validations import check_if_immutable_object_is_changed
from varda.serializers_common import OidRelatedField, TunnisteRelatedField
from varda.validators import (fill_missing_fields_for_validations, validate_henkilo_oid, validate_nimi,
                              validate_henkilotunnus_or_oid_needed, validate_organisaatio_oid)


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

    def validate(self, attrs):
        henkilo_oid = attrs.get('henkilo_oid')
        validate_henkilo_oid(henkilo_oid)
        return attrs


class UpdateOphStaffSerializer(serializers.Serializer):
    virkailija_id = serializers.IntegerField(write_only=True, required=True)

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

    def validate(self, attrs):
        clear_cache = attrs.get('clear_cache')
        if clear_cache.lower() != 'yes':
            raise serializers.ValidationError({'errors': [ErrorMessages.AD005.value]}, code='invalid')
        return attrs


"""
User-specific viewsets below
"""


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
    refresh_token = serializers.BooleanField(label=_('Refresh token'))

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
    personOidsForSamePerson = serializers.ListField(required=True)
    organisationOids = serializers.ListField(required=False)
    loggedInUserRoles = serializers.ListField(required=False)
    loggedInUserOid = serializers.CharField(required=True)


"""
RelatedField serializers
Show only relevant options in the dropdown menus (where changed_by=user)
"""


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

    def __init__(self, *args, **kwargs):
        self.permission_groups = kwargs.pop('permission_groups', [])
        super(ToimipaikkaPermissionCheckedHLField, self).__init__(*args, **kwargs)


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


"""
VARDA serializers
"""


class VakaJarjestajaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    nimi = serializers.CharField(read_only=True)
    y_tunnus = serializers.CharField(read_only=True)
    yritysmuoto = serializers.CharField(read_only=True)
    kunnallinen_kytkin = serializers.ReadOnlyField()
    organisaatio_oid = serializers.CharField(read_only=True)
    kunta_koodi = serializers.CharField(read_only=True)
    kayntiosoite = serializers.CharField(read_only=True)
    kayntiosoite_postinumero = serializers.CharField(read_only=True)
    kayntiosoite_postitoimipaikka = serializers.CharField(read_only=True)
    postiosoite = serializers.CharField(read_only=True)
    postinumero = serializers.CharField(read_only=True)
    postitoimipaikka = serializers.CharField(read_only=True)
    alkamis_pvm = serializers.CharField(read_only=True)
    paattymis_pvm = serializers.CharField(read_only=True)
    muutos_pvm = serializers.CharField(read_only=True)
    # Let's use "_top" to decrease the amount of child relations visible. Otherwise the parent-query becomes quickly unreadable.
    toimipaikat_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='toimipaikka-detail')

    class Meta:
        model = VakaJarjestaja
        exclude = ('ytjkieli', 'integraatio_organisaatio', 'luonti_pvm', 'changed_by',)

    @caching_to_representation('vakajarjestaja')
    def to_representation(self, instance):
        return super(VakaJarjestajaSerializer, self).to_representation(instance)


class ToimipaikkaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    vakajarjestaja = VakaJarjestajaPermissionCheckedHLField(view_name='vakajarjestaja-detail', required=False,
                                                            permission_groups=[Z4_CasKayttoOikeudet.TALLENTAJA,
                                                                               Z4_CasKayttoOikeudet.PALVELUKAYTTAJA])
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validators.validate_organisaatio_oid,
                                         either_required=True)
    organisaatio_oid = serializers.CharField(read_only=True, required=False)
    kayntiosoite = serializers.CharField(min_length=3, max_length=100)
    postiosoite = serializers.CharField(min_length=3, max_length=100)
    toiminnallisetpainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='toiminnallinenpainotus-detail')
    kielipainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='kielipainotus-detail')
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    hallinnointijarjestelma = serializers.CharField(read_only=True)

    class Meta:
        model = Toimipaikka
        exclude = ('nimi_sv', 'luonti_pvm', 'changed_by',)

    def validate(self, data):
        if self.instance:
            fill_missing_fields_for_validations(data, self.instance)

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

        return data

    @caching_to_representation('toimipaikka')
    def to_representation(self, instance):
        return super(ToimipaikkaSerializer, self).to_representation(instance)


class ToiminnallinenPainotusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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
        if self.instance:  # PUT/PATCH
            fill_missing_fields_for_validations(data, self.instance)
            check_if_immutable_object_is_changed(self.instance, data, 'toimipaikka')
            validators.validate_dates_within_toimipaikka(data, self.instance.toimipaikka)
        else:  # POST
            validators.validate_dates_within_toimipaikka(data, data['toimipaikka'])
        return data


class KieliPainotusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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
        if self.instance:  # PUT/PATCH
            fill_missing_fields_for_validations(data, self.instance)
            check_if_immutable_object_is_changed(self.instance, data, 'toimipaikka')
            validators.validate_dates_within_toimipaikka(data, self.instance.toimipaikka)
        else:  # POST
            validators.validate_dates_within_toimipaikka(data, data['toimipaikka'])
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
    id = serializers.ReadOnlyField()
    etunimet = serializers.CharField(required=True)
    kutsumanimi = serializers.CharField(required=True)
    sukunimi = serializers.CharField(required=True)
    henkilo_oid = serializers.CharField(required=False)
    syntyma_pvm = serializers.DateField(read_only=True)
    lapsi = serializers.SerializerMethodField()
    tyontekija = serializers.SerializerMethodField()
    henkilotunnus = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = Henkilo
        exclude = ('henkilotunnus_unique_hash', 'aidinkieli_koodi', 'sukupuoli_koodi', 'katuosoite', 'turvakielto',
                   'vtj_yksiloity', 'vtj_yksilointi_yritetty', 'postinumero', 'postitoimipaikka', 'kotikunta_koodi',
                   'luonti_pvm', 'muutos_pvm', 'changed_by')

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

    def get_lapsi(self, obj):
        request = self.context.get('request')
        user = request.user
        lapset = []

        qs = Lapsi.objects.filter(henkilo=obj.pk).order_by('id')

        for lapsi in qs:
            if user.has_perm('view_lapsi', lapsi):
                lapset.append(request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': lapsi.pk})))

        return lapset

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
    id = serializers.ReadOnlyField()
    huoltaja = serializers.SerializerMethodField()

    def get_lapsi(self, obj):
        request = self.context.get('request')
        lapset = []

        qs = Lapsi.objects.filter(henkilo=obj.pk).order_by('id')

        for lapsi in qs:
            lapset.append(request.build_absolute_uri(reverse('lapsi-detail', kwargs={'pk': lapsi.pk})))

        return lapset

    def get_tyontekija(self, obj):
        request = self.context.get('request')
        tyontekijat = []

        qs = Tyontekija.objects.filter(henkilo=obj.pk).order_by('id')

        for tyontekija in qs:
            tyontekijat.append(request.build_absolute_uri(reverse('tyontekija-detail', kwargs={'pk': tyontekija.pk})))

        return tyontekijat

    def get_huoltaja(self, obj):
        request = self.context.get('request')
        huoltajat = []

        qs = Huoltaja.objects.filter(henkilo=obj.pk).order_by('id')

        for huoltaja in qs:
            huoltajat.append(request.build_absolute_uri(reverse('huoltaja-detail', kwargs={'pk': huoltaja.pk})))

        return huoltajat


class YksiloimattomatHenkilotSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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


class MaksutietoPostHuoltajaSerializer(serializers.ModelSerializer):
    henkilotunnus = serializers.CharField(required=False)
    henkilo_oid = serializers.CharField(required=False)
    etunimet = serializers.CharField(required=True)
    sukunimi = serializers.CharField(required=True)

    def validate_etunimet(self, value):
        validate_nimi(value)
        return value

    def validate_sukunimi(self, value):
        validate_nimi(value)
        return value

    def validate(self, data):
        validate_henkilotunnus_or_oid_needed(data)
        return data

    class Meta:
        model = Henkilo
        fields = ('henkilo_oid', 'henkilotunnus', 'etunimet', 'sukunimi')


class MaksutietoPostSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    url = serializers.ReadOnlyField()
    huoltajat = MaksutietoPostHuoltajaSerializer(required=True, allow_empty=False, many=True)
    lapsi = LapsiHLField(required=False, view_name='lapsi-detail')
    lapsi_tunniste = TunnisteRelatedField(object_type=Lapsi,
                                          parent_field='lapsi',
                                          prevalidator=validators.validate_tunniste,
                                          either_required=True)
    alkamis_pvm = serializers.DateField(required=True, validators=[validators.validate_vaka_date])

    class Meta:
        model = Maksutieto
        exclude = ('luonti_pvm', 'changed_by', 'yksityinen_jarjestaja',)

    def validate(self, data):
        if not self.context['request'].user.has_perm('view_lapsi', data['lapsi']):
            msg = {'lapsi': [ErrorMessages.GE008.value]}
            raise serializers.ValidationError(msg, code='invalid')

        if len(data['huoltajat']) > 7:
            raise serializers.ValidationError({'huoltajat': [ErrorMessages.MA011.value]})

        if list_of_dicts_has_duplicate_values(data['huoltajat'], 'henkilotunnus'):
            raise serializers.ValidationError({'huoltajat': [ErrorMessages.MA012.value]})

        if list_of_dicts_has_duplicate_values(data['huoltajat'], 'henkilo_oid'):
            raise serializers.ValidationError({'huoltajat': [ErrorMessages.MA013.value]})

        return data


class MaksutietoGetHuoltajaSerializer(serializers.ModelSerializer):
    henkilo_oid = serializers.CharField(read_only=True)
    etunimet = serializers.CharField(read_only=True)
    sukunimi = serializers.CharField(read_only=True)

    class Meta:
        model = Henkilo
        fields = ('henkilo_oid', 'etunimet', 'sukunimi')


def _get_lapsi_for_maksutieto(maksutieto):
    lapsi = maksutieto.huoltajuussuhteet.all().values('lapsi').distinct()
    if len(lapsi) != 1:
        logger.error('Could not find just one lapsi for maksutieto-id: {}'.format(maksutieto.id))
        raise APIException
    return Lapsi.objects.get(id=lapsi[0].get('lapsi'))


class MaksutietoGetUpdateSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    huoltajat = serializers.SerializerMethodField()
    lapsi = serializers.SerializerMethodField()
    lapsi_tunniste = TunnisteRelatedField(object_type=Lapsi,
                                          parent_field='lapsi',
                                          read_only=True,
                                          prevalidator=validators.validate_tunniste,
                                          parent_value_getter=_get_lapsi_for_maksutieto)
    paattymis_pvm = serializers.DateField(allow_null=True, validators=[validators.validate_vaka_date])

    def get_huoltajat(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    def get_lapsi(self, obj):
        lapsi = _get_lapsi_for_maksutieto(obj)
        return self.context['request'].build_absolute_uri(reverse('lapsi-detail', args=[lapsi]))

    def validate(self, data):
        if len(data) == 0:
            raise serializers.ValidationError({'errors': [ErrorMessages.GE014.value]})
        fill_missing_fields_for_validations(data, self.instance)
        return data

    class Meta:
        model = Maksutieto
        read_only_fields = ('url', 'id', 'huoltajat', 'lapsi', 'lapsi_tunniste', 'alkamis_pvm', 'perheen_koko',
                            'maksun_peruste_koodi', 'palveluseteli_arvo', 'asiakasmaksu')
        fields = ('url', 'id', 'huoltajat', 'lapsi', 'lapsi_tunniste', 'maksun_peruste_koodi', 'palveluseteli_arvo',
                  'asiakasmaksu', 'perheen_koko', 'alkamis_pvm', 'paattymis_pvm', 'lahdejarjestelma', 'tunniste',)


class LapsiSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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

    def validate(self, data):
        with ViewSetValidator() as validator:
            if self.instance:
                fill_missing_fields_for_validations(data, self.instance)

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

    @caching_to_representation('lapsi')
    def to_representation(self, instance):
        return super(LapsiSerializer, self).to_representation(instance)


class LapsiSerializerAdmin(serializers.HyperlinkedModelSerializer):
    """
    Do not inherit from LapsiSerializer, it messes up the cache!
    to_representation should not be run twice.
    """
    id = serializers.ReadOnlyField()
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


class HenkilohakuLapsetSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloSerializer()
    maksutiedot = serializers.SerializerMethodField()
    toimipaikat = serializers.SerializerMethodField()

    class Meta:
        model = Lapsi
        exclude = ('luonti_pvm', 'changed_by', 'muutos_pvm')

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
        return [{'nimi': toimipaikka.nimi, 'nimi_sv': toimipaikka.nimi_sv, 'organisaatio_oid': toimipaikka.organisaatio_oid}
                for toimipaikka
                in get_objects_for_user(request.user, 'view_toimipaikka', toimipaikat_query)
                ]

    @caching_to_representation('henkilohakulapset')
    def to_representation(self, instance):
        return super(HenkilohakuLapsetSerializer, self).to_representation(instance)


class HuoltajaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloHLField(view_name='henkilo-detail')
    huoltajuussuhteet = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='huoltajuussuhde-detail')

    class Meta:
        model = Huoltaja
        exclude = ('luonti_pvm', 'changed_by',)

    @caching_to_representation('huoltaja')
    def to_representation(self, instance):
        return super(HuoltajaSerializer, self).to_representation(instance)


class HuoltajuussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    lapsi = LapsiHLField(view_name='lapsi-detail')
    huoltaja = HuoltajaHLField(view_name='huoltaja-detail')
    voimassa_kytkin = serializers.BooleanField()
    maksutiedot = MaksutietoHLField(required=False, view_name='maksutieto-detail', many=True)
    muutos_pvm = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Huoltajuussuhde
        exclude = ('luonti_pvm', 'changed_by',)


class VarhaiskasvatuspaatosSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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
        if self.instance:
            if len(data) == 0:
                raise serializers.ValidationError({'errors': [ErrorMessages.GE014.value]})
            fill_missing_fields_for_validations(data, self.instance)

        lapsi_obj = data['lapsi']
        if not self.context['request'].user.has_perm('view_lapsi', lapsi_obj):
            msg = {'lapsi': [ErrorMessages.GE008.value]}
            raise serializers.ValidationError(msg, code='invalid')

        if self.instance:
            check_if_immutable_object_is_changed(self.instance, data, 'lapsi')
            check_if_immutable_object_is_changed(self.instance, data, 'vuorohoito_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'tuntimaara_viikossa', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'paivittainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'kokopaivainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'tilapainen_vaka_kytkin', compare_id=False)
            check_if_immutable_object_is_changed(self.instance, data, 'jarjestamismuoto_koodi', compare_id=False)

        jarjestamismuoto_koodi = data['jarjestamismuoto_koodi'].lower()
        paattymis_pvm = data.get('paattymis_pvm', None)

        self._validate_paos_specific_data(lapsi_obj, jarjestamismuoto_koodi, paattymis_pvm)
        self._validate_jarjestamismuoto(lapsi_obj, jarjestamismuoto_koodi, paattymis_pvm)
        self._validate_vuorohoito(data)
        self._validate_tilapainen_vaka_kytkin(data)

        return data

    def _validate_paos_specific_data(self, lapsi_obj, jarjestamismuoto_koodi, paattymis_pvm):
        jarjestamismuoto_koodit_paos = ['jm02', 'jm03']

        if (lapsi_obj.paos_organisaatio is None and
                paattymis_pvm and
                paattymis_pvm < datetime.date(year=2020, month=1, day=1)):
            # If paattymis_pvm is set and is before 2020, do not validate paos-koodit. Lapsi may be related to
            # tilapäinen toimipaikka. TODO: Remove this condition after tilapaiset toimipaikat are not in use.
            # https://jira.eduuni.fi/browse/CSCVARDA-1807
            return

        if lapsi_obj.paos_organisaatio is not None:
            check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(lapsi_obj.oma_organisaatio, lapsi_obj.paos_organisaatio)
            if jarjestamismuoto_koodi not in jarjestamismuoto_koodit_paos:
                msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP005.value]}
                raise serializers.ValidationError(msg, code='invalid')
        elif jarjestamismuoto_koodi in jarjestamismuoto_koodit_paos:
            msg = {'jarjestamismuoto_koodi': [ErrorMessages.VP006.value]}
            raise serializers.ValidationError(msg, code='invalid')

    def _validate_jarjestamismuoto(self, lapsi_obj, jarjestamismuoto_koodi, paattymis_pvm):
        jarjestamismuoto_koodit_kunta = ['jm01']
        jarjestamismuoto_koodit_yksityinen = ['jm04', 'jm05']

        if paattymis_pvm and paattymis_pvm < datetime.date(year=2020, month=1, day=1):
            # If paattymis_pvm is set and is before 2020, lapsi may be related to tilapäinen toimipaikka and thus have
            # jm02 or jm03, while also having kunnallinen vakatoimija.
            # TODO: Remove this condition after tilapaiset toimipaikat are not in use.
            # https://jira.eduuni.fi/browse/CSCVARDA-1807
            jarjestamismuoto_koodit_paos = ['jm02', 'jm03']
            jarjestamismuoto_koodit_kunta.extend(jarjestamismuoto_koodit_paos)

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

    @caching_to_representation('varhaiskasvatuspaatos')
    def to_representation(self, instance):
        return super(VarhaiskasvatuspaatosSerializer, self).to_representation(instance)


class VarhaiskasvatussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
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
        instance = self.instance
        if instance:
            fill_missing_fields_for_validations(data, instance)

        if not self.context['request'].user.has_perm('view_varhaiskasvatuspaatos', data['varhaiskasvatuspaatos']):
            msg = {'varhaiskasvatuspaatos': [ErrorMessages.GE008.value]}
            raise serializers.ValidationError(msg, code='invalid')
        elif data['varhaiskasvatuspaatos'].lapsi.paos_kytkin and data['varhaiskasvatuspaatos'].lapsi.paos_organisaatio != data['toimipaikka'].vakajarjestaja:
            msg = {'toimipaikka': [ErrorMessages.VS005.value]}
            raise serializers.ValidationError(msg, code='invalid')

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

        if toimipaikka.nimi.lower().startswith('palveluseteli ja ostopalvelu'):
            # If toimipaikka is tilapäinen toimipaikka, jarjestamismuoto can be paos-jarjestamismuoto as well
            # TODO: Remove this condition after tilapaiset toimipaikat are not in use.
            # https://jira.eduuni.fi/browse/CSCVARDA-1807
            jarjestamismuoto_koodit_paos = ['jm02', 'jm03']
            jarjestamismuoto_koodit_kunta.extend(jarjestamismuoto_koodit_paos)

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
            if not validators.validate_paivamaara1_before_paivamaara2(data['alkamis_pvm'], toimipaikka_paattymis_pvm):
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

        if paattymis_pvm:
            if not validators.validate_paivamaara1_before_paivamaara2(alkamis_pvm, paattymis_pvm, can_be_same=True):
                raise ValidationError({'paattymis_pvm': [ErrorMessages.MI004.value]})
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

    id = serializers.ReadOnlyField()
    oma_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=True)
    paos_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    paos_toimipaikka = ToimipaikkaHLField(view_name='toimipaikka-detail', required=False)
    voimassa_kytkin = serializers.ReadOnlyField()

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
    id = serializers.ReadOnlyField()
    jarjestaja_kunta_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', read_only=True)
    tuottaja_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', read_only=True)
    voimassa_kytkin = serializers.ReadOnlyField()
    tallentaja_organisaatio = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=True)

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
    tilapainen_henkilosto_maara_kuluva_vuosi = serializers.IntegerField(read_only=True)
    tilapainen_henkilosto_tunnit_kuluva_vuosi = serializers.FloatField(read_only=True)


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
        fields = ('id', 'etunimet', 'kutsumanimi', 'sukunimi', 'henkilo_oid', 'syntyma_pvm',)


class LapsiKoosteVarhaiskasvatuspaatosSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Varhaiskasvatuspaatos
        fields = ('id', 'hakemus_pvm', 'alkamis_pvm', 'paattymis_pvm', 'jarjestamismuoto_koodi', 'tuntimaara_viikossa',
                  'paivittainen_vaka_kytkin', 'kokopaivainen_vaka_kytkin', 'vuorohoito_kytkin', 'pikakasittely_kytkin',
                  'tilapainen_vaka_kytkin', 'lahdejarjestelma', 'tunniste', 'muutos_pvm',)


class LapsiKoosteMaksutietoSerializer(serializers.HyperlinkedModelSerializer):
    huoltajat = serializers.SerializerMethodField('get_huoltajat_for_maksutieto')

    def get_huoltajat_for_maksutieto(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    class Meta:
        model = Maksutieto
        fields = ('id', 'huoltajat', 'alkamis_pvm', 'paattymis_pvm', 'yksityinen_jarjestaja', 'maksun_peruste_koodi',
                  'asiakasmaksu', 'palveluseteli_arvo', 'perheen_koko', 'lahdejarjestelma', 'tunniste', 'muutos_pvm',)


class LapsiKoosteSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi')
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')
    yksityinen_kytkin = serializers.ReadOnlyField()
    henkilo = LapsiKoosteHenkiloSerializer(many=False)
    varhaiskasvatuspaatokset = LapsiKoosteVarhaiskasvatuspaatosSerializer(many=True)
    varhaiskasvatussuhteet = LapsiKoosteVarhaiskasvatussuhdeSerializer(many=True)
    maksutiedot = LapsiKoosteMaksutietoSerializer(many=True)
    lahdejarjestelma = serializers.ReadOnlyField()
    tunniste = serializers.ReadOnlyField()


class NestedPaosOikeusSerializer(serializers.ModelSerializer):
    tallentaja_organisaatio_oid = serializers.ReadOnlyField(source='tallentaja_organisaatio.organisaatio_oid')

    class Meta:
        model = PaosOikeus
        fields = ('id', 'tallentaja_organisaatio_id', 'tallentaja_organisaatio_oid', 'voimassa_kytkin')


class PaosToimijatSerializer(serializers.HyperlinkedModelSerializer):
    paos_toiminta_url = serializers.HyperlinkedRelatedField(view_name='paostoiminta-detail', source='id', read_only=True)
    paos_toiminta_id = serializers.ReadOnlyField(source='id')
    vakajarjestaja_url = serializers.HyperlinkedRelatedField(view_name='vakajarjestaja-detail', source='paos_organisaatio.id', read_only=True)
    vakajarjestaja_id = serializers.ReadOnlyField(source='paos_organisaatio.id')
    vakajarjestaja_organisaatio_oid = serializers.ReadOnlyField(source='paos_organisaatio.organisaatio_oid')
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')
    paos_oikeus = serializers.SerializerMethodField('get_paos_oikeus')

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
    paos_toiminta_id = serializers.ReadOnlyField(source='id')
    toimija_url = serializers.HyperlinkedRelatedField(view_name='vakajarjestaja-detail', source='paos_toimipaikka.vakajarjestaja.id', read_only=True)
    toimija_id = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.id')
    toimija_organisaatio_oid = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.organisaatio_oid')
    toimija_y_tunnus = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.y_tunnus')
    toimija_nimi = serializers.ReadOnlyField(source='paos_toimipaikka.vakajarjestaja.nimi')
    toimipaikka_url = serializers.HyperlinkedRelatedField(view_name='toimipaikka-detail', source='paos_toimipaikka.id', read_only=True)
    toimipaikka_id = serializers.ReadOnlyField(source='paos_toimipaikka.id')
    toimipaikka_organisaatio_oid = serializers.ReadOnlyField(source='paos_toimipaikka.organisaatio_oid')
    toimipaikka_nimi = serializers.ReadOnlyField(source='paos_toimipaikka.nimi')
    paos_oikeus = serializers.SerializerMethodField('get_paos_oikeus')

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
    id = serializers.ReadOnlyField()
    nimi = serializers.CharField(read_only=True)
    y_tunnus = serializers.CharField(read_only=True)
    organisaatio_oid = serializers.CharField(read_only=True)
    kunnallinen_kytkin = serializers.ReadOnlyField()

    class Meta:
        model = VakaJarjestaja
        fields = ('id', 'url', 'nimi', 'y_tunnus', 'organisaatio_oid', 'kunnallinen_kytkin')

    @caching_to_representation('paosallvakajarjestaja')
    def to_representation(self, instance):
        return super(PaosVakaJarjestajaSerializer, self).to_representation(instance)


class PaosToimipaikkaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    nimi = serializers.CharField(read_only=True)
    organisaatio_oid = serializers.CharField(read_only=True)

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
    vakajarjestaja_id = serializers.ReadOnlyField(source='vakajarjestaja.id')
    vakajarjestaja_nimi = serializers.ReadOnlyField(source='vakajarjestaja.nimi')
    kielipainotukset = ToimipaikkaKoosteKieliPainotusSerializer(many=True, read_only=True)
    toiminnalliset_painotukset = ToimipaikkaKoosteToiminnallinenPainotusSerializer(source='toiminnallisetpainotukset',
                                                                                   many=True, read_only=True)

    class Meta:
        model = Toimipaikka
        exclude = ('changed_by', 'vakajarjestaja', 'luonti_pvm', 'muutos_pvm',)
