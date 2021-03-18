import datetime
import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status

from varda.models import (VakaJarjestaja, Lapsi, Henkilo, Maksutieto, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          Tyontekija, Tyoskentelypaikka, Palvelussuhde, PidempiPoissaolo, Tutkinto)
from varda.unit_tests.test_utils import SetUpTestClient, assert_validation_error, assert_status_code


class VardaViewsReportingTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']
    headers = {
        'HTTP_X_SSL_Authenticated': 'SUCCESS',
        'HTTP_X_SSL_User_DN': 'CN=kela cert,O=user1 company,ST=Some-State,C=FI',
    }

    """
    Reporting related view-tests
    """

    def test_reporting_api(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {
            'excel-reports': 'http://testserver/api/reporting/v1/excel-reports/',
            'tiedonsiirto': 'http://testserver/api/reporting/v1/tiedonsiirto/',
            'tiedonsiirto/yhteenveto': 'http://testserver/api/reporting/v1/tiedonsiirto/yhteenveto/',
            'tiedonsiirtotilasto': 'http://testserver/api/reporting/v1/tiedonsiirtotilasto/'
        })

    def test_kela_reporting_api(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'aloittaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/aloittaneet/',
                                                    'lopettaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/lopettaneet/',
                                                    'maaraaikaiset': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/',
                                                    'korjaustiedot': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/',
                                                    'korjaustiedotpoistetut': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/'})

    def test_reporting_api_kelaetuusmaksatusaloittaneet_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 403)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusaloittaneet_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get_date_filters(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm=2010-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get_alkamis_pvm(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm=2018-01-01', **self.headers)
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
        self._verify_error_report_result(resp, ['MA015', 'MA016'])

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
        self._verify_error_report_result(resp_1, ['VP013', 'VP002'])

        # Set alkamis_pvm for Varhaiskasvatussuhde so that error is not raised
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(alkamis_pvm=today)

        # Set paattymis_pvm for Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(paattymis_pvm=today)
        resp_2 = client.get(url)
        self._verify_error_report_result(resp_2, ['VS012'])

        # Set paattymis_pvm for Varhaiskasvatussuhde to be after Varhaiskasvatuspaatos
        tomorrow = today + datetime.timedelta(days=1)
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(paattymis_pvm=tomorrow)
        resp_3 = client.get(url)
        self._verify_error_report_result(resp_3, ['VP003'])

        # Remove Varhaiskasvatussuhde
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).delete()
        resp_4 = client.get(url)
        self._verify_error_report_result(resp_4, ['VS014'])

        # Remove Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).delete()
        resp_5 = client.get(url)
        self._verify_error_report_result(resp_5, ['VP012'])

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
        self._verify_error_report_result(resp, ['MA016', 'VP013'])

    def test_api_error_report_tyontekijat(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        tyontekija = Tyontekija.objects.get(vakajarjestaja=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.2431884920041')

        client = SetUpTestClient('henkilosto_tallentaja_93957375488').client()
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-tyontekijat/'

        # Make Tyoskentelypaikka start before Palvelussuhde
        # and remove paattymis_pvm from Palvelussuhde and Tyoskentelypaikka
        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(alkamis_pvm=today, paattymis_pvm=None)
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(alkamis_pvm=yesterday,
                                                                                      paattymis_pvm=None)
        resp_1 = client.get(url)
        self._verify_error_report_result(resp_1, ['TA008'])

        # Set alkamis_pvm for Tyoskentelypaikka so that error is not raised
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(alkamis_pvm=today)

        # Set paattymis_pvm for Palvelussuhde
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(paattymis_pvm=today)
        resp_2 = client.get(url)
        self._verify_error_report_result(resp_2, ['TA013'])

        # Set paattymis_pvm for Tyoskentelypaikka to be after Palvelussuhde
        tomorrow = today + datetime.timedelta(days=1)
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=tomorrow)
        resp_3 = client.get(url)
        self._verify_error_report_result(resp_3, ['TA006'])

        # Remove Tyoskentelypaikka
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        resp_4 = client.get(url)
        self._verify_error_report_result(resp_4, ['TA014'])

        # Remove Palvelussuhde (PidempiPoissaolo must be removed as well)
        PidempiPoissaolo.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        Palvelussuhde.objects.filter(tyontekija=tyontekija).delete()
        resp_5 = client.get(url)
        self._verify_error_report_result(resp_5, ['PS008'])

        # Remove Tutkinto
        Tutkinto.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=tyontekija.henkilo).delete()
        resp_6 = client.get(url)
        self._verify_error_report_result(resp_6, ['TU004'])

    def _verify_error_report_result(self, response, error_code_list):
        assert_status_code(response, status.HTTP_200_OK)
        response_json = json.loads(response.content)
        self.assertEqual(len(response_json['results']), 1)
        self.assertEqual(len(response_json['results'][0]['errors']), len(error_code_list))
        response_string = response.content.decode('utf-8')
        for error_code in error_code_list:
            self.assertIn(error_code, response_string)

    def test_api_error_report_tyontekijat_no_permissions(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-tyontekijat/'

        # No view_tyontekija permissions
        client_no_permissions_1 = SetUpTestClient('tester2').client()
        resp_no_permissions_1 = client_no_permissions_1.get(url)
        assert_status_code(resp_no_permissions_1, status.HTTP_403_FORBIDDEN)

        # No permissions to correct groups
        client_no_permissions_2 = SetUpTestClient('tyontekija_toimipaikka_tallentaja_9395737548815').client()
        resp_no_permissions_2 = client_no_permissions_2.get(url)
        assert_status_code(resp_no_permissions_2, status.HTTP_404_NOT_FOUND)

        # No permissions to correct VakaJarjestaja
        client_no_permissions_3 = SetUpTestClient('henkilosto_tallentaja_93957375488').client()
        resp_no_permissions_3 = client_no_permissions_3.get(url)
        assert_status_code(resp_no_permissions_3, status.HTTP_404_NOT_FOUND)

    def test_api_error_report_lapset_filter(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/'
        client = SetUpTestClient('tester2').client()

        resp_1 = client.get(url)
        assert_status_code(resp_1, status.HTTP_200_OK)
        resp_1_string = resp_1.content.decode('utf8')
        self.assertIn('VP002', resp_1_string)
        self.assertIn('VP013', resp_1_string)

        resp_2 = client.get(f'{url}?error=VP002')
        assert_status_code(resp_2, status.HTTP_200_OK)
        resp_2_string = resp_2.content.decode('utf8')
        self.assertNotIn('VP013', resp_2_string)
        self.assertIn('VP002', resp_2_string)

    def test_api_tiedonsiirto(self):
        client = SetUpTestClient('tester2').client()

        vakasuhde_json = json.loads(client.get('/api/v1/varhaiskasvatussuhteet/').content)['results'][0]
        vakasuhde_json['paattymis_pvm'] = None
        client.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_json["id"]}/', json.dumps(vakasuhde_json), content_type='application/json')

        # Must use vakajarjestajat filter if not admin or oph user
        resp_1 = client.get('/api/reporting/v1/tiedonsiirto/')
        assert_status_code(resp_1, status.HTTP_200_OK)
        self.assertEqual(0, len(json.loads(resp_1.content)['results']))

        resp_2 = client.get('/api/reporting/v1/tiedonsiirto/?vakajarjestajat=1')
        assert_status_code(resp_2, status.HTTP_200_OK)
        self.assertEqual(1, len(json.loads(resp_2.content)['results']))

    def test_api_tiedonsiirto_admin(self):
        client = SetUpTestClient('credadmin').client()
        client.delete('/api/henkilosto/v1/tyontekijat/1/')

        resp = client.get('/api/reporting/v1/tiedonsiirto/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(1, len(json.loads(resp.content)['results']))

    def test_tiedonsiirto_yhteenveto(self):
        client = SetUpTestClient('tester2').client()
        client.delete('/api/v1/varhaiskasvatussuhteet/1/')

        resp = client.get('/api/reporting/v1/tiedonsiirto/yhteenveto/?vakajarjestajat=1')
        assert_status_code(resp, status.HTTP_200_OK)

        accepted_response = {
            'date': datetime.date.today().strftime('%Y-%m-%d'),
            'successful': 0,
            'unsuccessful': 1,
            'user_id': User.objects.get(username='tester2').id,
            'username': 'tester2'
        }
        self.assertDictEqual(json.loads(resp.content)['results'][0], accepted_response)
