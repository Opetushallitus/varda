from datetime import date
from decimal import Decimal
from django_filters import FilterSet
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from varda import validators, koodistopalvelu
from varda.filters import VakaJarjestajaFilter, LapsiFilter
from varda.models import (VakaJarjestaja, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Huoltaja,
                          Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z2_Koodisto, Z2_Code)


class VardaModelsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_vakajarjestajat(self):
        test_vakajarjestaja = VakaJarjestaja.objects.get(pk=1).nimi
        self.assertEqual(test_vakajarjestaja, 'Tester2 organisaatio')

    def test_toimipaikat(self):
        test_toimipaikka = Toimipaikka.objects.get(pk=1).nimi
        self.assertEqual(test_toimipaikka, 'Espoo')

        test_toimipaikka_varhaiskasvatuspaikat = Toimipaikka.objects.get(pk=1).varhaiskasvatuspaikat
        self.assertEqual(test_toimipaikka_varhaiskasvatuspaikat, 120)

        test_toimipaikka_jarjestamismuoto = Toimipaikka.objects.get(pk=1).jarjestamismuoto_koodi
        self.assertEqual(test_toimipaikka_jarjestamismuoto[0], 'jm01')

    def test_toiminnalliset_painotukset(self):
        test_toiminnallinen_painotus = ToiminnallinenPainotus.objects.get(pk=1).toimintapainotus_koodi
        self.assertEqual(test_toiminnallinen_painotus, 'tp01')

    def test_kieli_painotukset(self):
        test_kieli_painotus = KieliPainotus.objects.get(pk=1).kielipainotus_koodi
        self.assertEqual(test_kieli_painotus, 'FI')

    def test_henkilot(self):
        test_henkilo = Henkilo.objects.get(pk=2).henkilo_oid
        self.assertEqual(test_henkilo, '1.2.246.562.24.47279942650')

    def test_varhaiskasvatussuhteet(self):
        test_varhaiskasvatussuhde = Varhaiskasvatussuhde.objects.get(pk=1).alkamis_pvm
        self.assertEqual(test_varhaiskasvatussuhde, date(2017, 2, 11))

    def test_huoltajat(self):
        test_huoltaja = Huoltaja.objects.get(pk=1).henkilo_id
        self.assertEqual(test_huoltaja, 4)

    def test_varhaiskasvatuspaatokset(self):
        test_varhaiskasvatuspaatos = Varhaiskasvatuspaatos.objects.get(pk=1).tuntimaara_viikossa
        self.assertEqual(test_varhaiskasvatuspaatos, Decimal('37.5'))

    def test_koodistot(self):
        test_koodisto = Z2_Koodisto.objects.get(name=koodistopalvelu.Koodistot.toiminnallinen_painotus_koodit.value)
        self.assertEqual(Z2_Code.objects.filter(koodisto=test_koodisto).count(), 11)

    def test_VakaJarjestajaFilter_is_FilterSet(self):
        of = VakaJarjestajaFilter()
        self.assertIsInstance(of, FilterSet)

    def test_LapsiFilter_contains_filters(self):
        lf = LapsiFilter()
        self.assertIn('filters', dir(lf))

    """
    TODO: unit-tests MUST use mocked integrations
    def test_organisaatiopalvelu_integration(self):
        import varda.organisaatiopalvelu as orgpalv
        vakajarjestaja = VakaJarjestaja.objects.filter(y_tunnus="1057860-7")    # Haetaan testidatasta Helsingin tiedot
        self.assertEqual(vakajarjestaja[0].kayntiosoite, "Helsinginkatu 123")   # Testidatassa Helsingin käyntiosoite
        orgpalv.fetch_organisaatio_info()                                       # Organisaatiotietojen päivitys
        vakajarjestaja = VakaJarjestaja.objects.filter(y_tunnus="1057860-7")    # Haetaan Hkin tiedot päivityksen jälkeen
        self.assertEqual(vakajarjestaja[0].kayntiosoite, "Hämeentie 11 A")      # Hkin käyntiosoite päivitettynä organisaatiopalvelusta
    """

    def test_ytjkieli(self):
        vakajarjestaja = VakaJarjestaja.objects.filter(ytjkieli="FI")
        self.assertEqual(vakajarjestaja[0].nimi, "Tester organisaatio")

    def test_organisaatio_oid_1(self):
        oid = "1.2.246.562.10.22993275845.0"
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {"oid": ['Number of sections in OID is incorrect.']})

    def test_organisaatio_oid_2(self):
        oid = "1.2.246.563.10.22993275845"
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {"oid": ['OPH part of OID is incorrect.']})

    def test_organisaatio_oid_3(self):
        oid = "1.2.246.562.10.22993275845229932758453"
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {"oid": ['OID identifier is incorrect.']})

    def test_organisaatio_oid_4(self):
        oid = "1.2.246.562.12.22993275845"
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {"oid": ['Not an OID for an organization.']})
