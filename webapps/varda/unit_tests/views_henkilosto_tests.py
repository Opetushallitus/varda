import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from varda.models import VakaJarjestaja, Henkilo
from varda.unit_tests.test_utils import assert_status_code


class SetUpTestClient:

    def __init__(self, name):
        self.name = name

    def client(self):
        user = User.objects.filter(username=self.name)[0]
        api_c = APIClient()
        api_c.force_authenticate(user=user)
        return api_c


class VardaHenkiloViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_push_tyontekija_correct(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 201)

    def test_tyontekija_add_twice(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1'
        }

        resp_original = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_original, 201)
        tyontekija_url_1 = json.loads(resp_original.content)['url']

        resp_duplicate = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_duplicate, 200)
        tyontekija_url_2 = json.loads(resp_duplicate.content)['url']

        self.assertEqual(tyontekija_url_1, tyontekija_url_2)

    def test_api_push_tyontekija_correct_oid(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 201)

    def test_api_push_tyontekija_incorrect_oid(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.472799426504',
            'vakajarjestaja_oid': '1.2.246.562.10.346830234894',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_push_tyontekija_incorrect_tunniste(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.472799426504',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': '250700A5074',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_push_tyontekija_henkilo_is_lapsi(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/2/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_push_tyontekija_lahdejarjestelma_tunniste_not_unique(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija_1 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp_1 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_1)
        assert_status_code(resp_1, 201)

        tyontekija_2 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp_2 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_2)
        assert_status_code(resp_2, 400)

    def test_api_push_tyontekija_missing_henkilo(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_push_tyontekija_missing_vakajarjestaja(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_push_tyontekija_missing_lahdejarjestelma(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 400)

    def test_api_put_tyontekija_vakajarjestaja_edit(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, 201)

        tyontekija_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tyontekija_edit)
        assert_status_code(resp_edit, 400)

    def test_api_push_tilapainen_henkilosto_correct(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, 201)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-04-30',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, 201)

    def test_api_push_tilapainen_henkilosto_correct_oid(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 201)

    def test_api_push_tilapainen_henkilosto_missing_vakajarjestaja(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_missing_kuukausi(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_missing_tyontekijamaara(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-03-31',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_missing_lahdejarjestelma(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-03-31',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_missing_tuntimaara(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_incorrect_tunniste(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': '070501A2296',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 400)

    def test_api_push_tilapainen_henkilosto_lahdejarjestelma_tunniste_not_unique(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, 201)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-04-30',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, 400)

    def test_api_push_tilapainen_henkilosto_double_month(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, 201)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, 400)

    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 201)

        tilapainen_henkilosto_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tilapainen_henkilosto_edit)
        assert_status_code(resp_edit, 400)

    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit_oid(self):
        client = SetUpTestClient('credadmin').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 201)

        tilapainen_henkilosto_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tilapainen_henkilosto_edit)
        assert_status_code(resp_edit, 400)

    def test_api_tilapainen_henkilosto_filter(self):
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_id = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid).id

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, 201)

        correct_queries = ['?vakajarjestaja={0}'.format(vakajarjestaja_oid),
                           '?vakajarjestaja={0}'.format(vakajarjestaja_id),
                           '?vakajarjestaja={0}&vuosi=2020&kuukausi=3'.format(vakajarjestaja_id),
                           '?vakajarjestaja={0}&vuosi=2020&kuukausi=3'.format(vakajarjestaja_oid),
                           '?vuosi=2020&kuukausi=3', '?vuosi=2020', '?kuukausi=3']

        incorrect_queries = ['?vakajarjestaja=999', '?vakajarjestaja=test', '?vuosi=2020&kuukausi=4',
                             '?vakajarjestaja={0}&vuosi=2020&kuukausi=2'.format(vakajarjestaja_id),
                             '?vuosi=2019', '?kuukausi=5']

        for query in correct_queries:
            resp_filter_correct = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_correct, 200)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 1)

        for query in incorrect_queries:
            resp_filter_incorrect = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_incorrect, 200)
            self.assertEqual(json.loads(resp_filter_incorrect.content)['count'], 0)

        # Invalid format
        resp_filter_error = client.get('/api/henkilosto/v1/tilapainen-henkilosto/?kuukausi=2020-03-32')
        assert_status_code(resp_filter_error, 400)

    def test_api_push_tutkinto_correct(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'henkilo': '/api/v1/henkilot/1/',
            'tutkinto_koodi': '002'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 201)

    def test_api_push_tutkinto_correct_oid(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.47279942650',
            'tutkinto_koodi': '002'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 201)

    def test_api_push_tutkinto_twice(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto_1 = {
            'henkilo': '/api/v1/henkilot/10/',
            'tutkinto_koodi': '002'
        }

        resp_1 = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_1)
        assert_status_code(resp_1, 201)

        tutkinto_2 = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'tutkinto_koodi': '002'
        }

        resp_2 = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_2)
        assert_status_code(resp_2, 200)

    def test_api_push_tutkinto_missing_henkilo(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'tutkinto_koodi': '321901'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 400)

    def test_api_push_tutkinto_missing_tutkinto_koodi(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.47279942650'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 400)

    def test_api_delete_tutkinto(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'henkilo': '/api/v1/henkilot/1/',
            'tutkinto_koodi': '321901'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 201)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/?henkilo_id=1&tutkinto_koodi=321901')
        assert_status_code(resp_delete, 200)

    def test_api_delete_tutkinto_by_oid(self):
        client = SetUpTestClient('credadmin').client()

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.47279942650',
            'tutkinto_koodi': '001'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 201)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/'
                                    '?henkilo_oid=1.2.246.562.24.47279942650&tutkinto_koodi=001')
        assert_status_code(resp_delete, 200)

    def test_api_tutkinto_filter(self):
        henkilo_oid = '1.2.246.562.24.47279942650'
        henkilo_id = Henkilo.objects.get(henkilo_oid=henkilo_oid).id

        tutkinto = {
            'henkilo_oid': henkilo_oid,
            'tutkinto_koodi': '001'
        }

        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, 201)

        correct_queries = ['?henkilo={0}'.format(henkilo_oid),
                           '?henkilo={0}'.format(henkilo_id),
                           '?henkilo={0}&tutkinto_koodi=001'.format(henkilo_id),
                           '?henkilo={0}&tutkinto_koodi=001'.format(henkilo_oid),
                           '?tutkinto_koodi=001']

        incorrect_queries = ['?henkilo=999', '?henkilo=test', '?tutkinto_koodi=01',
                             '?henkilo={0}&tutkinto_koodi=test'.format(henkilo_id)]

        for query in correct_queries:
            resp_filter_correct = client.get('/api/henkilosto/v1/tutkinnot/' + query)
            assert_status_code(resp_filter_correct, 200)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 1)

        for query in incorrect_queries:
            resp_filter_incorrect = client.get('/api/henkilosto/v1/tutkinnot/' + query)
            assert_status_code(resp_filter_incorrect, 200)
            self.assertEqual(json.loads(resp_filter_incorrect.content)['count'], 0)
