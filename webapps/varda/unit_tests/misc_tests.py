import responses
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from varda import misc
from varda.models import Henkilo


class SetUpTestClient:

    def __init__(self, name):
        self.name = name

    def client(self):
        user = User.objects.filter(username=self.name)[0]
        api_c = APIClient()
        api_c.force_authenticate(user=user)
        return api_c


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
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": hetu,
            "etunimet": "Pauliina",
            "kutsumanimi": "Pauliina",
            "sukunimi": "Virtanen"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.json()["id"]

    def test_request_path_type(self):
        request_path_string = '/api/v1/toimipaikat/55/'
        request_path_bytes = b'/api/v1/toimipaikat/55/'
        request_path_empty_string = ''
        request_path_empty_byte = b''

        object_id_string = misc.get_object_id_from_path(request_path_string)
        object_id_bytes = misc.get_object_id_from_path(request_path_bytes)
        object_id_empty_string = misc.get_object_id_from_path(request_path_empty_string)
        object_id_empty_byte = misc.get_object_id_from_path(request_path_empty_byte)

        self.assertEqual(object_id_string, 55)
        self.assertEqual(object_id_bytes, 55)
        self.assertEqual(object_id_empty_string, None)
        self.assertEqual(object_id_empty_byte, None)
