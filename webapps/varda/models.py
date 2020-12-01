import logging
from datetime import datetime, timedelta, timezone

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import CheckConstraint, UniqueConstraint, F, Q
import django.utils.timezone
from simple_history.models import HistoricalRecords

from varda import validators
from varda.constants import JARJESTAMISMUODOT_YKSITYINEN
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.batcherror_type import BatchErrorType
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.enums.ytj import YtjYritysmuoto

# Get an instance of a logger
logger = logging.getLogger(__name__)

"""
Preserve the order of the tables (to keep the logical structure coherent):
- Organization first
- Person next
- Miscellaneous at the bottom
"""


class VakaJarjestaja(models.Model):
    nimi = models.CharField(max_length=400, blank=False)
    y_tunnus = models.CharField(max_length=20, unique=False, validators=[validators.validate_y_tunnus])
    organisaatio_oid = models.CharField(max_length=50, unique=True, blank=True, null=True, validators=[validators.validate_organisaatio_oid])
    kunta_koodi = models.CharField(max_length=20, blank=False, validators=[validators.validate_kunta_koodi])
    sahkopostiosoite = models.CharField(max_length=200, blank=True, null=True, validators=[validators.validate_email])
    tilinumero = models.CharField(max_length=25, blank=True, validators=[validators.validate_IBAN_koodi])
    ipv4_osoitteet = ArrayField(models.CharField(max_length=20, blank=True, validators=[validators.validate_ipv4_address]), blank=True, null=True)
    ipv6_osoitteet = ArrayField(models.CharField(max_length=50, blank=True, validators=[validators.validate_ipv6_address]), blank=True, null=True)
    kayntiosoite = models.CharField(max_length=100, blank=True)
    kayntiosoite_postinumero = models.CharField(max_length=10, blank=True, validators=[validators.validate_postinumero])
    kayntiosoite_postitoimipaikka = models.CharField(max_length=50, blank=True)
    postiosoite = models.CharField(max_length=100, blank=False)
    postinumero = models.CharField(max_length=10, blank=False, validators=[validators.validate_postinumero])
    postitoimipaikka = models.CharField(max_length=50, blank=False)
    puhelinnumero = models.CharField(max_length=20, blank=True, validators=[validators.validate_puhelinnumero])
    ytjkieli = models.CharField(max_length=5, blank=True)
    yritysmuoto = models.CharField(choices=YtjYritysmuoto.choices(), max_length=50, blank=False,
                                   default='EI_YRITYSMUOTOA')
    alkamis_pvm = models.DateField(blank=True, null=True)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    integraatio_organisaatio = ArrayField(models.CharField(max_length=50))  # This is needed for permissions checking
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='vakajarjestajat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    @property
    def toimipaikat_top(self):
        items_to_show = 3
        return self.toimipaikat.all().order_by('id')[:items_to_show]

    @property
    def kunnallinen_kytkin(self):
        return self.yritysmuoto in VakaJarjestaja.get_kuntatyypit()

    @staticmethod
    def get_kuntatyypit():
        """
        Note: Lowercase!
        :return: List of yritysmuoto which belong to kunta in lowercase.
        """
        return [YtjYritysmuoto.KUNTA.name, YtjYritysmuoto.KUNTAYHTYMA.name]

    class Meta:
        verbose_name_plural = "vakajarjestajat"


class Toimipaikka(models.Model):
    vakajarjestaja = models.ForeignKey(VakaJarjestaja, related_name='toimipaikat', on_delete=models.PROTECT)
    nimi = models.CharField(max_length=200, blank=False)
    nimi_sv = models.CharField(max_length=200, blank=True)
    organisaatio_oid = models.CharField(max_length=50, blank=True, validators=[validators.validate_organisaatio_oid])
    kayntiosoite = models.CharField(max_length=100, blank=False)
    kayntiosoite_postinumero = models.CharField(max_length=10, blank=False, validators=[validators.validate_postinumero])
    kayntiosoite_postitoimipaikka = models.CharField(max_length=50, blank=False)
    postiosoite = models.CharField(max_length=100, blank=False)
    postinumero = models.CharField(max_length=20, blank=False, validators=[validators.validate_postinumero])
    postitoimipaikka = models.CharField(max_length=100, blank=False)
    kunta_koodi = models.CharField(max_length=20, blank=False, validators=[validators.validate_kunta_koodi])
    puhelinnumero = models.CharField(max_length=20, blank=False, validators=[validators.validate_puhelinnumero])
    sahkopostiosoite = models.CharField(max_length=200, blank=False, null=False, validators=[validators.validate_email])
    kasvatusopillinen_jarjestelma_koodi = models.CharField(max_length=100, blank=False, validators=[validators.validate_kasvatusopillinen_jarjestelma_koodi])
    toimintamuoto_koodi = models.CharField(max_length=50, blank=False, validators=[validators.validate_toimintamuoto_koodi])
    asiointikieli_koodi = ArrayField(models.CharField(max_length=50, blank=False, validators=[validators.validate_kieli_koodi]), blank=False, validators=[validators.validate_arrayfield])
    jarjestamismuoto_koodi = ArrayField(models.CharField(max_length=50, validators=[validators.validate_jarjestamismuoto_koodi]), blank=False, validators=[validators.validate_arrayfield])
    varhaiskasvatuspaikat = models.PositiveSmallIntegerField(blank=False, null=False)
    toiminnallinenpainotus_kytkin = models.BooleanField(default=False)
    kielipainotus_kytkin = models.BooleanField(default=False)
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='toimipaikat', on_delete=models.PROTECT)
    history = HistoricalRecords()
    hallinnointijarjestelma = models.CharField(choices=Hallinnointijarjestelma.choices(),
                                               max_length=50,
                                               default=Hallinnointijarjestelma.VARDA)

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    @property
    def varhaiskasvatussuhteet_top(self):
        items_to_show = 3
        return self.varhaiskasvatussuhteet.all().order_by('id')[:items_to_show]

    @property
    def toiminnallisetpainotukset_top(self):
        items_to_show = 3
        return self.toiminnallisetpainotukset.all().order_by('id')[:items_to_show]

    @property
    def kielipainotukset_top(self):
        items_to_show = 3
        return self.kielipainotukset.all().order_by('id')[:items_to_show]

    class Meta:
        verbose_name_plural = 'toimipaikat'
        constraints = [
            UniqueConstraint(fields=['nimi', 'vakajarjestaja'],
                             name='nimi_vakajarjestaja_unique_constraint')
        ]


class ToiminnallinenPainotus(models.Model):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name="toiminnallisetpainotukset", on_delete=models.PROTECT)
    toimintapainotus_koodi = models.CharField(max_length=6, blank=False, null=False, validators=[validators.validate_toimintapainotus_koodi])
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='toiminnallisetpainotukset', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "toiminnalliset painotukset"


class KieliPainotus(models.Model):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name="kielipainotukset", on_delete=models.PROTECT)
    kielipainotus_koodi = models.CharField(max_length=4, blank=False, null=False, validators=[validators.validate_kieli_koodi])
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='kielipainotukset', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "kielipainotukset"


class Henkilo(models.Model):
    henkilotunnus = models.CharField(max_length=120, blank=True)  # Currently encrypted hetu-length is 100 characters
    henkilotunnus_unique_hash = models.CharField(max_length=80, blank=True)  # This is used for checking uniqueness (64 characters)
    syntyma_pvm = models.DateField(default=None, blank=True, null=True)
    henkilo_oid = models.CharField(max_length=50, validators=[validators.validate_henkilo_oid])
    etunimet = models.CharField(max_length=100)
    kutsumanimi = models.CharField(max_length=100)
    sukunimi = models.CharField(max_length=100)
    turvakielto = models.BooleanField(default=False)
    vtj_yksiloity = models.BooleanField(default=False)
    vtj_yksilointi_yritetty = models.BooleanField(default=False)
    aidinkieli_koodi = models.CharField(max_length=20, blank=True)
    kotikunta_koodi = models.CharField(max_length=20, blank=True)
    sukupuoli_koodi = models.CharField(max_length=20, blank=True)
    katuosoite = models.CharField(max_length=100, blank=True)
    postinumero = models.CharField(max_length=20, blank=True)
    postitoimipaikka = models.CharField(max_length=100, blank=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='henkilot', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def remove_address_information(self):
        self.kotikunta_koodi = ''
        self.katuosoite = ''
        self.postinumero = ''
        self.postitoimipaikka = ''

    class Meta:
        verbose_name_plural = 'henkilöt'
        constraints = [
            UniqueConstraint(fields=['henkilo_oid', 'henkilotunnus_unique_hash'],
                             name='henkilo_oid_henkilotunnus_unique_hash_unique_constraint')
        ]


class Lapsi(models.Model):
    henkilo = models.ForeignKey(Henkilo, related_name='lapsi', on_delete=models.PROTECT)
    vakatoimija = models.ForeignKey(VakaJarjestaja, related_name='lapsi_vakatoimija', on_delete=models.PROTECT, null=True)
    oma_organisaatio = models.ForeignKey(VakaJarjestaja, related_name='paos_lapsi_oma_organisaatio', on_delete=models.PROTECT, null=True)
    paos_organisaatio = models.ForeignKey(VakaJarjestaja, related_name='paos_lapsi_paos_organisaatio', on_delete=models.PROTECT, null=True)
    paos_kytkin = models.BooleanField(default=False)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='lapset', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    @property
    def varhaiskasvatuspaatokset_top(self):
        items_to_show = 3
        return self.varhaiskasvatuspaatokset.all().order_by('id')[:items_to_show]

    @property
    def yksityinen_kytkin(self):
        """
        TODO: Use vakatoimija-field when it is set for all lapset https://jira.eduuni.fi/browse/CSCVARDA-1946
        :return: True if lapsi is yksityinen, otherwise False
        """
        vakapaatos = self.varhaiskasvatuspaatokset.first()
        return vakapaatos and vakapaatos.jarjestamismuoto_koodi.lower() in JARJESTAMISMUODOT_YKSITYINEN

    class Meta:
        verbose_name_plural = 'lapset'
        constraints = [
            CheckConstraint(check=~Q(oma_organisaatio=F('paos_organisaatio')),
                            name='oma_organisaatio_is_not_paos_organisaatio'),
        ]


class Huoltaja(models.Model):
    henkilo = models.OneToOneField(Henkilo, related_name='huoltaja', on_delete=models.PROTECT)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='huoltajat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "huoltajat"


class Varhaiskasvatuspaatos(models.Model):
    lapsi = models.ForeignKey(Lapsi, related_name='varhaiskasvatuspaatokset', on_delete=models.PROTECT)
    vuorohoito_kytkin = models.BooleanField(default=False)
    pikakasittely_kytkin = models.BooleanField(default=False)
    tuntimaara_viikossa = models.DecimalField(max_digits=4, decimal_places=1, blank=False, null=False, validators=[MinValueValidator(1.0), MaxValueValidator(120.0)])
    paivittainen_vaka_kytkin = models.BooleanField(null=True)
    kokopaivainen_vaka_kytkin = models.BooleanField(null=True)
    tilapainen_vaka_kytkin = models.BooleanField(default=False)
    jarjestamismuoto_koodi = models.CharField(max_length=50, blank=False, validators=[validators.validate_jarjestamismuoto_koodi])
    hakemus_pvm = models.DateField(blank=False, null=False, validators=[validators.validate_vaka_date])
    alkamis_pvm = models.DateField(blank=False, null=False, validators=[validators.validate_vaka_date])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_vaka_date])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='varhaiskasvatuspaatokset', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    @property
    def varhaiskasvatussuhteet_top(self):
        items_to_show = 3
        return self.varhaiskasvatussuhteet.all().order_by('id')[:items_to_show]

    class Meta:
        verbose_name_plural = "varhaiskasvatuspaatokset"


class Varhaiskasvatussuhde(models.Model):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name='varhaiskasvatussuhteet', on_delete=models.PROTECT)
    varhaiskasvatuspaatos = models.ForeignKey(Varhaiskasvatuspaatos, related_name='varhaiskasvatussuhteet', on_delete=models.PROTECT)
    alkamis_pvm = models.DateField(blank=False, null=False, validators=[validators.validate_vaka_date])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_vaka_date])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='varhaiskasvatussuhteet', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "varhaiskasvatussuhteet"


class Maksutieto(models.Model):
    yksityinen_jarjestaja = models.BooleanField(default=False)
    maksun_peruste_koodi = models.CharField(max_length=5, blank=False, validators=[validators.validate_maksun_peruste_koodi])
    palveluseteli_arvo = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, blank=True, null=True, validators=[MinValueValidator(0.0)])
    asiakasmaksu = models.DecimalField(max_digits=6, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(0.0)])
    perheen_koko = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(2), MaxValueValidator(50)])
    alkamis_pvm = models.DateField(blank=True, null=True, validators=[validators.validate_vaka_date])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_vaka_date])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='maksutiedot', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "maksutiedot"


class Huoltajuussuhde(models.Model):
    lapsi = models.ForeignKey(Lapsi, related_name='huoltajuussuhteet', on_delete=models.PROTECT)
    huoltaja = models.ForeignKey(Huoltaja, related_name="huoltajuussuhteet", on_delete=models.PROTECT)
    voimassa_kytkin = models.BooleanField(default=True)
    maksutiedot = models.ManyToManyField(Maksutieto, related_name="huoltajuussuhteet", blank=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='huoltajuussuhteet', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "huoltajuussuhteet"


class PaosToiminta(models.Model):
    oma_organisaatio = models.ForeignKey(VakaJarjestaja, related_name="paos_toiminnat_oma_organisaatio",
                                         on_delete=models.PROTECT)
    paos_organisaatio = models.ForeignKey(VakaJarjestaja, related_name="paos_toiminnat_paos_organisaatio",
                                          on_delete=models.PROTECT, null=True, blank=True)
    paos_toimipaikka = models.ForeignKey(Toimipaikka, related_name='paos_toiminnat_paos_toimipaikka',
                                         on_delete=models.PROTECT, null=True, blank=True)
    voimassa_kytkin = models.BooleanField(default=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='paos_toiminnat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "Paos-toiminnat"
        constraints = [
            UniqueConstraint(fields=['oma_organisaatio', 'paos_organisaatio'],
                             name='oma_organisaatio_paos_organisaatio_unique_constraint'),
            UniqueConstraint(fields=['oma_organisaatio', 'paos_toimipaikka'],
                             name='oma_organisaatio_paos_toimipaikka_unique_constraint')
        ]


class PaosOikeus(models.Model):
    jarjestaja_kunta_organisaatio = models.ForeignKey(VakaJarjestaja, related_name="paos_oikeudet_jarjestaja_kunta", on_delete=models.PROTECT)
    tuottaja_organisaatio = models.ForeignKey(VakaJarjestaja, related_name="paos_oikeudet_tuottaja", on_delete=models.PROTECT)
    tallentaja_organisaatio = models.ForeignKey(VakaJarjestaja, related_name="paos_oikeudet_tallentaja_organisaatio", on_delete=models.PROTECT)
    voimassa_kytkin = models.BooleanField(default=False)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='paos_oikeudet', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = "Paos-oikeudet"
        constraints = [
            UniqueConstraint(fields=['jarjestaja_kunta_organisaatio', 'tuottaja_organisaatio'],
                             name='jarjestaja_kunta_organisaatio_tuottaja_organisaatio_unique_constraint'),
            CheckConstraint(check=~Q(jarjestaja_kunta_organisaatio=F('tuottaja_organisaatio')),
                            name='jarjestaja_kunta_organisaatio_is_not_tuottaja_organisaatio_constraint'),
        ]


class Tyontekija(models.Model):
    henkilo = models.ForeignKey(Henkilo, related_name='tyontekijat', on_delete=models.PROTECT)
    vakajarjestaja = models.ForeignKey(VakaJarjestaja, related_name='tyontekijat', on_delete=models.PROTECT)
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(max_length=120, null=True, blank=True, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='tyontekijat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(Tyontekija, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, Tyontekija)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(Tyontekija, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'tyontekijat'
        constraints = [
            models.UniqueConstraint(fields=['henkilo', 'vakajarjestaja'], name='unique_tyontekija')
        ]


class TilapainenHenkilosto(models.Model):
    vakajarjestaja = models.ForeignKey(VakaJarjestaja, related_name='tilapainen_henkilosto', on_delete=models.PROTECT)
    kuukausi = models.DateField()
    tuntimaara = models.DecimalField(max_digits=6, decimal_places=2)
    tyontekijamaara = models.IntegerField()
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(max_length=120, null=True, blank=True, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='tilapainen_henkilosto', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(TilapainenHenkilosto, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, TilapainenHenkilosto)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(TilapainenHenkilosto, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'tilapainen henkilosto'


class Tutkinto(models.Model):
    henkilo = models.ForeignKey(Henkilo, related_name='tutkinnot', on_delete=models.PROTECT)
    vakajarjestaja = models.ForeignKey(VakaJarjestaja, related_name='tutkinnot', on_delete=models.PROTECT, null=True, blank=True)
    tutkinto_koodi = models.CharField(max_length=10, validators=[validators.validate_tutkinto_koodi])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='tutkinnot', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = 'tutkinnot'


class Palvelussuhde(models.Model):
    tyontekija = models.ForeignKey(Tyontekija, related_name='palvelussuhteet', on_delete=models.PROTECT)
    tyosuhde_koodi = models.CharField(max_length=50, validators=[validators.validate_tyosuhde_koodi])
    tyoaika_koodi = models.CharField(max_length=50, validators=[validators.validate_tyoaika_koodi])
    tutkinto_koodi = models.CharField(max_length=50, validators=[validators.validate_tutkinto_koodi])
    tyoaika_viikossa = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(1.0), MaxValueValidator(50.0)])
    alkamis_pvm = models.DateField()
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_palvelussuhde_paattymis_pvm])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])

    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='palvelussuhteet', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(Palvelussuhde, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, Palvelussuhde)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(Palvelussuhde, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'palvelussuhteet'


class Tyoskentelypaikka(models.Model):
    palvelussuhde = models.ForeignKey(Palvelussuhde, related_name='tyoskentelypaikat', on_delete=models.PROTECT)
    toimipaikka = models.ForeignKey(Toimipaikka, blank=True, null=True, related_name='tyoskentelypaikat', on_delete=models.PROTECT)
    tehtavanimike_koodi = models.CharField(max_length=120, validators=[validators.validate_tehtavanimike_koodi])
    kelpoisuus_kytkin = models.BooleanField()
    kiertava_tyontekija_kytkin = models.BooleanField()
    alkamis_pvm = models.DateField()
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])

    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='tyoskentelypaikat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(Tyoskentelypaikka, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, Tyoskentelypaikka)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(Tyoskentelypaikka, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'tyoskentelypaikat'


def paattymis_pvm_default():
    return '9999-01-01'


class PidempiPoissaolo(models.Model):
    palvelussuhde = models.ForeignKey(Palvelussuhde, related_name='pidemmatpoissaolot', on_delete=models.PROTECT)
    alkamis_pvm = models.DateField()
    paattymis_pvm = models.DateField(default=paattymis_pvm_default, validators=[validators.validate_pidempi_poissaolo_paattymis_pvm])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])

    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='pidemmatpoissaolot', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(PidempiPoissaolo, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, PidempiPoissaolo)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(PidempiPoissaolo, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'pidemmatpoissaolot'


class Taydennyskoulutus(models.Model):
    tyontekijat = models.ManyToManyField(Tyontekija, through='TaydennyskoulutusTyontekija', related_name='taydennyskoulutukset')
    nimi = models.CharField(max_length=120)
    suoritus_pvm = models.DateField(validators=[validators.validate_taydennyskoulutus_suoritus_pvm])
    koulutuspaivia = models.DecimalField(max_digits=4, decimal_places=1, validators=[validators.create_validate_decimal_steps('0.5'),
                                                                                     MaxValueValidator(160)])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='taydennyskoulutukset', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    def validate_unique(self, *args, **kwargs):
        super(Taydennyskoulutus, self).validate_unique(*args, **kwargs)
        validators.validate_unique_lahdejarjestelma_tunniste_pair(self, Taydennyskoulutus)

    def save(self, *args, **kwargs):
        self.validate_unique()
        super(Taydennyskoulutus, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'taydennyskoulutukset'


class TaydennyskoulutusTyontekija(models.Model):
    tyontekija = models.ForeignKey(Tyontekija, related_name='taydennyskoulutukset_tyontekijat', on_delete=models.PROTECT)
    taydennyskoulutus = models.ForeignKey(Taydennyskoulutus, related_name='taydennyskoulutukset_tyontekijat', on_delete=models.PROTECT)
    tehtavanimike_koodi = models.CharField(max_length=20, validators=[validators.validate_tehtavanimike_koodi])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey('auth.User', related_name='taydennyskoulutukset_tyontekijat', on_delete=models.PROTECT)
    history = HistoricalRecords()

    def __str__(self):
        return str(self.id)

    @property
    def audit_loggable(self):
        return True

    @property
    def _history_user(self):
        return self.changed_by

    @_history_user.setter
    def _history_user(self, value):
        self.changed_by = value

    class Meta:
        verbose_name_plural = 'taydennyskoulutukset tyontekijat'


class Aikaleima(models.Model):
    """
    Simple state for regular tasks to hold last update information
    """
    avain = models.TextField(choices=AikaleimaAvain.choices(),
                             null=False,
                             unique=True)
    aikaleima = models.DateTimeField(default=django.utils.timezone.now)

    class Meta:
        verbose_name_plural = "aikaleimat"


class LogData(models.Model):
    """
    Simple state for log data related things
    """
    log_type = models.CharField(max_length=100, blank=False, primary_key=True)
    log_seq = models.BigIntegerField(default=0)

    class Meta:
        verbose_name_plural = "log data"


class BatchError(models.Model):
    """
    For storing errors in scheduled batches and allowing retries.
    """
    type = models.TextField(choices=BatchErrorType.choices(),
                            null=False)
    henkilo = models.ForeignKey(Henkilo, related_name='batcherrors', on_delete=models.PROTECT)
    retry_time = models.DateTimeField(default=django.utils.timezone.now)
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField()

    class Meta:
        verbose_name_plural = "batcherrors"

    def update_next_retry(self):
        """
        Updates object instance retry_time and retry_count to match the next retry
        :return: None
        """
        next_retry_in_days = 2 ** self.retry_count  # 1,2,4,8,...
        next_retry_time = datetime.now(tz=timezone.utc) + timedelta(days=next_retry_in_days)
        self.retry_time = next_retry_time
        self.retry_count += 1
        if self.retry_count == 5:
            logger.warning('Very high retry_count for BatchError {}'.format(self.id))


"""
Miscellaneous

Z(n) where n is a growing integer. Otherwise problems in migrations with CreateModel.

'Could not load contenttypes.ContentType(pk=22): duplicate key value violates unique constraint "django_content_type_app_label_model_76bd3d3b_uniq"'
"""


class Z1_OphAuthentication(models.Model):
    ticketing_granting_ticket = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = "OPH autentikaatio"


def maksun_peruste_koodit_default():
    return ['mp01', 'mp02', 'mp03']


def lahdejarjestelma_koodit_default():
    return ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15']


def tutkinto_koodit_default():
    return ['001', '002', '003', '321901', '371101', '371168', '371169', '374114', '381204', '381241', '384246',
            '511501', '571201', '571254', '612101', '612102', '612103', '612104', '612105', '612107', '612108',
            '612199', '612201', '612202', '612203', '612204', '612205', '612299', '612999', '613101', '613201',
            '613352', '613353', '613354', '613355', '613356', '613357', '613399', '613401', '613402', '613501',
            '613652', '613952', '613999', '671201', '712101', '712102', '712104', '712105', '712108', '712109',
            '712199', '712201', '712202', '712203', '712204', '712205', '712299', '719951', '719999', '771301',
            '812101', '812102', '812103', '815101', '815102', '815103']


class Z2_Koodisto(models.Model):
    name = models.CharField(max_length=256, unique=True)
    name_koodistopalvelu = models.CharField(max_length=256, unique=True)
    version = models.IntegerField()
    update_datetime = models.DateTimeField()

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = 'Varda koodistot'


class Z2_Code(models.Model):
    koodisto = models.ForeignKey(Z2_Koodisto, related_name='codes', on_delete=models.PROTECT)
    code_value = models.CharField(max_length=256)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = 'Varda codes'
        constraints = [
            models.UniqueConstraint(fields=['koodisto', 'code_value'], name='koodisto_code_value_unique_constraint')
        ]


class Z2_CodeTranslation(models.Model):
    code = models.ForeignKey(Z2_Code, related_name='translations', on_delete=models.PROTECT)
    language = models.CharField(max_length=10)
    name = models.CharField(max_length=256, blank=True)
    description = models.CharField(max_length=2048, blank=True)
    short_name = models.CharField(max_length=256, blank=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = 'Varda code translations'
        constraints = [
            models.UniqueConstraint(fields=['code', 'language'], name='code_language_unique_constraint')
        ]


class Z3_AdditionalCasUserFields(models.Model):
    user = models.OneToOneField(User, related_name='additional_user_info', on_delete=models.PROTECT, primary_key=True)
    kayttajatyyppi = models.CharField(max_length=50, blank=True)
    henkilo_oid = models.CharField(max_length=50, blank=True, validators=[validators.validate_henkilo_oid])
    asiointikieli_koodi = models.CharField(max_length=3, blank=True)
    approved_oph_staff = models.BooleanField(default=False)
    last_modified = models.DateTimeField(auto_now=True)
    huoltaja_oid = models.CharField(max_length=50, blank=True, null=True, validators=[validators.validate_henkilo_oid])

    def __str__(self):
        return str(self.user_id)

    class Meta:
        verbose_name_plural = 'Additional user fields'


class Z4_CasKayttoOikeudet(models.Model):
    PAAKAYTTAJA = 'VARDA-PAAKAYTTAJA'
    TALLENTAJA = 'VARDA-TALLENTAJA'
    KATSELIJA = 'VARDA-KATSELIJA'
    PALVELUKAYTTAJA = 'VARDA-PALVELUKAYTTAJA'
    HUOLTAJATIEDOT_TALLENTAJA = 'HUOLTAJATIETO_TALLENNUS'
    HUOLTAJATIEDOT_KATSELIJA = 'HUOLTAJATIETO_KATSELU'
    HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA = 'HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA'
    HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA = 'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA'
    HENKILOSTO_TILAPAISET_KATSELIJA = 'HENKILOSTO_TILAPAISET_KATSELIJA'
    HENKILOSTO_TILAPAISET_TALLENTAJA = 'HENKILOSTO_TILAPAISET_TALLENTAJA'
    HENKILOSTO_TYONTEKIJA_KATSELIJA = 'HENKILOSTO_TYONTEKIJA_KATSELIJA'
    HENKILOSTO_TYONTEKIJA_TALLENTAJA = 'HENKILOSTO_TYONTEKIJA_TALLENTAJA'
    # No use case for TOIMIJATIEDOT_KATSELIJA
    TOIMIJATIEDOT_KATSELIJA = 'VARDA_TOIMIJATIEDOT_KATSELIJA'
    TOIMIJATIEDOT_TALLENTAJA = 'VARDA_TOIMIJATIEDOT_TALLENTAJA'
    KAYTTOOIKEUSROOLIT = (
        (PAAKAYTTAJA, 'Varda-Pääkäyttäjä'),
        (TALLENTAJA, 'Varda-Tallentaja'),
        (KATSELIJA, 'Varda-Katselija'),
        (PALVELUKAYTTAJA, 'Varda-Palvelukäyttäjä'),
        (HUOLTAJATIEDOT_TALLENTAJA, 'Varda-Huoltajatietojen tallentaja'),
        (HUOLTAJATIEDOT_KATSELIJA, 'Varda-Huoltajatietojen katselija'),
        (HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA, 'Varda-Täydennyskoulutustietojen katselija'),
        (HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA, 'Varda-Täydennyskoulutustietojen tallentaja'),
        (HENKILOSTO_TILAPAISET_KATSELIJA, 'Varda-Tilapäisen henkilöstön katselija'),
        (HENKILOSTO_TILAPAISET_TALLENTAJA, 'Varda-Tilapäisen henkilöstön tallentaja'),
        (HENKILOSTO_TYONTEKIJA_KATSELIJA, 'Varda-Työntekijätietojen katselija'),
        (HENKILOSTO_TYONTEKIJA_TALLENTAJA, 'Varda-Työntekijätietojen tallentaja'),
        (TOIMIJATIEDOT_KATSELIJA, 'Varda-Toimijatietojen katselija'),
        (TOIMIJATIEDOT_TALLENTAJA, 'Varda-Toimijatietojen tallentaja'),
    )

    user = models.ForeignKey(User, related_name='kayttooikeudet', on_delete=models.PROTECT)
    organisaatio_oid = models.CharField(max_length=50, blank=True, validators=[validators.validate_organisaatio_oid])
    kayttooikeus = models.CharField(max_length=50, choices=KAYTTOOIKEUSROOLIT, blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = 'Kayttooikeudet'


class Z5_AuditLog(models.Model):
    user = models.ForeignKey(User, related_name='audit_log', on_delete=models.PROTECT)
    time_of_event = models.DateTimeField(auto_now=True)
    successful_get_request_path = models.CharField(max_length=100, blank=False)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name_plural = 'Audit log'
