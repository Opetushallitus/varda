from rest_framework import serializers

from varda import related_object_validations
from varda.cache import caching_to_representation
from varda.models import Henkilo, TilapainenHenkilosto, Tutkinto, Tyontekija, VakaJarjestaja, Palvelussuhde
from varda.serializers import HenkiloHLField, VakaJarjestajaHLField
from varda.serializers_common import OidRelatedField
from varda.validators import validate_henkilo_oid, validate_organisaatio_oid


class TyontekijaHLField(serializers.HyperlinkedRelatedField):
    """
    https://medium.com/django-rest-framework/limit-related-data-choices-with-django-rest-framework-c54e96f5815e
    """
    def get_queryset(self):
        user = self.context['request'].user
        if user.is_authenticated:
            queryset = Tyontekija.objects.all().order_by('id')
        else:
            queryset = Tyontekija.objects.none()
        return queryset


class TyontekijaSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    henkilo = HenkiloHLField(view_name='henkilo-detail', required=False)
    henkilo_oid = OidRelatedField(object_type=Henkilo,
                                  parent_field='henkilo',
                                  parent_attribute='henkilo_oid',
                                  prevalidator=validate_henkilo_oid,
                                  either_required=True)
    vakajarjestaja = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validate_organisaatio_oid,
                                         either_required=True)

    class Meta:
        model = Tyontekija
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tyontekija')
    def to_representation(self, instance):
        return super(TyontekijaSerializer, self).to_representation(instance)

    def validate(self, data):
        if 'henkilo' in data:
            self.validate_henkilo_not_lapsi(data)

        # Validate only when updating existing henkilo
        if self.context['request'].method in ['PUT', 'PATCH']:
            instance = self.context['view'].get_object()
            if 'henkilo' in data:
                related_object_validations.check_if_henkilo_is_changed_new(self.context['request'].user,
                                                                           instance.henkilo.id,
                                                                           data['henkilo'].id)
            if 'vakajarjestaja' in data and data['vakajarjestaja'].id != instance.vakajarjestaja.id:
                msg = {'vakajarjestaja': ['Changing of vakajarjestaja is not allowed']}
                raise serializers.ValidationError(msg, code='invalid')

        return data

    def validate_henkilo_not_lapsi(self, data):
        if data['henkilo'].lapsi.exists():
            raise serializers.ValidationError({'henkilo': ['This henkilo is already referenced by lapsi objects']})


class TilapainenHenkilostoSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    vakajarjestaja = VakaJarjestajaHLField(view_name='vakajarjestaja-detail', required=False)
    vakajarjestaja_oid = OidRelatedField(object_type=VakaJarjestaja,
                                         parent_field='vakajarjestaja',
                                         parent_attribute='organisaatio_oid',
                                         prevalidator=validate_organisaatio_oid,
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
        if self.context['request'].method in ['PUT', 'PATCH']:
            instance = self.context['view'].get_object()
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
                                  prevalidator=validate_henkilo_oid,
                                  either_required=True)

    class Meta:
        model = Tutkinto
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('tutkinto')
    def to_representation(self, instance):
        return super(TutkintoSerializer, self).to_representation(instance)


class PalvelussuhdeSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.ReadOnlyField()
    tyontekija = TyontekijaHLField(view_name='tyontekija-detail')

    class Meta:
        model = Palvelussuhde
        exclude = ('changed_by', 'luonti_pvm')

    @caching_to_representation('palvelussuhde')
    def to_representation(self, instance):
        return super(PalvelussuhdeSerializer, self).to_representation(instance)

    def validate(self, data):
        # Validate only when updating existing
        if self.context['request'].method in ['PUT', 'PATCH']:
            instance = self.context['view'].get_object()
            related_object_validations.check_if_immutable_object_is_changed(instance, data, 'tyontekija')

        return data
