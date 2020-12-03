from rest_framework import serializers
from varda.models import Varhaiskasvatussuhde
from varda.misc import decrypt_henkilotunnus

"""
Serializers for query-results used in reports
"""


class KelaEtuusmaksatusAloittaneetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='A', initial='A')
    vakasuhde_alkamis_pvm = serializers.DateField(source='alkamis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkamis_pvm']


class KelaEtuusmaksatusLopettaneetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='L', initial='L')
    vakasuhde_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusMaaraaikaisetSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='M', initial='M')
    vakasuhde_alkamis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkamis_pvm', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusKorjaustiedotSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.DateField(source='new_alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='new_paattymis_pvm')
    vakasuhde_alkuperainen_alkamis_pvm = serializers.SerializerMethodField()
    vakasuhde_alkuperainen_paattymis_pvm = serializers.SerializerMethodField()

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    def get_vakasuhde_alkuperainen_alkamis_pvm(self, data):
        if data['new_alkamis_pvm'].year == 1:
            return '0001-01-01'
        return data['alkamis_pvm']

    def get_vakasuhde_alkuperainen_paattymis_pvm(self, data):
        if data['new_paattymis_pvm'] is not None and data['new_paattymis_pvm'].year == 1:
            return '0001-01-01'
        return data['paattymis_pvm']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkuperainen_alkamis_pvm',
                  'vakasuhde_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm', 'vakasuhde_paattymis_pvm']


class KelaEtuusmaksatusKorjaustiedotPoistetutSerializer(serializers.Serializer):
    kotikunta_koodi = serializers.SerializerMethodField()
    henkilotunnus = serializers.SerializerMethodField()
    tietue = serializers.CharField(default='K', initial='K')
    vakasuhde_alkamis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_paattymis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.DateField(source='paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    class Meta:
        model = Varhaiskasvatussuhde
        fields = ['henkilotunnus', 'kotikunta_koodi', 'tietue', 'vakasuhde_alkuperainen_alkamis_pvm',
                  'vakasuhde_alkamis_pvm', 'vakasuhde_alkuperainen_paattymis_pvm', 'vakasuhde_paattymis_pvm']


class TiedonsiirtotilastoSerializer(serializers.Serializer):
    vakatoimijat = serializers.IntegerField()
    toimipaikat = serializers.IntegerField()
    vakasuhteet = serializers.IntegerField()
    vakapaatokset = serializers.IntegerField()
    lapset = serializers.IntegerField()
    maksutiedot = serializers.IntegerField()
    kielipainotukset = serializers.IntegerField()
    toiminnalliset_painotukset = serializers.IntegerField()
    paos_oikeudet = serializers.ReadOnlyField()
