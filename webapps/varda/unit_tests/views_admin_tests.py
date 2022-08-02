import datetime
import json

from django.test import TestCase, override_settings
from rest_framework import status

from varda.enums.reporting import ReportStatus
from varda.models import (Maksutieto, Palvelussuhde, Toimipaikka, Tyoskentelypaikka, Organisaatio,
                          Varhaiskasvatuspaatos, Varhaiskasvatussuhde)
from varda.unit_tests.test_utils import assert_status_code, assert_validation_error, mock_admin_user, SetUpTestClient


REAL_CACHE_SETTINGS = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'
    }
}


class VardaAdminViewSetTests(TestCase):
    fixtures = ['fixture_basics']

    @override_settings(CACHES=REAL_CACHE_SETTINGS)
    def test_set_paattymis_pvm_not_admin(self):
        client = SetUpTestClient('tester2').client()

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        paattymis_pvm = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'paattymis_pvm': '2022-02-01'
        }

        resp = client.post('/api/admin/set-paattymis-pvm/', paattymis_pvm)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    @override_settings(CACHES=REAL_CACHE_SETTINGS)
    def test_set_paattymis_pvm_correct(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')

        paattymis_pvm = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'paattymis_pvm': '2022-02-01'
        }

        expected_result = {
            'status': ReportStatus.FINISHED.value,
            'toimipaikka': 2,
            'kielipainotus': 1,
            'toiminnallinenpainotus': 1,
            'varhaiskasvatuspaatos': 3,
            'varhaiskasvatussuhde': 3,
            'maksutieto': 1,
            'palvelussuhde': 1,
            'tyoskentelypaikka': 2
        }

        resp = client.post('/api/admin/set-paattymis-pvm/', paattymis_pvm)
        assert_status_code(resp, status.HTTP_200_OK)
        identifier = json.loads(resp.content)['identifier']
        resp = client.get(f'/api/admin/set-paattymis-pvm/{identifier}/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertDictEqual(json.loads(resp.content), expected_result)

    @override_settings(CACHES=REAL_CACHE_SETTINGS)
    def test_set_paattymis_pvm_incorrect(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')

        paattymis_pvm = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'paattymis_pvm': '2018-02-01'
        }

        resp = client.post('/api/admin/set-paattymis-pvm/', paattymis_pvm)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.')

    @override_settings(CACHES=REAL_CACHE_SETTINGS)
    def test_set_paattymis_pvm_not_set(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        paattymis_pvm_date = datetime.date(year=2022, month=2, day=1)
        paattymis_pvm = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'paattymis_pvm': '2022-02-01'
        }

        expected_result = {
            'status': ReportStatus.FINISHED.value,
            'toimipaikka': 2,
            'kielipainotus': 0,
            'toiminnallinenpainotus': 0,
            'varhaiskasvatuspaatos': 1,
            'varhaiskasvatussuhde': 1,
            'maksutieto': 1,
            'palvelussuhde': 5,
            'tyoskentelypaikka': 1
        }

        resp = client.post('/api/admin/set-paattymis-pvm/', paattymis_pvm)
        assert_status_code(resp, status.HTTP_200_OK)
        identifier = json.loads(resp.content)['identifier']
        resp = client.get(f'/api/admin/set-paattymis-pvm/{identifier}/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertDictEqual(json.loads(resp.content), expected_result)

        self.assertEqual(Toimipaikka.objects.get(tunniste='testing-toimipaikka2').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Toimipaikka.objects.get(tunniste='testing-toimipaikka3').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos3').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos6').paattymis_pvm, datetime.date(year=2019, month=10, day=24))
        self.assertEqual(Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos_kela_tilapainen').paattymis_pvm, datetime.date(year=2021, month=10, day=2))
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='testing-varhaiskasvatussuhde3').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='testing-varhaiskasvatussuhde6').paattymis_pvm, datetime.date(year=2019, month=2, day=24))
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='kela_testing_public_tilapainen').paattymis_pvm, datetime.date(year=2021, month=10, day=2))
        self.assertEqual(Maksutieto.objects.get(tunniste='testing-maksutieto2').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Palvelussuhde.objects.get(tunniste='testing-palvelussuhde1').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2-2').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Palvelussuhde.objects.get(tunniste='testing-palvelussuhde4').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Palvelussuhde.objects.get(tunniste='testing-palvelussuhde-kiertava').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka1').paattymis_pvm, datetime.date(year=2020, month=9, day=10))
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka1-1').paattymis_pvm, datetime.date(year=2020, month=10, day=2))
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka2').paattymis_pvm, datetime.date(year=2021, month=5, day=2))
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka2_1').paattymis_pvm, paattymis_pvm_date)
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka4').paattymis_pvm, datetime.date(year=2020, month=10, day=2))
        self.assertEqual(Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentylypaikka-kiertava').paattymis_pvm, datetime.date(year=2020, month=10, day=2))
        # PAOS not set
        self.assertEqual(Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos4').paattymis_pvm, None)
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='testing-varhaiskasvatussuhde4').paattymis_pvm, None)
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='kela_testing_jm03').paattymis_pvm, datetime.date(year=2022, month=1, day=3))
        self.assertEqual(Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos9').paattymis_pvm, None)
        self.assertEqual(Varhaiskasvatussuhde.objects.get(tunniste='testing-varhaiskasvatussuhde9').paattymis_pvm, None)
