from rest_framework import serializers
from varda.models import Varhaiskasvatussuhde, Lapsi, Tyontekija
from varda.misc import decrypt_henkilotunnus


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
    vakasuhde_alkamis_pvm = serializers.SerializerMethodField()
    vakasuhde_paattymis_pvm = serializers.SerializerMethodField()
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='old_alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.DateField(source='old_paattymis_pvm')

    def get_henkilotunnus(self, data):
        return decrypt_henkilotunnus(data['varhaiskasvatuspaatos__lapsi__henkilo__henkilotunnus'])

    def get_kotikunta_koodi(self, data):
        return data['varhaiskasvatuspaatos__lapsi__henkilo__kotikunta_koodi']

    def get_vakasuhde_alkamis_pvm(self, data):
        if data['old_alkamis_pvm'].year == 1:
            return '0001-01-01'
        return data['alkamis_pvm']

    def get_vakasuhde_paattymis_pvm(self, data):
        if data['old_paattymis_pvm'] is not None and data['old_paattymis_pvm'].year == 1:
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
    vakasuhde_alkuperainen_alkamis_pvm = serializers.DateField(source='old_alkamis_pvm')
    vakasuhde_alkuperainen_paattymis_pvm = serializers.DateField(source='old_paattymis_pvm')

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


class AbstractErrorReportSerializer(serializers.ModelSerializer):
    henkilo_id = serializers.ReadOnlyField(source='henkilo.id')
    henkilo_oid = serializers.ReadOnlyField(source='henkilo.henkilo_oid')
    etunimet = serializers.ReadOnlyField(source='henkilo.etunimet')
    sukunimi = serializers.ReadOnlyField(source='henkilo.sukunimi')
    errors = serializers.SerializerMethodField()

    def get_errors(self, obj):
        """
        This function parses the list of errors from different error attributes in the Lapsi/Tyontekija object.
        :param obj: Lapsi/Tyontekija object with annotated errors
        :return: list of errors
        """
        error_list = []
        for error_key, error_tuple in self.context['view'].get_error_tuples().items():
            error_attr = getattr(obj, error_key.value['error_code'], '')
            if error_attr != '':
                model_id_list = error_attr.split(',')
                error_list.append({
                    **error_key.value,
                    'model_name': error_tuple[1],
                    'model_id_list': [int(model_id) for model_id in set(model_id_list)]
                })
        return error_list


class ErrorReportLapsetSerializer(AbstractErrorReportSerializer):
    lapsi_id = serializers.ReadOnlyField(source='id')
    oma_organisaatio_id = serializers.ReadOnlyField(source='oma_organisaatio.id')
    oma_organisaatio_oid = serializers.ReadOnlyField(source='oma_organisaatio.organisaatio_oid')
    oma_organisaatio_nimi = serializers.ReadOnlyField(source='oma_organisaatio.nimi')
    paos_organisaatio_id = serializers.ReadOnlyField(source='paos_organisaatio.id')
    paos_organisaatio_oid = serializers.ReadOnlyField(source='paos_organisaatio.organisaatio_oid')
    paos_organisaatio_nimi = serializers.ReadOnlyField(source='paos_organisaatio.nimi')

    class Meta:
        model = Lapsi
        fields = ('lapsi_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi',
                  'oma_organisaatio_id', 'oma_organisaatio_oid', 'oma_organisaatio_nimi',
                  'paos_organisaatio_id', 'paos_organisaatio_oid', 'paos_organisaatio_nimi',
                  'errors')


class ErrorReportTyontekijatSerializer(AbstractErrorReportSerializer):
    tyontekija_id = serializers.ReadOnlyField(source='id')

    class Meta:
        model = Tyontekija
        fields = ('tyontekija_id', 'henkilo_id', 'henkilo_oid', 'etunimet', 'sukunimi', 'errors')
