import json
import datetime
from unittest.mock import patch, MagicMock

from django.contrib.auth.models import User, Group
from django.test import TestCase
from rest_framework import status

from varda.unit_tests.test_utils import (assert_status_code, SetUpTestClient, assert_validation_error,
                                         post_henkilo_to_get_permissions, mock_date_decorator_factory,
                                         date_side_effect, timedelta_side_effect)
from varda.models import (VakaJarjestaja, Henkilo, Tyontekija, Palvelussuhde, Tyoskentelypaikka, Toimipaikka,
                          TilapainenHenkilosto, Taydennyskoulutus, TaydennyskoulutusTyontekija, PidempiPoissaolo,
                          Tutkinto)
from varda.viewsets_henkilosto import TyontekijaViewSet


datetime_path = 'varda.serializers_henkilosto.datetime'


class VardaHenkilostoViewSetTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_push_tyontekija_correct(self):
        client_tallentaja = SetUpTestClient('tyontekija_tallentaja').client()
        client_katselija = SetUpTestClient('tyontekija_katselija').client()

        post_henkilo_to_get_permissions(client_tallentaja, henkilo_id=1)
        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }
        expected_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid='1.2.246.562.10.34683023489').count()
        self._assert_create_and_list(client_katselija, client_tallentaja, tyontekija, '/api/henkilosto/v1/tyontekijat/', expected_count + 1)

    def test_api_tyontekija_filter(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        tyontekija_oid = '1.2.246.562.24.2431884920044'
        tyontekija_obj = Tyontekija.objects.filter(henkilo__henkilo_oid=tyontekija_oid).first()
        tyontekija_henkilo_id = tyontekija_obj.henkilo.id
        vakajarjestaja_obj = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
        vakajarjestaja_id = vakajarjestaja_obj.id
        expected_count = Tyontekija.objects.filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()

        resp = client.get(f'/api/henkilosto/v1/tyontekijat/?vakajarjestaja_oid={vakajarjestaja_oid}')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], expected_count)

        resp = client.get(f'/api/henkilosto/v1/tyontekijat/?vakajarjestaja_id={vakajarjestaja_id}')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], expected_count)

        # even if there are multiple Tyontekija this should only return one based on the permissions for the user
        tyontekija_henkilo_count = Tyontekija.objects.filter(henkilo__henkilo_oid=tyontekija_oid, vakajarjestaja__organisaatio_oid=vakajarjestaja_oid).count()
        resp = client.get(f'/api/henkilosto/v1/tyontekijat/?henkilo_oid={tyontekija_oid}')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], tyontekija_henkilo_count)

        resp = client.get(f'/api/henkilosto/v1/tyontekijat/?henkilo_id={tyontekija_henkilo_id}')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['count'], tyontekija_henkilo_count)

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
        assert_validation_error(resp_original, 'vakajarjestaja', 'GE008', 'Invalid hyperlink, object does not exist.')

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
        assert_validation_error(resp_original, 'vakajarjestaja_oid', 'RF003', 'Could not find matching object.')

    def test_tyontekija_add_twice(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        post_henkilo_to_get_permissions(client, henkilo_id=1)
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

    def mock_return_tyontekija_if_already_created(self, *args, **kwargs):
        return

    @patch.object(TyontekijaViewSet, 'return_tyontekija_if_already_created', mock_return_tyontekija_if_already_created)
    def test_tyontekija_add_twice_unique_constraint(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        post_henkilo_to_get_permissions(client, henkilo_id=1)
        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1'
        }

        resp_original = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_original, status.HTTP_201_CREATED)

        resp_duplicate = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp_duplicate, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_duplicate, 'errors', 'TY005', 'Combination of henkilo and vakajarjestaja fields should be unique.')

    def test_api_push_tyontekija_correct_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        henkilo_oid = '1.2.246.562.24.6815481182312'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        tyontekija = {
            'henkilo_oid': henkilo_oid,
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

    def test_api_push_tyontekija_tunniste(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        ok_cases = ['', 'test-tunniste1', 'test_-.tunniste.31432']

        for tunniste in ok_cases:
            resp = client.patch('/api/henkilosto/v1/tyontekijat/1/', {'tunniste': tunniste})
            assert_status_code(resp, status.HTTP_200_OK, tunniste)

        not_ok_cases = ['250700A5074', 'illegal:characters', r'illegal\characters', 'illegal/characters',
                        'illegal_chäräcters']

        for tunniste in not_ok_cases:
            resp = client.patch('/api/henkilosto/v1/tyontekijat/1/', {'tunniste': tunniste})
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST, tunniste)
            assert_validation_error(resp, 'tunniste', 'MI012', 'Not a valid tunniste.', tunniste)

        resp = client.patch('/api/henkilosto/v1/tyontekijat/1/',
                            {
                                'tunniste': 'tunniste_that_is_way_too_long_tunniste_that_is_way_too_long_tunniste_'
                                            'that_is_way_too_long_tunniste_that_is_way_too_long_1'
                            })
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tunniste', 'DY001', 'Ensure this field has no more than 120 characters.')

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
        client = SetUpTestClient('tyontekija_tallentaja').client()

        post_henkilo_to_get_permissions(client, henkilo_id=1)
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

        post_henkilo_to_get_permissions(client, henkilo_id=1)
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

    def test_tyontekija_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-tyontekija98'
        new_tunniste = 'testing-tyontekija99'
        henkilo_oid = '1.2.246.562.24.2434693467574'

        client = SetUpTestClient('tyontekija_tallentaja').client()
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        tyontekija_post = {
            'henkilo_oid': henkilo_oid,
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
            'tunniste': tunniste
        }
        resp_tyontekija_post = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_post)
        assert_status_code(resp_tyontekija_post, status.HTTP_201_CREATED)
        tyontekija = Tyontekija.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        tyontekija_url = f'/api/henkilosto/v1/tyontekijat/{lahdejarjestelma}:{tunniste}/'
        resp_tyontekija_get = client.get(tyontekija_url)
        assert_status_code(resp_tyontekija_get, status.HTTP_200_OK)
        self.assertEqual(tyontekija.id, json.loads(resp_tyontekija_get.content)['id'])

        resp_tyontekija_get_404 = client.get('/api/henkilosto/v1/tyontekijat/5:no/')
        assert_status_code(resp_tyontekija_get_404, status.HTTP_404_NOT_FOUND)

        tyontekija_put = {
            'henkilo': f'/api/v1/henkilot/{tyontekija.henkilo}/',
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{tyontekija.vakajarjestaja}/',
            'lahdejarjestelma': '1',
            'tunniste': new_tunniste
        }
        resp_tyontekija_put = client.put(tyontekija_url, tyontekija_put)
        assert_status_code(resp_tyontekija_put, status.HTTP_200_OK)

        tyontekija_patch = {
            'henkilo_oid': tyontekija.henkilo.henkilo_oid,
            'vakajarjestaja_oid': tyontekija.vakajarjestaja.organisaatio_oid,
            'tunniste': tunniste
        }
        tyontekija_url_patch = f'/api/henkilosto/v1/tyontekijat/{lahdejarjestelma}:{new_tunniste}/'
        resp_tyontekija_patch = client.patch(tyontekija_url_patch, tyontekija_patch)
        assert_status_code(resp_tyontekija_patch, status.HTTP_200_OK)

        resp_tyontekija_delete = client.delete(tyontekija_url)
        assert_status_code(resp_tyontekija_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tyontekija.objects.filter(id=tyontekija.id).exists())

    def test_api_delete_tyontekija_with_referencing_objects(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        resp_tyontekija_delete = client.delete(f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/')
        assert_status_code(resp_tyontekija_delete, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_tyontekija_delete, 'errors', 'TY001',
                                'Cannot delete Tyontekija. There are Tutkinto objects referencing it that need to be deleted first.')

        Tutkinto.objects.filter(vakajarjestaja=tyontekija.vakajarjestaja, henkilo=tyontekija.henkilo).delete()
        resp_tyontekija_delete2 = client.delete(f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/')
        assert_status_code(resp_tyontekija_delete2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_tyontekija_delete2, 'errors', 'TY002',
                                'Cannot delete Tyontekija. There are objects referencing it that need to be deleted first.')

        Tyoskentelypaikka.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        PidempiPoissaolo.objects.filter(palvelussuhde__tyontekija=tyontekija).delete()
        Palvelussuhde.objects.filter(tyontekija=tyontekija).delete()
        TaydennyskoulutusTyontekija.objects.filter(tyontekija=tyontekija).delete()
        resp_tyontekija_delete3 = client.delete(f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/')
        assert_status_code(resp_tyontekija_delete3, status.HTTP_204_NO_CONTENT)

    def test_api_push_tyontekija_henkilo_address_information_removed(self):
        # Get Henkilo that does not reference any Huoltaja or Lapsi object
        henkilo_qs = Henkilo.objects.filter(huoltaja__isnull=True, lapsi__isnull=True)
        henkilo_obj = henkilo_qs.first()
        self.assertTrue(henkilo_obj.kotikunta_koodi or henkilo_obj.katuosoite or
                        henkilo_obj.postinumero or henkilo_obj.postitoimipaikka)

        tyontekija = {
            'henkilo': f'/api/v1/henkilot/{henkilo_obj.id}/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'testitunniste'
        }

        client = SetUpTestClient('tyontekija_tallentaja').client()
        post_henkilo_to_get_permissions(client, henkilo_id=henkilo_obj.id)
        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        henkilo_obj = henkilo_qs.first()
        self.assertFalse(henkilo_obj.kotikunta_koodi or henkilo_obj.katuosoite or
                         henkilo_obj.postinumero or henkilo_obj.postitoimipaikka)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_correct(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-11-01',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-01',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_correct_oid(self,):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-12-01',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
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
            'kuukausi': '2020-12-01',
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

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_missing_vakajarjestaja(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'kuukausi': '2020-10-31',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
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

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_missing_tyontekijamaara(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-12-31',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_missing_lahdejarjestelma(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '47.53',
            'kuukausi': '2020-12-31',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_missing_tuntimaara(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-31',
            'tyontekijamaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_incorrect_tunniste(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-31',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': '070501A2296',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_lahdejarjestelma_tunniste_not_unique(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-11-01',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-01',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_double_month(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto_1 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-01',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp_1 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        tilapainen_henkilosto_2 = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-02',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste2',
            'lahdejarjestelma': '1'
        }

        resp_2 = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-01',
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

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_put_tilapainen_henkilosto_vakajarjestaja_edit_oid(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-12-01',
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

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_tuntimaara_is_zero(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-31',
            'tyontekijamaara': 5,
            'tuntimaara': 0,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_tyontekijamaara_is_zero(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-31',
            'tyontekijamaara': 0,
            'tuntimaara': 5,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_push_tilapainen_henkilosto_tyontekijamaara_and_tuntimaara_is_zero(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-12-01',
            'tyontekijamaara': 0,
            'tuntimaara': 0,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @mock_date_decorator_factory(datetime_path, '2020-12-01')
    def test_api_tilapainen_henkilosto_filter(self):
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_id = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid).id

        tilapainen_henkilosto = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'kuukausi': '2020-12-01',
            'tuntimaara': '47.53',
            'tyontekijamaara': 5,
            'tunniste': 'tunniste',
            'lahdejarjestelma': '2'
        }

        client = SetUpTestClient('tilapaiset_tallentaja').client()
        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_201_CREATED)

        correct_queries_1 = ['?vakajarjestaja={0}&vuosi=2020&kuukausi=9'.format(vakajarjestaja_id),
                             '?vakajarjestaja={0}&vuosi=2020&kuukausi=9'.format(vakajarjestaja_oid),
                             '?vuosi=2020&kuukausi=9', '?kuukausi=9']

        correct_queries_2 = ['?vakajarjestaja={0}'.format(vakajarjestaja_oid),
                             '?vakajarjestaja={0}'.format(vakajarjestaja_id), '?vuosi=2020']

        incorrect_queries = ['?vakajarjestaja=999', '?vakajarjestaja=test', '?vuosi=2020&kuukausi=10',
                             '?vakajarjestaja={0}&vuosi=2020&kuukausi=11'.format(vakajarjestaja_id),
                             '?vuosi=2021', '?kuukausi=11']

        for query in correct_queries_1:
            resp_filter_correct = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_correct, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 1)

        for query in correct_queries_2:
            resp_filter_correct = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_correct, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_correct.content)['count'], 2)

        for query in incorrect_queries:
            resp_filter_incorrect = client.get('/api/henkilosto/v1/tilapainen-henkilosto/' + query)
            assert_status_code(resp_filter_incorrect, status.HTTP_200_OK)
            self.assertEqual(json.loads(resp_filter_incorrect.content)['count'], 0)

        # Invalid format
        resp_filter_error = client.get('/api/henkilosto/v1/tilapainen-henkilosto/?kuukausi=2020-03-32')
        assert_status_code(resp_filter_error, status.HTTP_400_BAD_REQUEST)

    @mock_date_decorator_factory(datetime_path, '2020-09-01')
    def test_tilapainen_henkilosto_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-tilapainenhenkilosto1'

        tilapainen_henkilosto = TilapainenHenkilosto.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        client = SetUpTestClient('tilapaiset_tallentaja').client()
        tilapainen_henkilosto_url = f'/api/henkilosto/v1/tilapainen-henkilosto/{lahdejarjestelma}:{tunniste}/'
        resp_tilapainen_henkilosto_get = client.get(tilapainen_henkilosto_url)
        assert_status_code(resp_tilapainen_henkilosto_get, status.HTTP_200_OK)
        self.assertEqual(tilapainen_henkilosto.id, json.loads(resp_tilapainen_henkilosto_get.content)['id'])

        resp_tilapainen_henkilosto_get_404 = client.get('/api/henkilosto/v1/tilapainen-henkilosto/5:no/')
        assert_status_code(resp_tilapainen_henkilosto_get_404, status.HTTP_404_NOT_FOUND)

        tilapainen_henkilosto_put = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{tilapainen_henkilosto.vakajarjestaja.id}/',
            'kuukausi': '2020-09-01',
            'tuntimaara': '50',
            'tyontekijamaara': 40,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tilapainenhenkilosto1'
        }
        resp_tilapainen_henkilosto_put = client.put(tilapainen_henkilosto_url, tilapainen_henkilosto_put)
        assert_status_code(resp_tilapainen_henkilosto_put, status.HTTP_200_OK)

        tilapainen_henkilosto_patch = {
            'vakajarjestaja_oid': tilapainen_henkilosto.vakajarjestaja.organisaatio_oid,
            'tuntimaara': '40.21'
        }
        resp_tilapainen_henkilosto_patch = client.patch(tilapainen_henkilosto_url, tilapainen_henkilosto_patch)
        assert_status_code(resp_tilapainen_henkilosto_patch, status.HTTP_200_OK)

        resp_tilapainen_henkilosto_delete = client.delete(tilapainen_henkilosto_url)
        assert_status_code(resp_tilapainen_henkilosto_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(TilapainenHenkilosto.objects.filter(id=tilapainen_henkilosto.id).exists())

    @patch('varda.serializers_henkilosto.datetime')
    def test_api_push_tilapainen_henkilosto_kuukausi_in_allowed_period(self, mock_datetime):
        mock_datetime.date = MagicMock(side_effect=date_side_effect)
        mock_datetime.timedelta = MagicMock(side_effect=timedelta_side_effect)

        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tuntimaara': '0.00',
            'tyontekijamaara': 0,
            'lahdejarjestelma': '1'
        }

        # Freeze date used in validation (period 1)
        invalid_dates_period_1 = ('2021-06-01', '2022-07-01', '2022-12-01', '2020-01-01', '2023-01-01',)
        valid_dates_period_1 = ('2021-07-01', '2021-12-01', '2022-01-01', '2022-06-01',)

        # Freeze date used in validation (period 2)
        invalid_dates_period_2 = ('2021-12-01', '2023-01-01', '2023-06-01', '2020-01-01',)
        valid_dates_period_2 = ('2022-07-01', '2022-02-01', '2022-12-01')

        test_cases = ((datetime.date(2022, 1, 1), invalid_dates_period_1, valid_dates_period_1,),
                      (datetime.date(2022, 7, 1), invalid_dates_period_2, valid_dates_period_2),)

        for test_case in test_cases:
            mock_datetime.date.today.return_value = test_case[0]
            for invalid_case in test_case[1]:
                tilapainen_henkilosto['kuukausi'] = invalid_case
                resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
                assert_status_code(resp, status.HTTP_400_BAD_REQUEST, f'{test_case[0], invalid_case}')
                assert_validation_error(resp, 'kuukausi', 'TH007', 'TilapainenHenkilosto can be saved for either the previous, or the current period.')
            for valid_case in test_case[2]:
                tilapainen_henkilosto['kuukausi'] = valid_case
                resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
                assert_status_code(resp, status.HTTP_201_CREATED, f'{test_case[0], valid_case}')

    @mock_date_decorator_factory(datetime_path, '2020-09-01')
    def test_api_push_tilapainen_henkilosto_in_advance(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-10-01',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TH009', 'tuntimaara and tyontekijamaara must be 0 if TilapainenHenkilosto is saved in advance.')

    @mock_date_decorator_factory(datetime_path, '2020-09-01')
    def test_api_push_tilapainen_henkilosto_before_2020_09(self):
        client = SetUpTestClient('tilapaiset_tallentaja').client()

        tilapainen_henkilosto = {
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'kuukausi': '2020-08-01',
            'tuntimaara': '50',
            'tyontekijamaara': 99,
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tilapainen-henkilosto/', tilapainen_henkilosto)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kuukausi', 'TH008', 'kuukausi must be equal to or after 2020-09-01.')

    def test_api_push_tutkinto_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        post_henkilo_to_get_permissions(client, henkilo_id=1)
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

        henkilo_oid = '1.2.246.562.24.6815481182312'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        tyontekija = {
            'henkilo_oid': henkilo_oid,
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

        post_henkilo_to_get_permissions(client, henkilo_id=10)
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

        henkilo_oid = '1.2.246.562.24.6815481182312'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
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

        post_henkilo_to_get_permissions(client, henkilo_id=1)
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
            'tutkinto_koodi': '719999'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/'
                                    '?henkilo_id=1&tutkinto_koodi=719999&vakajarjestaja_id=1')
        assert_status_code(resp_delete, status.HTTP_204_NO_CONTENT)

    def test_api_delete_tutkinto_by_oid(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        henkilo_oid = '1.2.246.562.24.6815481182312'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        tyontekija = {
            'henkilo_oid': henkilo_oid,
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'tunniste': 'tunniste',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)

        tutkinto = {
            'henkilo_oid': '1.2.246.562.24.6815481182312',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '719999'
        }

        resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(resp, status.HTTP_201_CREATED)
        resp_delete = client.delete('/api/henkilosto/v1/tutkinnot/delete/'
                                    '?henkilo_oid=1.2.246.562.24.6815481182312'
                                    '&tutkinto_koodi=719999'
                                    '&vakajarjestaja_oid=1.2.246.562.10.34683023489')
        assert_status_code(resp_delete, status.HTTP_204_NO_CONTENT)

    def test_api_delete_tutkinto_with_tutkinto_koodi_in_use(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        post_henkilo_to_get_permissions(client, henkilo_id=1)
        tyontekija = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste',
        }

        resp = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija)
        assert_status_code(resp, status.HTTP_201_CREATED)
        tyontekija_id = json.loads(resp.content).get('id')

        tutkinto = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': '/api/v1/vakajarjestajat/1/',
            'tutkinto_koodi': '321901',
        }

        tutkinto_resp = client.post('/api/henkilosto/v1/tutkinnot/', tutkinto)
        assert_status_code(tutkinto_resp, status.HTTP_201_CREATED)
        tutkinto_id = json.loads(tutkinto_resp.content).get('id')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-01',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        delete_resp = client.delete('/api/henkilosto/v1/tutkinnot/{}/'.format(tutkinto_id))
        assert_status_code(delete_resp, status.HTTP_400_BAD_REQUEST)

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
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
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
            'paattymis_pvm': '2020-09-01',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_palvelussuhde_edit_allowed_and_delete(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        # Get initial data as a dictionary
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(tunniste='testing-tyoskentelypaikka2_1')
        resp = client.get(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/')
        assert_status_code(resp, status.HTTP_200_OK)
        palvelussuhde_dict = json.loads(resp.content)

        # These are the fields that can be edited
        palvelussuhde_edits = {
            'tyosuhde_koodi': '2',
            'tyoaika_koodi': '2',
            'tutkinto_koodi': '613101',
            'tyoaika_viikossa': '35.00',
            'alkamis_pvm': '2020-01-01',
            'paattymis_pvm': '2021-04-04',
            'lahdejarjestelma': '1',
            'tunniste': 'b'
        }

        # Change fields one by one and make sure we get a success
        for key, value in palvelussuhde_edits.items():
            palvelussuhde_edit = palvelussuhde_dict.copy()
            palvelussuhde_edit[key] = value
            palvelussuhde_id = palvelussuhde_dict['id']
            resp = client.put(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/', json.dumps(palvelussuhde_edit), content_type='application/json')
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Fetch object and ensure field was changed
            resp = client.get(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/')
            assert_status_code(resp, status.HTTP_200_OK)
            data = json.loads(resp.content)
            self.assertEqual(value, data[key])

        # user does not have permission to remove tyontekija from taydennyskoulutus
        TaydennyskoulutusTyontekija.objects.get(tyontekija=palvelussuhde.tyontekija).delete()

        delete_resp = client.delete(f'/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka.id}/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)

        delete_resp = client.delete(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)

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
            palvelussuhde_id = palvelussuhde_dict['id']
            resp = client.put(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/', json.dumps(palvelussuhde_edit), content_type='application/json')
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

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
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
            'alkamis_pvm': '2021-03-02',
            'paattymis_pvm': '2021-03-01',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.')

    def test_palvelussuhde_add_incorrect_tyoaika_viikossa(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '50.73',
            'alkamis_pvm': '2020-03-02',
            'paattymis_pvm': '2021-03-05',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tyoaika_viikossa', 'DY005', 'Ensure this value is less than or equal to 50.')

    def test_palvelussuhde_add_too_early_ending_paattymis_pvm(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '50.73',
            'alkamis_pvm': '2014-03-02',
            'paattymis_pvm': '2020-03-05',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'PS007', 'paattymis_pvm must be equal to or after 2020-09-01.')

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
            resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

        # The next one will fail
        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'PS006', 'Tyontekija already has 7 overlapping Palvelussuhde on the given date range.')

        # But later dates are ok
        palvelussuhde.update(alkamis_pvm='2022-02-02', paattymis_pvm='2023-03-03')
        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
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

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tyosuhde_koodi', 'KO003', 'Not a valid code.')
        assert_validation_error(resp, 'tyoaika_koodi', 'KO003', 'Not a valid code.')
        assert_validation_error(resp, 'tutkinto_koodi', 'KO003', 'Not a valid code.')

    def test_palvelussuhde_add_wrong_tutkinto(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija3')

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '001',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2021-03-02',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tutkinto_koodi', 'PS005', 'Tyontekija does not have the given Tutkinto.')

    def test_palvelussuhde_add_and_edit_tyosuhde_koodi_2(self):
        # tyosuhde_koodi 2 is for fixed term employees. Paattymis_pvm can't be undefined in these cases.
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija2')

        # missing paattymis_pvm
        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '2',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2021-03-01',
            'lahdejarjestelma': '1',
            'tunniste': 'testpalvelussuhde'
        }
        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

        # add paattymis_pvm so the request gets through
        palvelussuhde['paattymis_pvm'] = '2021-11-11'

        resp = client.post('/api/henkilosto/v1/palvelussuhteet/', json.dumps(palvelussuhde), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        palvelussuhde_patch = {
            'paattymis_pvm': None
        }

        palvelussuhde_id = json.loads(resp.content)['id']
        resp = client.patch(f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde_id}/', json.dumps(palvelussuhde_patch), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'PS003', 'paattymis_pvm is required for tyosuhde_koodi 2.')

    def test_palvelussuhde_tyontekija_tunniste_related_field(self):
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = {
            'tyontekija_tunniste': tyontekija.tunniste,
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'lahdejarjestelma': tyontekija.lahdejarjestelma,
        }
        resp_palvelussuhde = client.post('/api/henkilosto/v1/palvelussuhteet/', palvelussuhde)
        assert_status_code(resp_palvelussuhde, status.HTTP_201_CREATED)
        palvelussuhde_obj = Palvelussuhde.objects.get(id=json.loads(resp_palvelussuhde.content)['id'])
        self.assertEqual(tyontekija.id, palvelussuhde_obj.tyontekija.id)

    def test_palvelussuhde_tyontekija_invalid_tunniste_related_field(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = {
            'tyontekija_tunniste': 'tunniste300',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '001',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'lahdejarjestelma': '1',
        }
        resp_palvelussuhde = client.post('/api/henkilosto/v1/palvelussuhteet/', palvelussuhde)
        assert_status_code(resp_palvelussuhde, status.HTTP_400_BAD_REQUEST)

    def test_palvelussuhde_tyontekija_correct_tunniste_from_url(self):
        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'lahdejarjestelma': tyontekija.lahdejarjestelma,
        }
        resp_palvelussuhde = client.post('/api/henkilosto/v1/palvelussuhteet/', palvelussuhde)
        assert_status_code(resp_palvelussuhde, status.HTTP_201_CREATED)
        self.assertEqual(tyontekija.tunniste, json.loads(resp_palvelussuhde.content)['tyontekija_tunniste'])

    def test_palvelussuhde_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        palvelussuhde_tunniste = 'testing-palvelussuhde2'
        tyoskentelypaikka_tunniste = 'testing-tyoskentelypaikka2_1'

        palvelussuhde = Palvelussuhde.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=palvelussuhde_tunniste)
        tyoskentelypaikka = Tyoskentelypaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tyoskentelypaikka_tunniste)

        client = SetUpTestClient('tyontekija_tallentaja').client()
        palvelussuhde_url = f'/api/henkilosto/v1/palvelussuhteet/{lahdejarjestelma}:{palvelussuhde_tunniste}/'
        tyoskentelypaikka_url = f'/api/henkilosto/v1/tyoskentelypaikat/{lahdejarjestelma}:{tyoskentelypaikka_tunniste}/'
        resp_palvelussuhde_get = client.get(palvelussuhde_url)
        assert_status_code(resp_palvelussuhde_get, status.HTTP_200_OK)
        self.assertEqual(palvelussuhde.id, json.loads(resp_palvelussuhde_get.content)['id'])

        resp_palvelussuhde_get_404 = client.get('/api/henkilosto/v1/palvelussuhteet/5:no/')
        assert_status_code(resp_palvelussuhde_get_404, status.HTTP_404_NOT_FOUND)

        palvelussuhde_put = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{palvelussuhde.tyontekija}/',
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': '321901',
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2030-04-01',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-palvelussuhde2',
        }
        resp_palvelussuhde_put = client.put(palvelussuhde_url, palvelussuhde_put)
        assert_status_code(resp_palvelussuhde_put, status.HTTP_200_OK)

        palvelussuhde_patch = {
            'tyontekija': f'/api/henkilosto/v1/tyontekijat/{palvelussuhde.tyontekija}/',
            'alkamis_pvm': '2020-03-01',
            'tutkinto_koodi': '321901',
            'paattymis_pvm': '2030-05-01'
        }
        resp_palvelussuhde_patch = client.patch(palvelussuhde_url, palvelussuhde_patch)
        assert_status_code(resp_palvelussuhde_patch, status.HTTP_200_OK)

        # user does not have permission to remove person from taydennyskoulutus
        TaydennyskoulutusTyontekija.objects.get(tyontekija=palvelussuhde.tyontekija).delete()

        resp_tyoskentelypaikka_delete = client.delete(tyoskentelypaikka_url)
        assert_status_code(resp_tyoskentelypaikka_delete, status.HTTP_204_NO_CONTENT)

        resp_palvelussuhde_delete = client.delete(palvelussuhde_url)
        assert_status_code(resp_palvelussuhde_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tyoskentelypaikka.objects.filter(id=tyoskentelypaikka.id).exists())
        self.assertFalse(Palvelussuhde.objects.filter(id=palvelussuhde.id).exists())

    def test_tyoskentelypaikka_add_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815').first()

        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka': '/api/v1/toimipaikat/{}/'.format(toimipaikka.id),
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_add_too_many(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        palvelussuhde_22 = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2-2')
        palvelussuhde_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id)
        palvelussuhde_22_url = '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde_22.id)
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815').first()

        # Tietoluettelosta: 'Työntekijälle voi tallentaa enintään kolme pääasiallista toimipaikkaa, joissa työntekijä työskentelee.'

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
        for i in range(2):
            resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

        # The next one will fail
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TA011', 'Palvelussuhde already has 3 overlapping Tyoskentelypaikka on the given date range.')

        # This will succeed due to different palvelussuhde
        tyoskentelypaikka.update(palvelussuhde=palvelussuhde_22_url)
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        client.delete('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(json.loads(resp.content)['id']))

        # But cases where kiertava_tyontekija_kytkin is True are ok
        tyoskentelypaikka.update(kiertava_tyontekija_kytkin=True, toimipaikka=None)
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        # So are later dates
        tyoskentelypaikka.update(kiertava_tyontekija_kytkin=False, toimipaikka='/api/v1/toimipaikat/{}/'.format(toimipaikka), alkamis_pvm='2022-02-02', paattymis_pvm='2023-03-03')
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
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
            resp = client.put('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict['id']), json.dumps(tyoskentelypaikka_edit), content_type='application/json')
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Fetch object and ensure field was changed
            resp = client.get('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict['id']))
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
            resp = client.put(tyoskentelypaikka_url, json.dumps(tyoskentelypaikka_edit), content_type='application/json')
            assert_status_code(resp, status.HTTP_200_OK, key)

            # Make sure that the so-called edit didn't do anything
            resp = client.get(tyoskentelypaikka_url)
            assert_status_code(resp, status.HTTP_200_OK)
            tyoskentelypaikka_dict2 = json.loads(resp.content)
            self.assertEqual(tyoskentelypaikka_dict_original[key], tyoskentelypaikka_dict2[key])

    def test_tyoskentelypaikka_kiertava_disallows_toimipaikka(self):
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
            'kiertava_tyontekija_kytkin': True,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kiertava_tyontekija_kytkin', 'TA004',
                                'Toimipaikka cannot be specified with kiertava_tyontekija_kytkin.')

    def test_tyoskentelypaikka_require_toimipaikka_or_kiertava_true(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        tyoskentelypaikka = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'alkamis_pvm': '2020-09-01',
            'paattymis_pvm': '2021-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'toimipaikka', 'TA012', 'toimipaikka is required if kiertava_tyontekija_kytkin is false.')

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

        resp = client.put('/api/henkilosto/v1/tyoskentelypaikat/{}/'.format(tyoskentelypaikka_dict['id']), json.dumps(tyoskentelypaikka_dict), content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_tyoskentelypaikka_incorrect_date_validation(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')
        toimipaikka = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548815')[0]

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
            ('2020-03-01', '2020-01-01', 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.'),
            ('2020-03-01', '2031-01-01', 'paattymis_pvm', 'TA006', 'paattymis_pvm must be before or equal to Palvelussuhde paattymis_pvm.'),
            ('2019-03-01', '2021-01-01', 'alkamis_pvm', 'TA008', 'alkamis_pvm must be equal to or after Palvelussuhde alkamis_pvm.'),
            ('2031-03-01', '2032-01-01', 'alkamis_pvm', 'TA009', 'alkamis_pvm must be before or equal to Palvelussuhde paattymis_pvm.'),
            ('2020-08-01', '2020-08-28', 'paattymis_pvm', 'TA007', 'paattymis_pvm must be equal to or after 2020-09-01.'),
            ('2020-09-01', None, 'paattymis_pvm', 'TA013', 'Tyoskentelypaikka must have paattymis_pvm because Palvelussuhde has paattymis_pvm.')
        ]

        for (start, end, key, expected_error_code, expected_message) in cases:
            tyoskentelypaikka.update(alkamis_pvm=start, paattymis_pvm=end)
            resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST, f'{start}_{end}')
            assert_validation_error(resp, key, expected_error_code, expected_message)

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
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        # Try to add another on the same range with kiertava kiertava=True
        # This should fail.
        tyoskentelypaikka.update(toimipaikka=None, kiertava_tyontekija_kytkin=True, alkamis_pvm='2025-05-01', paattymis_pvm='2025-12-31')
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kiertava_tyontekija_kytkin', 'TA010',
                                'Cannot have different values of kiertava_tyontekija_kytkin on overlapping date ranges.')

        # But works on a different palvelussuhde, on the same tyontekija
        tyoskentelypaikka.update(palvelussuhde=palvelussuhde_22_url)
        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_add_incorrect_toimipaikka(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()
        toimipaikka_oid = '1.2.246.562.10.9395737548810'

        # User must have permission to toimipaikka or 400 toimipaikka not found is returned
        user = User.objects.get(username='tyontekija_tallentaja')
        permission_group = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.9395737548810')
        user.groups.add(permission_group)

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        tyoskentelypaikka = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'toimipaikka_oid': toimipaikka_oid,
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-05-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(tyoskentelypaikka), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'toimipaikka', 'TA005', 'Toimipaikka must have the same Vakajarjestaja as Tyontekija.')

    def test_tyoskentelypaikka_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-tyoskentelypaikka1'

        tyoskentelypaikka = Tyoskentelypaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        client = SetUpTestClient('tyontekija_tallentaja').client()
        tyoskentelypaikka_url = f'/api/henkilosto/v1/tyoskentelypaikat/{lahdejarjestelma}:{tunniste}/'
        resp_tyoskentelypaikka_get = client.get(tyoskentelypaikka_url)
        assert_status_code(resp_tyoskentelypaikka_get, status.HTTP_200_OK)
        self.assertEqual(tyoskentelypaikka.id, json.loads(resp_tyoskentelypaikka_get.content)['id'])

        resp_tyoskentelypaikka_get_404 = client.get('/api/henkilosto/v1/tyoskentelypaikat/5:no/')
        assert_status_code(resp_tyoskentelypaikka_get_404, status.HTTP_404_NOT_FOUND)

        tyoskentelypaikka_put = {
            'palvelussuhde_tunniste': tyoskentelypaikka.palvelussuhde.tunniste,
            'toimipaikka': f'/api/v1/toimipaikat/{tyoskentelypaikka.toimipaikka}/',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': False,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-tyoskentelypaikka1'
        }
        resp_tyoskentelypaikka_put = client.put(tyoskentelypaikka_url, tyoskentelypaikka_put)
        assert_status_code(resp_tyoskentelypaikka_put, status.HTTP_200_OK)

        tyoskentelypaikka_patch = {
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02'
        }
        resp_tyoskentelypaikka_patch = client.patch(tyoskentelypaikka_url, tyoskentelypaikka_patch)
        assert_status_code(resp_tyoskentelypaikka_patch, status.HTTP_200_OK)

        resp_tyoskentelypaikka_delete = client.delete(tyoskentelypaikka_url)
        assert_status_code(resp_tyoskentelypaikka_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Tyoskentelypaikka.objects.filter(id=tyoskentelypaikka.id).exists())

    def test_tyoskentelypaikka_palvelussuhde_tunniste_related_field(self):
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyoskentelypaikka = {
            'palvelussuhde_tunniste': palvelussuhde.tunniste,
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': False,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': palvelussuhde.lahdejarjestelma,
            'tunniste': 'tunniste500'
        }
        resp_tyoskentelypaikka = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(resp_tyoskentelypaikka, status.HTTP_201_CREATED)
        tyoskentelypaikka_obj = Tyoskentelypaikka.objects.get(id=json.loads(resp_tyoskentelypaikka.content)['id'])
        self.assertEqual(palvelussuhde.id, tyoskentelypaikka_obj.palvelussuhde.id)

    def test_tyoskentelypaikka_palvelussuhde_invalid_tunniste_related_field(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyoskentelypaikka = {
            'palvelussuhde_tunniste': 'tunniste_invalid',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-06-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': False,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste500'
        }
        resp_tyoskentelypaikka = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(resp_tyoskentelypaikka, status.HTTP_400_BAD_REQUEST)

    def test_tyoskentelypaikka_palvelussuhde_correct_tunniste_from_url(self):
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        tyoskentelypaikka = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'toimipaikka': '/api/v1/toimipaikat/2/',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': False,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste500'
        }
        resp_tyoskentelypaikka = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka)
        assert_status_code(resp_tyoskentelypaikka, status.HTTP_201_CREATED)
        self.assertEqual(palvelussuhde.tunniste, json.loads(resp_tyoskentelypaikka.content)['palvelussuhde_tunniste'])

    def test_tyoskentelypaikka_delete_invalid(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-tyoskentelypaikka2'

        tyoskentelypaikka = Tyoskentelypaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.delete(f'/api/henkilosto/v1/tyoskentelypaikat/{tyoskentelypaikka.id}/')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tehtavanimike_koodi', 'TA002',
                                'Cannot delete Tyoskentelypaikka. Taydennyskoulutus objects with this '
                                'tehtavanimike_koodi must be deleted first.')

    def test_tyoskentelypaikka_tehtavanimike_patch_invalid(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-tyoskentelypaikka2'

        tyoskentelypaikka_patch = {
            'tehtavanimike_koodi': '84724'
        }
        client = SetUpTestClient('tyontekija_tallentaja').client()
        resp = client.patch(f'/api/henkilosto/v1/tyoskentelypaikat/{lahdejarjestelma}:{tunniste}/',
                            tyoskentelypaikka_patch)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tehtavanimike_koodi', 'TA015',
                                'Cannot change tehtavanimike_koodi. There are Taydennyskoulutus objects that use this '
                                'tehtavanimike_koodi.')

    def test_pidempipoissaolo_add_correct(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        # Duration is exactly 60 days
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-01-01',
            'paattymis_pvm': '2021-03-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }

        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

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

        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-09-02',  # The day after the other poissaolo
            'paattymis_pvm': '2022-03-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo2'
        }

        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

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
            ('2020-10-01', '2020-09-01', 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.'),
            ('2022-01-01', '2022-01-30', 'paattymis_pvm', 'PP003', 'Poissaolo duration must be 60 days or more.'),
            ('2021-01-01', '2021-02-28', 'paattymis_pvm', 'PP003', 'Poissaolo duration must be 60 days or more.'),
            ('2021-01-01', '2021-02-29', 'paattymis_pvm', 'GE006', 'This field must be a date string in YYYY-MM-DD format.'),
        ]

        for (start, end, key, expected_error_code, expected_message) in cases:
            extra = f'{start}_{end}'
            pidempipoissaolo.update(alkamis_pvm=start, paattymis_pvm=end, tunniste=extra)
            resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
            assert_status_code(resp, 400, extra)
            assert_validation_error(resp, key, expected_error_code, expected_message, extra)

    def test_pidempipoissaolo_overlap(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        # Add initial poissaolo 1
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }
        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        # Add initial poissaolo 2
        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2023-06-01',
            'paattymis_pvm': '2029-08-15',
            'lahdejarjestelma': '1',
            'tunniste': 'foo2'
        }
        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

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
            resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
            assert_status_code(resp, 400, extra)
            assert_validation_error(resp, 'errors', 'PP007',
                                    'Palvelussuhde already has 1 overlapping PidempiPoissaolo on the given date range.',
                                    extra)

    def test_pidempipoissaolo_palvelussuhde_tunniste_related_field(self):
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        pidempi_poissaolo = {
            'palvelussuhde_tunniste': palvelussuhde.tunniste,
            'alkamis_pvm': '2023-06-01',
            'paattymis_pvm': '2024-06-01',
            'lahdejarjestelma': palvelussuhde.lahdejarjestelma,
            'tunniste': 'tunniste500'
        }
        resp_pidempi_poissaolo = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo)
        assert_status_code(resp_pidempi_poissaolo, status.HTTP_201_CREATED)
        pidempi_poissaolo_obj = PidempiPoissaolo.objects.get(id=json.loads(resp_pidempi_poissaolo.content)['id'])
        self.assertEqual(palvelussuhde.id, pidempi_poissaolo_obj.palvelussuhde.id)

    def test_pidempipoissaolo_palvelussuhde_invalid_tunniste_related_field(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        pidempi_poissaolo = {
            'palvelussuhde_tunniste': 'tunniste_invalid',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-06-02',
            'lahdejarjestelma': '1',
            'tunniste': 'tunniste500'
        }
        resp_pidempi_poissaolo = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo)
        assert_status_code(resp_pidempi_poissaolo, status.HTTP_400_BAD_REQUEST)

    def test_pidempipoissaolo_palvelussuhde_correct_tunniste_from_url(self):
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        client = SetUpTestClient('tyontekija_tallentaja').client()

        pidempi_poissaolo = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02',
            'lahdejarjestelma': palvelussuhde.lahdejarjestelma,
            'tunniste': 'tunniste500'
        }
        resp_pidempi_poissaolo = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', pidempi_poissaolo)
        assert_status_code(resp_pidempi_poissaolo, status.HTTP_201_CREATED)
        self.assertEqual(palvelussuhde.tunniste, json.loads(resp_pidempi_poissaolo.content)['palvelussuhde_tunniste'])

    def test_pidempipoissaolo_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-pidempipoissaolo1'

        pidempi_poissaolo = PidempiPoissaolo.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        client = SetUpTestClient('tyontekija_tallentaja').client()
        pidempi_poissaolo_url = f'/api/henkilosto/v1/pidemmatpoissaolot/{lahdejarjestelma}:{tunniste}/'
        resp_pidempi_poissaolo_get = client.get(pidempi_poissaolo_url)
        assert_status_code(resp_pidempi_poissaolo_get, status.HTTP_200_OK)
        self.assertEqual(pidempi_poissaolo.id, json.loads(resp_pidempi_poissaolo_get.content)['id'])

        resp_pidempi_poissaolo_get_404 = client.get('/api/henkilosto/v1/pidemmatpoissaolot/5:no/')
        assert_status_code(resp_pidempi_poissaolo_get_404, status.HTTP_404_NOT_FOUND)

        pidempi_poissaolo_put = {
            'palvelussuhde_tunniste': pidempi_poissaolo.palvelussuhde.tunniste,
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-10-02',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-pidempipoissaolo1'
        }
        resp_pidempi_poissaolo_put = client.put(pidempi_poissaolo_url, pidempi_poissaolo_put)
        assert_status_code(resp_pidempi_poissaolo_put, status.HTTP_200_OK)

        pidempi_poissaolo_patch = {
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2020-09-02'
        }
        resp_pidempi_poissaolo_patch = client.patch(pidempi_poissaolo_url, pidempi_poissaolo_patch)
        assert_status_code(resp_pidempi_poissaolo_patch, status.HTTP_200_OK)

        resp_pidempi_poissaolo_delete = client.delete(pidempi_poissaolo_url)
        assert_status_code(resp_pidempi_poissaolo_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(PidempiPoissaolo.objects.filter(id=pidempi_poissaolo.id).exists())

    def test_pidempipoissaolo_modify_and_delete(self):
        client = SetUpTestClient('tyontekija_tallentaja').client()

        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde2')

        pidempipoissaolo = {
            'palvelussuhde': '/api/henkilosto/v1/palvelussuhteet/{}/'.format(palvelussuhde.id),
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1',
            'tunniste': 'foo'
        }

        resp = client.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        delete_resp = client.delete('/api/henkilosto/v1/pidemmatpoissaolot/{}/'.format(json.loads(resp.content).get('id')))
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)

    def test_taydennyskoulutus_add_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        saved_taydennyskoulutus = json.loads(resp.content)

        # Check that what was saved is also returned.
        # The serializer populates additional fields, so they must be added here
        taydennyskoulutus.update({
            'taydennyskoulutus_tyontekijat': [{
                'tyontekija': f'http://testserver/api/henkilosto/v1/tyontekijat/{tyontekija.id}/',
                'tehtavanimike_koodi': '39407',
                'lahdejarjestelma': '1',
                'tunniste': 'testing-tyontekija1',
                'henkilo_oid': '1.2.246.562.24.2431884920041',
                'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            }],
        })

        for key, value in taydennyskoulutus.items():
            self.assertEqual(value, saved_taydennyskoulutus[key], key)

    def test_taydennyskoulutus_add_correct_oid(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{'henkilo_oid': tyontekija.henkilo.henkilo_oid, 'vakajarjestaja_oid': tyontekija.vakajarjestaja.organisaatio_oid, 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        saved_taydennyskoulutus = json.loads(resp.content)

        # Check tyontekijat separately
        taydennyskoulutus.pop('taydennyskoulutus_tyontekijat')
        tyontekijat = saved_taydennyskoulutus.pop('taydennyskoulutus_tyontekijat')
        self.assertEqual(tyontekijat[0]['tyontekija'], f'http://testserver/api/henkilosto/v1/tyontekijat/{tyontekija.id}/')

        # Check rest of the fields against the original request
        for key, value in taydennyskoulutus.items():
            self.assertEqual(value, saved_taydennyskoulutus[key], key)

    def test_taydennyskoulutus_add_correct_many(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija1 = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija4 = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija1.id}/', 'tehtavanimike_koodi': '39407'},
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija4.id}/', 'tehtavanimike_koodi': '77826'},
            ],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        saved_taydennyskoulutus = json.loads(resp.content)

        # Check tyontekijat
        tyontekijat = saved_taydennyskoulutus.pop('taydennyskoulutus_tyontekijat')
        self.assertEqual(tyontekijat[0]['tyontekija'], f'http://testserver/api/henkilosto/v1/tyontekijat/{tyontekija1.id}/')
        self.assertEqual(tyontekijat[0]['tehtavanimike_koodi'], '39407')
        self.assertEqual(tyontekijat[1]['tyontekija'], f'http://testserver/api/henkilosto/v1/tyontekijat/{tyontekija4.id}/')
        self.assertEqual(tyontekijat[1]['tehtavanimike_koodi'], '77826')

    def test_taydennyskoulutus_get_filtering(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija1 = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija4 = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'http://testserver/api/henkilosto/v1/tyontekijat/{tyontekija1.id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        taydennyskoulutus.update({
            'nimi': 'Kakkoskoulutus',
        })
        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        taydennyskoulutus.update({
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija4.id}/', 'tehtavanimike_koodi': '77826'}],
            'nimi': 'Kolmoskoulutus',
        })
        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        # Check koulutukset of first tyontekija
        resp = client.get(f'/api/henkilosto/v1/taydennyskoulutukset/?tyontekija={tyontekija1.id}', content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_data = json.loads(resp.content)
        self.assertEqual(resp_data['count'], 3)
        koulutus_nimet = [k['nimi'] for k in resp_data['results']]
        self.assertIn('Ensiapukoulutus', koulutus_nimet)
        self.assertIn('Kakkoskoulutus', koulutus_nimet)

        # Check the same one, but with a different query
        resp = client.get(f'/api/henkilosto/v1/taydennyskoulutukset/?henkilo_oid={tyontekija1.henkilo.henkilo_oid}&vakajarjestaja_oid={tyontekija1.vakajarjestaja.organisaatio_oid}', content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_data2 = json.loads(resp.content)
        self.assertEqual(resp_data, resp_data2)

        # Check koulutukset of second tyontekija
        resp = client.get(f'/api/henkilosto/v1/taydennyskoulutukset/?tyontekija={tyontekija4.id}', content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_data = json.loads(resp.content)
        self.assertEqual(resp_data['count'], 2)
        koulutus_nimet = [k['nimi'] for k in resp_data['results']]
        self.assertIn('Kolmoskoulutus', koulutus_nimet)

    def test_taydennyskoulutus_add_incorrect_tehtavanimike(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        taydennyskoulutus = {
            # Correct tehtavanimike_koodi is 39407
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '77826'}],
            'nimi': 'Etnsiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['tehtavanimike_koodi'], 'TK008', 'Tyontekija does not have given tehtavanimike_koodi.')

    def test_taydennyskoulutus_add_incorrect_koulutuspaivia(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        taydennyskoulutus_1 = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.7',  # Must be % 0.5
            'lahdejarjestelma': '1',
        }

        resp_1 = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus_1), content_type='application/json')
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'koulutuspaivia', 'GE018', 'Invalid decimal step.')

        taydennyskoulutus_2 = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '160.5',  # Must be < 160
            'lahdejarjestelma': '1',
        }

        resp_2 = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus_2), content_type='application/json')
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'koulutuspaivia', 'DY005', 'Ensure this value is less than or equal to 160.')

    def test_taydennyskoulutus_add_invalid_tyontekija(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija1 = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija2 = Tyontekija.objects.get(tunniste='testing-tyontekija2')

        cases = [
            [
                {'lahdejarjestelma': 1, 'tunniste': 'unknown_tyontekija'},
                ['taydennyskoulutus_tyontekijat', '0', 'tunniste'],
                'TK006',
                'Could not find Tyontekija matching the given (lahdejarjestelma, tunniste).'
            ],
            [
                {'tunniste': 'unknown_tyontekija'},
                ['taydennyskoulutus_tyontekijat', '0', 'tunniste'],
                'TK003',
                'Either both lahdejarjestelma and tunniste, or neither must be given.'
            ],
            [
                {'henkilo_oid': '1.2.246.562.24.2431884920040', 'vakajarjestaja_oid': '1.2.246.562.10.34683023489'},
                ['taydennyskoulutus_tyontekijat', '0', 'henkilo_oid'],
                'TK004',
                'Could not find Tyontekija matching the given (henkilo_oid, vakajarjestaja_oid).'
            ],
            [
                {'henkilo_oid': '1.2.246.562.24.2431884920040'},
                ['taydennyskoulutus_tyontekijat', '0', 'henkilo_oid'],
                'TK002',
                'Either both henkilo_oid and vakajarjestaja_oid, or neither must be given.'
            ],
            [
                {},
                ['taydennyskoulutus_tyontekijat', '0', 'tyontekija'],
                'TK001',
                'Tyontekija not specified. Use (tyontekija), (henkilo_oid, vakajarjestaja_oid) or (lahdejarjestelma, tunniste).'
            ],
            [
                {'tyontekija': '/api/henkilosto/v1/tyontekijat/1000000/'},
                ['taydennyskoulutus_tyontekijat', '0', 'tyontekija'],
                'GE008',
                'Invalid hyperlink, object does not exist.'
            ],
            [
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija1.id}/',
                 'henkilo_oid': tyontekija2.henkilo.henkilo_oid, 'vakajarjestaja_oid': tyontekija2.vakajarjestaja.organisaatio_oid},
                ['taydennyskoulutus_tyontekijat', '0', 'henkilo_oid'],
                'TK005',
                'henkilo_oid does not refer to the same Tyontekija as URL.'
            ],
            [
                {'henkilo_oid': tyontekija1.henkilo.henkilo_oid, 'vakajarjestaja_oid': tyontekija1.vakajarjestaja.organisaatio_oid,
                 'tunniste': tyontekija2.tunniste, 'lahdejarjestelma': tyontekija2.lahdejarjestelma},
                ['taydennyskoulutus_tyontekijat', '0', 'tunniste'],
                'TK007',
                'Tunniste does not refer to the same Tyontekija as URL or henkilo_oid.'
            ],
        ]

        for data, error_path, expected_error_code, expected_error_msg in cases:
            taydennyskoulutus = {
                'taydennyskoulutus_tyontekijat': [{'tehtavanimike_koodi': '39407', **data}],
                'nimi': 'Ensiapukoulutus',
                'suoritus_pvm': '2020-09-14',
                'koulutuspaivia': '1.5',
                'lahdejarjestelma': '1',
            }
            resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
            assert_status_code(resp, 400, data)
            assert_validation_error(resp, error_path, expected_error_code, expected_error_msg, data)

    def test_taydennyskoulutus_add_duplicate(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/'},
                {'tehtavanimike_koodi': '39407', 'henkilo_oid': tyontekija.henkilo.henkilo_oid, 'vakajarjestaja_oid': tyontekija.vakajarjestaja.organisaatio_oid}
            ],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'taydennyskoulutus_tyontekijat', 'TK010', 'Duplicates detected.')

    def test_taydennyskoulutus_update_tyontekijat_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_4_obj = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        taydennyskoulutus_put = {
            'taydennyskoulutus_tyontekijat': [
                {
                    'tehtavanimike_koodi': '39407',
                    'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'
                },
                {
                    'tehtavanimike_koodi': '77826',
                    'henkilo_oid': tyontekija_4_obj.henkilo.henkilo_oid,
                    'vakajarjestaja_oid': tyontekija_4_obj.vakajarjestaja.organisaatio_oid
                }
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '2',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        }
        resp_put = client.put(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                              json.dumps(taydennyskoulutus_put), content_type='application/json')
        assert_status_code(resp_put, status.HTTP_200_OK)
        self.assertEqual(taydennyskoulutus_qs.first().taydennyskoulutukset_tyontekijat.first().tehtavanimike_koodi, '39407')
        self.assertEqual(taydennyskoulutus_qs.first().koulutuspaivia, 2)

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'},
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'},
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ]
        }
        resp_patch = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                  json.dumps(taydennyskoulutus_patch), content_type='application/json')
        assert_status_code(resp_patch, status.HTTP_200_OK)
        self.assertEqual(taydennyskoulutus_qs.first().taydennyskoulutukset_tyontekijat.first().tehtavanimike_koodi, '39407')

    def test_taydennyskoulutus_update_tyontekijat_incorrect(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_4_obj = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        # Tyontekija does not have tehtavanimike_koodi
        taydennyskoulutus_put = {
            'taydennyskoulutus_tyontekijat': [
                {
                    'tehtavanimike_koodi': '84724',
                    'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'
                },
                {
                    'tehtavanimike_koodi': '77826',
                    'henkilo_oid': tyontekija_4_obj.henkilo.henkilo_oid,
                    'vakajarjestaja_oid': tyontekija_4_obj.vakajarjestaja.organisaatio_oid
                }
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '2',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        }
        resp_put = client.put(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                              json.dumps(taydennyskoulutus_put), content_type='application/json')
        assert_status_code(resp_put, status.HTTP_400_BAD_REQUEST)

        # Invalid tehtavanimike_koodi
        taydennyskoulutus_patch_1 = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': 'test', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_1 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_1), content_type='application/json')
        assert_status_code(resp_patch_1, status.HTTP_400_BAD_REQUEST)

        # Duplicates
        taydennyskoulutus_patch_2 = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'},
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_2 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_2), content_type='application/json')
        assert_status_code(resp_patch_2, status.HTTP_400_BAD_REQUEST)

        # tyontekijat and tyontekijat_remove
        taydennyskoulutus_patch_3 = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ]
        }
        resp_patch_3 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_3), content_type='application/json')
        assert_status_code(resp_patch_3, status.HTTP_400_BAD_REQUEST)

        # Delete TaydennyskoulutusTyontekija so that we can potentially add it again
        TaydennyskoulutusTyontekija.objects.get(tyontekija=tyontekija_1_obj,
                                                taydennyskoulutus__tunniste='testing-taydennyskoulutus1',
                                                tehtavanimike_koodi='64212').delete()

        # tyontekijat and tyontekijat_add
        taydennyskoulutus_patch_4 = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_4 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_4), content_type='application/json')
        assert_status_code(resp_patch_4, status.HTTP_400_BAD_REQUEST)

        # tyontekijat and tyontekijat_add and tyontekijat_remove
        taydennyskoulutus_patch_5 = {
            'taydennyskoulutus_tyontekijat': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ]
        }
        resp_patch_5 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_5), content_type='application/json')
        assert_status_code(resp_patch_5, status.HTTP_400_BAD_REQUEST)

    def test_taydennyskoulutus_update_tyontekijat_add_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        # Delete TaydennyskoulutusTyontekija so that we can add it again
        TaydennyskoulutusTyontekija.objects.get(tyontekija=tyontekija_1_obj,
                                                taydennyskoulutus__tunniste='testing-taydennyskoulutus1',
                                                tehtavanimike_koodi='64212').delete()

        taydennyskoulutus_put = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        }
        resp_put = client.put(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                              json.dumps(taydennyskoulutus_put), content_type='application/json')
        assert_status_code(resp_put, status.HTTP_200_OK)
        taydennyskoulutus_tyontekija_qs = taydennyskoulutus_qs.first().taydennyskoulutukset_tyontekijat.filter(tyontekija=tyontekija_1_obj)
        self.assertEqual(taydennyskoulutus_tyontekija_qs[0].tehtavanimike_koodi, '39407')
        self.assertEqual(taydennyskoulutus_tyontekija_qs[1].tehtavanimike_koodi, '64212')

    def test_taydennyskoulutus_update_tyontekijat_add_incorrect(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')

        # Delete TaydennyskoulutusTyontekija so that we can add it again
        TaydennyskoulutusTyontekija.objects.get(tyontekija=tyontekija_1_obj,
                                                taydennyskoulutus__tunniste='testing-taydennyskoulutus1',
                                                tehtavanimike_koodi='64212').delete()

        # Duplicate
        taydennyskoulutus_patch_1 = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'},
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_1 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_1), content_type='application/json')
        assert_status_code(resp_patch_1, status.HTTP_400_BAD_REQUEST)

        # Invalid tehtavanimike_koodi
        taydennyskoulutus_patch_2 = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': 'test', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_2 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_2), content_type='application/json')
        assert_status_code(resp_patch_2, status.HTTP_400_BAD_REQUEST)

        # Tyontekija doesn't have tehtavanimike_koodi
        taydennyskoulutus_patch_3 = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_3 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_3), content_type='application/json')
        assert_status_code(resp_patch_3, status.HTTP_400_BAD_REQUEST)

        # Already exists
        taydennyskoulutus_patch_4 = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_4 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_4), content_type='application/json')
        assert_status_code(resp_patch_4, status.HTTP_400_BAD_REQUEST)

    def test_taydennyskoulutus_update_tyontekijat_remove_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_4_obj = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        tyontekijat_count_original = taydennyskoulutus_qs.first().taydennyskoulutukset_tyontekijat.count()

        taydennyskoulutus_put = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        }
        resp_put = client.put(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                              json.dumps(taydennyskoulutus_put), content_type='application/json')
        assert_status_code(resp_put, status.HTTP_200_OK)
        self.assertEqual(tyontekijat_count_original - 1, len(json.loads(resp_put.content)['taydennyskoulutus_tyontekijat']))

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ]
        }
        resp_patch = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                  json.dumps(taydennyskoulutus_patch), content_type='application/json')
        assert_status_code(resp_patch, status.HTTP_200_OK)
        self.assertEqual(tyontekijat_count_original - 2, len(json.loads(resp_patch.content)['taydennyskoulutus_tyontekijat']))

    def test_taydennyskoulutus_update_tyontekijat_remove_incorrect(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_4_obj = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        # Delete TaydennyskoulutusTyontekija for tyontekija_1
        TaydennyskoulutusTyontekija.objects.get(tyontekija=tyontekija_1_obj,
                                                taydennyskoulutus__tunniste='testing-taydennyskoulutus1',
                                                tehtavanimike_koodi='64212').delete()

        # Tyontekija doesn't have this taydennyskoulutus
        taydennyskoulutus_patch_1 = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_1 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_1), content_type='application/json')
        assert_status_code(resp_patch_1, status.HTTP_400_BAD_REQUEST)

        # Removing all tyontekijat
        taydennyskoulutus_patch_2 = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'},
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ]
        }
        resp_patch_2 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                    json.dumps(taydennyskoulutus_patch_2), content_type='application/json')
        assert_status_code(resp_patch_2, status.HTTP_400_BAD_REQUEST)

    def test_taydennyskoulutus_update_remove_all(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_obj = Taydennyskoulutus.objects.get(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus2')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_2_obj = Tyontekija.objects.get(tunniste='testing-tyontekija2')

        # Taydennyskoulutus does not have other tyontekijat
        taydennyskoulutus_patch_1 = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_2_obj.id}/'}
            ]
        }
        resp_patch_1 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_obj.id}/',
                                    json.dumps(taydennyskoulutus_patch_1), content_type='application/json')
        assert_status_code(resp_patch_1, status.HTTP_400_BAD_REQUEST)

        # Other tyontekija added in same request
        taydennyskoulutus_patch_2 = {
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_2_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '39407', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch_2 = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_obj.id}/',
                                    json.dumps(taydennyskoulutus_patch_2), content_type='application/json')
        assert_status_code(resp_patch_2, status.HTTP_200_OK)

    def test_taydennyskoulutus_update_tyontekijat_add_and_remove_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        taydennyskoulutus_qs = Taydennyskoulutus.objects.filter(lahdejarjestelma=1, tunniste='testing-taydennyskoulutus1')
        tyontekija_1_obj = Tyontekija.objects.get(tunniste='testing-tyontekija1')
        tyontekija_4_obj = Tyontekija.objects.get(tunniste='testing-tyontekija4')

        # Delete TaydennyskoulutusTyontekija so that we can add it again
        TaydennyskoulutusTyontekija.objects.get(tyontekija=tyontekija_4_obj,
                                                taydennyskoulutus__tunniste='testing-taydennyskoulutus1',
                                                tehtavanimike_koodi='77826').delete()

        taydennyskoulutus_patch = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tehtavanimike_koodi': '77826', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_4_obj.id}/'}
            ],
            'taydennyskoulutus_tyontekijat_remove': [
                {'tehtavanimike_koodi': '64212', 'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_1_obj.id}/'}
            ]
        }
        resp_patch = client.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_qs.first().id}/',
                                  json.dumps(taydennyskoulutus_patch), content_type='application/json')
        assert_status_code(resp_patch, status.HTTP_200_OK)
        self.assertEqual(taydennyskoulutus_qs.first().taydennyskoulutukset_tyontekijat.count(), 2)
        self.assertEqual(taydennyskoulutus_qs.first()
                         .taydennyskoulutukset_tyontekijat.filter(tehtavanimike_koodi__in=['39407', '77826']).count(), 2)

    def test_taydennyskoulutus_delete_correct(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()
        taydennyskoulutus_obj = Taydennyskoulutus.objects.get(tunniste='testing-taydennyskoulutus1')
        resp_delete = client.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_obj.id}/')
        assert_status_code(resp_delete, status.HTTP_204_NO_CONTENT)

    def test_taydennyskoulutus_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-taydennyskoulutus1'

        taydennyskoulutus = Taydennyskoulutus.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        client = SetUpTestClient('credadmin').client()
        taydennyskoulutus_url = f'/api/henkilosto/v1/taydennyskoulutukset/{lahdejarjestelma}:{tunniste}/'
        resp_taydennyskoulutus_get = client.get(taydennyskoulutus_url)
        assert_status_code(resp_taydennyskoulutus_get, status.HTTP_200_OK)
        self.assertEqual(taydennyskoulutus.id, json.loads(resp_taydennyskoulutus_get.content)['id'])

        resp_taydennyskoulutus_get_404 = client.get('/api/henkilosto/v1/taydennyskoulutukset/5:no/')
        assert_status_code(resp_taydennyskoulutus_get_404, status.HTTP_404_NOT_FOUND)

        taydennyskoulutus_put = {
            'taydennyskoulutus_tyontekijat': [
                {
                    'lahdejarjestelma': '1',
                    'tunniste': 'testing-tyontekija1',
                    'tehtavanimike_koodi': '39407'
                }
            ],
            'nimi': 'Testikoulutus',
            'suoritus_pvm': '2020-09-01',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-taydennyskoulutus1'
        }
        resp_taydennyskoulutus_put = client.put(taydennyskoulutus_url, json.dumps(taydennyskoulutus_put),
                                                content_type='application/json')
        assert_status_code(resp_taydennyskoulutus_put, status.HTTP_200_OK)

        taydennyskoulutus_patch = {
            'suoritus_pvm': '2020-11-01',
            'koulutuspaivia': '3.5'
        }
        resp_taydennyskoulutus_patch = client.patch(taydennyskoulutus_url, taydennyskoulutus_patch)
        assert_status_code(resp_taydennyskoulutus_patch, status.HTTP_200_OK)

        resp_taydennyskoulutus_delete = client.delete(taydennyskoulutus_url)
        assert_status_code(resp_taydennyskoulutus_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Taydennyskoulutus.objects.filter(id=taydennyskoulutus.id).exists())

    def test_taydennyskoulutus_invalid_tyontekija_permission_create(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()

        tyontekija = Tyontekija.objects.get(tunniste='testing-tyontekija-without-permission')

        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/henkilosto/v1/taydennyskoulutukset/', json.dumps(taydennyskoulutus), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        error_path = ['taydennyskoulutus_tyontekijat', '0']
        expected_error_code = 'TK001'
        expected_error_msg = 'Tyontekija not specified. Use (tyontekija), (henkilo_oid, vakajarjestaja_oid) or (lahdejarjestelma, tunniste).'
        assert_validation_error(resp, error_path, expected_error_code, expected_error_msg)

    def test_taydennyskoulutus_tyontekija_list(self):
        client = SetUpTestClient('taydennyskoulutus_tallentaja').client()
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        correct_taydennyskoulutus_count = (Taydennyskoulutus.objects
                                           .filter(taydennyskoulutukset_tyontekijat__tyontekija__vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                                           .distinct()
                                           .count()
                                           )
        correct_jarjestaja_tyontekija_count = (Tyontekija.objects
                                               .filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                                               .count()
                                               )
        taydennyskoulutus_list_resp = client.get('/api/henkilosto/v1/taydennyskoulutukset/')
        assert_status_code(taydennyskoulutus_list_resp, status.HTTP_200_OK)
        taydennyskoulutus_content = json.loads(taydennyskoulutus_list_resp.content)
        # Only taydennyskoulutukset user has permission to are returned
        self.assertEqual(taydennyskoulutus_content.get('count'), correct_taydennyskoulutus_count)
        self.assertEqual(len(taydennyskoulutus_content.get('results')), correct_taydennyskoulutus_count)
        tyontekija_list_resp = client.get('/api/henkilosto/v1/taydennyskoulutukset/tyontekija-list/')
        assert_status_code(tyontekija_list_resp, status.HTTP_200_OK)
        tyontekija_content = json.loads(tyontekija_list_resp.content)

        # Only taydennyskoulutustyontekijat user has permission to are returned
        self.assertEqual(tyontekija_content.get('count'), correct_jarjestaja_tyontekija_count)
        self.assertEqual(len(tyontekija_content.get('results')), correct_jarjestaja_tyontekija_count)

    def test_taydennyskoulutus_tyontekija_list_filter(self):
        client = SetUpTestClient('credadmin').client()
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        correct_tyontekija_count = Tyontekija.objects.all().count()
        tyontekija_list_resp = client.get('/api/henkilosto/v1/taydennyskoulutukset/tyontekija-list/')
        assert_status_code(tyontekija_list_resp, status.HTTP_200_OK)
        tyontekija_content = json.loads(tyontekija_list_resp.content)
        self.assertEqual(tyontekija_content.get('count'), correct_tyontekija_count)
        self.assertEqual(len(tyontekija_content.get('results')), correct_tyontekija_count)

        correct_jarjestaja_tyontekija_count = (Tyontekija.objects
                                               .filter(vakajarjestaja__organisaatio_oid=vakajarjestaja_oid)
                                               .count()
                                               )
        tyontekija_list_filtered_resp = client.get('/api/henkilosto/v1/taydennyskoulutukset/tyontekija-list/?vakajarjestaja_oid={}'
                                                   .format(vakajarjestaja_oid))
        assert_status_code(tyontekija_list_filtered_resp, status.HTTP_200_OK)
        tyontekija_filtered_content = json.loads(tyontekija_list_filtered_resp.content)
        self.assertEqual(tyontekija_filtered_content.get('count'), correct_jarjestaja_tyontekija_count)
        self.assertEqual(len(tyontekija_filtered_content.get('results')), correct_jarjestaja_tyontekija_count)

    def test_taydennyskoulutus_toimipaikka_permissions(self):
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        tyontekija = Tyontekija.objects.filter(vakajarjestaja=vakajarjestaja).first()

        client_toimipaikka = SetUpTestClient('taydennyskoulutus_toimipaikka_tallentaja').client()
        client_jarjestaja = SetUpTestClient('henkilosto_tallentaja_93957375488').client()

        taydennyskoulutus_1 = {
            'taydennyskoulutus_tyontekijat': [
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '43525'}
            ],
            'nimi': 'Testikoulutus 1',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }
        resp_1 = client_toimipaikka.post('/api/henkilosto/v1/taydennyskoulutukset/',
                                         json.dumps(taydennyskoulutus_1),
                                         content_type='application/json')
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        taydennyskoulutus_1_id = json.loads(resp_1.content).get('id')

        taydennyskoulutus_1_patch = {
            'taydennyskoulutus_tyontekijat_add': [
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '77826'}
            ]
        }
        resp_patch_1 = client_toimipaikka.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_1_id}/',
                                                json.dumps(taydennyskoulutus_1_patch),
                                                content_type='application/json')
        assert_status_code(resp_patch_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_patch_1, ['taydennyskoulutus_tyontekijat_add', '0'], 'TK001',
                                'Tyontekija not specified. Use (tyontekija), (henkilo_oid, vakajarjestaja_oid) or (lahdejarjestelma, tunniste).')
        resp_patch_2 = client_jarjestaja.patch(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_1_id}/',
                                               json.dumps(taydennyskoulutus_1_patch),
                                               content_type='application/json')
        assert_status_code(resp_patch_2, status.HTTP_200_OK)

        resp_delete_1 = client_toimipaikka.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_1_id}/')
        assert_status_code(resp_delete_1, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_delete_1, 'errors', 'TK014', 'Insufficient permissions to Taydennyskoulutus related Tyontekija objects.')

        resp_delete_2 = client_jarjestaja.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_1_id}/')
        assert_status_code(resp_delete_2, status.HTTP_204_NO_CONTENT)

        taydennyskoulutus_2 = {
            'taydennyskoulutus_tyontekijat': [
                {'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/', 'tehtavanimike_koodi': '43525'}
            ],
            'nimi': 'Testikoulutus 2',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }
        resp_2 = client_toimipaikka.post('/api/henkilosto/v1/taydennyskoulutukset/',
                                         json.dumps(taydennyskoulutus_2),
                                         content_type='application/json')
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        taydennyskoulutus_2_id = json.loads(resp_2.content).get('id')

        resp_delete_3 = client_toimipaikka.delete(f'/api/henkilosto/v1/taydennyskoulutukset/{taydennyskoulutus_2_id}/')
        assert_status_code(resp_delete_3, status.HTTP_204_NO_CONTENT)

    def test_toimipaikka_tyontekija_create_all(self):
        client_tyontekija_tallentaja = SetUpTestClient('tyontekija_toimipaikka_tallentaja').client()
        client_tyontekija_katselija = SetUpTestClient('tyontekija_toimipaikka_katselija').client()

        henkilo_url = '/api/v1/henkilot/1/'
        post_henkilo_to_get_permissions(client_tyontekija_tallentaja, henkilo_id=1)

        vakajarjestaja_url = '/api/v1/vakajarjestajat/2/'
        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        # Tyontekija
        tyontekija = {
            'henkilo': henkilo_url,
            'vakajarjestaja': vakajarjestaja_url,
            'lahdejarjestelma': '1',
            'toimipaikka_oid': toimipaikka_oid,
        }
        tyontekija_resp = self._assert_create_and_list(client_tyontekija_katselija, client_tyontekija_tallentaja,
                                                       tyontekija, '/api/henkilosto/v1/tyontekijat/', expected_count=2)
        tyontekija_url = json.loads(tyontekija_resp.content)['url']
        tyontekija_id = json.loads(tyontekija_resp.content)['id']

        # Tutkinto
        tutkinto_koodi = '002'
        tutkinto = {
            'henkilo': henkilo_url,
            'vakajarjestaja': vakajarjestaja_url,
            'tutkinto_koodi': tutkinto_koodi,
            'toimipaikka_oid': toimipaikka_oid
        }
        self._assert_create_and_list(client_tyontekija_katselija, client_tyontekija_tallentaja, tutkinto, '/api/henkilosto/v1/tutkinnot/')

        # Palvelussuhde
        palvelussuhde = {
            'tyontekija': tyontekija_url,
            'tyosuhde_koodi': '1',
            'tyoaika_koodi': '1',
            'tutkinto_koodi': tutkinto_koodi,
            'tyoaika_viikossa': '38.73',
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2022-03-02',
            'lahdejarjestelma': '1',
            'toimipaikka_oid': toimipaikka_oid,
        }
        palvelussuhde_resp = self._assert_create_and_list(client_tyontekija_katselija, client_tyontekija_tallentaja,
                                                          palvelussuhde, '/api/henkilosto/v1/palvelussuhteet/', expected_count=2)
        palvelussuhde_url = json.loads(palvelussuhde_resp.content)['url']

        # Pidempipoissaolo
        # Toimipaikka tallentaja can't get access to Pidempipoissaolo until tyoskentelypaikka has been created so this will fail
        pidempipoissaolo = {
            'palvelussuhde': palvelussuhde_url,
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1'
        }
        create_response = client_tyontekija_tallentaja.post('/api/henkilosto/v1/pidemmatpoissaolot/', json.dumps(pidempipoissaolo), content_type='application/json')
        assert_status_code(create_response, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(create_response, 'tyoskentelypaikka', 'PP002', 'No matching Tyoskentelypaikka exists.')

        # Tyoskentelypaikka
        tyoskentelypaikka = {
            'palvelussuhde': palvelussuhde_url,
            'alkamis_pvm': '2020-03-01',
            'paattymis_pvm': '2022-03-02',
            'tehtavanimike_koodi': '39407',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': True,
            'lahdejarjestelma': '1',
        }

        # Toimipaikka tallentaja is not allowed to create kiertava tyontekija
        tyoskentelypaikka_resp = client_tyontekija_tallentaja.post('/api/henkilosto/v1/tyoskentelypaikat/',
                                                                   json.dumps(tyoskentelypaikka),
                                                                   content_type='application/json')
        assert_status_code(tyoskentelypaikka_resp, status.HTTP_403_FORBIDDEN)

        tyoskentelypaikka.update({
            'kiertava_tyontekija_kytkin': False,
            'toimipaikka_oid': toimipaikka_oid,
        })
        self._assert_create_and_list(client_tyontekija_katselija, client_tyontekija_tallentaja, tyoskentelypaikka,
                                     '/api/henkilosto/v1/tyoskentelypaikat/', expected_count=2)

        # Pidempipoissaolo
        # After adding Tyoskentelypaikka toimipaikka_tallentaja can add pidempipoissaolo
        pidempipoissaolo = {
            'palvelussuhde': palvelussuhde_url,
            'alkamis_pvm': '2021-06-01',
            'paattymis_pvm': '2021-09-01',
            'lahdejarjestelma': '1'
        }
        self._assert_create_and_list(client_tyontekija_katselija, client_tyontekija_tallentaja, pidempipoissaolo, '/api/henkilosto/v1/pidemmatpoissaolot/')

        # Taydennyskoulutus
        client_koulutus_katselija = SetUpTestClient('taydennyskoulutus_toimipaikka_katselija').client()
        client_koulutus_tallentaja = SetUpTestClient('taydennyskoulutus_toimipaikka_tallentaja').client()
        taydennyskoulutus_list_resp = client_koulutus_tallentaja.get('/api/henkilosto/v1/taydennyskoulutukset/')
        taydennyskoulutus_count_before = json.loads(taydennyskoulutus_list_resp.content).get('count')
        taydennyskoulutus_list_resp = client_koulutus_katselija.get('/api/henkilosto/v1/taydennyskoulutukset/')
        self.assertEqual(json.loads(taydennyskoulutus_list_resp.content).get('count'), taydennyskoulutus_count_before)
        taydennyskoulutus = {
            'taydennyskoulutus_tyontekijat': [{'tyontekija': f'/api/henkilosto/v1/tyontekijat/{tyontekija_id}/', 'tehtavanimike_koodi': '39407'}],
            'nimi': 'Ensiapukoulutus',
            'suoritus_pvm': '2020-09-14',
            'koulutuspaivia': '1.5',
            'lahdejarjestelma': '1',
        }
        self._assert_create_and_list(client_koulutus_katselija,
                                     client_koulutus_tallentaja,
                                     taydennyskoulutus,
                                     '/api/henkilosto/v1/taydennyskoulutukset/',
                                     taydennyskoulutus_count_before + 1)

    def _assert_create_and_list(self, client_katselija, client_tallentaja, create_dict, api_url, expected_count=1):
        """
        Asserts katselija user can't create and both users get same list response after create. Assumes create and
        list url is the same.
        :param client_katselija: view only user
        :param client_tallentaja: crud user
        :param create_dict: dict of create dto
        :param api_url: url to create and list api
        :param expected_count: expected list count to assert
        :return: create response
        """
        create_response_fail = client_katselija.post(api_url, json.dumps(create_dict), content_type='application/json')
        assert_status_code(create_response_fail, status.HTTP_403_FORBIDDEN)
        create_response = client_tallentaja.post(api_url, json.dumps(create_dict), content_type='application/json')
        assert_status_code(create_response, status.HTTP_201_CREATED)

        list_response_tallentaja = client_tallentaja.get(api_url)
        self.assertEqual(json.loads(list_response_tallentaja.content).get('count'), expected_count)
        list_response_katselija = client_katselija.get(api_url)
        self.assertEqual(json.loads(list_response_katselija.content).get('count'), expected_count)

        return create_response

    def test_ui_tyontekija_kooste(self):
        tyontekija = Tyontekija.objects.filter(tunniste='testing-tyontekija2').first()

        client_tyontekija = SetUpTestClient('tyontekija_tallentaja').client()
        resp_tyontekija = client_tyontekija.get(f'/api/henkilosto/v1/tyontekijat/{tyontekija.id}/kooste/')
        resp_content_tyontekija = json.loads(resp_tyontekija.content)
        self.assertEqual(len(resp_content_tyontekija['palvelussuhteet']), tyontekija.palvelussuhteet.count())
        # No access to taydennyskoulutukset
        self.assertEqual(len(resp_content_tyontekija['taydennyskoulutukset']), 0)

    def test_tyontekija_vakajarjestaja_permission_group(self):
        # If user has vaka permissions in one organization and henkilosto permissions in another organization,
        # user should not be able to create a Tyontekija in the organization with only vaka permissions
        vakajarjestaja_vaka = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        vakajarjestaja_henkilosto = VakaJarjestaja.objects.get(organisaatio_oid='1.2.246.562.10.93957375488')
        user = User.objects.get(username='tester2')

        # Give user tyontekija permissions in another organization
        permission_group = Group.objects.get(name='HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.93957375488')
        user.groups.add(permission_group)

        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)

        tyontekija_invalid_1 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja_oid': vakajarjestaja_vaka.organisaatio_oid,
            'lahdejarjestelma': '1'
        }

        resp_invalid_1 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_invalid_1)
        assert_status_code(resp_invalid_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_invalid_1, 'vakajarjestaja_oid', 'RF003', 'Could not find matching object.')

        tyontekija_invalid_2 = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja_vaka.id}/',
            'lahdejarjestelma': '1'
        }

        resp_invalid_2 = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_invalid_2)
        assert_status_code(resp_invalid_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_invalid_2, 'vakajarjestaja', 'GE008', 'Invalid hyperlink, object does not exist.')

        tyontekija_valid = {
            'henkilo': '/api/v1/henkilot/1/',
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja_henkilosto.id}/',
            'lahdejarjestelma': '1'
        }
        resp_valid = client.post('/api/henkilosto/v1/tyontekijat/', tyontekija_valid)
        assert_status_code(resp_valid, status.HTTP_201_CREATED)

    def test_tyoskentelypaikka_toimipaikka_permission_group(self):
        toimipaikka_valid = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')
        toimipaikka_invalid = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548811')
        palvelussuhde = Palvelussuhde.objects.get(tunniste='testing-palvelussuhde5')
        user = User.objects.get(username='tyontekija_toimipaikka_tallentaja')

        # Give user VakaJarjestaja level vaka permissions in same organization
        permission_group = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.93957375488')
        user.groups.add(permission_group)

        client = SetUpTestClient('tyontekija_toimipaikka_tallentaja').client()

        tyoskentelypaikka_invalid_1 = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_invalid.id}/',
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-09-02',
            'tehtavanimike_koodi': '64212',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1'
        }

        resp_invalid_1 = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka_invalid_1)
        assert_status_code(resp_invalid_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_invalid_1, 'toimipaikka', 'GE008', 'Invalid hyperlink, object does not exist.')

        tyoskentelypaikka_invalid_2 = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'toimipaikka_oid': toimipaikka_invalid.organisaatio_oid,
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-09-02',
            'tehtavanimike_koodi': '64212',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1'
        }

        resp_invalid_2 = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka_invalid_2)
        assert_status_code(resp_invalid_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_invalid_2, 'toimipaikka_oid', 'RF003', 'Could not find matching object.')

        tyoskentelypaikka_valid = {
            'palvelussuhde': f'/api/henkilosto/v1/palvelussuhteet/{palvelussuhde.id}/',
            'toimipaikka_oid': toimipaikka_valid.organisaatio_oid,
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': '2021-09-02',
            'tehtavanimike_koodi': '64212',
            'kelpoisuus_kytkin': True,
            'kiertava_tyontekija_kytkin': False,
            'lahdejarjestelma': '1'
        }

        resp_valid = client.post('/api/henkilosto/v1/tyoskentelypaikat/', tyoskentelypaikka_valid)
        assert_status_code(resp_valid, status.HTTP_201_CREATED)
