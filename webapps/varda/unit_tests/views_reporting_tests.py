import datetime
import json
import time
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from varda.enums.change_type import ChangeType
from varda.enums.koodistot import Koodistot
from varda.misc import decrypt_henkilotunnus
from varda.models import (Henkilo, Huoltaja, Huoltajuussuhde, KieliPainotus, Lapsi, Maksutieto, Palvelussuhde,
                          PaosToiminta, PidempiPoissaolo, Taydennyskoulutus, TaydennyskoulutusTyontekija,
                          TilapainenHenkilosto, ToiminnallinenPainotus, Toimipaikka, Tutkinto, Tyontekija,
                          Tyoskentelypaikka, Organisaatio, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Z2_Code)
from varda.organisation_transformations import transfer_toimipaikat_to_vakajarjestaja
from varda.unit_tests.test_utils import (assert_status_code, assert_validation_error, mock_admin_user,
                                         mock_date_decorator_factory, SetUpTestClient)
from varda.unit_tests.views_tests import mock_check_if_toimipaikka_exists_by_name, mock_create_organisaatio


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
            'tiedonsiirtotilasto': 'http://testserver/api/reporting/v1/tiedonsiirtotilasto/',
            'transfer-outage': 'http://testserver/api/reporting/v1/transfer-outage/',
            'transfer-outage-lahdejarjestelma': 'http://testserver/api/reporting/v1/transfer-outage-lahdejarjestelma/',
            'request-summary': 'http://testserver/api/reporting/v1/request-summary/',
            'yearly-reporting-summary': 'http://testserver/api/reporting/v1/yearly-reporting-summary/'
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

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_luonti_pvm_lte_date_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().date()
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_gte={now}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE020', 'This field must be a datetime string in YYYY-MM-DDTHH:MM:SSZ format.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_luonti_pvm_filter_too_far(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_gte=2018-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_luonti_pvm_filter_no_gte(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_lte=2030-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE021', 'Both datetime field filters are required.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_luonti_pvm_gte_filter_too_far(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_gte=2018-01-01T09:00:00Z', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_filters_wrong_values(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_gte={now}&luonti_pvm_lte={earlier}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_lte', 'GE022', 'Greater than date filter value needs to be before less than date filter.')

    def test_reporting_api_kela_etuusmaksatus_aloittaneet_luonti_pvm_gte_and_lte_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm_gte={earlier}&luonti_pvm_lte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

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
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm_gte=2010-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_gte', 'GE020', 'This field must be a datetime string in YYYY-MM-DDTHH:MM:SSZ format.')

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_get_date_gte_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm_gte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_muutos_pvm_filter_no_gte(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm_lte=2030-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_gte', 'GE021', 'Both datetime field filters are required.')

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_get_correct_date_filters(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm_gte={earlier}&muutos_pvm_lte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_lopettaneet_filters_wrong_values(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm_gte={now}&muutos_pvm_lte={earlier}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_lte', 'GE022', 'Greater than date filter value needs to be before less than date filter.')

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

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_luonti_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm_gte=2018-01-01T00:00:00Z', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_correct_luonti_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm_gte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_luonti_pvm_filter_no_gte(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm_lte=2030-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_gte', 'GE021', 'Both datetime field filters are required.')

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_correct_luonti_pvm_dates_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm_gte={earlier}&luonti_pvm_lte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_filters_wrong_values(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm_gte={now}&luonti_pvm_lte={earlier}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm_lte', 'GE022', 'Greater than date filter value needs to be before less than date filter.')

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

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_get_muutos_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm_gte=2018-01-01T01:00:00%2B00:00', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_gte', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_correct_muutos_pvm_gte_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm_gte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_muutos_pvm_filter_no_gte(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm_lte=2030-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_gte', 'GE021', 'Both datetime field filters are required.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_get_correct_muutos_pvm_filters(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm_gte={earlier}?muutos_pvm_lte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_filters_wrong_values(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm_gte={now}&muutos_pvm_lte={earlier}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm_lte', 'GE022', 'Greater than date filter value needs to be before less than date filter.')

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

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_get_incorrect_poisto_pvm_date_format(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_gte=2018-01-01', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm_gte', 'GE020', 'This field must be a datetime string in YYYY-MM-DDTHH:MM:SSZ format.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_get_incorrect_poisto_pvm(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_gte=2018-01-01T09:00:00Z', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm_gte', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kela_etuusmaksatus_maaraaikaiset_correct_poisto_pvm_filter(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_gte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poisto_pvm_filter_no_gte(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_lte=2030-01-01T09:00:00%2B0300', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm_gte', 'GE021', 'Both datetime field filters are required.')

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_get_correct_poisto_pvm_filters(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_gte={earlier}&poisto_pvm_lte={now}', **self.headers)
        self.assertEqual(resp.status_code, 200)

    def test_reporting_api_kela_etuusmaksatus_korjaustiedot_poistetut_filters_wrong_values(self):
        client = SetUpTestClient('kela_luovutuspalvelu').client()
        now = datetime.datetime.now().astimezone()
        earlier = now - datetime.timedelta(hours=2)
        now = now.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        earlier = earlier.strftime('%Y-%m-%dT%H:%M:%S%z').replace('+', '%2B')
        resp = client.get(f'/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm_gte={now}&poisto_pvm_lte={earlier}', **self.headers)
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm_lte', 'GE022', 'Greater than date filter value needs to be before less than date filter.')

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
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        client = SetUpTestClient('tester10').client()
        resp_empty = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/')
        assert_status_code(resp_empty, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp_empty.content)['count'], 0)

    def test_api_error_report_lapset_no_permissions(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-lapset/'

        # No permissions to Organisaatio
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
        assert_status_code(resp_no_permissions_2, status.HTTP_404_NOT_FOUND)

    def test_api_error_report_lapset_huoltajatiedot(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
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
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(vakatoimija=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.8925547856499')

        # Make Henkilo over 8 years old and not yksiloity
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2000, month=1, day=1),
                                                   vtj_yksiloity=False)

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
        self._verify_error_report_result(resp_1, ['VP013', 'VP002', 'HE017'])

        # Make Henkilo under 8 years old and yksiloity so that errors are not raised
        Henkilo.objects.filter(lapsi=lapsi).update(syntyma_pvm=datetime.date(year=2017, month=1, day=1),
                                                   vtj_yksiloity=True)
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
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
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

    @mock_date_decorator_factory('varda.viewsets_reporting.datetime', '2022-01-01')
    def test_api_error_report_tyontekijat(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        tyontekija = Tyontekija.objects.get(vakajarjestaja=vakajarjestaja, henkilo__henkilo_oid='1.2.246.562.24.2431884920041')

        client = SetUpTestClient('henkilosto_tallentaja_93957375488').client()
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-tyontekijat/'

        # Make Henkilo not yksiloity
        Henkilo.objects.filter(tyontekijat=tyontekija).update(vtj_yksiloity=False)

        # Make Tyoskentelypaikka start before Palvelussuhde
        # and remove paattymis_pvm from Palvelussuhde and Tyoskentelypaikka
        today = datetime.date(year=2022, month=1, day=1)
        yesterday = today - datetime.timedelta(days=1)
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(alkamis_pvm=today, paattymis_pvm=None)
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(alkamis_pvm=yesterday,
                                                                                      paattymis_pvm=None)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA008', 'HE017'])

        # Make Henkilo yksiloity so that error is not raised
        Henkilo.objects.filter(tyontekijat=tyontekija).update(vtj_yksiloity=True)
        # Set alkamis_pvm for Tyoskentelypaikka so that error is not raised
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(alkamis_pvm=today)

        # Set paattymis_pvm for Palvelussuhde
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(paattymis_pvm=today)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA013'])

        # Set paattymis_pvm for Tyoskentelypaikka to be after Palvelussuhde
        tomorrow = today + datetime.timedelta(days=1)
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=tomorrow)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA006'])

        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=today)

        # Set paattymis_pvm for Tyoskentelypaikka related Toimipaikka
        Toimipaikka.objects.filter(tyoskentelypaikat__palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=yesterday)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA016'])
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=None)
        Palvelussuhde.objects.filter(tyontekija=tyontekija).update(paattymis_pvm=None)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA016'])

        # Remove paattymis_pvm from Toimipaikka so that error is not raised
        Toimipaikka.objects.filter(tyoskentelypaikat__palvelussuhde__tyontekija=tyontekija).update(paattymis_pvm=None)

        # Create situations where active Palvelussuhde does not have active Tyoskentelypaikka or PidempiPoissaolo
        palvelussuhde_tunniste = 'testing-palvelussuhde5'
        tyoskentelypaikka_1_tunniste = 'testing-tyoskentylypaikka5-1'
        tyoskentelypaikka_2_tunniste = 'testing-tyoskentylypaikka5-2'
        pidempi_poissaolo_tunniste = 'pidempi_poissaolo500'
        Tyoskentelypaikka.objects.filter(tunniste=tyoskentelypaikka_1_tunniste).update(paattymis_pvm=yesterday)
        resp = client.get(url)
        self._verify_error_report_result(resp, [])
        Tyoskentelypaikka.objects.filter(tunniste=tyoskentelypaikka_2_tunniste).update(paattymis_pvm=yesterday)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['PS009'])
        pidempi_poissaolo = {
            'lahdejarjestelma': '1',
            'palvelussuhde_tunniste': palvelussuhde_tunniste,
            'alkamis_pvm': '2022-01-01',
            'paattymis_pvm': '2023-01-01',
            'tunniste': pidempi_poissaolo_tunniste
        }
        assert_status_code(client.post('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo), status.HTTP_201_CREATED)
        resp = client.get(url)
        self._verify_error_report_result(resp, [])
        PidempiPoissaolo.objects.filter(tunniste=pidempi_poissaolo_tunniste).update(alkamis_pvm='2022-06-01')
        resp = client.get(url)
        self._verify_error_report_result(resp, ['PS009'])

        # Remove Tyoskentelypaikka
        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TA014'])

        # Remove Palvelussuhde (PidempiPoissaolo must be removed as well)
        PidempiPoissaolo.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        Palvelussuhde.objects.filter(tyontekija=tyontekija).delete()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['PS008'])

        # Remove Tutkinto
        Tutkinto.objects.filter(vakajarjestaja=vakajarjestaja, henkilo=tyontekija.henkilo).delete()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TU004'])

    def test_api_error_report_tyontekijat_no_permissions(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-tyontekijat/'

        # No view_tyontekija permissions
        client_no_permissions_1 = SetUpTestClient('tester2').client()
        resp_no_permissions_1 = client_no_permissions_1.get(url)
        assert_status_code(resp_no_permissions_1, status.HTTP_404_NOT_FOUND)

        # No permissions to correct groups
        client_no_permissions_2 = SetUpTestClient('tyontekija_toimipaikka_tallentaja_9395737548815').client()
        resp_no_permissions_2 = client_no_permissions_2.get(url)
        assert_status_code(resp_no_permissions_2, status.HTTP_404_NOT_FOUND)

        # No permissions to correct Organisaatio
        client_no_permissions_3 = SetUpTestClient('henkilosto_tallentaja_93957375488').client()
        resp_no_permissions_3 = client_no_permissions_3.get(url)
        assert_status_code(resp_no_permissions_3, status.HTTP_404_NOT_FOUND)

    def test_api_error_report_filter(self):
        vakajarjestaja_1 = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        vakajarjestaja_2 = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        Varhaiskasvatussuhde.objects.filter(tunniste='testing-varhaiskasvatussuhde3').update(alkamis_pvm='2017-01-01')

        lapsi_url = f'/api/v1/vakajarjestajat/{vakajarjestaja_1.id}/error-report-lapset/'
        lapsi_client = SetUpTestClient('tester2').client()

        resp = lapsi_client.get(lapsi_url)
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertIn('VP002', resp_string)
        self.assertIn('VP013', resp_string)
        self.assertIn('1.2.246.562.24.6815981182311', resp_string)
        self.assertIn('1.2.246.562.24.49084901392', resp_string)

        resp = lapsi_client.get(f'{lapsi_url}?error=VP002')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertNotIn('VP013', resp_string)
        self.assertIn('VP002', resp_string)

        resp = lapsi_client.get(f'{lapsi_url}?error=noerrorlikethis')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(0, len(json.loads(resp.content)['results']))

        resp = lapsi_client.get(f'{lapsi_url}?search=1.2.246.562.24.49084901392')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertNotIn('1.2.246.562.24.6815981182311', resp_string)
        self.assertIn('1.2.246.562.24.49084901392', resp_string)

        toimipaikka_client = SetUpTestClient('pkvakajarjestaja2').client()
        toimipaikka_url = f'/api/v1/vakajarjestajat/{vakajarjestaja_2.id}/error-report-toimipaikat/'
        resp = toimipaikka_client.get(toimipaikka_url)
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertIn('TP023', resp_string)
        self.assertIn('TO005', resp_string)
        self.assertIn('KP005', resp_string)
        self.assertIn('Espoo yksityinen', resp_string)
        self.assertIn('Espoo_3', resp_string)

        resp = toimipaikka_client.get(f'{toimipaikka_url}?error=TP023&search=Espoo_3')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertNotIn('TO005', resp_string)
        self.assertNotIn('KP005', resp_string)
        self.assertNotIn('Espoo yksityinen', resp_string)
        self.assertIn('TP023', resp_string)
        self.assertIn('Espoo_3', resp_string)

        resp = toimipaikka_client.get(f'{toimipaikka_url}?error=noerrorlikethis')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(0, len(json.loads(resp.content)['results']))

        tyontekija_client = SetUpTestClient('tyontekija_tallentaja').client()
        tyontekija_url = f'/api/v1/vakajarjestajat/{vakajarjestaja_1.id}/error-report-tyontekijat/'
        resp = tyontekija_client.get(tyontekija_url)
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertIn('TA014', resp_string)
        self.assertIn('PS008', resp_string)
        self.assertIn('Calervo', resp_string)
        self.assertIn('Bella', resp_string)

        resp = tyontekija_client.get(f'{tyontekija_url}?error=TA014')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertIn('TA014', resp_string)
        self.assertNotIn('PS008', resp_string)

        resp = tyontekija_client.get(f'{tyontekija_url}?error=noerrorlikethis')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(0, len(json.loads(resp.content)['results']))

        resp = tyontekija_client.get(f'{tyontekija_url}?search=BeL')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_string = resp.content.decode('utf8')
        self.assertNotIn('Calervo', resp_string)
        self.assertIn('Bella', resp_string)

    def test_api_error_report_toimipaikat_no_errors(self):
        client = SetUpTestClient('tester10').client()
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        resp_no_errors = client.get(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-toimipaikat/')
        assert_status_code(resp_no_errors, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp_no_errors.content)['count'], 0)

    @mock_date_decorator_factory('varda.viewsets_reporting.datetime', '2022-01-01')
    def test_api_error_report_toimipaikat(self):
        today = datetime.date(year=2022, month=1, day=1)
        yesterday = today - datetime.timedelta(days=1)
        tomorrow = today + datetime.timedelta(days=1)
        client = SetUpTestClient('tester10').client()
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.2565458382544')
        url = f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/error-report-toimipaikat/'

        # Create situations where toimipaikka has passive kasvatusopillinen_jarjestelma_koodi
        toimipaikka.kasvatusopillinen_jarjestelma_koodi = 'kj99'
        toimipaikka.save()
        kj99_code = Z2_Code.objects.get(koodisto__name=Koodistot.kasvatusopillinen_jarjestelma_koodit.value,
                                        code_value__iexact='kj99')
        # Is passive today but Toimipaikka is still active
        kj99_code.paattymis_pvm = yesterday
        kj99_code.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TP027'])
        # Ends before Toimipaikka starts
        kj99_code.paattymis_pvm = '2018-04-30'
        kj99_code.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TP027'])
        # Ends before Toimipaikka ends
        kj99_code.paattymis_pvm = '2020-04-30'
        kj99_code.save()
        toimipaikka.paattymis_pvm = '2030-01-01'
        toimipaikka.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TP027'])

        # Reset paattymis_pvm and kasvatusopillinen_jarjestelma_koodi so that errors are not raised
        toimipaikka.paattymis_pvm = None
        toimipaikka.kasvatusopillinen_jarjestelma_koodi = 'kj03'
        toimipaikka.save()

        # Set toiminnallinenpainotus_kytkin and kielipainotus_kytkin True when Toimipaikka does not have
        # painotus objects
        toimipaikka.toiminnallinenpainotus_kytkin = True
        toimipaikka.kielipainotus_kytkin = True
        toimipaikka.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TO005', 'KP005'])

        # Set toiminnallinenpainotus_kytkin and kielipainotus_kytkin False when Toimipaikka has painotus objects
        ToiminnallinenPainotus.objects.create(toimipaikka=toimipaikka, toimintapainotus_koodi='TP01', alkamis_pvm=today)
        KieliPainotus.objects.create(toimipaikka=toimipaikka, kielipainotus_koodi='FI', alkamis_pvm=today)
        toimipaikka.toiminnallinenpainotus_kytkin = False
        toimipaikka.kielipainotus_kytkin = False
        toimipaikka.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TO004', 'KP004'])

        toimipaikka.toiminnallinenpainotus_kytkin = True
        toimipaikka.kielipainotus_kytkin = True

        # Set paattymis_pvm for Toimipaikka while painotus, vakasuhde, and tyoskentelypaikka objects do not have it
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=None)
        toimipaikka.paattymis_pvm = yesterday
        toimipaikka.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TO003', 'KP003', 'TP021', 'TP022'])

        # Set paattymis_pvm of painotus, vakasuhde, and tyoskentelypaikka objects to be tomorrow
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TO002', 'KP002', 'TP021', 'TP022'])

        toimipaikka.paattymis_pvm = today
        toimipaikka.save()
        ToiminnallinenPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        KieliPainotus.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)
        Tyoskentelypaikka.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=today)

        # Remove tyoskentelypaikat when Toimipaikka is active
        toimipaikka.tyoskentelypaikat.all().delete()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TP023'])

        # Set varhaiskasvatuspaikat to 0 when there are active Varhaiskasvatussuhde objects
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka).update(paattymis_pvm=tomorrow)
        toimipaikka.varhaiskasvatuspaikat = 0
        toimipaikka.save()
        resp = client.get(url)
        self._verify_error_report_result(resp, ['TP020', 'TP021'])

    def _verify_error_report_result(self, response, error_code_list):
        assert_status_code(response, status.HTTP_200_OK)
        response_json = json.loads(response.content)

        if len(error_code_list) > 0 and not isinstance(error_code_list[0], list):
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

    def test_tk_organisaatiot_all(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        vakajarjestaja_count = 0
        toimipaikka_count = 0
        kielipainotus_count = 0
        toiminnallinen_painotus_count = 0

        url = '/api/reporting/v1/tilastokeskus/organisaatiot/'
        while url:
            resp = client.get(url)
            response = json.loads(resp.content)
            for result in response['results']:
                vakajarjestaja_count += 1
                for toimipaikka in result['toimipaikat']:
                    toimipaikka_count += 1
                    kielipainotus_count += len(toimipaikka['kielipainotukset'])
                    toiminnallinen_painotus_count += len(toimipaikka['toiminnalliset_painotukset'])
            url = response['next']

        self.assertEqual(Organisaatio.objects.count(), vakajarjestaja_count)
        self.assertEqual(Toimipaikka.objects.count(), toimipaikka_count)
        self.assertEqual(KieliPainotus.objects.count(), kielipainotus_count)
        self.assertEqual(ToiminnallinenPainotus.objects.count(), toiminnallinen_painotus_count)

    def test_tk_organisaatiot_invalid_format(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        resp = client.get('/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt=2021-01-01T00:00:00'
                          '&datetime_lte=2022-01-0100:00:00%2B0300')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'datetime_gt', 'GE020',
                                'This field must be a datetime string in YYYY-MM-DDTHH:MM:SSZ format.')
        assert_validation_error(resp, 'datetime_lte', 'GE020',
                                'This field must be a datetime string in YYYY-MM-DDTHH:MM:SSZ format.')

    def test_tk_organisaatiot_no_change(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        vakajarjestaja_id = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.93957375488').id
        toimipaikka_id = Toimipaikka.objects.get(tunniste='testing-toimipaikka1').id
        kielipainotus = {
            'toimipaikka_tunniste': 'testing-toimipaikka1',
            'kielipainotus_koodi': 'de',
            'alkamis_pvm': '2018-09-05',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, status.HTTP_201_CREATED)
        kielipainotus_id = json.loads(resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_kielipainotus_action(self, resp, vakajarjestaja_id, toimipaikka_id, kielipainotus_id,
                                      ChangeType.CREATED.value)

        datetime_gt_2 = _get_iso_datetime_now()
        resp = client.delete(f'/api/v1/kielipainotukset/{kielipainotus_id}/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_kielipainotus_action(self, resp, vakajarjestaja_id, toimipaikka_id, kielipainotus_id,
                                      ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        # Object was created and deleted within the time range
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    @mock.patch('varda.organisaatiopalvelu.check_if_toimipaikka_exists_by_name',
                mock_check_if_toimipaikka_exists_by_name)
    @mock.patch('varda.organisaatiopalvelu.create_organisaatio',
                mock_create_organisaatio)
    def test_tk_organisaatiot_modifified_displayed_as_created(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        vakajarjestaja_id = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489').id
        toimipaikka = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja_id}/',
            'nimi': 'Uusi toimipaikka',
            'kayntiosoite': 'Katukaksi',
            'kayntiosoite_postitoimipaikka': 'Postitoimipaikkakolme',
            'kayntiosoite_postinumero': '00109',
            'postiosoite': 'Katukaksi',
            'postitoimipaikka': 'Postitoimipaikkakolme',
            'postinumero': '00109',
            'kunta_koodi': '091',
            'puhelinnumero': '+35810123456',
            'sahkopostiosoite': 'test2@domain.com',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI', 'SV'],
            'jarjestamismuoto_koodi': ['jm01'],
            'varhaiskasvatuspaikat': 200,
            'alkamis_pvm': '2020-09-02',
            'paattymis_pvm': '2021-09-02',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_201_CREATED)
        toimipaikka_id = json.loads(resp.content)['id']

        datetime_gt_2 = _get_iso_datetime_now()
        toimipaikka_patch = {
            'puhelinnumero': '+35810123457'
        }
        resp = client.patch(f'/api/v1/toimipaikat/{toimipaikka_id}/', toimipaikka_patch)
        assert_status_code(resp, status.HTTP_200_OK)

        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        toimipaikka_result = json.loads(resp.content)['results'][0]['toimipaikat'][0]
        self.assertEqual(toimipaikka_result['id'], toimipaikka_id)
        self.assertEqual(toimipaikka_result['action'], ChangeType.CREATED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte}')
        toimipaikka_result = json.loads(resp.content)['results'][0]['toimipaikat'][0]
        self.assertEqual(toimipaikka_result['id'], toimipaikka_id)
        self.assertEqual(toimipaikka_result['action'], ChangeType.MODIFIED.value)

    def test_tk_organisaatiot_nested_delete(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        toimipaikka = Toimipaikka.objects.get(tunniste='testing-toimipaikka6')
        toimipaikka_id = toimipaikka.id
        kielipainotus = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'kielipainotus_koodi': 'de',
            'alkamis_pvm': '2018-09-05',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, status.HTTP_201_CREATED)
        kielipainotus_id = json.loads(resp.content)['id']
        toiminnallinen_painotus = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'toimintapainotus_koodi': 'tp01',
            'alkamis_pvm': '2018-09-05',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinen_painotus)
        assert_status_code(resp, status.HTTP_201_CREATED)
        toiminnallinen_painotus_id = json.loads(resp.content)['id']

        datetime_gt = _get_iso_datetime_now()
        assert_status_code(client.delete(f'/api/v1/kielipainotukset/{kielipainotus_id}/'), status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/toiminnallisetpainotukset/{toiminnallinen_painotus_id}/'),
                           status.HTTP_204_NO_CONTENT)
        PaosToiminta.objects.filter(paos_toimipaikka=toimipaikka).delete()
        toimipaikka.delete()
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        toimipaikka_result = json.loads(resp.content)['results'][0]['toimipaikat'][0]
        self.assertEqual(toimipaikka_result['id'], toimipaikka_id)
        self.assertEqual(toimipaikka_result['action'], ChangeType.DELETED.value)
        kielipainotus_result = toimipaikka_result['kielipainotukset'][0]
        self.assertEqual(kielipainotus_result['id'], kielipainotus_id)
        self.assertEqual(kielipainotus_result['action'], ChangeType.DELETED.value)
        toiminnallinen_painotus_result = toimipaikka_result['toiminnalliset_painotukset'][0]
        self.assertEqual(toiminnallinen_painotus_result['id'], toiminnallinen_painotus_id)
        self.assertEqual(toiminnallinen_painotus_result['action'], ChangeType.DELETED.value)

    def test_tk_vakatiedot_all(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        # Initialize count variables
        lapsi_count = 0
        huoltajuussuhde_count = 0
        maksutieto_count = 0
        vakapaatos_count = 0
        vakasuhde_count = 0

        url = '/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/'
        while url:
            resp = client.get(url)
            response = json.loads(resp.content)
            for result in response['results']:
                lapsi_count += 1
                huoltajuussuhde_count += len(result['huoltajat'])
                maksutieto_count += len(result['maksutiedot'])
                for vakapaatos in result['varhaiskasvatuspaatokset']:
                    vakapaatos_count += 1
                    vakasuhde_count += len(vakapaatos['varhaiskasvatussuhteet'])
            url = response['next']

        self.assertEqual(Lapsi.objects.count(), lapsi_count)
        self.assertEqual(Huoltajuussuhde.objects.count(), huoltajuussuhde_count)
        self.assertEqual(Maksutieto.objects.count(), maksutieto_count)
        self.assertEqual(Varhaiskasvatuspaatos.objects.count(), vakapaatos_count)
        self.assertEqual(Varhaiskasvatussuhde.objects.count(), vakasuhde_count)

    def test_tk_vakatiedot_no_change(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi3').id
        vakapaatos_id = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos3').id
        vakasuhde = {
            'varhaiskasvatuspaatos_tunniste': 'testing-varhaiskasvatuspaatos3',
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'alkamis_pvm': '2018-09-05',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp, status.HTTP_201_CREATED)
        vakasuhde_id = json.loads(resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_vakasuhde_action(self, resp, lapsi_id, vakapaatos_id, vakasuhde_id, ChangeType.CREATED.value)

        datetime_gt_2 = _get_iso_datetime_now()
        resp = client.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_id}/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_vakasuhde_action(self, resp, lapsi_id, vakapaatos_id, vakasuhde_id, ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        # Object was created and deleted within the time range
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_vakatiedot_nested_delete(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        vakasuhde_1_id = Varhaiskasvatussuhde.objects.get(tunniste='testing-varhaiskasvatussuhde10').id
        vakasuhde_2_id = Varhaiskasvatussuhde.objects.get(tunniste='kela_testing_private').id
        vakapaatos_1_id = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos10').id
        vakapaatos_2_id = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos_kela_private').id
        maksutieto_id = Maksutieto.objects.get(tunniste='testing-maksutieto5').id
        lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi10').id

        assert_status_code(client.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_1_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/varhaiskasvatussuhteet/{vakasuhde_2_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_1_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_2_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/maksutiedot/{maksutieto_id}/'), status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/v1/lapset/{lapsi_id}/'), status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.DELETED.value)
        for vakapaatos_result in lapsi_result['varhaiskasvatuspaatokset']:
            self.assertIn(vakapaatos_result['id'], (vakapaatos_1_id, vakapaatos_2_id,))
            self.assertEqual(vakapaatos_result['action'], ChangeType.DELETED.value)
            vakasuhde_result = vakapaatos_result['varhaiskasvatussuhteet'][0]
            self.assertIn(vakasuhde_result['id'], (vakasuhde_1_id, vakasuhde_2_id,))
            self.assertEqual(vakasuhde_result['action'], ChangeType.DELETED.value)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.DELETED.value)

    def test_tk_vakatiedot_huoltaja(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi2').id
        henkilo_obj = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.5826267847674')
        huoltaja_id = Huoltaja.objects.get_or_create(henkilo=henkilo_obj)[0].id

        datetime_gt = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt
        time.sleep(0.1)
        huoltajuussuhde_obj = Huoltajuussuhde.objects.create(huoltaja_id=huoltaja_id, lapsi_id=lapsi_id,
                                                             voimassa_kytkin=True)
        huoltajuussuhde_id = huoltajuussuhde_obj.id
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['huoltajat']), 1)
        huoltaja_result = lapsi_result['huoltajat'][0]
        self.assertEqual(huoltaja_result['id'], huoltajuussuhde_id)
        self.assertEqual(huoltaja_result['action'], ChangeType.CREATED.value)
        self.assertEqual(huoltaja_result['henkilo_oid'], '1.2.246.562.24.5826267847674')
        self.assertEqual(huoltaja_result['henkilotunnus'], '100646-792P')

        datetime_gt_2 = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt_2
        time.sleep(0.1)
        henkilo_obj.aidinkieli_koodi = 'SV'
        henkilo_obj.save()
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['huoltajat']), 1)
        huoltaja_result = lapsi_result['huoltajat'][0]
        self.assertEqual(huoltaja_result['id'], huoltajuussuhde_id)
        self.assertEqual(huoltaja_result['action'], ChangeType.MODIFIED.value)
        self.assertEqual(huoltaja_result['henkilo_oid'], '1.2.246.562.24.5826267847674')
        self.assertEqual(huoltaja_result['henkilotunnus'], '100646-792P')

        datetime_gt_3 = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt_3
        time.sleep(0.1)
        huoltajuussuhde_obj.delete()
        datetime_lte_3 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_3}'
                          f'&datetime_lte={datetime_lte_3}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['huoltajat']), 1)
        huoltaja_result = lapsi_result['huoltajat'][0]
        self.assertEqual(huoltaja_result['id'], huoltajuussuhde_id)
        self.assertEqual(huoltaja_result['action'], ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_3}')
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

        datetime_gt_4 = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt_4
        time.sleep(0.1)
        henkilo_obj.aidinkieli_koodi = 'FI'
        henkilo_obj.save()
        datetime_lte_4 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_4}'
                          f'&datetime_lte={datetime_lte_4}')
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_vakatiedot_maksutieto(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi11').id
        huoltaja_1 = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.2434693467574')
        huoltaja_1_hetu = decrypt_henkilotunnus(huoltaja_1.henkilotunnus)
        huoltaja_2 = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.3367432256266')
        huoltaja_2_hetu = decrypt_henkilotunnus(huoltaja_2.henkilotunnus)

        maksutieto = {
            'lapsi': f'/api/v1/lapset/{lapsi_id}/',
            'huoltajat': [{
                'henkilotunnus': huoltaja_1_hetu,
                'etunimet': huoltaja_1.etunimet,
                'sukunimi': huoltaja_1.sukunimi,
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-02-01',
            'lahdejarjestelma': '1'
        }

        datetime_gt = _get_iso_datetime_now()
        maksutieto_resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(maksutieto_resp, status.HTTP_201_CREATED)
        maksutieto_id = json.loads(maksutieto_resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['maksutiedot']), 1)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(maksutieto_result['huoltajat'],
                              [{'henkilotunnus': huoltaja_1_hetu, 'henkilo_oid': huoltaja_1.henkilo_oid}])

        maksutieto_patch = {
            'huoltajat_add': [{
                'henkilotunnus': huoltaja_2_hetu,
                'etunimet': huoltaja_2.etunimet,
                'sukunimi': huoltaja_2.sukunimi,
            }]
        }

        datetime_gt_2 = _get_iso_datetime_now()
        assert_status_code(client.patch(f'/api/v1/maksutiedot/{maksutieto_id}/', json.dumps(maksutieto_patch),
                                        content_type='application/json'), status.HTTP_200_OK)
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['maksutiedot']), 1)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.MODIFIED.value)
        self.assertCountEqual(maksutieto_result['huoltajat'],
                              [{'henkilotunnus': huoltaja_1_hetu, 'henkilo_oid': huoltaja_1.henkilo_oid},
                               {'henkilotunnus': huoltaja_2_hetu, 'henkilo_oid': huoltaja_2.henkilo_oid}])

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_2}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['maksutiedot']), 1)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(maksutieto_result['huoltajat'],
                              [{'henkilotunnus': huoltaja_1_hetu, 'henkilo_oid': huoltaja_1.henkilo_oid},
                               {'henkilotunnus': huoltaja_2_hetu, 'henkilo_oid': huoltaja_2.henkilo_oid}])

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['maksutiedot']), 1)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(maksutieto_result['huoltajat'],
                              [{'henkilotunnus': huoltaja_1_hetu, 'henkilo_oid': huoltaja_1.henkilo_oid}])

        datetime_gt_3 = _get_iso_datetime_now()
        assert_status_code(client.delete(f'/api/v1/maksutiedot/{maksutieto_id}/'), status.HTTP_204_NO_CONTENT)
        datetime_lte_3 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_3}'
                          f'&datetime_lte={datetime_lte_3}')
        lapsi_result = _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(lapsi_result['maksutiedot']), 1)
        maksutieto_result = lapsi_result['maksutiedot'][0]
        self.assertEqual(maksutieto_result['id'], maksutieto_id)
        self.assertEqual(maksutieto_result['action'], ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_3}')
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_vakatiedot_henkilo(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        henkilo = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.4473262898463')
        original_lapsi_id = Lapsi.objects.get(tunniste='testing-lapsi15').id

        lapsi = {
            'henkilo_oid': henkilo.henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1'
        }
        datetime_gt = _get_iso_datetime_now()
        resp_lapsi = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi, status.HTTP_201_CREATED)
        lapsi_id = json.loads(resp_lapsi.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _validate_tk_basic_single_result(self, resp, lapsi_id, ChangeType.CREATED.value)

        datetime_gt_2 = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt_2
        time.sleep(0.1)
        henkilo.aidinkieli_koodi = 'SV'
        henkilo.save()
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        results = json.loads(resp.content)['results']
        self.assertEqual(len(results), 2)
        for lapsi_result in results:
            self.assertEqual(lapsi_result['action'], ChangeType.MODIFIED.value)
            self.assertIn(lapsi_result['id'], (original_lapsi_id, lapsi_id,))

        assert_status_code(client.delete(f'/api/v1/lapset/{lapsi_id}/'), status.HTTP_204_NO_CONTENT)
        datetime_lte_3 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_3}')
        _validate_tk_basic_single_result(self, resp, original_lapsi_id, ChangeType.MODIFIED.value)

    def test_tk_henkilostotiedot_all(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        tyontekija_count = 0
        tutkinto_count = 0
        palvelussuhde_count = 0
        tyoskentelypaikka_count = 0
        pidempi_poissaolo_count = 0
        taydennyskoulutus_id_set = set()
        taydennyskoulutus_tyontekija_count = 0

        url = '/api/reporting/v1/tilastokeskus/henkilostotiedot/'
        while url:
            resp = client.get(url)
            response = json.loads(resp.content)
            for result in response['results']:
                tyontekija_count += 1
                tutkinto_count += len(result['tutkinnot'])
                for palvelussuhde in result['palvelussuhteet']:
                    palvelussuhde_count += 1
                    tyoskentelypaikka_count += len(palvelussuhde['tyoskentelypaikat'])
                    pidempi_poissaolo_count += len(palvelussuhde['pidemmat_poissaolot'])
                for taydennyskoulutus in result['taydennyskoulutukset']:
                    taydennyskoulutus_id_set.add(taydennyskoulutus['id'])
                    taydennyskoulutus_tyontekija_count += len(taydennyskoulutus['tehtavanimikkeet'])
            url = response['next']

        self.assertEqual(Tyontekija.objects.count(), tyontekija_count)
        self.assertEqual(Tutkinto.objects.count(), tutkinto_count)
        self.assertEqual(Palvelussuhde.objects.count(), palvelussuhde_count)
        self.assertEqual(Tyoskentelypaikka.objects.count(), tyoskentelypaikka_count)
        self.assertEqual(PidempiPoissaolo.objects.count(), pidempi_poissaolo_count)
        self.assertEqual(Taydennyskoulutus.objects.count(), len(taydennyskoulutus_id_set))
        self.assertEqual(TaydennyskoulutusTyontekija.objects.count(), taydennyskoulutus_tyontekija_count)

    def test_tk_henkilostotiedot_tyoskentelypaikka_no_change(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        tyontekija_id = Tyontekija.objects.get(tunniste='testing-tyontekija2').id
        palvelussuhde_id = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2').id
        tyoskentelypaikka = {
            'palvelussuhde_tunniste': 'testing-palvelussuhde2',
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'alkamis_pvm': '2021-09-05',
            'paattymis_pvm': '2022-01-01',
            'tehtavanimike_koodi': '77826',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(resp, status.HTTP_201_CREATED)
        tyoskentelypaikka_id = json.loads(resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_henkilostotieto_action(self, resp, tyontekija_id, palvelussuhde_id, ChangeType.CREATED.value,
                                        model=Tyoskentelypaikka, instance_id=tyoskentelypaikka_id)

        datetime_gt_2 = _get_iso_datetime_now()
        resp = client.delete(f'/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka_id}/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_henkilostotieto_action(self, resp, tyontekija_id, palvelussuhde_id, ChangeType.DELETED.value,
                                        model=Tyoskentelypaikka, instance_id=tyoskentelypaikka_id)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        # Object was created and deleted within the time range
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_henkilostotiedot_pidempi_poissaolo_no_change(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        tyontekija_id = Tyontekija.objects.get(tunniste='testing-tyontekija2').id
        palvelussuhde_id = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2').id
        pidempi_poissaolo = {
            'palvelussuhde_tunniste': 'testing-palvelussuhde2',
            'alkamis_pvm': '2021-09-05',
            'paattymis_pvm': '2023-01-01',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        pidempi_poissaolo_id = json.loads(resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_henkilostotieto_action(self, resp, tyontekija_id, palvelussuhde_id, ChangeType.CREATED.value,
                                        model=PidempiPoissaolo, instance_id=pidempi_poissaolo_id)

        datetime_gt_2 = _get_iso_datetime_now()
        resp = client.delete(f'/api/henkilosto/v1/pidemmatpoissaolot/{pidempi_poissaolo_id}/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte}')
        _test_tk_henkilostotieto_action(self, resp, tyontekija_id, palvelussuhde_id, ChangeType.DELETED.value,
                                        model=PidempiPoissaolo, instance_id=pidempi_poissaolo_id)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        # Object was created and deleted within the time range
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_henkilostotiedot_nested_delete(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        datetime_gt = _get_iso_datetime_now()
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija7')
        tyontekija_id = tyontekija.id
        tutkinto_id = Tutkinto.objects.get(henkilo=tyontekija.henkilo, vakajarjestaja=tyontekija.vakajarjestaja).id
        taydennyskoulutus_id = Taydennyskoulutus.objects.get(tunniste='testing-taydennyskoulutus4').id
        tyoskentelypaikka_id = Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentylypaikka7').id
        pidempi_poissaolo_id = PidempiPoissaolo.objects.get(tunniste='testing-pidempipoissaolo3').id
        palvelussuhde_id = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde7').id

        assert_status_code(client.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/henkilosto/v1/pidemmatpoissaolot/{pidempi_poissaolo_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/henkilosto/v1/tutkinnot/{tutkinto_id}/'),
                           status.HTTP_204_NO_CONTENT)
        assert_status_code(client.delete(f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/'),
                           status.HTTP_204_NO_CONTENT)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        tyontekija_result = json.loads(resp.content)['results'][0]
        self.assertEqual(tyontekija_result['id'], tyontekija_id)
        self.assertEqual(tyontekija_result['action'], ChangeType.DELETED.value)
        palvelussuhde_result = tyontekija_result['palvelussuhteet'][0]
        self.assertEqual(palvelussuhde_result['id'], palvelussuhde_id)
        self.assertEqual(palvelussuhde_result['action'], ChangeType.DELETED.value)
        tyoskentelypaikka_result = palvelussuhde_result['tyoskentelypaikat'][0]
        self.assertEqual(tyoskentelypaikka_result['id'], tyoskentelypaikka_id)
        self.assertEqual(tyoskentelypaikka_result['action'], ChangeType.DELETED.value)
        pidempi_poissaolo_result = palvelussuhde_result['pidemmat_poissaolot'][0]
        self.assertEqual(pidempi_poissaolo_result['id'], pidempi_poissaolo_id)
        self.assertEqual(pidempi_poissaolo_result['action'], ChangeType.DELETED.value)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.DELETED.value)
        tutkinto_result = tyontekija_result['tutkinnot'][0]
        self.assertEqual(tutkinto_result['id'], tutkinto_id)
        self.assertEqual(tutkinto_result['action'], ChangeType.DELETED.value)

    def test_tk_henkilostotiedot_taydennyskoulutus(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        tyontekija_id = Tyontekija.objects.get(tunniste='testing-tyontekija1').id
        tyontekija_2_id = Tyontekija.objects.get(tunniste='testing-tyontekija2').id

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{
                'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/',
                'tehtavanimike_koodi': '39407'
            }],
            'nimi': 'Testikoulutus20',
            'suoritus_pvm': '2021-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1'
        }

        datetime_gt = _get_iso_datetime_now()
        taydennyskoulutus_resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/',
                                             json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(taydennyskoulutus_resp, status.HTTP_201_CREATED)
        taydennyskoulutus_id = json.loads(taydennyskoulutus_resp.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], ['39407'])

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat_add': [{
                'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/',
                'tehtavanimike_koodi': '64212'
            }]
        }

        datetime_gt_2 = _get_iso_datetime_now()
        assert_status_code(client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/',
                                        json.dumps(taydennyskoulutus_patch), content_type='application/json'),
                           status.HTTP_200_OK)
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.MODIFIED.value)
        self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], ['39407', '64212'])

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_2}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], ['39407', '64212'])

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.CREATED.value)
        self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], ['39407'])

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat_add': [{
                'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_2_id}/',
                'tehtavanimike_koodi': '77826'
            }]
        }

        datetime_gt_3 = _get_iso_datetime_now()
        assert_status_code(client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/',
                                        json.dumps(taydennyskoulutus_patch), content_type='application/json'),
                           status.HTTP_200_OK)
        datetime_lte_3 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_3}'
                          f'&datetime_lte={datetime_lte_3}')
        result_list = json.loads(resp.content)['results']
        self.assertEqual(len(result_list), 2)
        for result in result_list:
            result_id = result['id']
            self.assertIn(result_id, [tyontekija_id, tyontekija_2_id])
            self.assertEqual(result['action'], ChangeType.UNCHANGED.value)
            self.assertEqual(len(result['taydennyskoulutukset']), 1)
            taydennyskoulutus_result = result['taydennyskoulutukset'][0]
            self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
            self.assertEqual(taydennyskoulutus_result['action'], ChangeType.MODIFIED.value)
            tehtavanimike_list = ['39407', '64212'] if result_id == tyontekija_id else ['77826']
            self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], tehtavanimike_list)

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat_remove': [{
                'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/',
                'tehtavanimike_koodi': '39407'
            }, {
                'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/',
                'tehtavanimike_koodi': '64212'
            }]
        }

        datetime_gt_4 = _get_iso_datetime_now()
        assert_status_code(client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/',
                                        json.dumps(taydennyskoulutus_patch), content_type='application/json'),
                           status.HTTP_200_OK)
        datetime_lte_4 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_4}'
                          f'&datetime_lte={datetime_lte_4}')
        result_list = json.loads(resp.content)['results']
        self.assertEqual(len(result_list), 2)
        for result in result_list:
            result_id = result['id']
            self.assertIn(result_id, [tyontekija_id, tyontekija_2_id])
            self.assertEqual(result['action'], ChangeType.UNCHANGED.value)
            self.assertEqual(len(result['taydennyskoulutukset']), 1)
            taydennyskoulutus_result = result['taydennyskoulutukset'][0]
            self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
            self.assertEqual(taydennyskoulutus_result['action'], ChangeType.MODIFIED.value)
            tehtavanimike_list = [] if result_id == tyontekija_id else ['77826']
            self.assertCountEqual(taydennyskoulutus_result['tehtavanimikkeet'], tehtavanimike_list)

        taydennyskoulutus_patch = {
            'nimi': 'Testikoulutus21'
        }

        datetime_gt_5 = _get_iso_datetime_now()
        assert_status_code(client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/',
                                        json.dumps(taydennyskoulutus_patch), content_type='application/json'),
                           status.HTTP_200_OK)
        datetime_lte_5 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_5}'
                          f'&datetime_lte={datetime_lte_5}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_2_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.MODIFIED.value)
        self.assertEqual(taydennyskoulutus_result['nimi'], 'Testikoulutus21')

        datetime_gt_6 = _get_iso_datetime_now()
        assert_status_code(client.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_id}/'),
                           status.HTTP_204_NO_CONTENT)
        datetime_lte_6 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_6}'
                          f'&datetime_lte={datetime_lte_6}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_2_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
        taydennyskoulutus_result = tyontekija_result['taydennyskoulutukset'][0]
        self.assertEqual(taydennyskoulutus_result['id'], taydennyskoulutus_id)
        self.assertEqual(taydennyskoulutus_result['action'], ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_6}')
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_henkilostotiedot_henkilo(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        henkilo = Henkilo.objects.get(henkilo_oid='1.2.246.562.24.2431884920042')
        original_tyontekija_id = Tyontekija.objects.get(tunniste='testing-tyontekija2').id

        tyontekija = {
            'henkilo_oid': henkilo.henkilo_oid,
            'vakajarjestaja_oid': '1.2.246.562.10.52966755795',
            'lahdejarjestelma': '1'
        }
        datetime_gt = _get_iso_datetime_now()
        resp_tyontekija = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_tyontekija, status.HTTP_201_CREATED)
        tyontekija_id = json.loads(resp_tyontekija.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.CREATED.value)

        datetime_gt_2 = _get_iso_datetime_now()
        # Wait for 0.1 seconds so database action happens after datetime_gt_2
        time.sleep(0.1)
        henkilo.aidinkieli_koodi = 'SV'
        henkilo.save()
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        results = json.loads(resp.content)['results']
        self.assertEqual(len(results), 2)
        for lapsi_result in results:
            self.assertEqual(lapsi_result['action'], ChangeType.MODIFIED.value)
            self.assertIn(lapsi_result['id'], (original_tyontekija_id, tyontekija_id,))

        assert_status_code(client.delete(f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/'),
                           status.HTTP_204_NO_CONTENT)
        datetime_lte_3 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_3}')
        _validate_tk_basic_single_result(self, resp, original_tyontekija_id, ChangeType.MODIFIED.value)

    def test_tk_henkilostotiedot_tutkinto(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        tyontekija_id = Tyontekija.objects.get(tunniste='testing-tyontekija5').id
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        henkilo_oid = '1.2.246.562.24.2431884920041'

        tutkinto = {
            'vakajarjestaja_oid': vakajarjestaja_oid,
            'henkilo_oid': henkilo_oid,
            'tutkinto_koodi': '712104'
        }

        datetime_gt = _get_iso_datetime_now()
        resp_tyontekija = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp_tyontekija, status.HTTP_201_CREATED)
        tutkinto_id = json.loads(resp_tyontekija.content)['id']
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['tutkinnot']), 1)
        tutkinto_result = tyontekija_result['tutkinnot'][0]
        self.assertEqual(tutkinto_result['id'], tutkinto_id)
        self.assertEqual(tutkinto_result['action'], ChangeType.CREATED.value)

        datetime_gt_2 = _get_iso_datetime_now()
        assert_status_code(client.delete(f'/api/henkilosto/v1/tutkinnot/{tutkinto_id}/'), status.HTTP_204_NO_CONTENT)
        datetime_lte_2 = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt_2}'
                          f'&datetime_lte={datetime_lte_2}')
        tyontekija_result = _validate_tk_basic_single_result(self, resp, tyontekija_id, ChangeType.UNCHANGED.value)
        self.assertEqual(len(tyontekija_result['tutkinnot']), 1)
        tutkinto_result = tyontekija_result['tutkinnot'][0]
        self.assertEqual(tutkinto_result['id'], tutkinto_id)
        self.assertEqual(tutkinto_result['action'], ChangeType.DELETED.value)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte_2}')
        self.assertEqual(len(json.loads(resp.content)['results']), 0)

    def test_tk_transferred_data(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        new_vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        old_vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.52966755795')

        # Initiate complicated situation with overlapping Lapsi and Tyontekija objects
        toimipaikka_id_list = list(Toimipaikka.objects.filter(vakajarjestaja=old_vakajarjestaja)
                                   .values_list('id', flat=True))
        tilapainen_henkilosto_id_list = list(TilapainenHenkilosto.objects.filter(vakajarjestaja=old_vakajarjestaja)
                                             .values_list('id', flat=True))
        lapsi_id_list = list(Lapsi.objects.filter(vakatoimija=old_vakajarjestaja).values_list('id', flat=True))
        tyontekija_id_list = list(Tyontekija.objects.filter(vakajarjestaja=old_vakajarjestaja)
                                  .values_list('id', flat=True))
        lapsi_oid = '1.2.246.562.24.5289462746686'
        lapsi = {
            'henkilo_oid': lapsi_oid,
            'vakatoimija_oid': new_vakajarjestaja.organisaatio_oid,
            'lahdejarjestelma': '1'
        }
        assert_status_code(client.post('/api/v1/lapset/', lapsi), status.HTTP_201_CREATED)

        tyontekija_oid = '1.2.246.562.24.5826267847674'
        tyontekija = {
            'henkilo_oid': tyontekija_oid,
            'vakajarjestaja_oid': new_vakajarjestaja.organisaatio_oid,
            'lahdejarjestelma': '1'
        }
        assert_status_code(client.post('/api/henkilosto/v1/tyontekijat/', tyontekija), status.HTTP_201_CREATED)
        tutkinto_1 = {
            'henkilo_oid': tyontekija_oid,
            'vakajarjestaja_oid': old_vakajarjestaja.organisaatio_oid,
            'tutkinto_koodi': '712104',
            'lahdejarjestelma': '1'
        }
        assert_status_code(client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_1), status.HTTP_201_CREATED)
        tutkinto_2 = {
            'henkilo_oid': tyontekija_oid,
            'vakajarjestaja_oid': new_vakajarjestaja.organisaatio_oid,
            'tutkinto_koodi': '321901',
            'lahdejarjestelma': '1'
        }
        assert_status_code(client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_2), status.HTTP_201_CREATED)

        datetime_gt = _get_iso_datetime_now()
        transfer_toimipaikat_to_vakajarjestaja(new_vakajarjestaja, old_vakajarjestaja)
        datetime_lte = _get_iso_datetime_now()

        resp = client.get(f'/api/reporting/v1/tilastokeskus/organisaatiot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        results = json.loads(resp.content)['results']
        self.assertEqual(len(results), 1)
        toimipaikka_results = results[0]['toimipaikat']
        self.assertEqual(len(toimipaikka_results), len(toimipaikka_id_list))
        for toimipaikka_result in toimipaikka_results:
            self.assertEqual(toimipaikka_result['action'], ChangeType.MOVED.value)
            self.assertIn(toimipaikka_result['id'], toimipaikka_id_list)
        tilapainen_henkilosto_results = results[0]['tilapainen_henkilosto']
        self.assertEqual(len(tilapainen_henkilosto_results), len(tilapainen_henkilosto_id_list))
        for tilapainen_henkilosto_result in tilapainen_henkilosto_results:
            self.assertEqual(tilapainen_henkilosto_result['action'], ChangeType.MOVED.value)
            self.assertIn(tilapainen_henkilosto_result['id'], tilapainen_henkilosto_id_list)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/varhaiskasvatustiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        results = json.loads(resp.content)['results']
        # 1 moved, 1 deleted, 1 existing got new data
        self.assertEqual(len(results), len(lapsi_id_list) + 1)
        for lapsi_result in results:
            if lapsi_result['id'] in lapsi_id_list and lapsi_result['henkilo_oid'] == lapsi_oid:
                # Old lapsi that was deleted
                self.assertEqual(lapsi_result['action'], ChangeType.DELETED.value)
                self.assertEqual(len(lapsi_result['varhaiskasvatuspaatokset']), 0)
                self.assertEqual(len(lapsi_result['maksutiedot']), 0)
                self.assertEqual(len(lapsi_result['huoltajat']), 1)
                self.assertEqual(lapsi_result['huoltajat'][0]['action'], ChangeType.DELETED.value)
            elif not lapsi_result['id'] in lapsi_id_list:
                # Existing lapsi that got new data
                self.assertEqual(lapsi_result['action'], ChangeType.UNCHANGED.value)
                self.assertEqual(len(lapsi_result['varhaiskasvatuspaatokset']), 1)
                self.assertEqual(lapsi_result['varhaiskasvatuspaatokset'][0]['action'], ChangeType.MOVED.value)
                self.assertEqual(len(lapsi_result['maksutiedot']), 1)
                self.assertEqual(lapsi_result['maksutiedot'][0]['action'], ChangeType.MOVED.value)
            else:
                # Lapsi that was moved
                self.assertEqual(lapsi_result['action'], ChangeType.MODIFIED.value)
                self.assertEqual(len(lapsi_result['varhaiskasvatuspaatokset']), 0)
                self.assertEqual(len(lapsi_result['maksutiedot']), 0)
                self.assertEqual(len(lapsi_result['huoltajat']), 0)

        resp = client.get(f'/api/reporting/v1/tilastokeskus/henkilostotiedot/?datetime_gt={datetime_gt}'
                          f'&datetime_lte={datetime_lte}')
        results = json.loads(resp.content)['results']
        # 1 deleted, 1 existing got new data
        self.assertEqual(len(results), len(tyontekija_id_list) + 1)
        for tyontekija_result in results:
            if tyontekija_result['id'] in tyontekija_id_list and tyontekija_result['henkilo_oid'] == tyontekija_oid:
                # Old tyontekija that was deleted
                self.assertEqual(tyontekija_result['action'], ChangeType.DELETED.value)
                self.assertEqual(len(tyontekija_result['palvelussuhteet']), 0)
                self.assertEqual(len(tyontekija_result['tutkinnot']), 1)
                self.assertEqual(tyontekija_result['tutkinnot'][0]['tutkinto_koodi'], '321901')
                self.assertEqual(tyontekija_result['tutkinnot'][0]['action'], ChangeType.DELETED.value)
                self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
                self.assertEqual(tyontekija_result['taydennyskoulutukset'][0]['action'], ChangeType.MODIFIED.value)
                self.assertEqual(len(tyontekija_result['taydennyskoulutukset'][0]['tehtavanimikkeet']), 0)
            elif not tyontekija_result['id'] in tyontekija_id_list:
                # Existing tyontekija that got new data
                self.assertEqual(tyontekija_result['action'], ChangeType.UNCHANGED.value)
                self.assertEqual(len(tyontekija_result['palvelussuhteet']), 1)
                self.assertEqual(tyontekija_result['palvelussuhteet'][0]['action'], ChangeType.MOVED.value)
                self.assertEqual(len(tyontekija_result['tutkinnot']), 1)
                self.assertEqual(tyontekija_result['tutkinnot'][0]['action'], ChangeType.MOVED.value)
                self.assertEqual(tyontekija_result['tutkinnot'][0]['tutkinto_koodi'], '712104')
                self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 1)
                self.assertEqual(tyontekija_result['taydennyskoulutukset'][0]['action'], ChangeType.MODIFIED.value)
                self.assertEqual(len(tyontekija_result['taydennyskoulutukset'][0]['tehtavanimikkeet']), 1)
                self.assertEqual(tyontekija_result['taydennyskoulutukset'][0]['tehtavanimikkeet'][0], '43525')
            else:
                # Tyontekija that was moved
                self.assertEqual(tyontekija_result['action'], ChangeType.MODIFIED.value)
                self.assertEqual(len(tyontekija_result['palvelussuhteet']), 0)
                self.assertEqual(len(tyontekija_result['tutkinnot']), 0)
                self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 0)

    def test_yearlysummarydata_api_missing_vakajarjestaja(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        data = {
            'tilastovuosi': 2021
        }

        resp = client.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_yearlysummarydata_varhaiskasvatus_api_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        data = {
            'vakajarjestaja_input': 1,
            'tilastovuosi': 2021
        }

        resp = client.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_200_OK)
        report_id = json.loads(resp.content)['id']
        poiminta_pvm = json.loads(resp.content)['poiminta_pvm']

        accepted_response = {
            'id': report_id,
            'vakajarjestaja': 1,
            'status': 'PENDING',
            'tilasto_pvm': '2021-12-31',
            'poiminta_pvm': poiminta_pvm,
            'vakajarjestaja_count': None,
            'vakajarjestaja_is_active': None,
            'toimipaikka_count': None,
            'toimintapainotus_count': None,
            'kielipainotus_count': None,
            'yhteensa_henkilo_count': None,
            'yhteensa_lapsi_count': None,
            'yhteensa_varhaiskasvatussuhde_count': None,
            'yhteensa_varhaiskasvatuspaatos_count': None,
            'yhteensa_vuorohoito_count': None,
            'oma_henkilo_count': None,
            'oma_lapsi_count': None,
            'oma_varhaiskasvatussuhde_count': None,
            'oma_varhaiskasvatuspaatos_count': None,
            'oma_vuorohoito_count': None,
            'paos_henkilo_count': None,
            'paos_lapsi_count': None,
            'paos_varhaiskasvatussuhde_count': None,
            'paos_varhaiskasvatuspaatos_count': None,
            'paos_vuorohoito_count': None,
            'yhteensa_maksutieto_count': None,
            'yhteensa_maksutieto_mp01_count': None,
            'yhteensa_maksutieto_mp02_count': None,
            'yhteensa_maksutieto_mp03_count': None,
            'oma_maksutieto_count': None,
            'oma_maksutieto_mp01_count': None,
            'oma_maksutieto_mp02_count': None,
            'oma_maksutieto_mp03_count': None,
            'paos_maksutieto_count': None,
            'paos_maksutieto_mp01_count': None,
            'paos_maksutieto_mp02_count': None,
            'paos_maksutieto_mp03_count': None
        }
        self.assertDictEqual(json.loads(resp.content), accepted_response)

        time.sleep(2)

        resp = client.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_200_OK)

        accepted_response = {
            'id': report_id,
            'vakajarjestaja': 1,
            'status': 'FINISHED',
            'tilasto_pvm': '2021-12-31',
            'poiminta_pvm': poiminta_pvm,
            'vakajarjestaja_count': 1,
            'vakajarjestaja_is_active': True,
            'toimipaikka_count': 2,
            'toimintapainotus_count': 0,
            'kielipainotus_count': 0,
            'yhteensa_henkilo_count': 3,
            'yhteensa_lapsi_count': 3,
            'yhteensa_varhaiskasvatussuhde_count': 4,
            'yhteensa_varhaiskasvatuspaatos_count': 3,
            'yhteensa_vuorohoito_count': 0,
            'oma_henkilo_count': 1,
            'oma_lapsi_count': 1,
            'oma_varhaiskasvatussuhde_count': 1,
            'oma_varhaiskasvatuspaatos_count': 1,
            'oma_vuorohoito_count': 0,
            'paos_henkilo_count': 2,
            'paos_lapsi_count': 2,
            'paos_varhaiskasvatussuhde_count': 3,
            'paos_varhaiskasvatuspaatos_count': 2,
            'paos_vuorohoito_count': 0,
            'yhteensa_maksutieto_count': 1,
            'yhteensa_maksutieto_mp01_count': 0,
            'yhteensa_maksutieto_mp02_count': 1,
            'yhteensa_maksutieto_mp03_count': 0,
            'oma_maksutieto_count': 1,
            'oma_maksutieto_mp01_count': 0,
            'oma_maksutieto_mp02_count': 1,
            'oma_maksutieto_mp03_count': 0,
            'paos_maksutieto_count': 0,
            'paos_maksutieto_mp01_count': 0,
            'paos_maksutieto_mp02_count': 0,
            'paos_maksutieto_mp03_count': 0
        }

        self.assertDictEqual(json.loads(resp.content), accepted_response)

    def test_yearlysummarydata_api_get_all(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester').client()
        client2 = SetUpTestClient('tester2').client()

        data = {'vakajarjestaja_input': 'all'}

        resp = client.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

        resp = client2.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_200_OK)

    def test_yearlysummarydata_api_get_history(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        past_poiminta_pvm = datetime.datetime.now().astimezone()
        past_poiminta_pvm = past_poiminta_pvm.strftime('%Y-%m-%dT%H:%M:%S%z')

        data = {'vakajarjestaja_input': 'all', 'poiminta_pvm': past_poiminta_pvm}

        resp = client.post('/api/reporting/v1/yearly-reporting-summary/', data)
        assert_status_code(resp, status.HTTP_200_OK)


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


def _get_iso_datetime_now():
    return timezone.now().isoformat().replace('+', '%2B')


def _test_tk_kielipainotus_action(self, resp, vakajarjestaja_id, toimipaikka_id, kielipainotus_id, action):
    results = json.loads(resp.content)['results']
    self.assertEqual(len(results), 1)

    vakajarjestaja_result = results[0]
    self.assertEqual(vakajarjestaja_result['id'], vakajarjestaja_id)
    self.assertEqual(vakajarjestaja_result['action'], ChangeType.UNCHANGED.value)
    self.assertEqual(len(vakajarjestaja_result['toimipaikat']), 1)

    toimipaikka_result = vakajarjestaja_result['toimipaikat'][0]
    self.assertEqual(toimipaikka_result['id'], toimipaikka_id)
    self.assertEqual(toimipaikka_result['action'], ChangeType.UNCHANGED.value)
    self.assertEqual(len(toimipaikka_result['toiminnalliset_painotukset']), 0)
    self.assertEqual(len(toimipaikka_result['kielipainotukset']), 1)

    kielipainotus_result = toimipaikka_result['kielipainotukset'][0]
    self.assertEqual(kielipainotus_result['id'], kielipainotus_id)
    self.assertEqual(kielipainotus_result['action'], action)


def _test_tk_vakasuhde_action(self, resp, lapsi_id, vakapaatos_id, vakasuhde_id, action):
    results = json.loads(resp.content)['results']
    self.assertEqual(len(results), 1)

    lapsi_result = results[0]
    self.assertEqual(lapsi_result['id'], lapsi_id)
    self.assertEqual(lapsi_result['action'], ChangeType.UNCHANGED.value)
    self.assertEqual(len(lapsi_result['maksutiedot']), 0)
    self.assertEqual(len(lapsi_result['varhaiskasvatuspaatokset']), 1)

    vakapaatos_result = lapsi_result['varhaiskasvatuspaatokset'][0]
    self.assertEqual(vakapaatos_result['id'], vakapaatos_id)
    self.assertEqual(vakapaatos_result['action'], ChangeType.UNCHANGED.value)
    self.assertEqual(len(vakapaatos_result['varhaiskasvatussuhteet']), 1)

    vakasuhde_result = vakapaatos_result['varhaiskasvatussuhteet'][0]
    self.assertEqual(vakasuhde_result['id'], vakasuhde_id)
    self.assertEqual(vakasuhde_result['action'], action)


def _validate_tk_basic_single_result(self, resp, instance_id, action):
    results = json.loads(resp.content)['results']
    self.assertEqual(len(results), 1)
    single_result = results[0]
    self.assertEqual(single_result['id'], instance_id)
    self.assertEqual(single_result['action'], action)
    return single_result


def _test_tk_henkilostotieto_action(self, resp, tyontekija_id, palvelussuhde_id, action, model=None,
                                    instance_id=None):
    results = json.loads(resp.content)['results']
    self.assertEqual(len(results), 1)

    tyontekija_result = results[0]
    self.assertEqual(tyontekija_result['id'], tyontekija_id)
    self.assertEqual(tyontekija_result['action'], ChangeType.UNCHANGED.value)
    self.assertEqual(len(tyontekija_result['taydennyskoulutukset']), 0)
    self.assertEqual(len(tyontekija_result['palvelussuhteet']), 1)

    palvelussuhde_result = tyontekija_result['palvelussuhteet'][0]
    self.assertEqual(palvelussuhde_result['id'], palvelussuhde_id)
    palvelussuhde_action = action if not model else ChangeType.UNCHANGED.value
    self.assertEqual(palvelussuhde_result['action'], palvelussuhde_action)
    pidemmat_poissaolot_count = 1 if model == PidempiPoissaolo else 0
    self.assertEqual(len(palvelussuhde_result['pidemmat_poissaolot']), pidemmat_poissaolot_count)
    tyoskentelypaikat_count = 1 if model == Tyoskentelypaikka else 0
    self.assertEqual(len(palvelussuhde_result['tyoskentelypaikat']), tyoskentelypaikat_count)

    if model in (Tyoskentelypaikka, PidempiPoissaolo,):
        field_name = 'tyoskentelypaikat' if model == Tyoskentelypaikka else 'pidemmat_poissaolot'
        instance_result = palvelussuhde_result[field_name][0]
        self.assertEqual(instance_result['id'], instance_id)
        self.assertEqual(instance_result['action'], action)
