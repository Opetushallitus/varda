import json

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status

from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient, assert_validation_error
from varda.models import (VakaJarjestaja, Henkilo, Tyontekija, Palvelussuhde, Tyoskentelypaikka, Toimipaikka,
                          TilapainenHenkilosto)


class VardaHenkilostoViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_push_tyontekija_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyontekija_add_incorrect_vakajarjestaja(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1'
        }

        resp_original = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        # Masking 403 as validation error
        assert_status_code(resp_original, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(b'{"vakajarjestaja":["Invalid hyperlink - Object does not exist."]}', resp_original.content)

    def test_tyontekija_add_incorrect_vakajarjestaja_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja_oid': '1.2.246.562.10.93957375488',
            'lahdejarjestelma': '1'
        }

        resp_original = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        # Masking 403 as validation error
        assert_status_code(resp_original, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(b'{"vakajarjestaja_oid":{"vakajarjestaja_oid":["Unknown oid"]}}', resp_original.content)

    def test_tyontekija_add_twice(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1'
        }

        resp_original = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_original, status.HTTP_201_CREATED)
        tyontekija_url_1 = json.loads(resp_original.content)['url']

        resp_duplicate = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_duplicate, status.HTTP_200_OK)
        tyontekija_url_2 = json.loads(resp_duplicate.content)['url']

        self.assertEqual(tyontekija_url_1, tyontekija_url_2)

    def test_api_push_tyontekija_correct_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_tyontekija_incorrect_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.472799426504',
            'vakajarjestaja_oid': '1.2.246.562.10.346830234894',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_incorrect_tunniste(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.472799426504',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': '250700A5074',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_henkilo_is_lapsi(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/2/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_lahdejarjestelma_tunniste_not_unique(self):
        client = SetUpTestClient('credadmin').client()

        tyontekija_1 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp_1 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tyontekija_2 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp_2 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_missing_henkilo(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_missing_vakajarjestaja(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tyontekija_missing_lahdejarjestelma(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_put_tyontekija_vakajarjestaja_edit(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tyontekija_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tyontekija_edit)
        assert_status_code(resp_edit, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_correct(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-04-30',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)

    def test_api_push_tilapainen_henkilosto_correct_oid(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_tilapainen_henkilosto_delete(self):
        # No user has permissions to this
        admin_user = User.objects.get(username='credadmin')
        vakajarjestaja_tester = VakaJarjestaja.objects.filter(nimi='Tester organisaatio')[0]
        tilapainen = TilapainenHenkilosto.objects.create(vakajarjestaja=vakajarjestaja_tester,
                                                         kuukausi='2019-09-01',
                                                         tuntimaara=10.0,
                                                         tyontekijamaara=10,
                                                         lahdejarjestelma='1',
                                                         changed_by=admin_user)

        client = SetUpTestClient('tilapaiset_tallentaja').client()

        resp_delete_1 = client.delete('/api/henkilosto/v1/tilapainen-henkilosto/{}/'.format(tilapainen))
        assert_status_code(resp_delete_1, status.HTTP_404_NOT_FOUND)

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp, status.HTTP_201_CREATED)
        tilapinen_id = json.loads(resp.content).get('id')
        resp_delete_2 = client.delete('/api/henkilosto/v1/tilapainen-henkilosto/{}/'.format(tilapinen_id))
        assert_status_code(resp_delete_2, status.HTTP_204_NO_CONTENT)

    def test_api_push_tilapainen_henkilosto_missing_vakajarjestaja(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_missing_kuukausi(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_missing_tyontekijamaara(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-03-31',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_missing_lahdejarjestelma(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-03-31',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_missing_tuntimaara(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_incorrect_tunniste(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': '070501A2296',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_lahdejarjestelma_tunniste_not_unique(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-04-30',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tilapainen_henkilosto_double_month(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)

    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tilapainen_henkilosto_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tilapainen_henkilosto_edit)
        assert_status_code(resp_edit, status.HTTP_400_BAD_REQUEST)

    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit_oid(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-03-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tilapainen_henkilosto_edit = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/2/'
        }

        resp_edit = client.patch(json.loads(resp.content)['url'], tilapainen_henkilosto_edit)
        assert_status_code(resp_edit, status.HTTP_400_BAD_REQUEST)

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

        client = SetUpTestClient('tilapaiset_tallentaja').client()
        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

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
            assert_status_code(resp_filter_correct, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 1)

        for query in incorrect_queries:
            resp_filter_incorrect = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_incorrect, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_incorrect.content)['count'], 0)

        # Invalid format
        resp_filter_error = client.get('/api/henkilosto/v1/tilapainen-henkilosto/?kuukausi=2020-03-32')
        assert_status_code(resp_filter_error, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tutkinto_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '002'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_tutkinto_correct_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '002'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_tutkinto_twice(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija1 = {
            'henkilo': '/api/v1/henkilot/10/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija1)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto_1 = {
            'henkilo': '/api/v1/henkilot/10/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '002'
        }

        resp_1 = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tyontekija2 = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija2)
        assert_status_code(resp, status.HTTP_200_OK)

        tutkinto_2 = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '002'
        }

        resp_2 = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto_2)
        assert_status_code(resp_2, status.HTTP_200_OK)

    def test_api_push_tutkinto_missing_henkilo(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tutkinto = {
            'tutkinto_koodi': '321901'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_push_tutkinto_missing_tutkinto_koodi(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.47279942650'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_delete_tutkinto(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '321901'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/?henkilo_id=1&tutkinto_koodi=321901')
        assert_status_code(resp_delete, status.HTTP_200_OK)

    def test_api_delete_tutkinto_by_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '001'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/'
                                    '?henkilo_oid=1.2.246.562.24.6815481182312&tutkinto_koodi=001')
        assert_status_code(resp_delete, status.HTTP_200_OK)

    def test_api_tutkinto_filter(self):
        henkilo_oid = '1.2.246.562.24.6815481182312'
        henkilo_id = Henkilo.objects.get(henkilo_oid=henkilo_oid).id

        tyontekija = {
            'henkilo_oid': henkilo_oid,
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo_oid': henkilo_oid,
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '001'
        }
        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)

        correct_queries = ['?henkilo={0}'.format(henkilo_oid),
                           '?henkilo={0}'.format(henkilo_id),
                           '?henkilo={0}&tutkinto_koodi=001'.format(henkilo_id),
                           '?henkilo={0}&tutkinto_koodi=001'.format(henkilo_oid),
                           '?tutkinto_koodi=001']

        incorrect_queries = ['?henkilo=999', '?henkilo=test', '?tutkinto_koodi=01',
                             '?henkilo={0}&tutkinto_koodi=test'.format(henkilo_id)]

        for query in correct_queries:
            resp_filter_correct = client.get('/api/henkilosto/v1/tutkinnot/' + query)
            assert_status_code(resp_filter_correct, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 1)

        for query in incorrect_queries:
            resp_filter_incorrect = client.get('/api/henkilosto/v1/tutkinnot/' + query)
            assert_status_code(resp_filter_incorrect, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_incorrect.content)['count'], 0)

    def test_palvelussuhde_add_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-03-02',
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_palvelussuhde_edit_allowed(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        # Get initial data as a dictionary
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        resp = client.get(f"/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/")
        assert_status_code(resp, status.HTTP_200_OK)
        palvelussuhde_dict = json.loads(resp.content)

        # These are the fields that can be edited
        palvelussuhde_edits = {
            'tyosuhde_koodi': '2',
            'tyoaika_koodi': '2',
            'tutkinto_koodi': '613101',
            'tyoaika_viikossa': '35.00',
            'alkamis_pvm': '2020-01-01',
            'paattymis_pvm': '2020-04-04',
            'lahdejarjestelma': '2',
            'tunniste': 'b'
        }

        # Change fields one by one and make sure we get a success
        for key, value in palvelussuhde_edits.items():
            palvelussuhde_edit = palvelussuhde_dict.copy()
            palvelussuhde_edit[key] = value
            resp = client.put(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_dict["id"]}/', json.dumps(palvelussuhde_edit), content_type="application/json")
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Fetch object and ensure field was changed
            resp = client.get(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_dict["id"]}/')
            assert_status_code(resp, status.HTTP_200_OK)
            data = json.loads(resp.content)
            self.assertEqual(value, data[key])

    def test_palvelussuhde_edit_disallowed(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija_3 = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        # Get initial data as a dictionary
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        resp = client.get(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/')
        assert_status_code(resp, status.HTTP_200_OK)
        palvelussuhde_dict = json.loads(resp.content)

        # These are the fields that can't be edited
        palvelussuhde_edits = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_3.id}/',
        }

        # Change fields one by one and make sure we get a fail
        for key, value in palvelussuhde_edits.items():
            palvelussuhde_edit = palvelussuhde_dict.copy()
            palvelussuhde_edit[key] = value
            resp = client.put(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_dict["id"]}/', json.dumps(palvelussuhde_edit), content_type="application/json")
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST, key)

    def test_palvelussuhde_add_correct_end_date_null(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': None,
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_palvelussuhde_add_incorrect_end_date(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-03-01',  # Not after alkamis_pvm
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('paattymis_pvm', 'paattymis_pvm must be after alkamis_pvm.', resp)

    def test_palvelussuhde_add_too_many(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2021-11-11',
            'lahdejarjestelma': '1',
        }

        # Add as many as we can
        for i in range(7):
            resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
            assert_status_code(resp, status.HTTP_201_CREATED)

        # The next one will fail
        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('palvelussuhde', 'Already have 7 overlapping palvelussuhde on the defined time range.', resp)

        # But later dates are ok
        palvelussuhde.update(alkamis_pvm='2022-02-02', paattymis_pvm='2023-03-03')
        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_palvelussuhde_add_invalid_codes(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': 'foo1',
            'tyoaika_koodi': 'foo2',
            'tutkinto_koodi': 'foo3',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('tyosuhde_koodi', 'foo1 : Not a valid tyosuhde_koodi.', resp)
        assert_validation_error('tyoaika_koodi', 'foo2 : Not a valid tyoaika_koodi.', resp)
        assert_validation_error('tutkinto_koodi', 'foo3 : Not a valid tutkinto_koodi.', resp)

    def test_palvelussuhde_add_wrong_tutkinto(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '003',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-03-02',
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/palvelussuhteet/", json.dumps(palvelussuhde), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('tutkinto_koodi', 'tyontekija has tutkinnot other than just 003.', resp)

    def test_tyoskentelypaikka_add_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815').first()

        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_add_too_many(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        palvelussuhde_22 = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2-2')
        palvelussuhde_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id)
        palvelussuhde_22_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde_22.id)
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815').first()

        # Tietoluettelosta: "Työntekijälle voi tallentaa enintään kolme pääasiallista toimipaikkaa, joissa työntekijä työskentelee."

        tyoskentelypaikka = {
            'palvelussuhde': palvelussuhde_url,
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        # Add as many as we can
        for i in range(3):
            resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
            assert_status_code(resp, status.HTTP_201_CREATED)

        # The next one will fail
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('palvelussuhde', 'Already have 3 overlapping tyoskentelypaikka on the defined time range.', resp)

        # So does this: limit is global across all palvelussuhteet
        tyoskentelypaikka.update(palvelussuhde=palvelussuhde_22_url)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('palvelussuhde', 'Already have 3 overlapping tyoskentelypaikka on the defined time range.', resp)

        # But cases where kiertava_tyontekija_kytkin is True are ok
        tyoskentelypaikka.update(kiertava_tyontekija_kytkin=True, toimipaikka=None)
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

        # So are later dates
        tyoskentelypaikka.update(kiertava_tyontekija_kytkin=False, toimipaikka='/api/v1/toimipaikat/{}/'.format(toimipaikka), alkamis_pvm='2022-02-02', paattymis_pvm='2023-03-03')
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_edit_allowed(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        # Get initial data as a dictionary
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka1')
        resp = client.get('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka.id))
        assert_status_code(resp, status.HTTP_200_OK)
        tyoskentelypaikka_dict = json.loads(resp.content)

        # These are the fields that can be edited
        tyoskentelypaikka_edits = {
            'alkamis_pvm': '2020-04-01',
            'paattymis_pvm': '2022-12-31',
            'tehtavanimike_koodi': '84724',
            'lahdejarjestelma': '2',
            'tunniste': 'tunniste2',
            'kelpoisuus_kytkin': True,  # Change this last, otherwise it gets messed up due to downgrade disallow
        }

        # Change fields one by one and make sure we get a success
        for key, value in tyoskentelypaikka_edits.items():
            tyoskentelypaikka_edit = tyoskentelypaikka_dict.copy()
            tyoskentelypaikka_edit[key] = value
            resp = client.put('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict["id"]), json.dumps(tyoskentelypaikka_edit), content_type="application/json")
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Fetch object and ensure field was changed
            resp = client.get('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict["id"]))
            assert_status_code(resp, status.HTTP_200_OK)
            data = json.loads(resp.content)
            self.assertEqual(value, data[key])

    def test_tyoskentelypaikka_edit_ignored(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde_2 = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka_2 = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815')[0]

        # Get initial data as a dictionary
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka1')
        tyoskentelypaikka_url = '/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka.id)
        resp = client.get(tyoskentelypaikka_url)
        assert_status_code(resp, status.HTTP_200_OK)
        tyoskentelypaikka_dict = json.loads(resp.content)
        tyoskentelypaikka_dict_original = tyoskentelypaikka_dict.copy()

        # These need to be changed in unison, but we are changing them one by one, so just delete them
        del tyoskentelypaikka_dict['toimipaikka']
        del tyoskentelypaikka_dict['toimipaikka_oid']

        # These are the basic fields that can't be edited
        tyoskentelypaikka_edits = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde_2.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka_2.id),
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
        }

        # Change fields one by one and make sure we get a fail
        for key, value in tyoskentelypaikka_edits.items():
            tyoskentelypaikka_edit = tyoskentelypaikka_dict.copy()
            tyoskentelypaikka_edit[key] = value
            resp = client.put(tyoskentelypaikka_url, json.dumps(tyoskentelypaikka_edit), content_type="application/json")
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Make sure that the so-called edit didn't do anything
            resp = client.get(tyoskentelypaikka_url)
            assert_status_code(resp, status.HTTP_200_OK)
            tyoskentelypaikka_dict2 = json.loads(resp.content)
            self.assertEqual(tyoskentelypaikka_dict_original[key], tyoskentelypaikka_dict2[key])

    def test_tyoskentelypaikka_kiertava_disallows_toimipaikka(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548810')[0]

        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': True,
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('kiertava_tyontekija_kytkin', 'toimipaikka can\'t be specified with kiertava_tyontekija_kytkin.', resp)

    def test_tyoskentelypaikka_kelpoisuus_downgrade_allowed(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        # Get initial data as a dictionary and adjust for kelpoisuus_kytkin
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka1')
        tyoskentelypaikka.kelpoisuus_kytkin = True  # Downgrade is allowed
        tyoskentelypaikka.save()
        resp = client.get('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka.id))
        assert_status_code(resp, status.HTTP_200_OK)
        tyoskentelypaikka_dict = json.loads(resp.content)

        tyoskentelypaikka_dict.update(kelpoisuus_kytkin=False)

        resp = client.put('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict["id"]), json.dumps(tyoskentelypaikka_dict), content_type="application/json")
        assert_status_code(resp, status.HTTP_200_OK)

    def test_tyoskentelypaikka_incorrect_date_validation(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548810')[0]

        # These are the fields that can be edited
        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        # Palvelussuhde alkamis_pvm   2020-03-01
        # Palvelussuhde paattymis_pvm 2030-03-01

        cases = [
            ('2020-03-01', '2020-01-01', 'paattymis_pvm', 'paattymis_pvm must be after alkamis_pvm.'),
            ('2020-03-01', '2031-01-01', 'paattymis_pvm', 'paattymis_pvm must be before palvelussuhde paattymis_pvm (or same).'),
            ('1999-03-01', '2021-01-01', 'alkamis_pvm', 'alkamis_pvm must be after palvelussuhde alkamis_pvm (or same).'),
            ('2031-03-01', '2032-01-01', 'alkamis_pvm', 'alkamis_pvm must be before palvelussuhde paattymis_pvm.'),
        ]

        for (start, end, key, expected_message) in cases:
            tyoskentelypaikka.update(alkamis_pvm=start, paattymis_pvm=end)
            resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST, f'{start}_{end}')
            assert_validation_error(key, expected_message, resp)

    def test_tyoskentelypaikka_non_kiertava_overlaps_kiertava(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        palvelussuhde_22 = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2-2')
        palvelussuhde_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id)
        palvelussuhde_22_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde_22.id)
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815').first()

        # Mikäli on kiertävä työntekijä jollain ajanjaksolla (ko. palvelussuhteessa) ei voi
        # lisätä työskentelypaikkaa jossa on toimipaikkatieto. Sama myös toisinpäin: jos on
        # jo toimipaikkakohtanen tieto, niin työntekijästä ei voi tehdä kiertävää ko. ajanjaksolla.

        tyoskentelypaikka = {
            'palvelussuhde': palvelussuhde_url,
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2025-01-01',
            'paattymis_pvm': '2025-10-01',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        # Add a tyoskentelypaikka on some date range with kiertava=False
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

        # Try to add another on the same range with kiertava kiertava=True
        # This should fail.
        tyoskentelypaikka.update(toimipaikka=None, kiertava_tyontekija_kytkin=True, alkamis_pvm='2025-05-01', paattymis_pvm='2025-12-31')
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error('kiertava_tyontekija_kytkin', 'can\'t have different values of kiertava_tyontekija_kytkin on overlapping date ranges', resp)

        # But works on a different palvelussuhde, on the same tyontekija
        tyoskentelypaikka.update(palvelussuhde=palvelussuhde_22_url)
        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_add_incorrect_toimipaikka(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka_oid': '1.2.246.562.10.9395737548810',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp = client.post("/api/henkilosto/v1/tyoskentelypaikat/", json.dumps(tyoskentelypaikka), content_type="application/json")
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        messages = json.loads(resp.content)
        self.assertIn('Toimipaikka must have the same vakajarjestaja as tyontekija', messages.get('toimipaikka', []))

    def test_pidempipoissaolo_add_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }

        resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
        assert_status_code(resp, 201)

    def test_pidempipoissaolo_add_correct_two(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }

        resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
        assert_status_code(resp, 201)

        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-09-02',  # The day after the other poissaolo
            'paattymis_pvm': '2022-03-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo2'
        }

        resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
        assert_status_code(resp, 201)

    def test_pidempipoissaolo_incorrect_date_validation(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        # Invariant data
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'lahdejarjestelma': '1'
        }

        # Palvelussuhde alkamis_pvm   2020-03-01
        # Palvelussuhde paattymis_pvm 2030-03-01

        cases = [
            ('2020-03-01', '2020-01-01', 'paattymis_pvm', 'paattymis_pvm must be after alkamis_pvm.'),
            ('2020-03-01', '2031-01-01', 'paattymis_pvm', 'paattymis_pvm must be before palvelussuhde paattymis_pvm (or same).'),
            ('1999-03-01', '2021-01-01', 'alkamis_pvm', 'alkamis_pvm must be after palvelussuhde alkamis_pvm (or same).'),
            ('2031-03-01', '2032-01-01', 'alkamis_pvm', 'alkamis_pvm must be before palvelussuhde paattymis_pvm.'),
            ('2022-01-01', '2022-01-30', 'paattymis_pvm', 'poissaolo duration must be 60 days or more.'),
        ]

        for (start, end, key, expected_message) in cases:
            extra = f'{start}_{end}'
            pidempipoissaolo.update(alkamis_pvm=start, paattymis_pvm=end, tunniste=extra)
            resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
            assert_status_code(resp, 400, extra)
            assert_validation_error(key, expected_message, resp, extra)

    def test_pidempipoissaolo_overlap(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        # Add initial poissaolo 1, with set duration
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }
        resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
        assert_status_code(resp, 201)

        # Add initial poissaolo 2, without end date
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2023-06-01',
            'paattymis_pvm': None,
            'lahdejarjestelma': '1',
            'tunniste': 'foo2'
        }
        resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
        assert_status_code(resp, 201)

        cases = [
            ('2021-06-01', '2021-09-01'),
            ('2021-05-01', '2021-06-01'),
            ('2021-05-01', '2021-07-01'),
            ('2021-06-01', '2021-10-01'),
            ('2021-07-01', '2021-09-01'),
            ('2021-09-01', '2021-10-01'),

            ('2023-05-01', '2023-06-01'),
            ('2023-06-01', '2023-09-01'),
            ('2023-07-01', '2023-10-01'),
        ]

        for (start, end) in cases:
            extra = f'{start}_{end}'
            pidempipoissaolo.update(alkamis_pvm=start, paattymis_pvm=end, tunniste=extra)
            resp = client.post("/api/henkilosto/v1/pidemmatpoissaolot/", json.dumps(pidempipoissaolo), content_type="application/json")
            assert_status_code(resp, 400, extra)
            assert_validation_error('palvelussuhde', 'Already have overlapping pidempipoissaolo on the defined time range.', resp, extra)
