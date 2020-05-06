import logging

from django.contrib.auth.models import User, Group
from django.db.models import Q
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from guardian.shortcuts import get_objects_for_user
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.validators import UniqueTogetherValidator

from varda import validators
from varda.cache import caching_to_representation
from varda.misc import list_of_dicts_has_duplicate_values
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Maksutieto, Henkilo,
                          Lapsi, Huoltaja, Huoltajuussuhde, PaosOikeus, PaosToiminta, Varhaiskasvatuspaatos,
                          Varhaiskasvatussuhde, Z3_AdditionalCasUserFields, Tyontekija)
from varda.permissions import check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement
from varda.serializers_common import OidRelatedField
from varda.validators import validate_henkilo_oid, validate_nimi, validate_henkilotunnus_or_oid_needed, validate_organisaatio_oid

# Get an instance of a logger
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
            raise serializers.ValidationError({"virkailija_id": "Incorrect data format. Id should be a positive integer."})

        try:
            user = User.objects.get(id=virkailija_id)
        except User.DoesNotExist:
            raise serializers.ValidationError({"virkailija_id": "User was not found with id: " + str(virkailija_id) + "."})

        try:
            oph_staff_user_obj = Z3_AdditionalCasUserFields.objects.get(user=user)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            raise serializers.ValidationError({"virkailija_id": "User with id: " + str(virkailija_id) + ", is not a CAS-user."})

        if not user.groups.filter(name="oph_staff").exists():
            raise serializers.ValidationError({"virkailija_id": "User with id: " + str(virkailija_id) + ", is not in oph_staff group."})

        oph_staff_user_obj.approved_oph_staff = True
        oph_staff_user_obj.save()

        return attrs


class ClearCacheSerializer(serializers.Serializer):
    clear_cache = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        clear_cache = attrs.get('clear_cache')
        if clear_cache.lower() != "yes":
            msg = _("You must approve with 'yes'.")
            raise serializers.ValidationError(msg, code='invalid')
        return attrs


"""
User-specific viewsets below
"""


class ActiveUserSerializer(serializers.ModelSerializer):
    asiointikieli_koodi = serializers.SerializerMethodField()
    henkilo_oid = serializers.SerializerMethodField()
    kayttajatyyppi = serializers.SerializerMethodField()
    kayttooikeudet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('username', 'email', 'asiointikieli_koodi', 'henkilo_oid', 'kayttajatyyppi', 'kayttooikeudet')

    def get_asiointikieli_koodi(self, obj):
        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(user_id=obj.id)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            return "fi"
        return cas_user_obj.asiointikieli_koodi

    def get_henkilo_oid(self, obj):
        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(user_id=obj.id)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            return ""
        return cas_user_obj.henkilo_oid

    def get_kayttajatyyppi(self, obj):
        user = obj
        if user.is_superuser:
            return 'ADMIN'

        try:
            cas_user_obj = Z3_AdditionalCasUserFields.objects.get(user_id=user.id)
        except Z3_AdditionalCasUserFields.DoesNotExist:
            return ""
        return cas_user_obj.kayttajatyyppi

    def get_kayttooikeudet(self, obj):
        kayttooikeudet = []
        user_groups = obj.groups.filter(Q(name__startswith='VARDA-') | Q(name__startswith='HUOLTAJATIETO_'))
        for user_group in user_groups:
            user_group_name = user_group.name.rsplit('_', maxsplit=1)
            kayttooikeus = user_group_name[0]
            organisaatio_oid = user_group_name[1]
            kayttooikeudet.append({'organisaatio': organisaatio_oid, 'kayttooikeus': kayttooikeus})
        return kayttooikeudet


class AuthTokenSerializer(serializers.Serializer):
    refresh_token = serializers.BooleanField(label=_("Refresh token"))

    def validate(self, attrs):
        refresh = attrs.get('refresh_token')

        if refresh:
            pass
        else:
            msg = _('Token was not refreshed.')
            raise serializers.ValidationError(msg, code='invalid')

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


class ToimipaikkaHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Toimipaikka.objects.all().order_by('id')
        else:
            queryset = Toimipaikka.objects.none()
        return queryset


class VarhaiskasvatuspaatosHLField(serializers.HyperlinkedRelatedField):
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Varhaiskasvatuspaatos.objects.all().order_by('id')
        else:
            queryset = Varhaiskasvatuspaatos.objects.none()
        return queryset


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
    vakajarjestaja = VakaJarjestajaHLField(view_name='vakajarjestaja-detail')
    organisaatio_oid = serializers.CharField(read_only=True, required=False)
    kayntiosoite = serializers.CharField(min_length=3, max_length=100)
    postiosoite = serializers.CharField(min_length=3, max_length=100)
    toiminnallisetpainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='toiminnallinenpainotus-detail')
    kielipainotukset_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='kielipainotus-detail')
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    lahdejarjestelma = serializers.CharField(read_only=True)

    class Meta:
        model = Toimipaikka
        exclude = ('nimi_sv', 'luonti_pvm', 'changed_by',)
        validators = [
            UniqueTogetherValidator(
                queryset=Toimipaikka.objects.all(),
                fields=('nimi', 'vakajarjestaja'),
                message='Combination of nimi and vakajarjestaja fields should be unique'
            )
        ]

    def validate(self, data):
        if ('vakajarjestaja' in data and
                not self.context['request'].user.has_perm('view_vakajarjestaja', data['vakajarjestaja'])):
            msg = {"vakajarjestaja": ["Invalid hyperlink - Object does not exist.", ]}
            raise serializers.ValidationError(msg, code='invalid')
        #  names that collide with temporary toimipaikka are not allowed
        if 'nimi' in data and data['nimi'].lower().startswith('palveluseteli ja ostopalvelu'):
            msg = {"nimi": ["toimipaikka with name palveluseteli ja ostopalvelu is reserved for system"]}
            raise serializers.ValidationError(msg, code='invalid')
        return data

    @caching_to_representation('toimipaikka')
    def to_representation(self, instance):
        return super(ToimipaikkaSerializer, self).to_representation(instance)


class ToiminnallinenPainotusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    toimipaikka = ToimipaikkaHLField(view_name='toimipaikka-detail')

    class Meta:
        model = ToiminnallinenPainotus
        exclude = ('luonti_pvm', 'changed_by',)

    def validate_toimipaikka(self, value):
        if self.instance and value != self.instance.toimipaikka:
            raise serializers.ValidationError("This field is not allowed to be changed.")
        return value


class KieliPainotusSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    toimipaikka = ToimipaikkaHLField(view_name='toimipaikka-detail')

    class Meta:
        model = KieliPainotus
        exclude = ('luonti_pvm', 'changed_by',)

    def validate_toimipaikka(self, value):
        if self.instance and value != self.instance.toimipaikka:
            raise serializers.ValidationError("This field is not allowed to be changed.")
        return value


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
            if user.has_perm("view_lapsi", lapsi):
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


class HenkiloOppijanumeroSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Henkilo
        fields = ('id', 'henkilo_oid')


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
    lapsi = LapsiHLField(required=True, view_name='lapsi-detail')
    alkamis_pvm = serializers.DateField(required=True, validators=[validators.validate_vaka_date])

    class Meta:
        model = Maksutieto
        exclude = ('luonti_pvm', 'changed_by', 'yksityinen_jarjestaja',)

    def validate(self, data):
        if 'lapsi' in data and self.context['request'].user.has_perm('view_lapsi', data['lapsi']):
            pass
        else:
            msg = {"lapsi": ["Invalid hyperlink - Object does not exist.", ]}
            raise serializers.ValidationError(msg, code='invalid')

        if len(data["huoltajat"]) > 7:
            raise serializers.ValidationError({"huoltajat": ["maximum number of huoltajat is 7"]})

        if list_of_dicts_has_duplicate_values(data["huoltajat"], 'henkilotunnus'):
            raise serializers.ValidationError({"huoltajat": ["duplicated henkilotunnus given"]})

        if list_of_dicts_has_duplicate_values(data["huoltajat"], 'henkilo_oid'):
            raise serializers.ValidationError({"huoltajat": ["duplicated henkilo_oid given"]})

        return data


class MaksutietoGetHuoltajaSerializer(serializers.ModelSerializer):
    henkilo_oid = serializers.CharField(read_only=True)
    etunimet = serializers.CharField(read_only=True)
    sukunimi = serializers.CharField(read_only=True)

    class Meta:
        model = Henkilo
        fields = ('henkilo_oid', 'etunimet', 'sukunimi')


class MaksutietoGetSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    huoltajat = serializers.SerializerMethodField('get_huoltajat_for_maksutieto')
    lapsi = serializers.SerializerMethodField('get_lapsi_for_maksutieto')

    def get_huoltajat_for_maksutieto(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    def get_lapsi_for_maksutieto(self, obj):
        lapsi = obj.huoltajuussuhteet.all().values('lapsi').distinct()
        if len(lapsi) != 1:
            logger.error('Could not find just one lapsi for maksutieto-id: {}'.format(obj.id))
            raise APIException
        else:
            lapsi = lapsi[0].get('lapsi')
        return self.context['request'].build_absolute_uri(reverse('lapsi-detail', args=[lapsi]))

    class Meta:
        model = Maksutieto
        fields = ('url', 'id', 'huoltajat', 'lapsi', 'maksun_peruste_koodi', 'palveluseteli_arvo', 'asiakasmaksu',
                  'perheen_koko', 'alkamis_pvm', 'paattymis_pvm')


class MaksutietoUpdateSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    huoltajat = serializers.SerializerMethodField('get_huoltajat_for_maksutieto')
    lapsi = serializers.SerializerMethodField('get_lapsi_for_maksutieto')
    paattymis_pvm = serializers.DateField(allow_null=True, required=True, validators=[validators.validate_vaka_date])

    def get_huoltajat_for_maksutieto(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    def get_lapsi_for_maksutieto(self, obj):
        lapsi = obj.huoltajuussuhteet.all().values('lapsi').distinct()
        if len(lapsi) != 1:
            logger.error('Could not find just one lapsi for maksutieto-id: {}'.format(obj.id))
            raise APIException
        else:
            lapsi = lapsi[0].get('lapsi')
        return self.context['request'].build_absolute_uri(reverse('lapsi-detail', args=[lapsi]))

    def validate(self, data):
        if len(data) == 0:
            raise serializers.ValidationError("No data given.")
        return data

    class Meta:
        model = Maksutieto
        read_only_fields = ['url', 'id', 'huoltajat', "lapsi", "alkamis_pvm", "perheen_koko", 'maksun_peruste_koodi',
                            "palveluseteli_arvo", "asiakasmaksu"]
        exclude = ('luonti_pvm', 'changed_by', 'yksityinen_jarjestaja',)


class LapsiSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloHLField(view_name='henkilo-detail')
    vakatoimija = VakaJarjestajaHLField(allow_null=True, required=False, view_name='vakajarjestaja-detail')
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
        errors = []
        if 'henkilo' in data and not self.context['request'].user.has_perm('view_henkilo', data['henkilo']):
            msg = {"henkilo": ["Invalid hyperlink - Object does not exist.", ]}
            errors.append(msg)

        vakatoimija = data.get('vakatoimija')
        oma_organisaatio = data.get('oma_organisaatio')
        paos_organisaatio = data.get('paos_organisaatio')
        # We don't require vakatoimija for regular (non-paos) lapsi since this would change api signature. This can be
        # changed when all users input vakatoimija or in v2 api.
        if vakatoimija and oma_organisaatio or vakatoimija and paos_organisaatio:
            msg = 'Lapsi cannot be paos and regular one same time.'
            errors.append(msg)

        if oma_organisaatio and not paos_organisaatio or paos_organisaatio and not oma_organisaatio:
            msg = 'For PAOS-lapsi both oma_organisaatio and paos_organisaatio are needed.'
            errors.append(msg)
        if oma_organisaatio and oma_organisaatio == paos_organisaatio:
            msg = {"detail": "oma_organisaatio cannot be same as paos_organisaatio."}
            errors.append(msg)
        if errors:
            raise serializers.ValidationError(errors, code='invalid')
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
    henkilo = HenkiloHLField(view_name='henkilo-detail')
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
        return [{"nimi": toimipaikka.nimi, "nimi_sv": toimipaikka.nimi_sv, "organisaatio_oid": toimipaikka.organisaatio_oid}
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
        exclude = ('luonti_pvm', 'changed_by')


class VarhaiskasvatuspaatosSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    lapsi = LapsiHLField(view_name='lapsi-detail')
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    alkamis_pvm = serializers.DateField(validators=[validators.validate_vaka_date])
    hakemus_pvm = serializers.DateField(validators=[validators.validate_vaka_date])
    vuorohoito_kytkin = serializers.BooleanField(required=True)

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('luonti_pvm', 'changed_by',)
        read_only_fields = ['pikakasittely_kytkin']

    def validate(self, data):
        lapsi_obj = data['lapsi']
        jarjestamismuoto_koodi_paos = ['jm02', 'jm03']
        if not self.context['request'].user.has_perm('view_lapsi', lapsi_obj):
            msg = {"lapsi": ["Invalid hyperlink - Object does not exist.", ]}
            raise serializers.ValidationError(msg, code='invalid')

        if (lapsi_obj.paos_organisaatio is not None and
                data['jarjestamismuoto_koodi'].lower() not in jarjestamismuoto_koodi_paos):
            msg = {'jarjestamismuoto_koodi': ['Invalid code for paos-lapsi.', ]}
            raise serializers.ValidationError(msg, code='invalid')

        if (lapsi_obj.paos_organisaatio is not None):
            check_if_oma_organisaatio_and_paos_organisaatio_have_paos_agreement(lapsi_obj.oma_organisaatio,
                                                                                lapsi_obj.paos_organisaatio)

        """
        TODO: Activate when PAOS-yksityiset in production.
        NOTE: Also uncomment the relevant test case in views_tests.py: test_api_push_vakapaatos_non_paos_lapsi
        if (lapsi_obj.paos_organisaatio is None and
                data['jarjestamismuoto_koodi'].lower() in jarjestamismuoto_koodi_paos):
            msg = {'jarjestamismuoto_koodi': ['Invalid code for non-paos-lapsi.', ]}
            raise serializers.ValidationError(msg, code='invalid')
        """

        if not data["vuorohoito_kytkin"]:
            msg = {}
            if "paivittainen_vaka_kytkin" not in data or data["paivittainen_vaka_kytkin"] is None:
                msg["paivittainen_vaka_kytkin"] = "paivittainen_vaka_kytkin must be given if vuorohoito_kytkin is False"
            if "kokopaivainen_vaka_kytkin" not in data or data["kokopaivainen_vaka_kytkin"] is None:
                msg["kokopaivainen_vaka_kytkin"] = "kokopaivainen_vaka_kytkin must be given if vuorohoito_kytkin is False"
            if msg:
                raise serializers.ValidationError(msg, code='invalid')
        return data

    @caching_to_representation('varhaiskasvatuspaatos')
    def to_representation(self, instance):
        return super(VarhaiskasvatuspaatosSerializer, self).to_representation(instance)


class VarhaiskasvatuspaatosPutSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    alkamis_pvm = serializers.DateField(required=True, validators=[validators.validate_vaka_date])
    hakemus_pvm = serializers.DateField(required=True, validators=[validators.validate_vaka_date])

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('luonti_pvm', 'changed_by',)
        read_only_fields = ('lapsi', 'vuorohoito_kytkin', 'pikakasittely_kytkin', 'tuntimaara_viikossa', 'paivittainen_vaka_kytkin',
                            'kokopaivainen_vaka_kytkin', 'jarjestamismuoto_koodi')


class VarhaiskasvatuspaatosPatchSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    varhaiskasvatussuhteet_top = serializers.HyperlinkedRelatedField(many=True, read_only=True, view_name='varhaiskasvatussuhde-detail')
    alkamis_pvm = serializers.DateField(required=False, validators=[validators.validate_vaka_date])
    hakemus_pvm = serializers.DateField(required=False, validators=[validators.validate_vaka_date])

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('luonti_pvm', 'changed_by',)
        read_only_fields = ('lapsi', 'vuorohoito_kytkin', 'pikakasittely_kytkin', 'tuntimaara_viikossa', 'paivittainen_vaka_kytkin',
                            'kokopaivainen_vaka_kytkin', 'jarjestamismuoto_koodi')

    def validate(self, data):
        if len(data) == 0:
            raise serializers.ValidationError("No data given.")
        return data


class VarhaiskasvatussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    varhaiskasvatuspaatos = VarhaiskasvatuspaatosHLField(view_name='varhaiskasvatuspaatos-detail')
    toimipaikka = ToimipaikkaHLField(required=False, view_name='toimipaikka-detail')
    toimipaikka_oid = OidRelatedField(either_required=True,
                                      object_type=Toimipaikka,
                                      parent_field='toimipaikka',
                                      parent_attribute='organisaatio_oid',
                                      prevalidator=validate_organisaatio_oid)

    class Meta:
        model = Varhaiskasvatussuhde
        exclude = ('luonti_pvm', 'changed_by',)

    def validate(self, data):
        if ('varhaiskasvatuspaatos' in data and
                not self.context['request'].user.has_perm('view_varhaiskasvatuspaatos', data['varhaiskasvatuspaatos'])):
            msg = {"varhaiskasvatuspaatos": ["Invalid hyperlink - Object does not exist.", ]}
            raise serializers.ValidationError(msg, code='invalid')
        elif data['varhaiskasvatuspaatos'].lapsi.paos_kytkin and data['varhaiskasvatuspaatos'].lapsi.paos_organisaatio != data['toimipaikka'].vakajarjestaja:
            msg = {'non_field_errors': ['Vakajarjestaja is different than paos_organisaatio for lapsi.']}
            raise serializers.ValidationError(msg, code='invalid')
        return data


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
            msg = _("Either paos_organisaatio or paos_toimipaikka is needed, not both.")
            raise serializers.ValidationError(msg, code='invalid')

        if 'paos_organisaatio' not in data and 'paos_toimipaikka' not in data:
            msg = ("Either paos_organisaatio or paos_toimipaikka is needed")
            raise serializers.ValidationError(msg, code='invalid')

        if not self.context['request'].user.has_perm('view_vakajarjestaja', data['oma_organisaatio']):
            msg = {"oma_organisaatio": ["Invalid hyperlink - Object does not exist.", ]}
            raise serializers.ValidationError(msg, code='invalid')

        if ('paos_organisaatio' in data and data['paos_organisaatio'] is not None and
                not data['paos_organisaatio'].kunnallinen_kytkin):
            msg = {"paos_organisaatio": ["paos_organisaatio must be kunta or kuntayhtyma.", ]}
            raise serializers.ValidationError(msg, code='invalid')

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
            raise serializers.ValidationError({"tallentaja_organisaatio": ["This field is required"]}, code='invalid')
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


class ToimipaikanLapsetKatseluSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    etunimet = serializers.CharField()
    sukunimi = serializers.CharField()
    lapsi_id = serializers.IntegerField()


class LapsiKoosteVarhaiskasvatussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    toimipaikka_nimi = serializers.ReadOnlyField(source='toimipaikka.nimi')

    class Meta:
        model = Varhaiskasvatussuhde
        exclude = ('url', 'luonti_pvm', 'changed_by')


class LapsiKoosteHenkiloSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Henkilo
        fields = ['id', 'etunimet', 'kutsumanimi', 'sukunimi', 'henkilo_oid', 'syntyma_pvm']


class LapsiKoosteVarhaiskasvatuspaatosSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = Varhaiskasvatuspaatos
        exclude = ('url', 'lapsi', 'luonti_pvm', 'changed_by')


class LapsiKoosteMaksutietoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    huoltajat = serializers.SerializerMethodField('get_huoltajat_for_maksutieto')

    def get_huoltajat_for_maksutieto(self, obj):
        huoltajuussuhteet = obj.huoltajuussuhteet.all()
        huoltajat = Henkilo.objects.filter(huoltaja__huoltajuussuhteet__in=huoltajuussuhteet)
        return MaksutietoGetHuoltajaSerializer(huoltajat, many=True).data

    class Meta:
        model = Maksutieto
        exclude = ('url', 'luonti_pvm', 'changed_by')


class LapsiKoosteSerializer(serializers.Serializer):
    id = serializers.ReadOnlyField()
    henkilo = LapsiKoosteHenkiloSerializer(many=False)
    varhaiskasvatuspaatokset = LapsiKoosteVarhaiskasvatuspaatosSerializer(many=True)
    varhaiskasvatussuhteet = LapsiKoosteVarhaiskasvatussuhdeSerializer(many=True)
    maksutiedot = LapsiKoosteMaksutietoSerializer(many=True)


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
        paos_oikeus = PaosOikeus.objects.filter(
            Q(jarjestaja_kunta_organisaatio=instance.oma_organisaatio, tuottaja_organisaatio=instance.paos_organisaatio) |
            Q(jarjestaja_kunta_organisaatio=instance.paos_organisaatio, tuottaja_organisaatio=instance.oma_organisaatio)
        ).select_related('tallentaja_organisaatio').first()
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
