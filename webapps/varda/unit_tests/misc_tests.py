import json

import responses
from django.test import TestCase
from rest_framework import status

from varda import misc
from varda.models import Henkilo
from varda.unit_tests.test_utils import assert_status_code, assert_validation_error, SetUpTestClient


class MiscTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    @responses.activate
    def test_hetu_crypting(self):
        hetu = '210669-043K'
        henkilo_id = self._create_henkilo(hetu)
        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))

        new_hetu = '111299-913S'
        new_henkilo_id = self._create_henkilo(new_hetu)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(hetu_encrypted)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(new_hetu_encrypted)

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        new_key_only_hetu = '111299-9255'
        new_key_only_henkilo_id = self._create_henkilo(new_key_only_hetu)
        new_key_only_hetu_encrypted = Henkilo.objects.get(id=new_key_only_henkilo_id).henkilotunnus
        self.assertEqual(new_key_only_hetu, misc.decrypt_henkilotunnus(new_key_only_hetu_encrypted))

    def _create_henkilo(self, hetu):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED)
        henkilo = {
            'henkilotunnus': hetu,
            'etunimet': 'Pauliina',
            'kutsumanimi': 'Pauliina',
            'sukunimi': 'Virtanen'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.json()['id']

    def test_request_path_type(self):
        request_path_string = '/api/v1/toimipaikat/55/'
        request_path_bytes = b'/api/v1/toimipaikat/55/'
        request_path_empty_string = ''
        request_path_empty_byte = b''

        url_string, params_string = misc.path_parse(request_path_string)
        url_bytes, params_bytes = misc.path_parse(request_path_bytes)
        url_empty_string, params_empty_string = misc.path_parse(request_path_empty_string)
        url_empty_byte, params_empty_byte = misc.path_parse(request_path_empty_byte)

        self.assertEqual(url_string, request_path_string)
        self.assertEqual(url_bytes, request_path_string)
        self.assertEqual(url_empty_string, '')
        self.assertEqual(url_empty_byte, '')

    def test_dy011_error(self):
        client = SetUpTestClient('tester10').client()

        test_cases = [
            ('', 'Invalid JSON payload. Expected a dictionary, but got str.',),
            (1, 'Invalid JSON payload. Expected a dictionary, but got int.',),
            (1.1, 'Invalid JSON payload. Expected a dictionary, but got float.',),
            (False, 'Invalid JSON payload. Expected a dictionary, but got bool.',),
            ([''], 'Invalid JSON payload. Expected a dictionary, but got list.',)
        ]
        for test_case in test_cases:
            resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(test_case[0]),
                               content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
            assert_validation_error(resp, 'errors', 'DY011', test_case[1])
