from rest_framework import serializers

from varda import related_object_validations
from varda.cache import caching_to_representation
from varda.models import Tyontekija, Henkilo, VakaJarjestaja
from varda.serializers import HenkiloHLField, VakaJarjestajaHLField
from varda.serializers_common import OidRelatedField
from varda.validators import validate_henkilo_oid, validate_organisaatio_oid


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
                msg = ({'vakajarjestaja': ['Changing of vakajarjestaja is not allowed']})
                raise serializers.ValidationError(msg, code='invalid')

        return data

    def validate_henkilo_not_lapsi(self, data):
        if data['henkilo'].lapsi.exists():
            raise serializers.ValidationError({'henkilo': 'This henkilo is already referenced by lapsi objects'})
