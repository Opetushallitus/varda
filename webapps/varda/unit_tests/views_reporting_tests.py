import datetime
import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status

from varda.models import (VakaJarjestaja, Lapsi, Henkilo, Maksutieto, Varhaiskasvatuspaatos, Varhaiskasvatussuhde,
                          Tyontekija, Tyoskentelypaikka, Palvelussuhde, PidempiPoissaolo, Tutkinto, Toimipaikka,
                          ToiminnallinenPainotus, KieliPainotus)
from varda.unit_tests.test_utils import SetUpTestClient, assert_validation_error, assert_status_code, \
    mock_date_decorator_factory


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

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 403)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_correct_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos_url = _load_base_data_for_kela_success_testing()

        data_vakasuhde = {
            'varhaiskasvatuspaatos': vakapaatos_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-05',
            'lahdejarjestelma': '1'
        }

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_count = resp_content['count']

        resp_vakasuhde = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', data_vakasuhde)
        assert_status_code(resp_vakasuhde, 201)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '049', 'henkilotunnus': '071119A884T', 'tietue': 'A', 'vakasuhde_alkamis_pvm': '2021-01-05'}
        self.assertEqual(resp_content['count'], existing_count + 1)
        self.assertIn(expected_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_non_applicable_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos_public_url, vakapaatos_private_url = _load_base_data_for_kela_error_testing()

        data_vakasuhde_public = {
            'varhaiskasvatuspaatos': vakapaatos_public_url,
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2021-01-05',
            'lahdejarjestelma': '1'
        }

        data_vakasuhde_private = {
            'varhaiskasvatuspaatos': vakapaatos_private_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-05',
            'lahdejarjestelma': '1'
        }

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_count = resp_content['count']

        resp_vakasuhde = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', data_vakasuhde_public)
        assert_status_code(resp_vakasuhde, 201)

        resp_vakasuhde = client_tester5.post('/api/v1/varhaiskasvatussuhteet/', data_vakasuhde_private)
        assert_status_code(resp_vakasuhde, 201)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(existing_count, resp_content['count'])

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        self.assertEqual(resp.status_code, 403)

        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_get_date_filters(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm=2010-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_update(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos3')
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatussuhde3')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        # Because korjaustiedot and lopettaneet are both based on changes verify that the added end date here does not
        # appear on korjaustiedot API
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2018-09-05',
            'paattymis_pvm': '2021-06-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', update_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '091', 'henkilotunnus': '170334-130B', 'tietue': 'L', 'vakasuhde_paattymis_pvm': '2021-06-10'}
        self.assertEqual(resp_content['count'], existing_lopettaneet_count + 1)
        self.assertIn(expected_result, resp_content['results'])

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_non_applicable_data_update(self):
        client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 2
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        private_vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='kela_testing_private')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        # Because korjaustiedot and lopettaneet are both based on changes verify that the added end date here does not
        # appear on korjaustiedot API
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{private_vakasuhde.varhaiskasvatuspaatos_id}/',
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-04-15',
            'paattymis_pvm': '2021-06-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester5.put(f'/api/v1/varhaiskasvatussuhteet/{private_vakasuhde.id}/', update_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_lopettaneet_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_same_day_update(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        public_vakapaatos_url = _load_base_data_for_kela_success_testing()

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_maaraaikaiset_content = json.loads(resp_kela_api_maaraaikaiset.content)
        existing_maaraaikaiset_count = resp_maaraaikaiset_content['count']

        # Because korjaustiedot and lopettaneet are both based on changes verify that the added end date here does not
        # appear on korjaustiedot API
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        create_aloittanut = {
            'varhaiskasvatuspaatos': public_vakapaatos_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-09-05',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_create = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', create_aloittanut)
        assert_status_code(resp_vakasuhde_create, 201)

        created_vakasuhde_id = json.loads(resp_vakasuhde_create.content)['id']

        add_end_date = {
            'varhaiskasvatuspaatos': public_vakapaatos_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-09-05',
            'paattymis_pvm': '2021-11-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{created_vakasuhde_id}/', add_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        # even though this could be considered as aloittanut + lopettanut it is treated as maaraaikainen since the end
        # date was added the same day . If data transfer is between the operation eg. create morning and add date on evening
        # this will generate a maaraaikainen instead of lopettanut even though an aloittanut has been transfered

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api_maaraaikaiset.content)
        self.assertEqual(resp_content['count'], existing_maaraaikaiset_count + 1)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_lopettaneet_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_same_day_add_and_update(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos3')
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatussuhde3')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_maaraaikaiset_content = json.loads(resp_kela_api_maaraaikaiset.content)
        existing_maaraaikaiset_count = resp_maaraaikaiset_content['count']

        # Because korjaustiedot and lopettaneet are both based on changes verify that the added end date here does not
        # appear on korjaustiedot API
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        add_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2018-09-05',
            'paattymis_pvm': '2021-11-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', add_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api_maaraaikaiset.content)
        self.assertEqual(resp_content['count'], existing_maaraaikaiset_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_lopettaneet_count + 1)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

        alter_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2018-09-05',
            'paattymis_pvm': '2021-12-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', alter_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api_maaraaikaiset.content)
        self.assertEqual(resp_content['count'], existing_maaraaikaiset_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_lopettanut_response = {'kotikunta_koodi': '091', 'henkilotunnus': '170334-130B', 'tietue': 'L',
                                        'vakasuhde_paattymis_pvm': '2021-12-10'}
        self.assertEqual(resp_content['count'], existing_lopettaneet_count + 1)
        self.assertIn(expected_lopettanut_response, resp_content['results'])

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        self.assertEqual(resp.status_code, 403)

        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_correct_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos_url = _load_base_data_for_kela_success_testing()

        resp_kela_api_maaraaikaiset = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_maaraaikaiset_content = json.loads(resp_kela_api_maaraaikaiset.content)
        existing_maaraaikaiset_count = resp_maaraaikaiset_content['count']

        create_vakasuhde = {
            'varhaiskasvatuspaatos': vakapaatos_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-05',
            'paattymis_pvm': '2021-06-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', create_vakasuhde)
        assert_status_code(resp_vakasuhde, 201)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '049', 'henkilotunnus': '071119A884T', 'tietue': 'M',
                           'vakasuhde_alkamis_pvm': '2021-01-05', 'vakasuhde_paattymis_pvm': '2021-06-10'}
        self.assertEqual(resp_content['count'], existing_maaraaikaiset_count + 1)
        self.assertIn(expected_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_maaraaikainen_non_applicable_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 2
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos_public_url, vakapaatos_private_url = _load_base_data_for_kela_error_testing()

        data_vakasuhde_public = {
            'varhaiskasvatuspaatos': vakapaatos_public_url,
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2021-01-05',
            'paattymis_pvm': '2022-02-01',
            'lahdejarjestelma': '1'
        }

        data_vakasuhde_private = {
            'varhaiskasvatuspaatos': vakapaatos_private_url,
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-05',
            'paattymis_pvm': '2022-02-01',
            'lahdejarjestelma': '1'
        }

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_count = resp_content['count']

        resp_vakasuhde = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', data_vakasuhde_public)
        assert_status_code(resp_vakasuhde, 201)

        resp_vakasuhde = client_tester5.post('/api/v1/varhaiskasvatussuhteet/', data_vakasuhde_private)
        assert_status_code(resp_vakasuhde, 201)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(existing_count, resp_content['count'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        self.assertEqual(resp.status_code, 403)

        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_get_alkamis_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_add_end_date_alter_start_date(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos3')
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatussuhde3')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        # Altering start date and adding end date creates both korjaus and lopettaneet set
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_start_and_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2018-09-07',
            'paattymis_pvm': '2021-06-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', update_start_and_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_lopettaneet_content['count'], existing_lopettaneet_count + 1)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count + 1)

        # verify that the end date remains 0001-01-01 and alkamis_pvm is updated
        expected_korjaus_result = {'kotikunta_koodi': '091',
                                   'henkilotunnus': '170334-130B',
                                   'tietue': 'K',
                                   'vakasuhde_alkamis_pvm': '2018-09-07',
                                   'vakasuhde_paattymis_pvm': '0001-01-01',
                                   'vakasuhde_alkuperainen_alkamis_pvm': '2018-09-05',
                                   'vakasuhde_alkuperainen_paattymis_pvm': '0001-01-01'}

        # verify that the corresponding lopettanut is generated
        expected_lopettaneet_result = {'kotikunta_koodi': '091', 'henkilotunnus': '170334-130B', 'tietue': 'L',
                                       'vakasuhde_paattymis_pvm': '2021-06-10'}
        self.assertIn(expected_korjaus_result, resp_content['results'])
        self.assertIn(expected_lopettaneet_result, resp_lopettaneet_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_alter_start_and_end_date(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos4')
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='kela_testing_jm03')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        # Altering start date and adding end date creates both korjaus and lopettaneet set
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_start_and_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-07',
            'paattymis_pvm': '2022-01-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', update_start_and_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_lopettaneet_content['count'], existing_lopettaneet_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count + 1)

        # verify that both dates are updated and previous dates are included
        expected_korjaus_result = {'kotikunta_koodi': '091', 'henkilotunnus': '120699-985W', 'tietue': 'K',
                                   'vakasuhde_alkamis_pvm': '2021-01-07',
                                   'vakasuhde_paattymis_pvm': '2022-01-10',
                                   'vakasuhde_alkuperainen_alkamis_pvm': '2021-01-05',
                                   'vakasuhde_alkuperainen_paattymis_pvm': '2022-01-03'}
        self.assertIn(expected_korjaus_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_alter_end_date(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos4')
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='kela_testing_jm03')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        # Altering end date generates a korjaustieto
        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-01-05',
            'paattymis_pvm': '2022-01-10',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/', update_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_lopettaneet_content['count'], existing_lopettaneet_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count + 1)

        # verify that the alkamis_pvm remains 0001-01-01 and paattymis_pvm is updated
        expected_korjaus_result = {'kotikunta_koodi': '091',
                                   'henkilotunnus': '120699-985W',
                                   'tietue': 'K',
                                   'vakasuhde_alkamis_pvm': '0001-01-01',
                                   'vakasuhde_paattymis_pvm': '2022-01-10',
                                   'vakasuhde_alkuperainen_alkamis_pvm': '0001-01-01',
                                   'vakasuhde_alkuperainen_paattymis_pvm': '2022-01-03'}
        self.assertIn(expected_korjaus_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_non_applicable_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 11
        client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 2
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        public_vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma='1', tunniste='kela_testing_public_tilapainen')
        public_vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma='1', tunniste='testing-varhaiskasvatuspaatos_kela_tilapainen')
        private_vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma='1', tunniste='testing-varhaiskasvatuspaatos_kela_private')
        private_vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma='1', tunniste='kela_testing_private')

        resp_kela_api_lopettaneet = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api_lopettaneet.content)
        existing_lopettaneet_count = resp_lopettaneet_content['count']

        resp_kela_api_korjaustiedot = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_korjaustiedot_content = json.loads(resp_kela_api_korjaustiedot.content)
        existing_korjaustiedot_count = resp_korjaustiedot_content['count']

        update_public_start_and_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{public_vakapaatos.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{public_vakasuhde.toimipaikka_id}/',
            'alkamis_pvm': '2021-09-29',
            'paattymis_pvm': '2021-10-01',
            'lahdejarjestelma': '1'
        }

        update_private_start_and_end_date = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{private_vakapaatos.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{private_vakasuhde.toimipaikka_id}/',
            'alkamis_pvm': '2021-04-18',
            'paattymis_pvm': '2022-05-05',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_update = client_tester2.put(f'/api/v1/varhaiskasvatussuhteet/{public_vakasuhde.id}/', update_public_start_and_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_vakasuhde_update = client_tester5.put(f'/api/v1/varhaiskasvatussuhteet/{private_vakasuhde.id}/', update_private_start_and_end_date)
        assert_status_code(resp_vakasuhde_update, 200)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/', **self.headers)
        resp_lopettaneet_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_lopettaneet_content['count'], existing_lopettaneet_count)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_korjaustiedot_count)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_get(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        self.assertEqual(resp.status_code, 403)

        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_get_alkamis_pvm(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_deleted_varhaiskasvatussuhde(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakasuhde_id = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=1, tunniste='kela_testing_jm03')

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_korjaustiedot_poistetut_count = resp_content['count']

        resp_vakasuhde_delete = client_tester2.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_id}/')
        assert_status_code(resp_vakasuhde_delete, 204)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '091', 'henkilotunnus': '120699-985W', 'tietue': 'K',
                           'vakasuhde_alkamis_pvm': '0001-01-01',
                           'vakasuhde_paattymis_pvm': '0001-01-01',
                           'vakasuhde_alkuperainen_alkamis_pvm': '2021-01-05',
                           'vakasuhde_alkuperainen_paattymis_pvm': '2022-01-03'}
        self.assertEqual(resp_content['count'], existing_korjaustiedot_poistetut_count + 1)
        self.assertIn(expected_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_deleted_varhaiskasvatuspaatos(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos4')
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos_id=vakapaatos.id)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_korjaustiedot_poistetut_count = resp_content['count']

        for vakasuhde in vakasuhteet:
            resp_vakasuhde_delete = client_tester2.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/')
            assert_status_code(resp_vakasuhde_delete, 204)

        resp_vakapaatos_delete = client_tester2.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/')
        assert_status_code(resp_vakapaatos_delete, 204)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '091', 'henkilotunnus': '120699-985W', 'tietue': 'K',
                           'vakasuhde_alkamis_pvm': '0001-01-01',
                           'vakasuhde_paattymis_pvm': '0001-01-01',
                           'vakasuhde_alkuperainen_alkamis_pvm': '2021-01-05',
                           'vakasuhde_alkuperainen_paattymis_pvm': '2022-01-03'}
        self.assertEqual(resp_content['count'], existing_korjaustiedot_poistetut_count + len(vakasuhteet))
        self.assertIn(expected_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_deleted_lapsi(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos4')
        vakasuhteet = Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos_id=vakapaatos.id)
        lapsi = Lapsi.objects.get(id=vakapaatos.lapsi_id)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        existing_korjaustiedot_poistetut_count = resp_content['count']

        for vakasuhde in vakasuhteet:
            resp_vakasuhde_delete = client_tester2.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde.id}/')
            assert_status_code(resp_vakasuhde_delete, 204)

        resp_vakapaatos_delete = client_tester2.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/')
        assert_status_code(resp_vakapaatos_delete, 204)

        resp_lapsi_delete = client_tester2.delete(f'/api/v1/lapset/{lapsi.id}/')
        assert_status_code(resp_lapsi_delete, 204)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        expected_result = {'kotikunta_koodi': '091', 'henkilotunnus': '120699-985W', 'tietue': 'K',
                           'vakasuhde_alkamis_pvm': '0001-01-01',
                           'vakasuhde_paattymis_pvm': '0001-01-01',
                           'vakasuhde_alkuperainen_alkamis_pvm': '2021-01-05',
                           'vakasuhde_alkuperainen_paattymis_pvm': '2022-01-03'}
        self.assertEqual(resp_content['count'], existing_korjaustiedot_poistetut_count + len(vakasuhteet))
        self.assertIn(expected_result, resp_content['results'])

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_instant_delete(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 11
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=1, tunniste='testing-varhaiskasvatuspaatos4')

        resp_kela_api_poistetut = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_poistetut_content = json.loads(resp_kela_api_poistetut.content)
        existing_poistetut_count = resp_poistetut_content['count']

        vakasuhde = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': '/api/v1/toimipaikat/5/',
            'alkamis_pvm': '2021-02-01',
            'paattymis_pvm': '2022-03-02',
            'lahdejarjestelma': '1'
        }

        resp_vakasuhde_create = client_tester2.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde_create, 201)
        create_id = json.loads(resp_vakasuhde_create.content)['id']

        resp_vakasuhde_delete = client_tester2.delete(f'/api/v1/varhaiskasvatussuhteet/{create_id}/')
        assert_status_code(resp_vakasuhde_delete, 204)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_poistetut_count)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_non_applicable_data(self):
        client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 11
        client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 2
        client_tester_kela = SetUpTestClient('kela_luovutuspalvelu').client()
        public_vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma='1', tunniste='kela_testing_public_tilapainen')
        private_vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma='1', tunniste='kela_testing_private')

        resp_kela_api_poistetut = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_poistetut_content = json.loads(resp_kela_api_poistetut.content)
        existing_poistetut_count = resp_poistetut_content['count']

        resp_vakasuhde_update = client_tester2.delete(f'/api/v1/varhaiskasvatussuhteet/{public_vakasuhde.id}/')
        assert_status_code(resp_vakasuhde_update, 204)

        resp_vakasuhde_update = client_tester5.delete(f'/api/v1/varhaiskasvatussuhteet/{private_vakasuhde.id}/')
        assert_status_code(resp_vakasuhde_update, 204)

        resp_kela_api = client_tester_kela.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/', **self.headers)
        resp_content = json.loads(resp_kela_api.content)
        self.assertEqual(resp_content['count'], existing_poistetut_count)

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

    @mock_date_decorator_factory('varda.viewsets_reporting.datetime', '2021-01-01')
    def test_api_error_report_lapset_vakatiedot(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(vakatoimija=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.8925547856499')

        # Make Lapsi over 8 years old
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2000, month=1, day=1))

        # Make Varhaiskasvatussuhde start before Varhaiskasvatuspaatos
        # and remove paattymis_pvm from Varhaiskasvatuspaatos and Varhaiskasvatussuhde
        today = datetime.date(year=2021, month=1, day=1)
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

        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2017, month=1, day=1))

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

        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(paattymis_pvm=today)

        # Set paattymis_pvm for Varhaiskasvatussuhde related Toimipaikka
        Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.2565458382544').update(paattymis_pvm=yesterday)
        resp_4 = client.get(url)
        self._verify_error_report_result(resp_4, ['VS015'])
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).update(paattymis_pvm=None)
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).update(paattymis_pvm=None)
        resp_5 = client.get(url)
        self._verify_error_report_result(resp_5, ['VS015'])

        # Remove Varhaiskasvatussuhde
        Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi).delete()
        resp_6 = client.get(url)
        self._verify_error_report_result(resp_6, ['VS014'])

        # Remove Varhaiskasvatuspaatos
        Varhaiskasvatuspaatos.objects.filter(lapsi=lapsi).delete()
        resp_7 = client.get(url)
        self._verify_error_report_result(resp_7, ['VP012'])

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

        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=today)

        # Set paattymis_pvm for Tyoskentelypaikka related Toimipaikka
        Toimipaikka.objects.filter(tyoskentelypaikat__palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=yesterday)
        resp_4 = client.get(url)
        self._verify_error_report_result(resp_4, ['TA016'])
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=None)
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(paattymis_pvm=None)
        resp_5 = client.get(url)
        self._verify_error_report_result(resp_5, ['TA016'])

        # Remove Tyoskentelypaikka
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        resp_6 = client.get(url)
        self._verify_error_report_result(resp_6, ['TA014'])

        # Remove Palvelussuhde (PidempiPoissaolo must be removed as well)
        PidempiPoissaolo.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        Palvelussuhde.objects.filter(tyontekija=tyontekija).delete()
        resp_7 = client.get(url)
        self._verify_error_report_result(resp_7, ['PS008'])

        # Remove Tutkinto
        Tutkinto.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=tyontekija.henkilo).delete()
        resp_8 = client.get(url)
        self._verify_error_report_result(resp_8, ['TU004'])

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
        Varhaiskasvatussuhde.objects.filter(tunniste='testing-varhaiskasvatussuhde3').update(alkamis_pvm='2017-01-01')

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

    def test_api_error_report_toimipaikat_no_errors(self):
        client = SetUpTestClient('tester10').client()
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        resp_no_errors = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-toimipaikat/')
        assert_status_code(resp_no_errors, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp_no_errors.content)['count'], 0)

    def test_api_error_report_toimipaikat(self):
        today = datetime.date.today()
        client = SetUpTestClient('tester10').client()
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.6727877596658')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-toimipaikat/'

        # Set toiminnallinenpainotus_kytkin and kielipainotus_kytkin True when Toimipaikka does not have
        # painotus objects
        toimipaikka.toiminnallinenpainotus_kytkin = True
        toimipaikka.kielipainotus_kytkin = True
        toimipaikka.save()
        resp_1 = client.get(url)
        assert_status_code(resp_1, status.HTTP_200_OK)
        self._verify_error_report_result(resp_1, ['TO005', 'KP005'])

        # Set toiminnallinenpainotus_kytkin and kielipainotus_kytkin False when Toimipaikka has painotus objects
        ToiminnallinenPainotus.objects.create(toimipaikka=toimipaikka, toimintapainotus_koodi='TP01', alkamis_pvm=today,
                                              changed_by_id=1)
        KieliPainotus.objects.create(toimipaikka=toimipaikka, kielipainotus_koodi='FI', alkamis_pvm=today,
                                     changed_by_id=1)
        toimipaikka.toiminnallinenpainotus_kytkin = False
        toimipaikka.kielipainotus_kytkin = False
        toimipaikka.save()
        resp_2 = client.get(url)
        assert_status_code(resp_2, status.HTTP_200_OK)
        self._verify_error_report_result(resp_2, ['TO004', 'KP004'])

        toimipaikka.toiminnallinenpainotus_kytkin = True
        toimipaikka.kielipainotus_kytkin = True

        # Set paattymis_pvm for Toimipaikka while painotus, vakasuhde, and tyoskentelypaikka objects do not have it
        yesterday = today - datetime.timedelta(days=1)
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        toimipaikka.paattymis_pvm = yesterday
        toimipaikka.save()
        resp_3 = client.get(url)
        assert_status_code(resp_3, status.HTTP_200_OK)
        self._verify_error_report_result(resp_3, ['TO003', 'KP003', 'TP021', 'TP022'])

        # Set paattymis_pvm of painotus, vakasuhde, and tyoskentelypaikka objects to be tomorrow
        tomorrow = today + datetime.timedelta(days=1)
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        resp_4 = client.get(url)
        assert_status_code(resp_4, status.HTTP_200_OK)
        self._verify_error_report_result(resp_4, ['TO002', 'KP002', 'TP021', 'TP022'])

        toimipaikka.paattymis_pvm = today
        toimipaikka.save()
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)

        # Set varhaiskasvatuspaikat to 0 when there are active Varhaiskasvatussuhde objects
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        toimipaikka.varhaiskasvatuspaikat = 0
        toimipaikka.save()
        # Remove tyoskentelypaikat when Toimipaikka is active
        toimipaikka.tyoskentelypaikat.all().delete()
        resp_5 = client.get(url)
        assert_status_code(resp_5, status.HTTP_200_OK)
        self._verify_error_report_result(resp_5, ['TP020', 'TP021', 'TP023'])

    def _verify_error_report_result(self, response, error_code_list):
        assert_status_code(response, status.HTTP_200_OK)
        response_json = json.loads(response.content)

        if not isinstance(error_code_list[0], list):
            error_code_list = [error_code_list]

        self.assertEqual(len(response_json['results']), len(error_code_list))

        for index, error_codes in enumerate(error_code_list):
            self.assertEqual(len(response_json['results'][index]['errors']), len(error_codes))
            response_string = response.content.decode('utf-8')
            for error_code in error_codes:
                self.assertIn(error_code, response_string)

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


def _load_base_data_for_kela_success_testing():
    client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1

    data_henkilo = {
        'henkilotunnus': '071119A884T',
        'etunimet': 'Minna Maija',
        'kutsumanimi': 'Maija',
        'sukunimi': 'Suroinen'
    }
    resp_henkilo = client_tester2.post('/api/v1/henkilot/', data_henkilo)
    assert_status_code(resp_henkilo, 200)
    henkilo_url = json.loads(resp_henkilo.content)['url']

    # public daycare child
    data_lapsi = {
        'henkilo': henkilo_url,
        'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
        'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
        'lahdejarjestelma': '1'
    }
    resp_public_lapsi = client_tester2.post('/api/v1/lapset/', data_lapsi)
    assert_status_code(resp_public_lapsi, 201)

    public_lapsi_url = json.loads(resp_public_lapsi.content)['url']

    data_vakapaatos = {
        'lapsi': public_lapsi_url,
        'tuntimaara_viikossa': 45,
        'jarjestamismuoto_koodi': 'jm03',
        'tilapainen_vaka_kytkin': False,
        'vuorohoito': True,
        'alkamis_pvm': '2021-01-05',
        'hakemus_pvm': '2021-01-01',
        'lahdejarjestelma': '1'
    }

    resp_vakapaatos = client_tester2.post('/api/v1/varhaiskasvatuspaatokset/', data_vakapaatos)
    assert_status_code(resp_vakapaatos, 201)

    vakapaatos_url = json.loads(resp_vakapaatos.content)['url']

    return vakapaatos_url


def _load_base_data_for_kela_error_testing():
    client_tester2 = SetUpTestClient('tester2').client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
    client_tester5 = SetUpTestClient('tester5').client()  # tallentaja, vakajarjestaja 2

    data_henkilo = {
        'henkilotunnus': '071119A884T',
        'etunimet': 'Minna Maija',
        'kutsumanimi': 'Maija',
        'sukunimi': 'Suroinen'
    }
    resp_henkilo = client_tester2.post('/api/v1/henkilot/', data_henkilo)
    assert_status_code(resp_henkilo, 200)

    resp_henkilo = client_tester5.post('/api/v1/henkilot/', data_henkilo)
    assert_status_code(resp_henkilo, 200)

    henkilo_url = json.loads(resp_henkilo.content)['url']

    # public daycare child
    data_public_lapsi = {
        'henkilo': henkilo_url,
        'vakatoimija': '/api/v1/vakajarjestajat/1/',
        'lahdejarjestelma': '1'
    }
    resp_public_lapsi = client_tester2.post('/api/v1/lapset/', data_public_lapsi)
    assert_status_code(resp_public_lapsi, 201)

    public_lapsi_url = json.loads(resp_public_lapsi.content)['url']

    data_private_lapsi = {
        'henkilo': henkilo_url,
        'vakatoimija': '/api/v1/vakajarjestajat/2/',
        'lahdejarjestelma': '1'
    }

    resp_private_lapsi = client_tester5.post('/api/v1/lapset/', data_private_lapsi)
    assert_status_code(resp_private_lapsi, 201)

    private_lapsi_url = json.loads(resp_private_lapsi.content)['url']

    data_private_vakapaatos = {
        'lapsi': private_lapsi_url,
        'tuntimaara_viikossa': 45,
        'jarjestamismuoto_koodi': 'jm04',
        'tilapainen_vaka_kytkin': False,
        'vuorohoito': True,
        'alkamis_pvm': '2021-01-05',
        'hakemus_pvm': '2021-01-01',
        'lahdejarjestelma': '1'
    }

    data_public_vakapaatos = {
        'lapsi': public_lapsi_url,
        'tuntimaara_viikossa': 45,
        'jarjestamismuoto_koodi': 'jm01',
        'tilapainen_vaka_kytkin': True,
        'vuorohoito': True,
        'alkamis_pvm': '2021-01-05',
        'hakemus_pvm': '2021-01-01',
        'lahdejarjestelma': '1'
    }

    resp_public_vakapaatos = client_tester2.post('/api/v1/varhaiskasvatuspaatokset/', data_public_vakapaatos)
    assert_status_code(resp_public_vakapaatos, 201)

    resp_private_vakapaatos = client_tester5.post('/api/v1/varhaiskasvatuspaatokset/', data_private_vakapaatos)
    assert_status_code(resp_public_vakapaatos, 201)

    public_vakapaatos_url = json.loads(resp_public_vakapaatos.content)['url']
    private_vakapaatos_url = json.loads(resp_private_vakapaatos.content)['url']

    return public_vakapaatos_url, private_vakapaatos_url
