from datetime import date
from decimal import Decimal
from django_filters import FilterSet
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from varda import validators
from varda.enums.koodistot import Koodistot
from varda.filters import OrganisaatioFilter, LapsiFilter
from varda.models import (Organisaatio, Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Henkilo, Huoltaja,
                          Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z2_Koodisto, Z2_Code)


class VardaModelsTests(TestCase):
    fixtures = ['fixture_basics']

    def test_vakajarjestajat(self):
        test_vakajarjestaja = Organisaatio.objects.get(pk=1).nimi
        self.assertEqual(test_vakajarjestaja, 'Tester2 organisaatio')

    def test_toimipaikat(self):
        test_toimipaikka = Toimipaikka.objects.get(pk=1).nimi
        self.assertEqual(test_toimipaikka, 'Espoo')

        test_toimipaikka_varhaiskasvatuspaikat = Toimipaikka.objects.get(pk=1).varhaiskasvatuspaikat
        self.assertEqual(test_toimipaikka_varhaiskasvatuspaikat, 120)

        test_toimipaikka_jarjestamismuoto = Toimipaikka.objects.get(pk=1).jarjestamismuoto_koodi
        self.assertEqual(test_toimipaikka_jarjestamismuoto[0], 'jm02')

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
        test_koodisto = Z2_Koodisto.objects.get(name=Koodistot.toiminnallinen_painotus_koodit.value)
        self.assertEqual(Z2_Code.objects.filter(koodisto=test_koodisto).count(), 11)

    def test_OrganisaatioFilter_is_FilterSet(self):
        of = OrganisaatioFilter()
        self.assertIsInstance(of, FilterSet)

    def test_LapsiFilter_contains_filters(self):
        lf = LapsiFilter()
        self.assertIn('filters', dir(lf))

    def test_ytjkieli(self):
        vakajarjestaja = Organisaatio.objects.filter(ytjkieli='FI')
        self.assertEqual(vakajarjestaja[0].nimi, 'Tester organisaatio')

    def test_organisaatio_oid_1(self):
        oid = '1.2.246.562.10.22993275845.0'
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {'organisaatio_oid': [{'error_code': 'MI007', 'description': 'Number of OID sections is incorrect.'}]})

    def test_organisaatio_oid_2(self):
        oid = '1.2.246.563.10.22993275845'
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {'organisaatio_oid': [{'error_code': 'MI008', 'description': 'OPH part of OID is incorrect.'}]})

    def test_organisaatio_oid_3(self):
        oid = '1.2.246.562.10.22993275845229932758453'
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {'organisaatio_oid': [{'error_code': 'MI009', 'description': 'OID is incorrect.'}]})

    def test_organisaatio_oid_4(self):
        oid = '1.2.246.562.12.22993275845'
        try:
            validators.validate_organisaatio_oid(oid)
        except ValidationError as e:
            self.assertEqual(e.detail, {'organisaatio_oid': [{'error_code': 'MI010', 'description': 'Not an OID for an organization.'}]})
