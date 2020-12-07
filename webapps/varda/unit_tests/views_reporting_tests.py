import datetime
import json

from django.test import TestCase
from rest_framework import status

from varda.models import VakaJarjestaja, Lapsi, Henkilo, Maksutieto, Varhaiskasvatuspaatos, Varhaiskasvatussuhde
from varda.unit_tests.test_utils import SetUpTestClient, assert_validation_error, mock_admin_user, assert_status_code


class VardaViewsReportingTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    """
    Reporting related view-tests
    """

    def test_reporting_api(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'tiedonsiirtotilasto': 'http://testserver/api/reporting/v1/tiedonsiirtotilasto/'})

    def test_kela_reporting_api(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'aloittaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/aloittaneet/',
                                                    'lopettaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/lopettaneet/',
                                                    'maaraaikaiset': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/',
                                                    'korjaustiedot': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/',
                                                    'korjaustiedotpoistetut': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/'})

    def test_reporting_api_kelaetuusmaksatusaloittaneet_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusaloittaneet_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get_date_filters(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm=2010-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get_alkamis_pvm(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_api_error_report_lapset(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        client = SetUpTestClient('tester10').client()
        resp_empty = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/')
        assert_status_code(resp_empty, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp_empty.content)['count'], 0)

    def test_api_error_report_lapset_no_permissions(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/'

        # No permissions to VakaJarjestaja
        client_no_permissions_1 = SetUpTestClient('tester10').client()
        resp_no_permissions_1 = client_no_permissions_1.get(url)
        assert_status_code(resp_no_permissions_1, status.HTTP_404_NOT_FOUND)

        # No permissions to correct groups
        client_no_permissions_2 = SetUpTestClient('vakatietojen_toimipaikka_tallentaja').client()
        resp_no_permissions_2 = client_no_permissions_2.get(url)
        assert_status_code(resp_no_permissions_2, status.HTTP_404_NOT_FOUND)

        # No view_lapsi permission
        client_no_permissions_2 = SetUpTestClient('henkilosto_tallentaja_93957375488').client()
        resp_no_permissions_2 = client_no_permissions_2.get(url)
        assert_status_code(resp_no_permissions_2, status.HTTP_403_FORBIDDEN)

    def test_api_error_report_lapset_huoltajatiedot(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(vakatoimija=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.6779627637492')

        # Make Lapsi over 8 years old
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2000, month=1, day=1))

        # Remove paattymis_pvm from Maksutieto
        Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).update(paattymis_pvm=None)

        # Set paattymis_pvm for Varhaiskasvatuspaatos
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(paattymis_pvm=yesterday)

        # Set paattymis_pvm for Varhaiskasvatussuhde so that error is not raised
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(paattymis_pvm=yesterday)

        client = SetUpTestClient('tester10').client()
        resp = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/')
        assert_status_code(resp, status.HTTP_200_OK)

        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json['results']), 1)
        self.assertEqual(len(resp_json['results'][0]['errors']), 2)

        resp_string = resp.content.decode('utf-8')
        self.assertIn('MA015', resp_string)
        self.assertIn('MA016', resp_string)

    def test_api_error_report_lapset_vakatiedot(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(vakatoimija=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.6779627637492')

        # Make Lapsi over 8 years old
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2000, month=1, day=1))

        # Make Varhaiskasvatussuhde start before Varhaiskasvatuspaatos
        # and remove paattymis_pvm from Varhaiskasvatuspaatos and Varhaiskasvatussuhde
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(alkamis_pvm=today, paattymis_pvm=None)
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(alkamis_pvm=yesterday,
                                                                                       paattymis_pvm=None)

        # Set paattymis_pvm for Maksutieto so that error is not raised
        Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).update(paattymis_pvm=yesterday)

        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/'
        client = SetUpTestClient('tester10').client()

        resp_1 = client.get(url)
        assert_status_code(resp_1, status.HTTP_200_OK)

        resp_1_json = json.loads(resp_1.content)
        self.assertEqual(len(resp_1_json['results']), 1)
        self.assertEqual(len(resp_1_json['results'][0]['errors']), 2)

        resp_1_string = resp_1.content.decode('utf-8')
        self.assertIn('VP013', resp_1_string)
        self.assertIn('VP002', resp_1_string)

        # Set alkamis_pvm for Varhaiskasvatussuhde so that error is not raised
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(alkamis_pvm=today)

        # Set paattymis_pvm for Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(paattymis_pvm=today)
        resp_2 = client.get(url)
        assert_status_code(resp_2, status.HTTP_200_OK)

        resp_2_json = json.loads(resp_2.content)
        self.assertEqual(len(resp_2_json['results']), 1)
        self.assertEqual(len(resp_2_json['results'][0]['errors']), 1)

        resp_2_string = resp_2.content.decode('utf-8')
        self.assertIn('VS012', resp_2_string)

        # Set paattymis_pvm for Varhaiskasvatussuhde to be after Varhaiskasvatuspaatos
        tomorrow = today + datetime.timedelta(days=1)
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(paattymis_pvm=tomorrow)
        resp_3 = client.get(url)
        assert_status_code(resp_3, status.HTTP_200_OK)

        resp_3_json = json.loads(resp_3.content)
        self.assertEqual(len(resp_3_json['results']), 1)
        self.assertEqual(len(resp_3_json['results'][0]['errors']), 1)

        resp_3_string = resp_3.content.decode('utf-8')
        self.assertIn('VP003', resp_3_string)

        # Remove Varhaiskasvatussuhde
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).delete()
        resp_4 = client.get(url)
        assert_status_code(resp_4, status.HTTP_200_OK)

        resp_4_json = json.loads(resp_4.content)
        self.assertEqual(len(resp_4_json['results']), 1)
        self.assertEqual(len(resp_4_json['results'][0]['errors']), 1)

        resp_4_string = resp_4.content.decode('utf-8')
        self.assertIn('VS014', resp_4_string)

        # Remove Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).delete()
        resp_5 = client.get(url)
        assert_status_code(resp_5, status.HTTP_200_OK)

        resp_5_json = json.loads(resp_5.content)
        self.assertEqual(len(resp_5_json['results']), 1)
        self.assertEqual(len(resp_5_json['results'][0]['errors']), 1)

        resp_5_string = resp_5.content.decode('utf-8')
        self.assertIn('VP012', resp_5_string)

    def test_api_error_report_lapset_huoltajatiedot_vakatiedot(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(vakatoimija=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.6779627637492')

        # Make Lapsi over 8 years old
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2000, month=1, day=1))

        # Remove paattymis_pvm from Maksutieto
        Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi).update(paattymis_pvm=None)

        # Remove paattymis_pvm from Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(paattymis_pvm=None)

        client = SetUpTestClient('tester10').client()
        resp = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/')
        assert_status_code(resp, status.HTTP_200_OK)

        resp_json = json.loads(resp.content)
        self.assertEqual(len(resp_json['results']), 1)
        self.assertEqual(len(resp_json['results'][0]['errors']), 2)

        resp_string = resp.content.decode('utf-8')
        self.assertIn('MA016', resp_string)
        self.assertIn('VP013', resp_string)
