import logging
from datetime import datetime, timedelta, timezone

import django.utils.timezone
from django.contrib.auth.models import Group, User
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import IntegrityError, models
from django.db.models import CheckConstraint, F, Index, Q, UniqueConstraint
from rest_framework.exceptions import ValidationError
from simple_history.models import HistoricalRecords

from varda import validators
from varda.constants import YRITYSMUOTO_KUNTA
from varda.enums.batcherror_type import BatchErrorType
from varda.enums.error_messages import ErrorMessages
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.enums.organisaatiotyyppi import Organisaatiotyyppi

logger = logging.getLogger(__name__)


"""
Preserve the order of the tables (to keep the logical structure coherent):
1. Organizations
2. Child models
3. Employee models
4. Miscellaneous models
"""


class AbstractModel(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        return str(self.pk)

    @classmethod
    def get_name(cls):
        return cls.__name__.lower()


def get_history_user(request, **kwargs):
    """
    Override simple_history.models._default_get_user. If user cannot be determined
    from authenticated request, set user as varda_system user (e.g. periodic tasks).
    """
    try:
        user = request.user
    except AttributeError:
        user = None

    if not user:
        user = User.objects.filter(username='varda_system').first()
    return user


class HistoryAbstractModel(AbstractModel):
    history = HistoricalRecords(inherit=True, get_user=get_history_user)

    class Meta:
        abstract = True


class UniqueLahdejarjestelmaTunnisteMixin:
    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError as integrity_error:
            if 'lahdejarjestelma_tunniste_unique' in str(integrity_error):
                raise ValidationError({'errors': [ErrorMessages.MI013.value]})
            raise integrity_error


class CustomOrganisaatioManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(organisaatiotyyppi__contains=[Organisaatiotyyppi.VAKAJARJESTAJA.value])


class Organisaatio(HistoryAbstractModel):
    nimi = models.CharField(max_length=400, blank=False)
    y_tunnus = models.CharField(max_length=20, unique=False, validators=[validators.validate_y_tunnus])
    organisaatio_oid = models.CharField(max_length=50, unique=True, blank=True, null=True, validators=[validators.validate_organisaatio_oid])
    kunta_koodi = models.CharField(max_length=20, blank=False, validators=[validators.validate_kunta_koodi])
    sahkopostiosoite = models.CharField(max_length=200, blank=True, null=True, validators=[validators.validate_email])
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
    yritysmuoto = models.CharField(max_length=4, blank=False, default='0', validators=[validators.validate_yritysmuoto_koodi])
    alkamis_pvm = models.DateField(blank=True, null=True)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    integraatio_organisaatio = ArrayField(models.CharField(max_length=50), blank=True)  # This is needed for permissions checking
    organisaatiotyyppi = ArrayField(models.CharField(max_length=50), default=list)
    client_cert_common_name = models.CharField(max_length=50, blank=True, null=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    vakajarjestajat = CustomOrganisaatioManager()

    @property
    def toimipaikat_top(self):
        items_to_show = 3
        return self.toimipaikat.all().order_by('id')[:items_to_show]

    @property
    def kunnallinen_kytkin(self):
        return self.yritysmuoto in Organisaatio.get_kuntatyypit()

    @staticmethod
    def get_kuntatyypit():
        """
        Note: Lowercase!
        :return: List of yritysmuoto which belong to kunta in lowercase.
        """
        return YRITYSMUOTO_KUNTA

    class Meta:
        verbose_name_plural = 'organisaatiot'


class Toimipaikka(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='toimipaikat', on_delete=models.PROTECT)
    nimi = models.CharField(max_length=200, blank=False)
    nimi_sv = models.CharField(max_length=200, blank=True)
    organisaatio_oid = models.CharField(max_length=50, blank=True, validators=[validators.validate_organisaatio_oid])
    kayntiosoite = models.CharField(max_length=100, blank=False)
    kayntiosoite_postinumero = models.CharField(max_length=10, blank=False, validators=[validators.validate_postinumero_toimipaikka])
    kayntiosoite_postitoimipaikka = models.CharField(max_length=50, blank=False)
    postiosoite = models.CharField(max_length=100, blank=False)
    postinumero = models.CharField(max_length=20, blank=False, validators=[validators.validate_postinumero_toimipaikka])
    postitoimipaikka = models.CharField(max_length=100, blank=False)
    kunta_koodi = models.CharField(max_length=20, blank=False, validators=[validators.validate_kunta_koodi])
    puhelinnumero = models.CharField(max_length=20, blank=False, validators=[validators.validate_puhelinnumero])
    sahkopostiosoite = models.CharField(max_length=200, blank=False, null=False, validators=[validators.validate_email])
    kasvatusopillinen_jarjestelma_koodi = models.CharField(max_length=100, blank=False, validators=[validators.validate_kasvatusopillinen_jarjestelma_koodi])
    toimintamuoto_koodi = models.CharField(max_length=50, blank=False, validators=[validators.validate_toimintamuoto_koodi])
    toimintakieli_koodi = ArrayField(models.CharField(max_length=50, blank=False, validators=[validators.validate_kieli_koodi]), blank=False, validators=[validators.validate_arrayfield])
    jarjestamismuoto_koodi = ArrayField(models.CharField(max_length=50, validators=[validators.validate_jarjestamismuoto_koodi]), blank=False, validators=[validators.validate_arrayfield])
    varhaiskasvatuspaikat = models.PositiveSmallIntegerField(blank=False, null=False)
    toiminnallinenpainotus_kytkin = models.BooleanField(default=False)
    kielipainotus_kytkin = models.BooleanField(default=False)
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    hallinnointijarjestelma = models.CharField(choices=Hallinnointijarjestelma.choices(),
                                               max_length=50,
                                               default=Hallinnointijarjestelma.VARDA)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

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
            UniqueConstraint(fields=['nimi', 'vakajarjestaja'], name='nimi_vakajarjestaja_unique_constraint'),
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='toimipaikka_lahdejarjestelma_tunniste_unique_constraint')
        ]


class ToiminnallinenPainotus(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name='toiminnallisetpainotukset', on_delete=models.PROTECT)
    toimintapainotus_koodi = models.CharField(max_length=6, blank=False, null=False, validators=[validators.validate_toimintapainotus_koodi])
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'toiminnalliset painotukset'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='toiminnallinen_painotus_lahdejarjestelma_tunniste_unique_constraint')
        ]


class KieliPainotus(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name='kielipainotukset', on_delete=models.PROTECT)
    kielipainotus_koodi = models.CharField(max_length=4, blank=False, null=False, validators=[validators.validate_kieli_koodi])
    kielipainotustyyppi_koodi = models.CharField(max_length=4, blank=False, null=True, validators=[validators.validate_kielipainotustyyppi_koodi])
    alkamis_pvm = models.DateField(blank=False, null=False)
    paattymis_pvm = models.DateField(default=None, blank=True, null=True)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'kielipainotukset'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='kielipainotus_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Henkilo(HistoryAbstractModel):
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

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError as integrity_error:
            if 'henkilo_henkilotunnus_unique_hash_unique_constraint' in str(integrity_error):
                validation_error = ValidationError({'henkilotunnus': [ErrorMessages.HE014.value]})
                validation_error.duplicate_identifier = self.henkilotunnus_unique_hash
                raise validation_error
            elif 'henkilo_oid_unique_constraint' in str(integrity_error):
                validation_error = ValidationError({'henkilo_oid': [ErrorMessages.HE015.value]})
                validation_error.duplicate_identifier = self.henkilo_oid
                raise validation_error
            raise integrity_error

    def remove_address_information(self):
        self.kotikunta_koodi = ''
        self.katuosoite = ''
        self.postinumero = ''
        self.postitoimipaikka = ''

    class Meta:
        verbose_name_plural = 'henkilöt'
        constraints = [
            UniqueConstraint(fields=['henkilotunnus_unique_hash'], condition=~Q(henkilotunnus_unique_hash=''),
                             name='henkilo_henkilotunnus_unique_hash_unique_constraint'),
            UniqueConstraint(fields=['henkilo_oid'], condition=~Q(henkilo_oid=''),
                             name='henkilo_oid_unique_constraint')
        ]


class Lapsi(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    henkilo = models.ForeignKey(Henkilo, related_name='lapsi', on_delete=models.PROTECT)
    vakatoimija = models.ForeignKey(Organisaatio, related_name='lapsi_vakatoimija', on_delete=models.PROTECT, null=True)
    oma_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_lapsi_oma_organisaatio', on_delete=models.PROTECT, null=True)
    paos_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_lapsi_paos_organisaatio', on_delete=models.PROTECT, null=True)
    paos_kytkin = models.BooleanField(default=False)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    @property
    def varhaiskasvatuspaatokset_top(self):
        items_to_show = 3
        return self.varhaiskasvatuspaatokset.all().order_by('id')[:items_to_show]

    @property
    def yksityinen_kytkin(self):
        """
        :return: True if lapsi is yksityinen, otherwise False
        """
        organisaatio = self.vakatoimija or self.oma_organisaatio
        return not organisaatio.kunnallinen_kytkin

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError as integrity_error:
            if 'lapsi_vakatoimija_unique_constraint' in str(integrity_error):
                raise ValidationError({'errors': [ErrorMessages.LA009.value]})
            elif 'lapsi_paos_unique_constraint' in str(integrity_error):
                raise ValidationError({'errors': [ErrorMessages.LA010.value]})
            raise integrity_error

    class Meta:
        verbose_name_plural = 'lapset'
        constraints = [
            CheckConstraint(check=~Q(oma_organisaatio=F('paos_organisaatio')),
                            name='oma_organisaatio_is_not_paos_organisaatio'),
            UniqueConstraint(fields=['henkilo', 'vakatoimija'], condition=Q(vakatoimija__isnull=False),
                             name='lapsi_vakatoimija_unique_constraint'),
            UniqueConstraint(fields=['henkilo', 'oma_organisaatio', 'paos_organisaatio'],
                             condition=Q(oma_organisaatio__isnull=False) & Q(paos_organisaatio__isnull=False),
                             name='lapsi_paos_unique_constraint'),
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='lapsi_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Huoltaja(HistoryAbstractModel):
    henkilo = models.OneToOneField(Henkilo, related_name='huoltaja', on_delete=models.PROTECT)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'huoltajat'


class Varhaiskasvatuspaatos(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
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
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    @property
    def varhaiskasvatussuhteet_top(self):
        items_to_show = 3
        return self.varhaiskasvatussuhteet.all().order_by('id')[:items_to_show]

    class Meta:
        verbose_name_plural = 'varhaiskasvatuspaatokset'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='vakapaatos_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Varhaiskasvatussuhde(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    toimipaikka = models.ForeignKey(Toimipaikka, related_name='varhaiskasvatussuhteet', on_delete=models.PROTECT)
    varhaiskasvatuspaatos = models.ForeignKey(Varhaiskasvatuspaatos, related_name='varhaiskasvatussuhteet', on_delete=models.PROTECT)
    alkamis_pvm = models.DateField(blank=False, null=False, validators=[validators.validate_vaka_date])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_vaka_date])
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'varhaiskasvatussuhteet'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='vakasuhde_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Maksutieto(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    yksityinen_jarjestaja = models.BooleanField(default=False)
    maksun_peruste_koodi = models.CharField(max_length=5, blank=False, validators=[validators.validate_maksun_peruste_koodi])
    palveluseteli_arvo = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, blank=True, null=True, validators=[MinValueValidator(0.0)])
    asiakasmaksu = models.DecimalField(max_digits=6, decimal_places=2, blank=False, null=False, validators=[MinValueValidator(0.0)])
    perheen_koko = models.IntegerField(blank=True, null=True, validators=[MinValueValidator(2), MaxValueValidator(50)])
    alkamis_pvm = models.DateField(blank=True, null=True, validators=[validators.validate_vaka_date])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_vaka_date])
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'maksutiedot'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='maksutieto_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Huoltajuussuhde(HistoryAbstractModel):
    lapsi = models.ForeignKey(Lapsi, related_name='huoltajuussuhteet', on_delete=models.PROTECT)
    huoltaja = models.ForeignKey(Huoltaja, related_name='huoltajuussuhteet', on_delete=models.PROTECT)
    voimassa_kytkin = models.BooleanField(default=True)
    maksutiedot = models.ManyToManyField(Maksutieto, related_name='huoltajuussuhteet', through='MaksutietoHuoltajuussuhde', blank=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'huoltajuussuhteet'


class MaksutietoHuoltajuussuhde(HistoryAbstractModel):
    huoltajuussuhde = models.ForeignKey(Huoltajuussuhde, related_name='maksutiedot_huoltajuussuhteet', on_delete=models.PROTECT)
    maksutieto = models.ForeignKey(Maksutieto, related_name='maksutiedot_huoltajuussuhteet', on_delete=models.PROTECT)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'maksutiedot huoltajuussuhteet'


class PaosToiminta(HistoryAbstractModel):
    oma_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_toiminnat_oma_organisaatio',
                                         on_delete=models.PROTECT)
    paos_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_toiminnat_paos_organisaatio',
                                          on_delete=models.PROTECT, null=True, blank=True)
    paos_toimipaikka = models.ForeignKey(Toimipaikka, related_name='paos_toiminnat_paos_toimipaikka',
                                         on_delete=models.PROTECT, null=True, blank=True)
    voimassa_kytkin = models.BooleanField(default=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Paos-toiminnat'
        constraints = [
            UniqueConstraint(fields=['oma_organisaatio', 'paos_organisaatio'],
                             name='oma_organisaatio_paos_organisaatio_unique_constraint'),
            UniqueConstraint(fields=['oma_organisaatio', 'paos_toimipaikka'],
                             name='oma_organisaatio_paos_toimipaikka_unique_constraint')
        ]


class PaosOikeus(HistoryAbstractModel):
    jarjestaja_kunta_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_oikeudet_jarjestaja_kunta', on_delete=models.PROTECT)
    tuottaja_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_oikeudet_tuottaja', on_delete=models.PROTECT)
    tallentaja_organisaatio = models.ForeignKey(Organisaatio, related_name='paos_oikeudet_tallentaja_organisaatio', on_delete=models.PROTECT)
    voimassa_kytkin = models.BooleanField(default=False)
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Paos-oikeudet'
        constraints = [
            UniqueConstraint(fields=['jarjestaja_kunta_organisaatio', 'tuottaja_organisaatio'],
                             name='jarjestaja_kunta_organisaatio_tuottaja_organisaatio_unique_constraint'),
            CheckConstraint(check=~Q(jarjestaja_kunta_organisaatio=F('tuottaja_organisaatio')),
                            name='jarjestaja_kunta_organisaatio_is_not_tuottaja_organisaatio_constraint'),
        ]


class Tyontekija(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    henkilo = models.ForeignKey(Henkilo, related_name='tyontekijat', on_delete=models.PROTECT)
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='tyontekijat', on_delete=models.PROTECT)
    sahkopostiosoite = models.CharField(max_length=200, blank=True, null=True, validators=[validators.validate_email])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(max_length=120, null=True, blank=True, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError as integrity_error:
            if 'unique_tyontekija' in str(integrity_error):
                raise ValidationError({'errors': [ErrorMessages.TY005.value]})
            raise integrity_error

    class Meta:
        verbose_name_plural = 'tyontekijat'
        constraints = [
            models.UniqueConstraint(fields=['henkilo', 'vakajarjestaja'], name='unique_tyontekija'),
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='tyontekija_lahdejarjestelma_tunniste_unique_constraint')
        ]


class VuokrattuHenkilosto(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='vuokrattu_henkilosto', on_delete=models.PROTECT)
    kuukausi = models.DateField()
    tuntimaara = models.DecimalField(max_digits=8, decimal_places=2)
    tyontekijamaara = models.IntegerField()
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(max_length=120, null=True, blank=True, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'vuokrattu henkilosto'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='vuokrattu_henkilosto_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Tukipaatos(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='tukipaatos', on_delete=models.PROTECT)
    paatosmaara = models.PositiveIntegerField(default=0)
    yksityinen_jarjestaja = models.BooleanField(default=False)
    ikaryhma_koodi = models.CharField(max_length=20, validators=[validators.validate_ikaryhma_koodi])
    tuentaso_koodi = models.CharField(max_length=10, validators=[validators.validate_tuentaso_koodi])
    tilastointi_pvm = models.DateField()
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(max_length=120, null=True, blank=True, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.ikaryhma_koodi = self.ikaryhma_koodi.upper()
        self.tuentaso_koodi = self.tuentaso_koodi.upper()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'tukipaatokset'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='tukipaatos_lahdejarjestelma_tunniste_unique_constraint'),
        ]


class TukipaatosAikavali(HistoryAbstractModel):
    alkamis_pvm = models.DateField()
    paattymis_pvm = models.DateField()
    tilastointi_pvm = models.DateField()
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'tukipaatos aikavalit'


class Tutkinto(HistoryAbstractModel):
    henkilo = models.ForeignKey(Henkilo, related_name='tutkinnot', on_delete=models.PROTECT)
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='tutkinnot', on_delete=models.PROTECT, null=True, blank=True)
    tutkinto_koodi = models.CharField(max_length=10, validators=[validators.validate_tutkinto_koodi])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        try:
            super().save(*args, **kwargs)
        except IntegrityError as integrity_error:
            if 'unique_tutkinto' in str(integrity_error):
                raise ValidationError({'errors': [ErrorMessages.TU005.value]})
            raise integrity_error

    class Meta:
        verbose_name_plural = 'tutkinnot'
        constraints = [
            UniqueConstraint(fields=['henkilo', 'vakajarjestaja', 'tutkinto_koodi'], name='unique_tutkinto'),
        ]


class Palvelussuhde(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    tyontekija = models.ForeignKey(Tyontekija, related_name='palvelussuhteet', on_delete=models.PROTECT)
    tyosuhde_koodi = models.CharField(max_length=50, validators=[validators.validate_tyosuhde_koodi])
    tyoaika_koodi = models.CharField(max_length=50, validators=[validators.validate_tyoaika_koodi])
    tutkinto_koodi = models.CharField(max_length=50, validators=[validators.validate_tutkinto_koodi])
    tyoaika_viikossa = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(0.0), MaxValueValidator(50.0)])
    alkamis_pvm = models.DateField(validators=[validators.validate_palvelussuhde_alkamis_pvm])
    paattymis_pvm = models.DateField(default=None, blank=True, null=True, validators=[validators.validate_palvelussuhde_paattymis_pvm])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'palvelussuhteet'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='palvelussuhde_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Tyoskentelypaikka(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
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

    class Meta:
        verbose_name_plural = 'tyoskentelypaikat'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='tyoskentelypaikka_lahdejarjestelma_tunniste_unique_constraint')
        ]


def paattymis_pvm_default():
    return '9999-01-01'


class PidempiPoissaolo(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    palvelussuhde = models.ForeignKey(Palvelussuhde, related_name='pidemmatpoissaolot', on_delete=models.PROTECT)
    alkamis_pvm = models.DateField()
    paattymis_pvm = models.DateField(default=paattymis_pvm_default, validators=[validators.validate_pidempi_poissaolo_paattymis_pvm])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'pidemmatpoissaolot'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='pidempi_poissaolo_lahdejarjestelma_tunniste_unique_constraint')
        ]


class Taydennyskoulutus(UniqueLahdejarjestelmaTunnisteMixin, HistoryAbstractModel):
    tyontekijat = models.ManyToManyField(Tyontekija, through='TaydennyskoulutusTyontekija', related_name='taydennyskoulutukset')
    nimi = models.CharField(max_length=120)
    suoritus_pvm = models.DateField(validators=[validators.validate_taydennyskoulutus_suoritus_pvm])
    koulutuspaivia = models.DecimalField(
        max_digits=4, decimal_places=1, validators=[
            validators.create_validate_decimal_steps('0.5'), MaxValueValidator(160)])
    lahdejarjestelma = models.CharField(max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    tunniste = models.CharField(null=True, blank=True, max_length=120, validators=[validators.validate_tunniste])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'taydennyskoulutukset'
        constraints = [
            UniqueConstraint(fields=['lahdejarjestelma', 'tunniste'],
                             condition=Q(tunniste__isnull=False) & ~Q(tunniste=''),
                             name='taydennyskoulutus_lahdejarjestelma_tunniste_unique_constraint')
        ]

    @classmethod
    def datamodel_additional_info(cls):
        return ["Täydennyskoulutustietojen tallentaminen on päättynyt 31.12.2024"]


class TaydennyskoulutusTyontekija(HistoryAbstractModel):
    tyontekija = models.ForeignKey(Tyontekija, related_name='taydennyskoulutukset_tyontekijat', on_delete=models.PROTECT)
    taydennyskoulutus = models.ForeignKey(Taydennyskoulutus, related_name='taydennyskoulutukset_tyontekijat', on_delete=models.PROTECT)
    tehtavanimike_koodi = models.CharField(max_length=20, validators=[validators.validate_tehtavanimike_koodi])
    luonti_pvm = models.DateTimeField(auto_now_add=True)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'taydennyskoulutukset tyontekijat'


class Aikaleima(AbstractModel):
    """
    Simple state for regular tasks to hold last update information
    """
    avain = models.CharField(max_length=200)
    aikaleima = models.DateTimeField(default=django.utils.timezone.now)
    organisaatio = models.ForeignKey(Organisaatio, null=True, related_name='aikaleimat', on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = 'aikaleimat'
        constraints = [
            UniqueConstraint(fields=['avain', 'organisaatio'],
                             name='avain_organisaatio_unique_constraint'),
            # avain_organisaatio_unique_constraint is not checked if organisaatio is None
            UniqueConstraint(fields=['avain'], condition=Q(organisaatio__isnull=True),
                             name='avain_organisaatio_is_null_unique_constraint')
        ]


class LogData(AbstractModel):
    """
    Simple state for log data related things
    """
    log_type = models.CharField(max_length=100, blank=False, primary_key=True)
    log_seq = models.BigIntegerField(default=0)

    class Meta:
        verbose_name_plural = 'log data'


class BatchError(AbstractModel):
    """
    For storing errors in scheduled batches and allowing retries.
    """
    type = models.TextField(choices=BatchErrorType.choices(),
                            null=False)
    henkilo = models.ForeignKey(Henkilo, related_name='batcherrors', on_delete=models.PROTECT)
    henkilo_duplicate = models.ForeignKey(Henkilo, null=True, related_name='batcherrors_duplicate', on_delete=models.PROTECT)
    retry_time = models.DateTimeField(default=django.utils.timezone.now)
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField()

    class Meta:
        verbose_name_plural = 'batcherrors'

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


class LoginCertificate(AbstractModel):
    organisaatio = models.ForeignKey(Organisaatio, null=True, default=None, related_name='logincertificates', on_delete=models.PROTECT)
    api_path = models.CharField(max_length=200)
    common_name = models.CharField(max_length=500)
    user = models.ForeignKey(User, null=True, related_name='logincertificates', on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = 'Login certificates'


class LuovutuspalveluClientCsr(HistoryAbstractModel):
    organisaatio = models.ForeignKey(Organisaatio, related_name='client_csrs', on_delete=models.PROTECT)
    client_cert_s3_bucket_key = models.CharField(max_length=200, null=True, blank=True)
    cert_chain_s3_bucket_key = models.CharField(max_length=200, null=True, blank=True)
    expiration_date = models.DateTimeField(null=True)
    luonti_pvm = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Client CSRs'


class ErrorReports(AbstractModel):
    organisaatio = models.OneToOneField(Organisaatio, related_name='error_reports', on_delete=models.PROTECT, primary_key=True)
    active_errors = models.BooleanField(default=False)
    muutos_pvm = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Error reports'


"""
Miscellaneous

Z(n) where n is a growing integer. Otherwise problems in migrations with CreateModel.

'Could not load contenttypes.ContentType(pk=22): duplicate key value violates unique constraint "django_content_type_app_label_model_76bd3d3b_uniq"'
"""


class Z1_OphAuthentication(AbstractModel):
    ticketing_granting_ticket = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name_plural = 'OPH autentikaatio'


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


class Z2_Koodisto(AbstractModel):
    """
    Z2_* models are used for koodistopalvelu and lokalisointipalvelu data.
    """
    name = models.CharField(max_length=256, unique=True)
    name_koodistopalvelu = models.CharField(max_length=256, unique=True)
    version = models.IntegerField()
    update_datetime = models.DateTimeField()

    class Meta:
        verbose_name_plural = 'Varda koodistot'


class Z2_Code(AbstractModel):
    koodisto = models.ForeignKey(Z2_Koodisto, related_name='codes', on_delete=models.PROTECT)
    code_value = models.CharField(max_length=256)
    alkamis_pvm = models.DateField(default='1990-01-01')
    paattymis_pvm = models.DateField(null=True)

    class Meta:
        verbose_name_plural = 'Varda codes'
        constraints = [
            models.UniqueConstraint(fields=['koodisto', 'code_value'], name='koodisto_code_value_unique_constraint')
        ]


class Z2_CodeTranslation(AbstractModel):
    code = models.ForeignKey(Z2_Code, related_name='translations', on_delete=models.PROTECT)
    language = models.CharField(max_length=10)
    name = models.TextField(blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Varda code translations'
        constraints = [
            models.UniqueConstraint(fields=['code', 'language'], name='code_language_unique_constraint')
        ]


class Z3_AdditionalCasUserFields(AbstractModel):
    user = models.OneToOneField(User, related_name='additional_cas_user_fields', on_delete=models.PROTECT, primary_key=True)
    kayttajatyyppi = models.CharField(max_length=50, blank=True)
    henkilo_oid = models.CharField(max_length=50, blank=True, null=True, validators=[validators.validate_henkilo_oid])
    etunimet = models.CharField(max_length=100, blank=True, null=True)
    kutsumanimi = models.CharField(max_length=100, blank=True, null=True)
    sukunimi = models.CharField(max_length=100, blank=True, null=True)
    huollettava_oid_list = ArrayField(models.CharField(max_length=50, blank=True, validators=[validators.validate_henkilo_oid]),
                                      null=True, blank=True, validators=[validators.validate_arrayfield])
    toimintakieli_koodi = models.CharField(max_length=3, blank=True)
    all_groups = models.ManyToManyField(Group, blank=True, related_name='additional_cas_user')
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Additional CAS-user fields'


class Z4_CasKayttoOikeudet(AbstractModel):
    PAAKAYTTAJA = 'VARDA-PAAKAYTTAJA'
    TALLENTAJA = 'VARDA-TALLENTAJA'
    KATSELIJA = 'VARDA-KATSELIJA'
    PALVELUKAYTTAJA = 'VARDA-PALVELUKAYTTAJA'
    HUOLTAJATIEDOT_TALLENTAJA = 'HUOLTAJATIETO_TALLENNUS'
    HUOLTAJATIEDOT_KATSELIJA = 'HUOLTAJATIETO_KATSELU'
    HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA = 'HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA'
    HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA = 'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA'
    HENKILOSTO_VUOKRATTU_KATSELIJA = 'HENKILOSTO_VUOKRATTU_KATSELIJA'
    HENKILOSTO_VUOKRATTU_TALLENTAJA = 'HENKILOSTO_VUOKRATTU_TALLENTAJA'
    HENKILOSTO_TYONTEKIJA_KATSELIJA = 'HENKILOSTO_TYONTEKIJA_KATSELIJA'
    HENKILOSTO_TYONTEKIJA_TALLENTAJA = 'HENKILOSTO_TYONTEKIJA_TALLENTAJA'
    TUEN_TIEDOT_KATSELIJA = 'TUEN_TIEDOT_KATSELIJA'
    TUEN_TIEDOT_TALLENTAJA = 'TUEN_TIEDOT_TALLENTAJA'
    # No use case for TOIMIJATIEDOT_KATSELIJA
    TOIMIJATIEDOT_KATSELIJA = 'VARDA_TOIMIJATIEDOT_KATSELIJA'
    TOIMIJATIEDOT_TALLENTAJA = 'VARDA_TOIMIJATIEDOT_TALLENTAJA'
    RAPORTTIEN_KATSELIJA = 'VARDA_RAPORTTIEN_KATSELIJA'
    LUOVUTUSPALVELU = 'VARDA_LUOVUTUSPALVELU'
    YLLAPITAJA = 'VARDA-YLLAPITAJA'
    KAYTTOOIKEUSROOLIT = (
        (PAAKAYTTAJA, 'Varda-Pääkäyttäjä'),
        (TALLENTAJA, 'Varda-Tallentaja'),
        (KATSELIJA, 'Varda-Katselija'),
        (PALVELUKAYTTAJA, 'Varda-Palvelukäyttäjä'),
        (HUOLTAJATIEDOT_TALLENTAJA, 'Varda-Huoltajatietojen tallentaja'),
        (HUOLTAJATIEDOT_KATSELIJA, 'Varda-Huoltajatietojen katselija'),
        (HENKILOSTO_TAYDENNYSKOULUTUS_KATSELIJA, 'Varda-Täydennyskoulutustietojen katselija'),
        (HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA, 'Varda-Täydennyskoulutustietojen tallentaja'),
        (HENKILOSTO_VUOKRATTU_KATSELIJA, 'Varda-Vuokratun henkilöstön katselija'),
        (HENKILOSTO_VUOKRATTU_TALLENTAJA, 'Varda-Vuokratun henkilöstön tallentaja'),
        (TUEN_TIEDOT_KATSELIJA, 'Varda-Tuen tiedot katselija'),
        (TUEN_TIEDOT_TALLENTAJA, 'Varda-Tuen tiedot tallentaja'),
        (HENKILOSTO_TYONTEKIJA_KATSELIJA, 'Varda-Työntekijätietojen katselija'),
        (HENKILOSTO_TYONTEKIJA_TALLENTAJA, 'Varda-Työntekijätietojen tallentaja'),
        (TOIMIJATIEDOT_KATSELIJA, 'Varda-Toimijatietojen katselija'),
        (TOIMIJATIEDOT_TALLENTAJA, 'Varda-Toimijatietojen tallentaja'),
        (RAPORTTIEN_KATSELIJA, 'Varda-Raporttien katselija'),
        (LUOVUTUSPALVELU, 'VARDA_LUOVUTUSPALVELU'),
        (YLLAPITAJA, 'VARDA-ylläpitäjä')
    )

    user = models.ForeignKey(User, related_name='kayttooikeudet', on_delete=models.PROTECT)
    organisaatio_oid = models.CharField(max_length=50, blank=True, validators=[validators.validate_organisaatio_oid])
    kayttooikeus = models.CharField(max_length=50, choices=KAYTTOOIKEUSROOLIT, blank=True)
    last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Kayttooikeudet'


class Z5_AuditLog(AbstractModel):
    user = models.ForeignKey(User, related_name='audit_log', on_delete=models.PROTECT)
    time_of_event = models.DateTimeField(auto_now=True)
    successful_get_request_path = models.CharField(max_length=200, blank=False)
    query_params = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Audit log'


class Z6_RequestLog(AbstractModel):
    request_url = models.CharField(max_length=200)
    request_method = models.CharField(max_length=10)
    request_body = models.TextField(blank=True)
    response_code = models.IntegerField()
    response_body = models.TextField(blank=True)
    target_model = models.CharField(null=True, max_length=100)
    target_id = models.IntegerField(null=True)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='request_log', on_delete=models.PROTECT, null=True)
    data_category = models.CharField(max_length=200, null=True)
    user = models.ForeignKey(User, related_name='request_log', on_delete=models.PROTECT, null=True)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            Index(fields=['timestamp']),
            Index(fields=['vakajarjestaja', 'timestamp']),
            Index(fields=['vakajarjestaja', 'user', 'timestamp']),
            Index(fields=['lahdejarjestelma', 'timestamp'])
        ]
        verbose_name_plural = 'Request log'


class Z6_LastRequest(AbstractModel):
    user = models.ForeignKey(User, related_name='last_requests', on_delete=models.PROTECT, null=True)
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='last_requests', on_delete=models.PROTECT, null=True)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    data_category = models.CharField(max_length=200, null=True)
    last_successful = models.DateTimeField(null=True)
    last_unsuccessful = models.DateTimeField(null=True)

    class Meta:
        verbose_name_plural = 'Last requests'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'vakajarjestaja', 'lahdejarjestelma', 'data_category'],
                name='last_request_user_vakaj_lahdej_data_categ_unique_constraint'
            )
        ]


class Z6_RequestSummary(AbstractModel):
    user = models.ForeignKey(User, related_name='request_summaries', on_delete=models.PROTECT, null=True)
    vakajarjestaja = models.ForeignKey(Organisaatio, related_name='request_summaries', on_delete=models.PROTECT, null=True)
    lahdejarjestelma = models.CharField(null=True, max_length=2, validators=[validators.validate_lahdejarjestelma_koodi])
    request_url_simple = models.CharField(null=True, max_length=200)
    summary_date = models.DateField()
    successful_count = models.IntegerField()
    unsuccessful_count = models.IntegerField()

    class Meta:
        verbose_name_plural = 'Request summaries'
        constraints = [
            models.UniqueConstraint(fields=['user', 'summary_date'],
                                    condition=Q(user__isnull=False),
                                    name='request_summary_user_summary_date_unique_constraint'),
            models.UniqueConstraint(fields=['vakajarjestaja', 'summary_date'],
                                    condition=Q(vakajarjestaja__isnull=False),
                                    name='request_summary_vakajarjestaja_summary_date_unique_constraint'),
            models.UniqueConstraint(fields=['lahdejarjestelma', 'summary_date'],
                                    condition=Q(lahdejarjestelma__isnull=False),
                                    name='request_summary_lahdejarjestelma_summary_date_unique_constraint'),
            models.UniqueConstraint(fields=['request_url_simple', 'summary_date'],
                                    condition=Q(request_url_simple__isnull=False),
                                    name='request_summary_request_url_simple_summary_date_unique_constraint')
        ]


class Z6_RequestCount(AbstractModel):
    request_summary = models.ForeignKey(Z6_RequestSummary, related_name='request_counts', on_delete=models.PROTECT)
    request_url_simple = models.CharField(max_length=200)
    request_method = models.CharField(max_length=10)
    response_code = models.IntegerField()
    count = models.IntegerField()

    class Meta:
        verbose_name_plural = 'Request counts'
        constraints = [
            models.UniqueConstraint(fields=['request_summary', 'request_url_simple', 'request_method', 'response_code'],
                                    name='request_count_unique_constraint')
        ]


class Z7_AdditionalUserFields(AbstractModel):
    user = models.OneToOneField(User, related_name='additional_user_fields', on_delete=models.PROTECT, primary_key=True)
    password_changed_timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Additional user fields'


class Z8_ExcelReport(AbstractModel):
    filename = models.CharField(max_length=200, null=True)
    s3_object_path = models.CharField(max_length=200, null=True)
    password = models.CharField(max_length=150)  # Currently encrypted password length is 120 characters
    status = models.CharField(max_length=50)
    report_type = models.CharField(max_length=50)
    report_subtype = models.CharField(max_length=50, null=True)
    target_date = models.DateField(null=True)
    target_date_secondary = models.DateField(null=True)
    language = models.CharField(max_length=2)
    organisaatio = models.ForeignKey(Organisaatio, null=True, related_name='excel_reports', on_delete=models.PROTECT)
    toimipaikka = models.ForeignKey(Toimipaikka, null=True, related_name='excel_reports', on_delete=models.PROTECT)
    user = models.ForeignKey(User, related_name='excel_reports', on_delete=models.PROTECT)
    timestamp = models.DateTimeField(auto_now=True)
    admin_user_all_organizations = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Excel reports'


class Z8_ExcelReportLog(AbstractModel):
    report_id = models.IntegerField(null=True)
    report_type = models.CharField(max_length=50)
    report_subtype = models.CharField(max_length=50, null=True)
    target_date = models.DateField(null=True)
    target_date_secondary = models.DateField(null=True)
    organisaatio = models.ForeignKey(Organisaatio, null=True, related_name='excel_report_logs', on_delete=models.PROTECT)
    toimipaikka_id = models.IntegerField(null=True)
    user = models.ForeignKey(User, related_name='excel_report_logs', on_delete=models.PROTECT)
    started_timestamp = models.DateTimeField()
    finished_timestamp = models.DateTimeField()
    duration = models.IntegerField()
    file_size = models.IntegerField()
    number_of_rows = ArrayField(models.IntegerField(), validators=[validators.validate_arrayfield])
    encryption_duration = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Excel report logs'


class Z9_RelatedObjectChanged(AbstractModel):
    """
    Used for storing e.g. when did data related to a certain Lapsi object change (Varhaiskasvatussuhde, Maksutieto...)
    """
    model_name = models.CharField(max_length=200)
    instance_id = models.IntegerField()
    parent_model_name = models.CharField(max_length=200, null=True)
    parent_instance_id = models.IntegerField(null=True)
    trigger_model_name = models.CharField(max_length=200)
    trigger_instance_id = models.IntegerField()
    changed_timestamp = models.DateTimeField()
    history_type = models.CharField(max_length=1)

    class Meta:
        indexes = [
            # Used by misc_queries.get_related_object_changed_id_qs to get list of IDs with true
            # (not add+delete) changes, PostgreSQL specific functionality (include)
            Index(name='varda_z9_mod_time_covering', fields=['model_name', 'changed_timestamp'],
                  include=['instance_id', 'trigger_model_name', 'trigger_instance_id', 'history_type']),
            # Used in serializers to get lower level changed objects (e.g. Varhaiskasvatuspaatos, Palvelussuhde objects)
            Index(fields=['model_name', 'parent_instance_id', 'changed_timestamp']),
            # Used in serializers to get Maksutieto and Taydennyskoulutus objects
            Index(fields=['model_name', 'instance_id', 'trigger_model_name', 'changed_timestamp']),
            # Used in serializers to get parent values for objects to determine MOVED state
            Index(fields=['parent_model_name', 'parent_instance_id', 'changed_timestamp'])
        ]
        verbose_name_plural = 'Related object changed'


class Z10_KelaVarhaiskasvatussuhde(AbstractModel):
    varhaiskasvatussuhde_id = models.IntegerField()
    suhde_luonti_pvm = models.DateTimeField()
    suhde_alkamis_pvm = models.DateField()
    suhde_paattymis_pvm = models.DateField(null=True)
    varhaiskasvatuspaatos_id = models.IntegerField()
    paatos_luonti_pvm = models.DateTimeField()
    jarjestamismuoto_koodi = models.CharField(max_length=50)
    tilapainen_vaka_kytkin = models.BooleanField()
    lapsi_id = models.IntegerField()
    henkilo_id = models.IntegerField()
    has_hetu = models.BooleanField()
    history_type = models.CharField(max_length=1)
    history_date = models.DateTimeField()

    class Meta:
        indexes = [
            # Used generally in all queries
            Index(fields=['history_date']),
            # Used when fetching last instance for specific Varhaiskasvatussuhde object
            Index(fields=['varhaiskasvatussuhde_id', '-history_date']),
            # Used when fetching matching created/deleted instances for specific Varhaiskasvatussuhde object
            Index(fields=['henkilo_id', 'suhde_alkamis_pvm', 'suhde_paattymis_pvm']),
        ]
        verbose_name_plural = 'Kela varhaiskasvatussuhteet'


class Z11_MessageLog(AbstractModel):
    message_type = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    organisaatio = models.ForeignKey(Organisaatio, related_name='message_logs', on_delete=models.PROTECT)
    timestamp = models.DateTimeField(default=django.utils.timezone.now)

    class Meta:
        verbose_name_plural = 'message logs'


class Z11_MessageTarget(AbstractModel):
    organisaatio = models.ForeignKey(Organisaatio, related_name='message_targets', on_delete=models.PROTECT)
    user_type = models.CharField(max_length=200)
    email = models.CharField(max_length=200)
    language = models.CharField(max_length=50, default='FI')

    class Meta:
        verbose_name_plural = 'message targets'
        constraints = [
            UniqueConstraint(fields=['organisaatio', 'user_type', 'email'],
                             name='organisaatio_user_type_email_unique_constraint')
        ]


class Z12_DataAccessLog(AbstractModel):
    henkilo_id = models.IntegerField()
    henkilo_oid = models.CharField(max_length=50, validators=[validators.validate_henkilo_oid])
    user = models.ForeignKey(User, related_name='data_access_logs', on_delete=models.PROTECT)
    organisaatio = models.ForeignKey(Organisaatio, related_name='data_access_logs', on_delete=models.PROTECT)
    access_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Data access logs'
        indexes = [
            Index(fields=['timestamp'])
        ]
