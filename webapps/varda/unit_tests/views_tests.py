import json
from datetime import datetime
from unittest import mock
from unittest.mock import patch

import responses
from django.conf import settings

from django.contrib.auth.models import Group, User
from django.test import TestCase
from guardian.core import ObjectPermissionChecker
from rest_framework import status
from rest_framework.exceptions import ValidationError as ValidationErrorRest
from rest_framework.test import APIClient

from varda.enums.organisaatiotyyppi import Organisaatiotyyppi
from varda.misc import hash_string, encrypt_string
from varda.models import (Organisaatio, Toimipaikka, PaosOikeus, Huoltaja, Huoltajuussuhde, Henkilo,
                          Lapsi, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Maksutieto, ToiminnallinenPainotus,
                          KieliPainotus, PaosToiminta, Z2_Code, MaksutietoHuoltajuussuhde, Z4_CasKayttoOikeudet)
from varda.permission_groups import assign_object_level_permissions
from varda.unit_tests.test_utils import (assert_status_code, SetUpTestClient, assert_validation_error, mock_admin_user,
                                         post_henkilo_to_get_permissions, mock_date_decorator_factory)
from varda.viewsets import HenkiloViewSet, LapsiViewSet


# Well known test organizations (name corresponds to oid)
test_org_34683023489 = '1.2.246.562.10.34683023489'  # Tester2 organisaatio
test_org_93957375488 = '1.2.246.562.10.93957375488'  # Tester organisaatio
test_org_93957375486 = '1.2.246.562.10.93957375486'  # varda-testi organisaatio
test_org_93957375484 = '1.2.246.562.10.93957375484'  # Frontti organisaatio


def mock_check_if_toimipaikka_exists_by_name(vakajarjestaja_id, toimipaikka_name):
    return False, []


def mock_create_organisaatio(organisaatio_json):
    return {
        'toimipaikka_created': True,
        'organisaatio_oid': '1.2.246.562.10.01234567891'
    }


class VardaViewsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_index(self):
        resp = self.client.get('/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_authentication_page(self):
        resp = self.client.get('/api-auth/login/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_release_notes(self):
        resp = self.client.get('/varda/release-notes/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_swagger_not_authenticated(self):
        resp = self.client.get('/varda/swagger/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_swagger_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/varda/swagger/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_varda_index(self):
        resp = self.client.get('/varda/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_root_not_authenticated(self):
        resp = self.client.get('/api/v1/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_root_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/')
        api_root = {
            'vakajarjestajat': 'http://testserver/api/v1/vakajarjestajat/',
            'toimipaikat': 'http://testserver/api/v1/toimipaikat/',
            'toiminnallisetpainotukset': 'http://testserver/api/v1/toiminnallisetpainotukset/',
            'kielipainotukset': 'http://testserver/api/v1/kielipainotukset/',
            'hae-henkilo': 'http://testserver/api/v1/hae-henkilo/',
            'henkilot': 'http://testserver/api/v1/henkilot/',
            'lapset': 'http://testserver/api/v1/lapset/',
            'maksutiedot': 'http://testserver/api/v1/maksutiedot/',
            'varhaiskasvatuspaatokset': 'http://testserver/api/v1/varhaiskasvatuspaatokset/',
            'varhaiskasvatussuhteet': 'http://testserver/api/v1/varhaiskasvatussuhteet/',
            'paos-toiminnat': 'http://testserver/api/v1/paos-toiminnat/',
            'paos-oikeudet': 'http://testserver/api/v1/paos-oikeudet/'
        }
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), api_root)

    def test_api_schema(self):
        resp = self.client.get('/api/v1/schema/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_wrong_address(self):
        resp = self.client.get('/api/v1/wrong_address/')
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)

    def test_api_users_admin(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/users/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_users_authenticated_but_not_admin(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/admin/users/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_users_not_authenticated(self):
        resp = self.client.get('/api/admin/users/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_get_user_data_anonymous(self):
        resp = self.client.get('/api/user/data/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

    def test_api_get_user_data_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/user/data/')
        result_json = {'asiointikieli_koodi': 'sv',
                       'email': '',
                       'henkilo_oid': '1.2.345678910',
                       'kayttajatyyppi': 'VIRKAILIJA',
                       'kayttooikeudet': [
                           {
                               'organisaatio': '1.2.246.562.10.9395737548810',
                               'kayttooikeus': 'VARDA-TALLENTAJA'
                           },
                           {
                               'organisaatio': '1.2.246.562.10.9395737548811',
                               'kayttooikeus': 'VARDA-KATSELIJA'
                           },
                           {
                               'organisaatio': '1.2.246.562.10.9395737548810',
                               'kayttooikeus': 'HUOLTAJATIETO_TALLENNUS'
                           },
                           {
                               'organisaatio': '1.2.246.562.10.34683023489',
                               'kayttooikeus': 'HUOLTAJATIETO_TALLENNUS'
                           }
                       ],
                       'username': 'tester'
                       }
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertCountEqual(json.loads(resp.content), result_json)

    def test_api_get_token_anonymous(self):
        resp = self.client.get('/api/user/apikey/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE005', 'Authentication credentials were not provided.')

    def test_api_get_token_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/user/apikey/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_refresh_token_anonymous(self):
        data = {
            'refresh_token': True
        }
        resp = self.client.post('/api/user/apikey/', data)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_refresh_token_authenticated(self):
        user = User.objects.get(username='tester')
        data = {
            'refresh_token': True
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/user/apikey/')
        assert_status_code(resp, status.HTTP_200_OK)
        token_1 = json.loads(resp.content)['token']

        token_client = APIClient()
        resp = token_client.post('/api/user/apikey/', data, **{'HTTP_AUTHORIZATION': f'Token {token_1}'})
        assert_status_code(resp, status.HTTP_201_CREATED)
        token_2 = json.loads(resp.content)['token']
        self.assertNotEqual(token_1, token_2)
        self.assertEqual(user.auth_token_set.all().count(), 1)

    def test_api_refresh_token_multiple(self):
        user = User.objects.get(username='tester')
        client = SetUpTestClient('tester').client()

        token_limit_per_user = settings.REST_KNOX['TOKEN_LIMIT_PER_USER']
        token_set = set()
        for i in range(token_limit_per_user):
            resp = client.get('/api/user/apikey/')
            assert_status_code(resp, status.HTTP_200_OK)
            token_set.add(json.loads(resp.content)['token'])

        self.assertEqual(len(token_set), token_limit_per_user)
        self.assertEqual(user.auth_token_set.all().count(), token_limit_per_user)

        resp = client.get('/api/user/apikey/')
        assert_status_code(resp, status.HTTP_200_OK)
        token_set.add(json.loads(resp.content)['token'])
        self.assertEqual(len(token_set), token_limit_per_user + 1)
        self.assertEqual(user.auth_token_set.all().count(), token_limit_per_user)

        assert_status_code(client.delete('/api/user/apikey/delete-all/'), status.HTTP_204_NO_CONTENT)
        self.assertEqual(user.auth_token_set.all().count(), 0)

    def test_api_refresh_token_authenticated_faulty_input(self):
        data = {
            'refresh_token': False
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/user/apikey/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI001', 'Token was not refreshed.')

    def test_api_refresh_token_authenticated_faulty_input_2(self):
        data = {}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/user/apikey/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI001', 'Token was not refreshed.')

    def test_api_vakajarjestajat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/vakajarjestajat/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_toimipaikat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_toimipaikat_with_empty_oid(self):
        """
        Result for this should always be at least one (1) so that EMPTY-string option is tested.
        """
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/?organisaatio_oid=EMPTY')
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_api_toimipaikat_permissions_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/')
        self.assertEqual(json.loads(resp.content)['count'], 7)

    def test_api_toimipaikat_permissions_2(self):
        """
        Keep this different than the test_api_toimipaikat_permissions_1, so that the
        permissions can be tested (different amount of objects visible to different users).
        """
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/')
        self.assertEqual(json.loads(resp.content)['count'], 4)

    def test_api_toimipaikat_permissions_3(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/1/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_toimipaikat_permissions_4(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/1/')
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)

    def test_api_toimipaikat_filtering_successful(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/?kayntiosoite=keil')  # katuosoite_exact == Keilaniemi
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_toimipaikat_filtering_failing(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/?kayntiosoite=keis')
        self.assertEqual(json.loads(resp.content)['count'], 0)

    def test_api_toimipaikat_filtering_arrayfield_successful(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/?jarjestamismuoto_koodi=jm01')
        self.assertEqual(json.loads(resp.content)['count'], 3)

    def test_api_toiminnallisetpainotukset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toiminnallisetpainotukset/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_toiminnallisetpainotukset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toiminnallisetpainotukset/?toimintapainotus_koodi=tp01&muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_api_kielipainotukset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/kielipainotukset/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_kielipainotukset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/kielipainotukset/?kielipainotus_koodi=EN&muutos_pvm=2017-02-10')
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_api_varhaiskasvatuspaatos_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/?jarjestamismuoto_koodi=jm04')
        self.assertEqual(json.loads(resp.content)['count'], 3)

    def test_post_vakajarjestaja_with_invalid_yritysmuoto(self):
        with self.assertRaises(ValidationErrorRest) as validation_error:
            organisaatio = Organisaatio.objects.create(
                nimi='Tester200 organisaatio',
                y_tunnus='8500570-7',
                organisaatio_oid='1.2.246.562.10.34683023481',
                kunta_koodi='091',
                sahkopostiosoite='organization@domain.com',
                kayntiosoite='Testerkatu 2',
                kayntiosoite_postinumero='00001',
                kayntiosoite_postitoimipaikka='Testilä',
                postiosoite='Testerkatu 2',
                postitoimipaikka='Testilä',
                postinumero='00001',
                puhelinnumero='+358101234567',
                yritysmuoto='1000',
                integraatio_organisaatio=[],
                organisaatiotyyppi=[Organisaatiotyyppi.VAKAJARJESTAJA.value],
                alkamis_pvm='2017-02-03',
                paattymis_pvm=None
            )
            organisaatio.full_clean()
            organisaatio.save()
        self.assertIn('KO003', str(validation_error.exception))

    def test_api_push_non_unique_henkilo_etunimi_correct_sukunimi_wrong(self):
        henkilo = {
            'henkilotunnus': '130266-915J',
            'etunimet': 'Lasse Eemeli',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Palomäki'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'turvakielto': False,
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_correct_sukunimi_wrong_small_letters(self):
        henkilo = {
            'henkilotunnus': '130266-915J',
            'etunimet': 'lasse eemeli',
            'kutsumanimi': 'lasse',
            'sukunimi': 'Palomäki'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'turvakielto': False,
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_correct(self):
        henkilo = {
            'henkilotunnus': '130266-915J',
            'etunimet': 'Ville',
            'kutsumanimi': 'Ville',
            'sukunimi': 'Manner'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'turvakielto': False,
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_correct_small_letters(self):
        henkilo = {
            'henkilotunnus': '130266-915J',
            'etunimet': 'Ville',
            'kutsumanimi': 'Ville',
            'sukunimi': 'manner'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'turvakielto': False,
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_wrong(self):
        henkilo = {
            'henkilotunnus': '130266-915J',
            'etunimet': 'Hanna Karin',
            'kutsumanimi': 'Karin',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'HE001', 'Person data does not match with the entered data.')

    def test_api_push_incorrect_varhaiskasvatuspaatos_date_sequence(self):
        vaka_paatos = {
            'lapsi': '/api/v1/lapset/3/',
            'vuorohoito_kytkin': False,
            'tuntimaara_viikossa': 33,
            'paivittainen_vaka_kytkin': True,
            'kokopaivainen_vaka_kytkin': True,
            'jarjestamismuoto_koodi': 'jm01',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2020-04-06',
            'alkamis_pvm': '2009-02-02',
            'paattymis_pvm': '2010-01-05',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vaka_paatos)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'hakemus_pvm', 'VP001', 'hakemus_pvm must be before or equal to alkamis_pvm.')

    def test_api_push_incorrect_varhaiskasvatussuhde_date_sequence(self):
        vaka_suhde = {
            'varhaiskasvatuspaatos': '/api/v1/varhaiskasvatuspaatokset/1/',
            'toimipaikka': '/api/v1/toimipaikat/1/',
            'alkamis_pvm': '2018-02-02',
            'paattymis_pvm': '2018-01-02',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vaka_suhde)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.')

    def test_api_push_incorrect_henkilo(self):  # wrong henkilotunnus-beginning
        henkilo = {
            'henkilotunnus': '123465-123P',
            'etunimet': 'Hanna Karin',
            'kutsumanimi': 'Karin',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilotunnus', 'HE007', 'Incorrect henkilotunnus date.')

    def test_api_push_incorrect_henkilo_2(self):  # wrong henkilotunnus-end; should end with P
        henkilo = {
            'henkilotunnus': '120465-123B',
            'etunimet': 'Hanna Karin',
            'kutsumanimi': 'Hanna',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilotunnus', 'HE008', 'ID number or control character is incorrect.')

    def test_api_push_incorrect_henkilo_3(self):  # empty kutsumanimi
        henkilo = {
            'henkilotunnus': '030187-851M',
            'etunimet': 'Hanna Karin',
            'kutsumanimi': '',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kutsumanimi', 'GE003', 'This field may not be blank.')

    def test_api_push_incorrect_henkilo_4(self):  # missing kutsumanimi
        henkilo = {
            'henkilotunnus': '030187-851M',
            'etunimet': 'Hanna Karin',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kutsumanimi', 'GE001', 'This field is required.')

    def test_api_push_incorrect_henkilo_5(self):  # wrong kutsumanimi
        henkilo = {
            'henkilotunnus': '030187-851M',
            'etunimet': 'Hanna Karin',
            'kutsumanimi': 'HannaKarin',
            'sukunimi': 'Palomäki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kutsumanimi', 'HE011', 'kutsumanimi is not valid.')

    def test_api_push_henkilo_oid_etunimi_correct_sukunimi_wrong(self):
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'etunimet': 'Susanna Maria',
            'kutsumanimi': 'Susanna',
            'sukunimi': 'Palomäki'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/3/',
            'id': 3,
            'etunimet': 'Susanna',
            'kutsumanimi': 'Susanna',
            'sukunimi': 'Virtanen',
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'syntyma_pvm': '2016-05-12',
            'turvakielto': False,
            'lapsi': ['http://testserver/api/v1/lapset/2/'],
            'tyontekija': []
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_henkilo_oid_etunimi_wrong_sukunimi_correct(self):
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'etunimet': 'Elina',
            'kutsumanimi': 'Elina',
            'sukunimi': 'Virtanen'
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/3/',
            'id': 3,
            'etunimet': 'Susanna',
            'kutsumanimi': 'Susanna',
            'sukunimi': 'Virtanen',
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'syntyma_pvm': '2016-05-12',
            'turvakielto': False,
            'lapsi': ['http://testserver/api/v1/lapset/2/'],
            'tyontekija': []
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_henkilo_oid_etunimi_wrong_sukunimi_wrong(self):
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'etunimet': 'Marko',
            'kutsumanimi': 'Marko',
            'sukunimi': 'Anttila'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'HE001', 'Person data does not match with the entered data.')

    @responses.activate
    def test_api_push_henkilo_oid_not_in_oppijanumerorekisteri(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.246.562.24.47279942111',
                      status=status.HTTP_201_CREATED
                      )
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={'hetu': None, 'yksiloity': True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.47279942111',
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @responses.activate
    def test_api_push_henkilo_oid_not_yksiloity_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={'hetu': None, 'yksiloity': False},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.47279942111',
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilo_oid', 'HE002', 'Unfortunately this Henkilo cannot be added. Is the Henkilo yksiloity?')

    @responses.activate
    def test_api_push_henkilo_oid_has_yksiloimatonhenkilotunnus_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={'hetu': '1', 'yksiloityVTJ': False},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.47279942111',
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @responses.activate
    def test_api_push_henkilo_oid_has_yksiloityhenkilotunnus_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={'hetu': '1', 'yksiloityVTJ': True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.47279942111',
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @responses.activate
    def test_api_push_henkilo_oid_successful(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={'hetu': None, 'yksiloity': True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            'henkilo_oid': '1.2.246.562.24.47279942111',
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertIn('http://testserver/api/v1/henkilot/', json.loads(resp.content)['url'])

    def test_api_varhaiskasvatussuhteet(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatussuhteet/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_varhaiskasvatussuhteet_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatussuhteet/?muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 5)

    def test_api_lapset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_hae_henkilo_empty_data(self):
        data = {}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'HE004', 'Either henkilotunnus or henkilo_oid is needed, but not both.')

    def test_hae_henkilo_missing_keys(self):
        data = {'foo': 12}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'HE004', 'Either henkilotunnus or henkilo_oid is needed, but not both.')

    def test_hae_henkilo_faulty_inputs(self):
        data = {'henkilotunnus': 'string', 'henkilo_oid': 'string'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'HE004', 'Either henkilotunnus or henkilo_oid is needed, but not both.')

    def test_hae_henkilo_not_found_oid(self):
        data = {'henkilo_oid': '1.2.246.562.24.47279942111'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)
        assert_validation_error(resp, 'errors', 'MI015', 'Not found.')

    def test_hae_henkilo_not_found_henkilotunnus(self):
        data = {'henkilotunnus': '290381-213W'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)
        assert_validation_error(resp, 'errors', 'MI015', 'Not found.')

    def test_hae_henkilo_found_oid(self):
        data = {'henkilo_oid': '1.2.246.562.24.49084901392'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['url'], 'http://testserver/api/v1/henkilot/7/')

    def test_hae_henkilo_found_henkilotunnus(self):
        data = {'henkilotunnus': '010114A0013'}
        client = SetUpTestClient('tester5').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)['url'], 'http://testserver/api/v1/henkilot/2/')

    def test_hae_henkilo_anonymous(self):
        data = {'henkilotunnus': '020476-321F'}
        resp = self.client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_huoltajat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/admin/huoltajat/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_huoltajat_filtering(self):
        # TO-DO: fix filtering
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/huoltajat/?sukunimi=Virtane&kayntiosoite=Torikatu%2011&postitoimipaikka=Lappeenranta&kotikunta_koodi=034&muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 9)

    def test_api_varhaiskasvatuspaatokset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_api_varhaiskasvatuspaatokset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/?hakemus_pvm=2017-01-12')
        self.assertEqual(json.loads(resp.content)['count'], 4)

    def test_api_get_lapsi_json(self):
        lapsi_json = {
            'url': 'http://testserver/api/v1/lapset/1/?format=json',
            'id': 1,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/2/?format=json',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'oma_organisaatio': None,
            'oma_organisaatio_oid': None,
            'paos_kytkin': False,
            'paos_organisaatio': None,
            'paos_organisaatio_oid': None,
            'henkilo': 'http://testserver/api/v1/henkilot/2/?format=json',
            'henkilo_oid': '1.2.246.562.24.47279942650',
            'varhaiskasvatuspaatokset_top': [
                'http://testserver/api/v1/varhaiskasvatuspaatokset/1/?format=json'
            ],
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi1'
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/1/?format=json')
        content = json.loads(resp.content)
        content.pop('muutos_pvm', None)
        self.assertEqual(content, lapsi_json)

    def test_api_oid_related_field_lapsi_nulls_allowed_in_oids(self):
        client = SetUpTestClient('tester2').client()
        data = {
            'henkilo': '/api/v1/henkilot/7/',
            'oma_organisaatio_oid': None,
            'paos_organisaatio_oid': None,
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/lapset/', json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio_oid'], '1.2.246.562.10.34683023489')
        self.assertEqual(json.loads(resp.content)['paos_organisaatio_oid'], '1.2.246.562.10.93957375488')

    def test_api_oid_related_field_lapsi_nulls_allowed_in_urls(self):
        client = SetUpTestClient('tester2').client()
        data = {
            'henkilo': '/api/v1/henkilot/7/',
            'oma_organisaatio_oid': test_org_34683023489,
            'paos_organisaatio_oid': test_org_93957375488,
            'oma_organisaatio': None,
            'paos_organisaatio': None,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/lapset/', json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/1/')
        self.assertEqual(json.loads(resp.content)['paos_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/2/')

    def test_api_oid_related_field_lapsi_nulls_allowed_in_creation(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654324',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '240219A149T',
            'etunimet': 'Pentti Jr',
            'kutsumanimi': 'Pentti',
            'sukunimi': 'Kivimäki'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        henkilo_url = json.loads(resp.content)['url']
        vakajarjestaja_id_34683023489 = Organisaatio.objects.filter(organisaatio_oid=test_org_34683023489).first().id

        lapsi = {
            'henkilo': henkilo_url,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_34683023489),
            'oma_organisaatio': None,
            'paos_organisaatio': None,
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', json.dumps(lapsi), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_api_oid_related_field_create_lapsi_with_oids(self):
        client = SetUpTestClient('tester2').client()
        data = {
            'henkilo': '/api/v1/henkilot/7/',
            'oma_organisaatio_oid': test_org_34683023489,
            'paos_organisaatio_oid': test_org_93957375488,
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/lapset/', json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/1/')
        self.assertEqual(json.loads(resp.content)['paos_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/2/')

    def test_api_oid_related_field_lapsi_change_denied(self):
        client = SetUpTestClient('tester2').client()
        data = {
            'url': '/api/v1/lapset/4/',
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio_oid': test_org_93957375484,
            'paos_organisaatio_oid': test_org_93957375488,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi4',
        }

        resp = client.put('/api/v1/lapset/4/', json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'oma_organisaatio', 'GE013', 'Changing of this field is not allowed.')

    def test_api_oid_related_field_lapsi_no_paos_organisaatio(self):
        client = SetUpTestClient('tester2').client()

        data = {
            'url': '/api/v1/lapset/4/',
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio_oid': test_org_93957375484,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi4',
            # no paos_organisaatio_oid
        }

        resp = client.put('/api/v1/lapset/4/', json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_oid_related_field_lapsi_one_with_oid_one_with_url(self):
        client = SetUpTestClient('tester2').client()
        data = {
            'henkilo': '/api/v1/henkilot/7/',
            'oma_organisaatio_oid': test_org_34683023489,
            # no oma_organisaatio as it is via oid
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi-test',
        }

        resp = client.post('/api/v1/lapset/', json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/1/')

    def test_api_oid_related_field_lapsi_roundtrip(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/lapset/4/?format=json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = json.loads(resp.content)

        resp = client.put('/api/v1/lapset/4/', json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_api_oid_related_field_lapsi_different_values_error(self):
        client = SetUpTestClient('tester2').client()

        data = {
            'url': '/api/v1/lapset/4/',
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio_oid': test_org_34683023489,  # id=1
            'paos_organisaatio_oid': None,
            'oma_organisaatio': '/api/v1/vakajarjestajat/4/',  # id=4
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi4',
        }

        resp = client.put('/api/v1/lapset/4/', json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_oid_related_field_lapsi_invalid_oma_organisaatio_oid(self):
        client = SetUpTestClient('tester2').client()

        data = {
            'url': '/api/v1/lapset/4/',
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio_oid': 'some_invalid_oid',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi4',
        }

        resp = client.put('/api/v1/lapset/4/', json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_api_oid_related_field_varhaiskasvatuspaatos_toimipaikka_field_required(self):
        """
        This test is copied from test_api_push_correct_lapsi, but henkilo ids changed.
        At the end toimipaikka is omitted and that error verified.
        """

        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654322',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '180315A901Y',
            'etunimet': 'Anton',
            'kutsumanimi': 'Anton',
            'sukunimi': 'Kivimäki'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        henkilo_url = json.loads(resp.content)['url']

        vakajarjestaja_id_34683023489 = Organisaatio.objects.filter(organisaatio_oid=test_org_34683023489).first().id
        lapsi = {
            'henkilo': henkilo_url,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_34683023489),
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        self.assertEqual(resp2.status_code, status.HTTP_201_CREATED)
        lapsi_url = json.loads(resp2.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        self.assertEqual(resp3.status_code, status.HTTP_201_CREATED)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        varhaiskasvatussuhde = {
            # no toimipaikka
            'varhaiskasvatuspaatos': varhaiskasvatuspaatos_url,
            'alkamis_pvm': '2018-10-01',
            'lahdejarjestelma': '1',
        }
        resp4 = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        self.assertEqual(resp4.status_code, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp4, 'toimipaikka_oid', 'RF001', 'Either this field or the parent field is required.')

    def test_api_push_lapsi_valid_henkilo_oid(self):
        henkilo_oid = '1.2.246.562.24.7777777777755'
        henkilo_obj = Henkilo.objects.get(henkilo_oid=henkilo_oid)

        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        url_pattern = 'http://testserver/api/v1/henkilot/{0}/'
        resp_henkilo_url = json.loads(resp.content)['henkilo']
        self.assertEqual(resp_henkilo_url, url_pattern.format(henkilo_obj.id))

    def test_api_push_lapsi_invalid_henkilo_oid(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo_oid': '1.2.246.562.24.77777777777555',
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1',
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_update_lapsi_vakatoimija(self):
        vakajarjestaja_oid_correct = '1.2.246.562.10.34683023489'
        vakajarjestaja_oid_invalid = '1.2.246.562.10.93957375488'

        user = User.objects.get(username='tester2')
        group = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.93957375488')
        group.user_set.add(user)

        lapsi = Lapsi.objects.filter(vakatoimija__organisaatio_oid=vakajarjestaja_oid_correct).first()
        lapsi_json = {
            'henkilo_oid': lapsi.henkilo.henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid_invalid,
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester2').client()

        lapsi_json['vakatoimija_oid'] = vakajarjestaja_oid_invalid
        resp = client.put(f'/api/v1/lapset/{lapsi.id}/', json.dumps(lapsi_json), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'vakatoimija', 'GE013', 'Changing of this field is not allowed.')

    def test_api_get_lapsi_json_admin(self):
        """
        TODO: Sort nested resources // CSCVARDA-1113
        """
        lapsi_json = {
            'url': 'http://testserver/api/v1/lapset/1/?format=json',
            'id': 1,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/2/?format=json',
            'vakatoimija_oid': '1.2.246.562.10.93957375488',
            'oma_organisaatio': None,
            'oma_organisaatio_oid': None,
            'paos_kytkin': False,
            'paos_organisaatio': None,
            'paos_organisaatio_oid': None,
            'henkilo': 'http://testserver/api/v1/henkilot/2/?format=json',
            'henkilo_oid': '1.2.246.562.24.47279942650',
            'varhaiskasvatuspaatokset_top': [
                'http://testserver/api/v1/varhaiskasvatuspaatokset/1/?format=json'
            ],
            'huoltajuussuhteet': [
                'http://testserver/api/admin/huoltajuussuhteet/1/?format=json',
                'http://testserver/api/admin/huoltajuussuhteet/2/?format=json'
            ],
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi1',
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/lapset/1/?format=json')
        content = json.loads(resp.content)
        content.pop('muutos_pvm', None)
        self.assertEqual(content, lapsi_json)

    def test_api_post_paos_lapsi_and_test_filtering(self):
        client = SetUpTestClient('tester2').client()

        resp = client.get('/api/v1/lapset/?paos_kytkin=False')
        former_paos_false_count = json.loads(resp.content)['count']

        resp = client.get('/api/v1/lapset/?paos_kytkin=True')
        former_paos_true_count = json.loads(resp.content)['count']

        lapsi_json = {
            'henkilo': '/api/v1/henkilot/7/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', data=lapsi_json)
        assert_status_code(resp, status.HTTP_201_CREATED)

        resp = client.get('/api/v1/lapset/?paos_kytkin=False')
        self.assertEqual(json.loads(resp.content)['count'], former_paos_false_count)

        resp = client.get('/api/v1/lapset/?paos_kytkin=True')
        self.assertEqual(json.loads(resp.content)['count'], former_paos_true_count + 1)

    @responses.activate
    def test_api_push_correct_lapsi(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '210616A028D',
            'etunimet': 'Anton',
            'kutsumanimi': 'Anton',
            'sukunimi': 'Kivimäki',
        }
        client = SetUpTestClient('tester5').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        henkilo_url = json.loads(resp.content)['url']

        vakajarjestaja_id_93957375488 = Organisaatio.objects.filter(organisaatio_oid=test_org_93957375488).first().id
        lapsi = {
            'henkilo': henkilo_url,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_93957375488),
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, status.HTTP_201_CREATED)
        lapsi_url = json.loads(resp2.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm04',
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp3, status.HTTP_201_CREATED)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        toimipaikka_oid = '1.2.246.562.10.9395737548810'
        toimipaikka_id = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_oid).first().id
        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/{}/'.format(toimipaikka_id),
            'varhaiskasvatuspaatos': varhaiskasvatuspaatos_url,
            'alkamis_pvm': '2018-10-01',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_lapsi_not_found_henkilo(self):
        client = SetUpTestClient('tester').client()
        henkilo_url = '/api/v1/henkilot/11111/'
        resp = client.get(henkilo_url)
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)

        lapsi = {
            'henkilo': henkilo_url,
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilo', 'GE008', 'Invalid hyperlink, object does not exist.')

    def test_api_push_lapsi_under_different_vakajarjestaja(self):
        client = SetUpTestClient('tester2').client()

        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/3/',
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, status.HTTP_201_CREATED)
        vakapaatos_url = json.loads(resp.content)['url']

        varhaiskasvatussuhde = {
            'toimipaikka': '/api/v1/toimipaikat/6/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2019-10-01',
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_validation_error(resp2, 'toimipaikka', 'MI019', 'Given Toimipaikka does not belong to the correct Organisaatio.')
        assert_status_code(resp2, status.HTTP_400_BAD_REQUEST)

    def test_api_push_lapsi_duplicate(self):
        client = SetUpTestClient('tester2').client()
        lapsi_obj = Lapsi.objects.get(tunniste='testing-lapsi3')
        lapsi_qs = Lapsi.objects.filter(id=lapsi_obj.id)

        lapsi = {
            'henkilo_oid': '1.2.246.562.24.49084901392',
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '3',
            'tunniste': 'lapsi300'
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)
        lapsi_obj = lapsi_qs.first()
        self.assertEqual(lapsi_obj.lahdejarjestelma, '3')
        self.assertEqual(lapsi_obj.tunniste, 'lapsi300')
        self.assertEqual(json.loads(resp.content)['id'], lapsi_obj.id)

        lapsi['lahdejarjestelma'] = '5'
        del lapsi['tunniste']
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)
        lapsi_obj = lapsi_qs.first()
        self.assertEqual(lapsi_obj.tunniste, None)
        self.assertEqual(lapsi_obj.lahdejarjestelma, '5')
        self.assertEqual(json.loads(resp.content)['id'], lapsi_obj.id)

    def test_api_push_lapsi_incorrect_paos(self):
        client = SetUpTestClient('tester').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'LA007', 'For PAOS, both oma_organisaatio and paos_organisaatio are required.')

        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp2, 'errors', 'LA007', 'For PAOS, both oma_organisaatio and paos_organisaatio are required.')

    def test_api_push_lapsi_incorrect_paos_2(self):
        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/1/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PO003', 'There is no active PaosOikeus.')

    def test_api_push_lapsi_correct_paos(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)  # already created

    def test_api_push_lapsi_correct_paos_2(self):
        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)
        lapsi_url = json.loads(resp.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': 45,
            'jarjestamismuoto_koodi': 'jm02',
            'tilapainen_vaka_kytkin': False,
            'alkamis_pvm': '2018-09-01',
            'hakemus_pvm': '2018-08-08',
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp2, status.HTTP_201_CREATED)
        vakapaatos_url = json.loads(resp2.content)['url']

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/2/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01',
            'lahdejarjestelma': '1',
        }
        resp3 = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp3, 'toimipaikka', 'MI019', 'Given Toimipaikka does not belong to the correct Organisaatio.')

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01',
            'lahdejarjestelma': '1',
        }
        resp4 = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_validation_error(resp4, 'errors', 'PT010', 'There is no active PaosToiminta to this Toimipaikka.')
        assert_status_code(resp4, status.HTTP_400_BAD_REQUEST)

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/5/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01',
            'lahdejarjestelma': '1',
        }
        resp5 = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp5, status.HTTP_201_CREATED)

    def test_api_push_paos_lapsi_duplicate(self):
        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)

        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, status.HTTP_200_OK)  # Lapsi is already added
        self.assertEqual(json.loads(resp2.content)['henkilo'], 'http://testserver/api/v1/henkilot/1/')

    def test_api_push_vakapaatos_paos_lapsi(self):
        """
        Paos-tallentaja needs tallentaja-permissions on vakajarjestaja-level in oma_organisaatio.
        """
        group_obj = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.34683023489')
        user = User.objects.get(username='tester')
        user.groups.add(group_obj)

        client = SetUpTestClient('tester').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)
        lapsi_url = json.loads(resp.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_validation_error(resp, 'jarjestamismuoto_koodi', 'VP005', 'Invalid code for PAOS Lapsi.')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

        varhaiskasvatuspaatos['jarjestamismuoto_koodi'] = 'jm02'
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_push_vakapaatos_non_paos_lapsi(self):
        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/1/',
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm03',
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'jarjestamismuoto_koodi', 'VP006', 'Invalid code for non-PAOS Lapsi.')

    def test_api_get_huoltaja_by_varhaiskasvatuspaatos(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/1/')
        lapsi_url = json.loads(resp.content)['lapsi']
        resp2 = client.get(lapsi_url)
        huoltajat_url = json.loads(resp2.content)['huoltajuussuhteet']
        self.assertEqual(len(huoltajat_url), 2)

    def test_api_external_permissions_no_virkailija(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            'accessAllowed': False,
            'errorMessage': 'loggedInUserOid was not found'
        }
        post_data = {
            'personOidsForSamePerson': ['1', '1.2.246.562.24.47279942650'],
            'organisationOids': ['string'],
            'loggedInUserRoles': ['string'],
            'loggedInUserOid': '1.2.34567891'
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_no_person(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            'accessAllowed': False,
            'errorMessage': 'Person not found'
        }
        post_data = {
            'personOidsForSamePerson': ['1', '1.2.246.562.24.490849013939'],
            'organisationOids': ['string'],
            'loggedInUserRoles': ['string'],
            'loggedInUserOid': '1.2.345678910'
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_multiple_person(self):
        client = SetUpTestClient('tester').client()
        post_data = {
            'personOidsForSamePerson': ['1.2.246.562.24.49084901392', '1.2.246.562.24.47279942650'],
            'organisationOids': ['string'],
            'loggedInUserRoles': ['string'],
            'loggedInUserOid': '1.2.345678910'
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 500)
        assert_validation_error(resp, 'errors', 'MI016', 'A server error occurred. Team is investigating this.')

    def test_api_external_permissions_no_permissions(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            'accessAllowed': False,
            'errorMessage': ''
        }
        post_data = {
            'personOidsForSamePerson': ['1', '1.2.246.562.24.47279942650'],
            'organisationOids': ['string'],
            'loggedInUserRoles': ['string'],
            'loggedInUserOid': '1.2.246.562.24.6722258949565'
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_has_permission(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            'accessAllowed': True,
            'errorMessage': ''
        }
        post_data = {
            'personOidsForSamePerson': ['1', '1.2.246.562.24.47279942650'],
            'organisationOids': ['string'],
            'loggedInUserRoles': ['string'],
            'loggedInUserOid': '1.2.345678910'
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    @responses.activate
    def test_api_push_huoltaja_not_allowed(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '050990-431L',
            'etunimet': 'Tobias Jonas',
            'kutsumanimi': 'Tobias',
            'sukunimi': 'Virkkunen'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        henkilo_url = json.loads(resp.content)['url']

        huoltaja = {
            'henkilo': henkilo_url
        }
        client = SetUpTestClient('credadmin').client()
        resp1 = client.post('/api/admin/huoltajat/', huoltaja)
        assert_status_code(resp1, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_api_get_vakajarjestaja_json(self):
        vakajarjestaja_json = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [
                {
                    'url': 'http://testserver/api/v1/vakajarjestajat/1/?format=json',
                    'id': 1,
                    'nimi': 'Tester2 organisaatio',
                    'y_tunnus': '8500570-7',
                    'yritysmuoto': '41',
                    'kunnallinen_kytkin': True,
                    'organisaatio_oid': '1.2.246.562.10.34683023489',
                    'kunta_koodi': '091',
                    'kayntiosoite': 'Testerkatu 2',
                    'kayntiosoite_postinumero': '00001',
                    'kayntiosoite_postitoimipaikka': 'Testilä',
                    'postiosoite': 'Testerkatu 2',
                    'postinumero': '00001',
                    'postitoimipaikka': 'Testilä',
                    'alkamis_pvm': '2017-02-03',
                    'paattymis_pvm': None,
                    'toimipaikat_top': [
                        'http://testserver/api/v1/toimipaikat/2/?format=json',
                        'http://testserver/api/v1/toimipaikat/3/?format=json'
                    ],
                    'sahkopostiosoite': 'organization@domain.com',
                    'ipv4_osoitteet': None,
                    'ipv6_osoitteet': None,
                    'puhelinnumero': '+358101234567',
                    'organisaatiotyyppi': [Organisaatiotyyppi.VAKAJARJESTAJA.value]
                }
            ]
        }
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/vakajarjestajat/?format=json')
        content = json.loads(resp.content)
        content['results'][0].pop('muutos_pvm', None)
        self.assertEqual(content, vakajarjestaja_json)

    def test_api_get_toimipaikat_json(self):
        toimipaikka_json = {
            'url': 'http://testserver/api/v1/toimipaikat/1/?format=json',
            'id': 1,
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/2/?format=json',
            'vakajarjestaja_oid': '1.2.246.562.10.93957375488',
            'toiminnallisetpainotukset_top': [
                'http://testserver/api/v1/toiminnallisetpainotukset/1/?format=json'
            ],
            'kielipainotukset_top': [
                'http://testserver/api/v1/kielipainotukset/1/?format=json'
            ],
            'varhaiskasvatussuhteet_top': [
                'http://testserver/api/v1/varhaiskasvatussuhteet/1/?format=json',
                'http://testserver/api/v1/varhaiskasvatussuhteet/2/?format=json',
                'http://testserver/api/v1/varhaiskasvatussuhteet/9/?format=json'
            ],
            'nimi': 'Espoo',
            'organisaatio_oid': '1.2.246.562.10.9395737548810',
            'kayntiosoite': 'Keilaranta 14',
            'kayntiosoite_postitoimipaikka': 'Espoo',
            'kayntiosoite_postinumero': '02100',
            'postiosoite': 'Keilaranta 14',
            'postitoimipaikka': 'Espoo',
            'postinumero': '02100',
            'kunta_koodi': '091',
            'puhelinnumero': '+35810123456',
            'sahkopostiosoite': 'test1@espoo.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj02',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI', 'SV'],
            'jarjestamismuoto_koodi': [
                'jm02',
                'jm03',
                'jm04',
                'jm05'
            ],
            'varhaiskasvatuspaikat': 120,
            'toiminnallinenpainotus_kytkin': True,
            'kielipainotus_kytkin': True,
            'alkamis_pvm': '2017-02-03',
            'paattymis_pvm': None,
            'hallinnointijarjestelma': 'ORGANISAATIO',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-toimipaikka1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/1/?format=json')
        content = json.loads(resp.content)
        content.pop('muutos_pvm', None)
        self.assertEqual(content, toimipaikka_json)

    def test_api_get_toimipaikat_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        resp = client.get('/api/v1/toimipaikat/?id=test')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'id', 'GE025', 'This field must be a number.')

        resp = client.get('/api/v1/toimipaikat/?id=1')
        assert_status_code(resp, status.HTTP_200_OK)
        results = json.loads(resp.content)['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], 1)

    def test_api_get_henkilo_syntyma_pvm(self):
        client = SetUpTestClient('tester').client()
        post_henkilo_to_get_permissions(client, henkilo_id=1)
        resp = client.get('/api/v1/henkilot/1/')
        henkilo = json.loads(resp.content)
        self.assertEqual(henkilo['syntyma_pvm'], '1956-04-12')

    def test_api_push_without_privilages(self):
        org = {
            'nimi': 'Fake-Helsingin kaupunki',
            'y_tunnus': '0201244-2',
            'kunta_koodi': '091',
            'sahkopostiosoite': 'fake@helsiki.fi',
            'puhelinnumero': '112'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)

    def test_api_push_incorrect_ipv4_address(self):
        org = {
            'nimi': 'Fake-Helsingin kaupunki',
            'y_tunnus': '0920632-0',
            'sahkopostiosoite': 'fake@helsiki.fi',
            'ipv4_osoitteet': ['192.168.0.1/'],
            'kunta_koodi': '091',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'puhelinnumero': '+3589123123'
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['ipv4_osoitteet', '0'], 'VJ007', 'Not a valid IPv4-address.')

    def test_api_push_incorrect_ipv6_address(self):
        org = {
            'nimi': 'Fake-Helsingin kaupunki',
            'y_tunnus': '0920632-0',
            'sahkopostiosoite': 'fake@helsiki.fi',
            'ipv4_osoitteet': ['192.168.0.1/32'],
            'ipv6_osoitteet': ['2001:db8::/480'],
            'kunta_koodi': '091',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'puhelinnumero': '+3589112112'
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['ipv6_osoitteet', '0'], 'VJ008', 'Not a valid IPv6-address.')

    def test_api_push_incorrect_email(self):
        client = SetUpTestClient('tester10').client()

        vakajarjestaja_patch = {
            'sahkopostiosoite': 'fake@helsinki.f'
        }
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')

        resp = client.patch(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/', vakajarjestaja_patch)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'sahkopostiosoite', 'GE024', 'This field must be an email address.')

    def test_api_push_incorrect_jarjestamismuoto_koodi(self):
        varhaiskasvatuspaatos = {
            'lapsi': 'http://testserver/api/v1/lapset/1/',
            'tuntimaara_viikossa': 45,
            'jarjestamismuoto_koodi': 'no_code',
            'alkamis_pvm': '2018-09-01',
            'hakemus_pvm': '2018-08-08',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'jarjestamismuoto_koodi', 'KO002', 'Code cannot have special characters.')

    @responses.activate
    def test_api_push_correct_toimipaikka(self):
        # This test relies on organisaatio_client default error handling
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TP007', 'Could not check duplicates from Organisaatiopalvelu. Please try again later.')

    def test_api_push_incorrect_toimipaikka(self):
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kayntiosoite', 'GE001', 'This field is required.')

        toimipaikka['kayntiosoite'] = ''
        resp2 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp2, 'kayntiosoite', 'GE003', 'This field may not be blank.')

        toimipaikka['kayntiosoite'] = 'Jo'
        resp3 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp3, 'kayntiosoite', 'DY002', 'Ensure this field has at least 3 characters.')

        toimipaikka['kayntiosoite'] = '12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901'
        resp4 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp4, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp4, 'kayntiosoite', 'DY001', 'Ensure this field has no more than 100 characters.')

    def test_api_push_incorrect_toimintamuoto(self):
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'eitoimintaa',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'toimintamuoto_koodi', 'KO003', 'Not a valid code.')

    def test_api_push_incorrect_kasvatusopillinen_jarjestelma(self):
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'ei kasvatusta',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kasvatusopillinen_jarjestelma_koodi', 'KO001', 'Code cannot have spaces.')

    def test_toimipaikka_incorrect_jarjestamismuoto(self):
        client_kunta = SetUpTestClient('tester2').client()
        vakajarjestaja_oid_kunta = '1.2.246.562.10.34683023489'
        client_yksityinen = SetUpTestClient('tester5').client()
        vakajarjestaja_oid_yksityinen = '1.2.246.562.10.93957375488'

        toimipaikka = {
            'vakajarjestaja_oid': vakajarjestaja_oid_kunta,
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj01',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03', 'JM01', 'jm05'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01',
            'lahdejarjestelma': '1',
        }

        resp_1 = client_kunta.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'jarjestamismuoto_koodi', 'TP017', 'Invalid codes for kunnallinen Toimipaikka.')
        assert_validation_error(resp_1, 'jarjestamismuoto_koodi', 'TP019', 'There are duplicate jarjestamismuoto codes.')

        toimipaikka['vakajarjestaja_oid'] = vakajarjestaja_oid_yksityinen
        toimipaikka['jarjestamismuoto_koodi'] = ['jm03', 'jm05', 'jm01']
        resp_2 = client_yksityinen.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'jarjestamismuoto_koodi', 'TP018', 'Invalid codes for yksityinen Toimipaikka.')

    def test_api_push_incorrect_toimintapainotus_koodi(self):
        toiminnallinenpainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'alkamis_pvm': '2018-07-01',
            'toimintapainotus_koodi': 'noc',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'toimintapainotus_koodi', 'KO003', 'Not a valid code.')

    def test_push_api_incorrect_kieli_koodi(self):
        kielipainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'alkamis_pvm': '2018-07-01',
            'kielipainotus_koodi': 'UU',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'kielipainotus_koodi', 'KO003', 'Not a valid code.')

    def test_push_api_incorrect_kielipainotus(self):
        kielipainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2018-08-09',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'KP001', 'KieliPainotus with this kielipainotus_koodi already exists '
                                                         'for toimipaikka on the given date range.')

    def test_push_correct_kielipainotus(self):
        kielipainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2019-08-09',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_push_api_incorrect_toiminnallinenpainotus(self):
        toiminnallinenpainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'toimintapainotus_koodi': 'tp01',
            'alkamis_pvm': '2018-08-09',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TO001', 'ToiminnallinenPainotus with this toimintapainotus_koodi '
                                                         'already exists for toimipaikka on the given date range.')

    def test_push_correct_toiminnallinenpainotus(self):
        toiminnallinenpainotus = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'toimintapainotus_koodi': 'tp02',
            'alkamis_pvm': '2019-08-09',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_api_filter_vakajarjestajat_kunnallinen_kytkin(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/vakajarjestajat/?kunnallinen_kytkin=True')
        result = json.loads(resp.content)
        count = result['count']
        kunnallinen_kytkin = result['results'][0]['kunnallinen_kytkin']
        self.assertEqual(count, 4)
        self.assertEqual(kunnallinen_kytkin, True)

        resp = client.get('/api/v1/vakajarjestajat/?kunnallinen_kytkin=False')
        result = json.loads(resp.content)
        count = result['count']
        kunnallinen_kytkin = result['results'][0]['kunnallinen_kytkin']
        self.assertEqual(count, 4)
        self.assertEqual(kunnallinen_kytkin, False)

        resp = client.get('/api/v1/vakajarjestajat/')
        result = json.loads(resp.content)
        count = result['count']
        self.assertEqual(count, 8)

    def test_push_incorrect_varhaiskasvatuspaatos_tuntimaara(self):
        varhaiskasvatuspaatos = {
            'lapsi': 'http://testserver/api/v1/lapset/1/',
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': 200,
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2018-07-30',
            'alkamis_pvm': '2018-10-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'tuntimaara_viikossa', 'DY005', 'Ensure this value is less than or equal to 120.')

    def test_push_api_varhaiskasvatuspaatos_pikakasittely_kytkin_true(self):
        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/2/',
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': 30,
            'jarjestamismuoto_koodi': 'jm04',
            'hakemus_pvm': '2018-01-01',
            'alkamis_pvm': '2018-01-15',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        json_data = json.loads(resp.content)
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json_data['pikakasittely_kytkin'], True)

    def test_push_api_varhaiskasvatuspaatos_pikakasittely_kytkin_false(self):
        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/2/',
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': 30,
            'jarjestamismuoto_koodi': 'jm04',
            'hakemus_pvm': '2018-01-01',
            'alkamis_pvm': '2018-01-16',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        json_data = json.loads(resp.content)
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json_data['pikakasittely_kytkin'], False)

    def test_push_api_varhaiskasvatuspaatos_date_validation(self):
        client = SetUpTestClient('tester').client()

        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/2/',
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': 30,
            'jarjestamismuoto_koodi': 'jm04',
            'lahdejarjestelma': '1',
        }

        ok_cases = [
            ('2018-01-01', '2018-02-01', None),          # no end date
            ('2017-12-31', '2018-10-14', '2020-12-12'),  # all correct
        ]

        fail_cases = [
            ('2017-02-01', '2016-02-01', None),          # application after start
            ('2017-02-01', '2017-12-31', '2017-11-30'),  # end before start
            ('1999-01-01', '2017-02-01', None),          # application before 2000
            ('1998-01-01', '1998-02-02', '1999-02-02'),  # all before 2000
            (None, '2018-07-01', None),                  # application missing, start ok
            (None, None, None),                          # all missing
        ]

        for (application, start, end) in ok_cases:
            varhaiskasvatuspaatos.update(
                hakemus_pvm=application,
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatuspaatos)
            resp = client.post('/api/v1/varhaiskasvatuspaatokset/', data=data, content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

            id = json.loads(resp.content)['id']
            Varhaiskasvatuspaatos.objects.get(id=id).delete()

        for (application, start, end) in fail_cases:
            varhaiskasvatuspaatos.update(
                hakemus_pvm=application,
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatuspaatos)
            resp = client.post('/api/v1/varhaiskasvatuspaatokset/', data=data, content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_delete_varhaiskasvatuspaatos(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/varhaiskasvatuspaatokset/1/')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'VP004', 'Cannot delete Varhaiskasvatuspaatos. There are objects '
                                                         'referencing it that need to be deleted first.')

    def test_push_api_varhaiskasvatussuhde_date_validation(self):
        client = SetUpTestClient('tester').client()

        varhaiskasvatussuhde = {
            'varhaiskasvatuspaatos': '/api/v1/varhaiskasvatuspaatokset/1/',
            'toimipaikka': '/api/v1/toimipaikat/1/',
            'lahdejarjestelma': '1',
        }

        # varhaiskasvatuspaatos with id 1: alkamis_pvm=2017-02-11, paattymis_pvm=2018-02-24

        ok_cases = [
            ('2017-10-14', '2018-02-12'),  # All correct
        ]

        fail_cases = [
            ('2017-04-01', None),          # No end date (vakapaatos has end date)
            ('2016-02-01', None),          # start before vakapaatos start
            ('2016-02-01', '2023-11-30'),  # start before vakapaatos start and end after vakapaatos end
            ('2017-12-31', '2023-11-30'),  # end after vakapaatos end
            ('1999-03-01', None),          # start before 2000
            ('1998-02-02', '1999-02-02'),  # all before 2000
            (None, '2023-01-01'),          # start missing
            (None, None),                  # all missing
        ]

        for (start, end) in ok_cases:
            varhaiskasvatussuhde.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatussuhde)
            resp = client.post('/api/v1/varhaiskasvatussuhteet/', data=data, content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

            id = json.loads(resp.content)['id']
            Varhaiskasvatussuhde.objects.get(id=id).delete()

        for (start, end) in fail_cases:
            varhaiskasvatussuhde.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatussuhde)
            resp = client.post('/api/v1/varhaiskasvatussuhteet/', data=data, content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_api_get_maksutieto(self):
        """
        Get-request should never return henkilotunnus for huoltajat.
        """
        expected_response = {
            'alkamis_pvm': '2019-09-01',
            'asiakasmaksu': '0.00',
            'huoltajat': [
                {
                    'etunimet': 'Pauliina',
                    'henkilo_oid': '1.2.987654321',
                    'sukunimi': 'Virtanen'
                },
                {
                    'etunimet': 'Pertti',
                    'henkilo_oid': '',
                    'sukunimi': 'Virtanen'
                }
            ],
            'id': 1,
            'lapsi': 'http://testserver/api/v1/lapset/1/',
            'lapsi_tunniste': 'testing-lapsi1',
            'maksun_peruste_koodi': 'mp01',
            'paattymis_pvm': None,
            'palveluseteli_arvo': '0.00',
            'perheen_koko': None,
            'url': 'http://testserver/api/v1/maksutiedot/1/',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-maksutieto1',
        }

        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/maksutiedot/1/')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_push_api_maksutieto_missing_huoltajat(self):
        maksutieto = {
            'huoltajat': [],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2019-01-01',
            'paattymis_pvm': '2020-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['huoltajat', 'errors'], 'GE005', 'This list may not be empty.')

    def test_push_api_maksutieto_missing_huoltaja_hetu_or_oid(self):
        maksutieto = {
            'huoltajat': [{'etunimet': 'Jukka', 'sukunimi': 'Pekkarinen'}],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2019-01-01',
            'paattymis_pvm': '2020-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['huoltajat', '0', 'errors'], 'HE004', 'Either henkilotunnus or henkilo_oid is needed, but not both.')

    def test_push_api_maksutieto_correct_format_1(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/3/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        returned_data = json.loads(resp.content)
        returned_id = returned_data['id']
        maksutieto_url = 'http://testserver/api/v1/maksutiedot/' + str(returned_id) + '/'

        accepted_response = {
            'url': maksutieto_url,
            'id': returned_id,
            'huoltajat': [
                {
                    'henkilo_oid': '',
                    'henkilotunnus': '120386-109V',
                    'etunimet': 'Pertti',
                    'sukunimi': 'Virtanen'
                }
            ],
            'lapsi': 'http://testserver/api/v1/lapset/3/',
            'lapsi_tunniste': 'testing-lapsi3',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': '120.00',
            'asiakasmaksu': '0.00',
            'perheen_koko': 2,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'tallennetut_huoltajat_count': 1,
            'ei_tallennetut_huoltajat_count': 2,
            'lahdejarjestelma': '1',
            'tunniste': None
        }
        self.assertEqual(json.loads(resp.content), accepted_response)

    def test_push_api_maksutieto_yksityinen_1(self):
        """
        In response:
         - Return henkilotunnus if huoltaja was given using it
         - Drop henkilotunnus-attribute from response if huoltaja was given using henkilo_oid
        """
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2018-02-23',
            'paattymis_pvm': '2021-02-24',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        client.delete('/api/v1/maksutiedot/1/')  # remove 1 maksutieto, otherwise error: more than two active maksutieto
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        returned_data = json.loads(resp.content)
        returned_id = returned_data['id']
        maksutieto_url = 'http://testserver/api/v1/maksutiedot/' + str(returned_id) + '/'

        accepted_response = {
            'url': maksutieto_url,
            'id': returned_id,
            'huoltajat': [
                {
                    'henkilo_oid': '1.2.987654321',
                    'etunimet': 'Pauliina',
                    'sukunimi': 'Virtanen'
                },
                {
                    'henkilo_oid': '',
                    'henkilotunnus': '120386-109V',
                    'etunimet': 'Pertti',
                    'sukunimi': 'Virtanen'
                }
            ],
            'lapsi': 'http://testserver/api/v1/lapset/1/',
            'lapsi_tunniste': 'testing-lapsi1',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': None,
            'asiakasmaksu': '0.00',
            'perheen_koko': None,
            'alkamis_pvm': '2018-02-23',
            'paattymis_pvm': '2021-02-24',
            'tallennetut_huoltajat_count': 2,
            'ei_tallennetut_huoltajat_count': 1,
            'lahdejarjestelma': '1',
            'tunniste': None,
        }
        self.assertEqual(json.loads(resp.content), accepted_response)

    def test_push_api_maksutieto_yksityinen_2(self):
        lapsi_oid = '1.2.246.562.24.52864662677'
        lapsi_obj = Lapsi.objects.get(henkilo__henkilo_oid=lapsi_oid)

        maksutieto = {
            'huoltajat': [
                {'henkilotunnus': '260980-642C', 'etunimet': 'Maija', 'sukunimi': 'Mallikas'}
            ],
            'lapsi': f'/api/v1/lapset/{lapsi_obj.id}/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 4,
            'alkamis_pvm': '2020-05-25',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

        resp_result = json.loads(resp.content)
        self.assertEqual(resp_result['palveluseteli_arvo'], None)
        self.assertEqual(resp_result['perheen_koko'], None)

        maksutieto_obj = Maksutieto.objects.get(id=resp_result['id'])
        self.assertTrue(maksutieto_obj.yksityinen_jarjestaja)

    def test_push_api_maksutieto_yksityinen_date_validation(self):
        lapsi_oid = '1.2.246.562.24.52864662677'
        lapsi_obj = Lapsi.objects.get(henkilo__henkilo_oid=lapsi_oid)

        maksutieto = {
            'huoltajat': [
                {'henkilotunnus': '260980-642C', 'etunimet': 'Maija', 'sukunimi': 'Mallikas'}
            ],
            'lapsi': f'/api/v1/lapset/{lapsi_obj.id}/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 4,
            'alkamis_pvm': '2020-05-25',
            'paattymis_pvm': '2020-08-30',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'MA014', 'paattymis_pvm must be equal to or after 2020-09-01 for yksityinen Lapsi.')

    def test_push_api_maksutieto_date_validation(self):
        """
        This test contains multiple individual date tests for maksutieto dates.
        All of them share the same setup code:

        For this we need a lapsi that doesn't already have any maksutiedot,
        and that it has vakapaatokset suitable for testing date ranges.
        As such data doesn't already exist, we must create it:
        * Create a lapsi person and a lapsi object
        * Create a huoltaja person and a huoltaja object
        * Link the huoltaja to the lapsi with a Huoltajuussuhde
        * Create a vakapaatosfor 2018-2019 and link to a toimipaikka
        * Create a vakapaatos for 2021- and link to a toimipaikka
        * Give permissions to each of these for the tester user's org
        """
        client = SetUpTestClient('tester').client()
        oid_of_client = '1.2.246.562.10.9395737548810'

        lapsi_hetu = '180210A9437'
        huoltaja_hetu = '180200A941K'

        lapsi_henkilo = Henkilo.objects.create(
            henkilotunnus=encrypt_string(lapsi_hetu),
            henkilotunnus_unique_hash=hash_string(lapsi_hetu),
            henkilo_oid='1.2.246.562.24.158201550073654912',
            etunimet='Juniori',
            kutsumanimi='Juniori',
            sukunimi='Nieminen'
        )
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        lapsi = Lapsi.objects.create(
            henkilo=lapsi_henkilo,
            lahdejarjestelma='1',
            vakatoimija=vakajarjestaja,
        )
        assign_object_level_permissions(oid_of_client, Henkilo, lapsi_henkilo)
        assign_object_level_permissions(oid_of_client, Lapsi, lapsi)

        huoltaja_henkilo = Henkilo.objects.create(
            henkilotunnus=encrypt_string(huoltaja_hetu),
            henkilotunnus_unique_hash=hash_string(huoltaja_hetu),
            henkilo_oid='1.2.246.562.24.158201550073654911',
            etunimet='Seniori',
            kutsumanimi='Seniori',
            sukunimi='Nieminen'
        )
        huoltaja_obj = {
            'henkilotunnus': huoltaja_hetu,
            'etunimet': huoltaja_henkilo.etunimet,
            'sukunimi': huoltaja_henkilo.sukunimi,
            'kutsumanimi': huoltaja_henkilo.kutsumanimi
        }
        assign_object_level_permissions(oid_of_client, Henkilo, huoltaja_henkilo)
        huoltaja = Huoltaja.objects.create(
            henkilo=huoltaja_henkilo
        )
        assign_object_level_permissions(oid_of_client, Huoltaja, huoltaja)

        hs = Huoltajuussuhde.objects.create(
            huoltaja=huoltaja,
            lapsi=lapsi,
            voimassa_kytkin=True
        )
        assign_object_level_permissions(oid_of_client, Huoltajuussuhde, hs)

        toimipaikka_1 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548815')

        vakapaatos = Varhaiskasvatuspaatos.objects.create(
            lapsi=lapsi,
            tuntimaara_viikossa=45,
            jarjestamismuoto_koodi='jm02',
            alkamis_pvm='2018-01-01',
            paattymis_pvm='2019-12-31',
            hakemus_pvm='2017-11-01',
            lahdejarjestelma='1',
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatuspaatos, vakapaatos)

        vakasuhde = Varhaiskasvatussuhde.objects.create(
            toimipaikka=toimipaikka_1,
            varhaiskasvatuspaatos=vakapaatos,
            alkamis_pvm='2018-01-01',
            paattymis_pvm='2019-12-31',
            lahdejarjestelma='1',
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatussuhde, vakasuhde)

        vakapaatos_2 = Varhaiskasvatuspaatos.objects.create(
            lapsi=lapsi,
            tuntimaara_viikossa=45,
            jarjestamismuoto_koodi='jm02',
            alkamis_pvm='2021-01-01',
            hakemus_pvm='2017-11-01',
            lahdejarjestelma='1',
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatuspaatos, vakapaatos_2)

        vakasuhde_2 = Varhaiskasvatussuhde.objects.create(
            toimipaikka=toimipaikka_1,
            varhaiskasvatuspaatos=vakapaatos_2,
            alkamis_pvm='2021-01-01',
            lahdejarjestelma='1',
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatussuhde, vakasuhde_2)

        """
        Now the test setup is finally done.
        Try to add a maksutieto in following cases:
        (And be sure to delete the added maksutieto after each success.)
        """

        ok_cases = [
            ('2018-02-01', '2018-07-01'),  # Within first vaka
            ('2018-01-01', '2019-12-31'),  # Exactly the first vaka
            ('2018-02-01', '2021-02-01'),  # Within first and second vaka
            ('2020-02-01', '2020-11-01'),  # Between vakas (move to fail cases after whenever stage 2 is implemented)
            ('2021-02-01', None),          # Open-ended; within second(open-ended) vaka
            ('2021-01-01', None),          # Open-ended; starting exactly from second vaka
            ('2018-02-01', None),          # Open-ended; starting within first vaka
        ]

        fail_cases = [
            ('2017-02-01', None),          # Before first vaka
            ('2017-02-01', '2017-12-31'),  # Before first vaka
            ('2017-02-01', '2017-02-01'),  # Start before first vaka
            ('1998-02-02', '1999-02-02'),  # Start and end before 2000
            (None, '2018-07-01'),          # Start missing, end ok
            (None, None),                  # Both missing
        ]

        maksutieto = {
            'huoltajat': [
                huoltaja_obj
            ],
            'lapsi': '/api/v1/lapset/{}/'.format(lapsi.id),
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'lahdejarjestelma': '1',
        }

        for (start, end) in ok_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

            id = json.loads(resp.content)['id']
            MaksutietoHuoltajuussuhde.objects.filter(maksutieto_id=id).delete()
            Maksutieto.objects.get(id=id).delete()

        for (start, end) in fail_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

        # to test ending date validations every vakapaatos needs to have paattymis_pvm
        vakapaatos_2.paattymis_pvm = '2025-01-01'
        vakapaatos_2.save()

        close_ended_ok_cases = [
            ('2021-01-01', '2025-01-01'),  # Within second vakapaatos
            ('2025-01-01', '2025-01-01'),  # One day maksu at the end of the last vakapaatos
            ('2021-01-01', '2021-01-01'),  # One day maksu at the start of the last vakapaatos
        ]

        for (start, end) in close_ended_ok_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, status.HTTP_201_CREATED)

            id = json.loads(resp.content)['id']
            MaksutietoHuoltajuussuhde.objects.filter(maksutieto_id=id).delete()
            Maksutieto.objects.get(id=id).delete()

        close_ended_fail_cases = [
            ('2017-12-31', '2025-01-02'),  # Before first vakapaatos and after the end of the second vakapaatos
            ('2018-01-01', '2025-01-02'),  # Ending after second vakapaatos
            ('2017-12-31', '2025-01-01'),  # Before first vakapaatos
            ('2025-01-03', '2025-01-05'),  # After both vakapaatos dates
        ]

        for (start, end) in close_ended_fail_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)

    def test_push_api_maksutieto_too_many_active(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MA004', 'Lapsi already has 2 overlapping Maksutieto on the given date range.')

    def test_push_api_maksutieto_duplicate_hetus(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat', 'MA017', 'Duplicate huoltajat detected.')

    def test_push_api_maksutieto_duplicate_henkilo_oids(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat', 'MA017', 'Duplicate huoltajat detected.')

    def test_push_api_maksutieto_missing_alkamis_pvm(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'alkamis_pvm', 'GE001', 'This field is required.')

    def test_push_api_maksutieto_incorrect_paattymis_pvm(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2022-01-01',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paattymis_pvm', 'MI004', 'paattymis_pvm must be equal to or after alkamis_pvm.')

    def test_push_api_correct_maksutieto_for_one_day(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '120386-109V', 'etunimet': 'Pertti', 'sukunimi': 'Virtanen'},
                {'henkilotunnus': '110548-316P', 'etunimet': 'Juhani', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/3/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2022-01-01',
            'paattymis_pvm': '2022-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_push_api_maksutieto_too_many_active_long_timeframe(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2018-01-02',
            'paattymis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MA004', 'Lapsi already has 2 overlapping Maksutieto on the given date range.')

    def test_push_api_maksutieto_too_many_active_short_timeframe(self):
        maksutieto = {
            'huoltajat': [
                {'henkilo_oid': '1.2.987654321', 'etunimet': 'Pauliina', 'sukunimi': 'Virtanen'}
            ],
            'lapsi': '/api/v1/lapset/1/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2019-03-02',
            'paattymis_pvm': '2021-06-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MA004', 'Lapsi already has 2 overlapping Maksutieto on the given date range.')

    def test_push_api_maksutieto_no_matching_huoltajat(self):
        maksutieto = {
            'huoltajat': [{'henkilotunnus': '110494-9153', 'etunimet': 'Jukka', 'sukunimi': 'Pekkarinen'}],
            'lapsi': '/api/v1/lapset/3/',
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2019-01-01',
            'paattymis_pvm': '2019-02-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat', 'MA003', 'No matching huoltaja found.')

    @responses.activate
    def test_push_api_maksutieto_no_varhaiskasvatuspaatos(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            'henkilotunnus': '080576-922J',
            'etunimet': 'Anni',
            'kutsumanimi': 'Anni',
            'sukunimi': 'Jussinen',
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        henkilo_url = json.loads(resp.content)['url']

        vakajarjestaja_id_34683023489 = Organisaatio.objects.filter(organisaatio_oid=test_org_34683023489).first().id
        lapsi = {
            'henkilo': henkilo_url,
            'vakatoimija': 'http://testserver/api/v1/vakajarjestajat/{}/'.format(vakajarjestaja_id_34683023489),
            'lahdejarjestelma': '1',
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, status.HTTP_201_CREATED)
        lapsi_url = json.loads(resp2.content)['url']
        maksutieto = {
            'huoltajat': [{'henkilotunnus': '110494-9153', 'etunimet': 'Jukka', 'sukunimi': 'Pekkarinen'}],
            'lapsi': lapsi_url,
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120,
            'asiakasmaksu': 0,
            'perheen_koko': 2,
            'alkamis_pvm': '2019-01-01',
            'paattymis_pvm': '2020-01-01',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MA009', 'Lapsi does not have Varhaiskasvatussuhde. Add Varhaiskasvatussuhde before adding Maksutieto.')

    def test_api_maksutieto_multiple_huoltaja_list_admin(self):
        # Maksutieto should only be listed once even if it has multiple huoltajat and lapsi-filter is used
        # (related object filter, many-to-many relationship)
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.57294396385')
        lapsi = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.6779627637492', vakatoimija=vakajarjestaja)

        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get(f'/api/v1/maksutiedot/?lapsi={lapsi.id}')
        assert_status_code(resp, status.HTTP_200_OK)
        resp_json = json.loads(resp.content)
        self.assertEqual(resp_json['count'], 1)

    def test_api_maksutieto_distinct_order_by(self):
        def _get_id_list_from_json(resp):
            json_resp = json.loads(resp.content)['results']
            return [maksutieto['id'] for maksutieto in json_resp]

        url = '/api/v1/maksutiedot/'
        maksutieto_qs = Maksutieto.objects.all()

        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()

        id_list_order_id = list(maksutieto_qs.order_by('id').values_list('id', flat=True))
        resp_order_id = client.get(url)
        resp_id_list_order_id = _get_id_list_from_json(resp_order_id)
        self.assertListEqual(id_list_order_id, resp_id_list_order_id)

        with mock.patch('varda.viewsets.MaksutietoViewSet.queryset',
                        Maksutieto.objects.all().order_by('perheen_koko', 'id').distinct()):
            id_list_order_perheen_koko = list(maksutieto_qs.order_by('perheen_koko', 'id').values_list('id', flat=True))
            resp_order_perheen_koko = client.get(url)
            resp_id_list_order_perheen_koko = _get_id_list_from_json(resp_order_perheen_koko)
            self.assertListEqual(id_list_order_perheen_koko, resp_id_list_order_perheen_koko)

    def test_push_duplicate_paos_toiminta(self):
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/'
        }
        client = SetUpTestClient('tester3').client()
        resp = client.post('/api/v1/paos-toiminnat/', json.dumps(paos_toiminta), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'PT004', 'Combination of oma_organisaatio and paos_organisaatio fields should be unique.')

    def test_push_duplicate_paos_toiminta_2(self):
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/',
            'paos_toimipaikka': 'http://localhost:8000/api/v1/toimipaikat/5/'
        }
        client = SetUpTestClient('tester4').client()
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'PT005', 'Combination of oma_organisaatio and paos_toimipaikka fields should be unique.')

    def test_delete_paos_toiminta_with_toimija_and_push_correct_paos_toiminta_organisaatio(self):
        """
        Pre-requisite: Remove all paos-vakasuhteet from toimipaikka 5.
        """
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548817')
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka,
                                            varhaiskasvatuspaatos__lapsi__oma_organisaatio__organisaatio_oid='1.2.246.562.10.34683023489').delete()

        client = SetUpTestClient('tester3').client()
        vakajarjestaja_group = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should have view access to toimipaikka')

        paos_toiminta = PaosToiminta.objects.get(oma_organisaatio__organisaatio_oid='1.2.246.562.10.93957375488',
                                                 paos_organisaatio__organisaatio_oid='1.2.246.562.10.34683023489')
        delete_resp = client.delete(f'/api/v1/paos-toiminnat/{paos_toiminta.id}/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)
        # ObjectPermissionChecker caches results so we need to make sure we init a new one
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertFalse(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should no longer have view access to toimipaikka')
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)

        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/'
        }
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_delete_paostoiminta_with_toimija_view_access_stays_if_children_in_toimipaikka(self):
        client = SetUpTestClient('tester2').client()
        lapsi_json = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/lapset/', lapsi_json)
        assert_status_code(resp, status.HTTP_200_OK)  # lapsi is already created
        varhaiskasvatuspaatos = {
            'lapsi': json.loads(resp.content)['url'],
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm03',
            'tilapainen_vaka_kytkin': False,
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30',
            'lahdejarjestelma': '1',
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp3, status.HTTP_201_CREATED)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/5/',
            'varhaiskasvatuspaatos': varhaiskasvatuspaatos_url,
            'alkamis_pvm': '2018-10-01',
            'lahdejarjestelma': '1',
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, status.HTTP_201_CREATED)

        client = SetUpTestClient('tester3').client()
        vakajarjestaja_group = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
        toimipaikka = Toimipaikka.objects.get(id=5)
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should have view access to toimipaikka')
        delete_resp = client.delete('/api/v1/paos-toiminnat/1/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)
        # ObjectPermissionChecker caches results so we need to make sure we init a new one
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should still have view access to toimipaikka with children')

    def test_delete_paostoiminta_with_toimipaikka(self):
        """
        Pre-requisite: Remove all paos-vakasuhteet from toimipaikka 5.
        """
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548817')
        Varhaiskasvatussuhde.objects.filter(toimipaikka=toimipaikka,
                                            varhaiskasvatuspaatos__lapsi__oma_organisaatio__organisaatio_oid='1.2.246.562.10.34683023489').delete()

        client = SetUpTestClient('tester4').client()
        vakajarjestaja_group = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should have view access to toimipaikka')

        paos_toiminta = PaosToiminta.objects.get(oma_organisaatio__organisaatio_oid='1.2.246.562.10.34683023489',
                                                 paos_toimipaikka=toimipaikka)
        delete_resp = client.delete(f'/api/v1/paos-toiminnat/{paos_toiminta.id}/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)
        # ObjectPermissionChecker caches results so we need to make sure we init a new one
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertFalse(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should no longer have view access to toimipaikka')
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)

    def test_push_incorrect_paos_toiminta_organisaatio(self):
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/3/'
        }
        client = SetUpTestClient('tester3').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paos_organisaatio', 'PT008', 'paos_organisaatio must be kunta or kuntayhtyma.')

    def test_push_incorrect_paos_toiminta_toimipaikka(self):  # Not possible to vakajarjestaja's own toimipaikka
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/',
            'paos_toimipaikka': 'http://localhost:8000/api/v1/toimipaikat/2/'
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paos_toimipaikka', 'PT002', 'paos_toimipaikka cannot be in oma_organisaatio.')

    def test_push_incorrect_paos_toiminta_toimipaikka_2(self):
        paos_toimipaikka_obj = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.2935996863483')
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/',
            'paos_toimipaikka': f'http://localhost:8000/api/v1/toimipaikat/{paos_toimipaikka_obj.id}/'
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'paos_toimipaikka', 'PT003', 'jarjestamismuoto_koodi is not jm02 or jm03.')

    def test_push_correct_paos_toiminta_toimipaikka(self):
        paos_toiminta = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/',
            'paos_toimipaikka': 'http://localhost:8000/api/v1/toimipaikat/4/'
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)

    def test_paos_toiminta_voimassa_kytkin_organisation_first(self):
        """
        VARDA_PAAKAYTTAJA from vakajarjestaja ID=2 (paos_toiminta_organisaatio) adds permission for
        paos_organisaatio to use their toimipaikat
        """
        paos_toiminta_organisaatio = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/2/',
            'paos_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/'
        }
        client_tester3 = SetUpTestClient('tester3').client()
        resp_1 = client_tester3.delete('/api/v1/paos-toiminnat/1/')  # duplicate must be removed first
        assert_status_code(resp_1, status.HTTP_204_NO_CONTENT)

        """
        VARDA_PAAKAYTTAJA from vakajarjestaja ID=1 requests permission for VARDA_TALLENTAJA or VARDA_PALVELUKAYTTAJA
        to add PAOS-lapset to toimipaikka (ID=5)
        """
        paos_toiminta_toimipaikka = {
            'oma_organisaatio': 'http://localhost:8000/api/v1/vakajarjestajat/1/',
            'paos_toimipaikka': 'http://localhost:8000/api/v1/toimipaikat/5/'
        }
        client_tester4 = SetUpTestClient('tester4').client()
        resp_2 = client_tester4.delete('/api/v1/paos-toiminnat/2/')  # duplicate must be removed first
        assert_status_code(resp_2, status.HTTP_204_NO_CONTENT)

        paos_toiminta_organisaatio = json.dumps(paos_toiminta_organisaatio)
        resp_organisaatio = client_tester3.post('/api/v1/paos-toiminnat/', paos_toiminta_organisaatio, content_type='application/json')
        resp_voimassa_kytkin = client_tester3.get('/api/v1/paos-oikeudet/1/')
        resp_voimassa_kytkin = json.loads(resp_voimassa_kytkin.content)['voimassa_kytkin']
        assert_status_code(resp_organisaatio, status.HTTP_201_CREATED)
        self.assertEqual(resp_voimassa_kytkin, False)

        paos_toiminta_toimipaikka = json.dumps(paos_toiminta_toimipaikka)
        resp_toimipaikka = client_tester4.post('/api/v1/paos-toiminnat/', paos_toiminta_toimipaikka, content_type='application/json')
        resp_voimassa_kytkin = client_tester4.get('/api/v1/paos-oikeudet/1/')
        resp_voimassa_kytkin = json.loads(resp_voimassa_kytkin.content)['voimassa_kytkin']
        assert_status_code(resp_toimipaikka, status.HTTP_201_CREATED)
        self.assertEqual(resp_voimassa_kytkin, True)

        resp_organisaatio_id = json.loads(resp_organisaatio.content)['id']
        path = '/api/v1/paos-toiminnat/' + str(resp_organisaatio_id) + '/'
        voimassa_kytkin_organisaatio = client_tester3.get('/api/v1/paos-oikeudet/1/')
        resp_voimassa_kytkin = json.loads(voimassa_kytkin_organisaatio.content)['voimassa_kytkin']
        self.assertEqual(resp_voimassa_kytkin, True)

        """
        VARDA_PAAKAYTTAJA from vakajarjestaja ID=2 removes permission to add lapset to their toimipaikat
        """
        remove_voimassa_kytkin = client_tester3.delete(path)
        assert_status_code(remove_voimassa_kytkin, status.HTTP_204_NO_CONTENT)

        """
        Verify that voimassa_kytkin returns to false because of the removal of the organisation permission
        """
        path = '/api/v1/paos-oikeudet/1/'
        resp_voimassa_kytkin = client_tester4.get(path)
        resp_voimassa_kytkin = json.loads(resp_voimassa_kytkin.content)['voimassa_kytkin']
        self.assertEqual(resp_voimassa_kytkin, False)

    def test_paos_toiminta_filter(self):
        client = SetUpTestClient('tester4').client()

        resp_paos_toiminnat = client.get('/api/v1/paos-toiminnat/?oma_organisaatio=1')
        resp_paos_toiminnat_count = json.loads(resp_paos_toiminnat.content)['count']
        self.assertEqual(resp_paos_toiminnat_count, 2)

        resp_paos_toiminnat = client.get('/api/v1/paos-toiminnat/?oma_organisaatio=2')
        resp_paos_toiminnat_count = json.loads(resp_paos_toiminnat.content)['count']
        self.assertEqual(resp_paos_toiminnat_count, 0)

        resp_paos_toiminnat = client.get('/api/v1/paos-toiminnat/?paos_organisaatio=2')
        resp_paos_toiminnat_count = json.loads(resp_paos_toiminnat.content)['count']
        self.assertEqual(resp_paos_toiminnat_count, 0)

        resp_paos_toiminnat = client.get('/api/v1/paos-toiminnat/?paos_toimipaikka=5')
        resp_paos_toiminnat_count = json.loads(resp_paos_toiminnat.content)['count']
        self.assertEqual(resp_paos_toiminnat_count, 1)

        resp_paos_toiminnat = client.get('/api/v1/paos-toiminnat/?paos_toimipaikka=3')
        resp_paos_toiminnat_count = json.loads(resp_paos_toiminnat.content)['count']
        self.assertEqual(resp_paos_toiminnat_count, 0)

    def test_nested_paos_toimipaikat_filter(self):
        client = SetUpTestClient('tester4').client()
        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?toimija_nimi=Tester')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 1)

        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?toimija_nimi=Espoo')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 0)

        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?toimipaikka_nimi=Espoo')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 2)

        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?toimipaikka_nimi=JokuIhanMuu')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 0)

        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?organisaatio_oid=JokuIhanMuu')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 0)

        resp_paos_toimipaikat = client.get('/api/v1/vakajarjestajat/1/paos-toimipaikat/?organisaatio_oid=1.2.246.562.10.9395737548817')
        resp_paos_toimipaikat_count = json.loads(resp_paos_toimipaikat.content)['count']
        self.assertEqual(resp_paos_toimipaikat_count, 1)

    def test_paos_oikeus_filter(self):
        client = SetUpTestClient('tester4').client()
        resp_paos_oikeus = client.get('/api/v1/paos-oikeudet/?jarjestaja_kunta_organisaatio=1')
        resp_paos_oikeus_count = json.loads(resp_paos_oikeus.content)['count']
        self.assertEqual(resp_paos_oikeus_count, 2)

        resp_paos_oikeus = client.get('/api/v1/paos-oikeudet/?tuottaja_organisaatio=1')
        resp_paos_oikeus_count = json.loads(resp_paos_oikeus.content)['count']
        self.assertEqual(resp_paos_oikeus_count, 0)

    def test_paos_oikeus_change_tallentaja_organisaatio_correct_format(self):
        client_tester4 = SetUpTestClient('tester4').client()
        tallentaja_organisaatio = {
            'tallentaja_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        resp_paos_oikeus_tallentaja_organisaatio = json.loads(resp_paos_oikeus.content)['tallentaja_organisaatio']
        assert_status_code(resp_paos_oikeus, status.HTTP_200_OK)
        self.assertEqual(resp_paos_oikeus_tallentaja_organisaatio, 'http://testserver/api/v1/vakajarjestajat/2/')

    def test_paos_oikeus_change_tallentaja_organisaatio_already_is_same(self):
        client_tester4 = SetUpTestClient('tester4').client()
        tallentaja_organisaatio = {'tallentaja_organisaatio': '/api/v1/vakajarjestajat/1/'}
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        assert_status_code(resp_paos_oikeus, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_paos_oikeus, 'tallentaja_organisaatio', 'PO002',
                                'tallentaja_organisaatio is already the same as requested.')

    def test_paos_oikeus_change_tallentaja_organisaatio_not_either_organisation(self):
        client_tester4 = SetUpTestClient('tester4').client()
        tallentaja_organisaatio = {'tallentaja_organisaatio': '/api/v1/vakajarjestajat/4/'}
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        assert_status_code(resp_paos_oikeus, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_paos_oikeus, 'tallentaja_organisaatio', 'PO001',
                                'tallentaja_organisaatio must be either jarjestaja_kunta_organisaatio or tuottaja_organisaatio.')

    def test_push_incorrect_puhelinnumero(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')
        puhelinnumero_list = ['+359400987654', '+35850123123.']
        client = SetUpTestClient('tester2').client()

        for puhelinnumero in puhelinnumero_list:
            patch_body = {
                'puhelinnumero': puhelinnumero
            }
            resp = client.patch(f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/', patch_body)
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST, puhelinnumero)
            assert_validation_error(resp, 'puhelinnumero', 'MI006', 'Not a valid Finnish phone number.', puhelinnumero)

    def test_api_delete_toimipaikka_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/toimipaikat/1/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def test_api_delete_toimipaikka_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.delete('/api/v1/toimipaikat/3/')
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

    def test_api_delete_lapsi_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/lapset/1/')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'LA003', 'Cannot delete Lapsi. There are Maksutieto objects referencing it that need to be deleted first.')

    def test_api_delete_lapsi_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.delete('/api/v1/lapset/4/')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'LA004', 'Cannot delete Lapsi. There are objects referencing it that need to be deleted first.')

    def test_api_delete_lapsi_3(self):
        Huoltajuussuhde.objects.get(id=5).delete()  # This is required before lapsi can be removed.
        client = SetUpTestClient('tester2').client()
        client.delete('/api/v1/varhaiskasvatussuhteet/1:kela_testing_jm03/')
        client.delete('/api/v1/varhaiskasvatussuhteet/1:testing-varhaiskasvatussuhde4/')
        client.delete('/api/v1/varhaiskasvatuspaatokset/1:testing-varhaiskasvatuspaatos4/')
        resp = client.delete('/api/v1/lapset/1:testing-lapsi4/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)

    def test_api_push_overlapping_varhaiskasvatuspaatos(self):
        client = SetUpTestClient('tester10').client()

        henkilo_oid = '1.2.246.562.24.47279942650'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        lapsi_tunniste = 'testing-lapsi'
        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.57294396385',
            'lahdejarjestelma': '1',
            'tunniste': lapsi_tunniste
        }
        resp_lapsi = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi, status.HTTP_201_CREATED)

        varhaiskasvatuspaatos = {
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': 20,
            'jarjestamismuoto_koodi': 'jm01',
            'vuorohoito_kytkin': False,
            'tilapainen_vaka_kytkin': False,
            'kokopaivainen_vaka_kytkin': True,
            'paivittainen_vaka_kytkin': True,
            'lahdejarjestelma': '1',
        }

        test_cases_list = ((('2021-01-01', None), ('2021-01-01', None), ('2021-01-01', None), ('2021-01-01', None),),
                           (('2020-01-01', '2021-01-01',), ('2021-01-01', None), ('2021-01-01', None), ('2021-01-01', None),),
                           (('2021-01-01', None), ('2021-01-01', None), ('2020-08-01', '2020-12-31'), ('2020-06-01', '2020-07-31'),
                            ('2019-08-01', '2020-05-31'), ('2020-01-07', None), ('2020-12-01', None)),
                           (('2021-01-01', '2021-01-01'), ('2021-01-01', '2021-01-01'),
                            ('2021-01-01', '2021-01-01'), ('2021-01-01', '2021-01-01'),),
                           (('2020-12-01', None), ('2021-01-01', '2021-01-01'), ('2021-01-01', '2021-01-01'), ('2020-07-01', None),),)

        for test_cases in test_cases_list:
            vakapaatos_id_list = []
            for index, test_case in enumerate(test_cases):
                varhaiskasvatuspaatos['hakemus_pvm'] = test_case[0]
                varhaiskasvatuspaatos['alkamis_pvm'] = test_case[0]
                varhaiskasvatuspaatos['paattymis_pvm'] = test_case[1]
                varhaiskasvatuspaatos['tuntimaara_viikossa'] += 0.5

                resp_post = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos),
                                        content_type='application/json')

                if index == len(test_cases) - 1:
                    # Last one
                    assert_status_code(resp_post, status.HTTP_400_BAD_REQUEST)
                    assert_validation_error(resp_post, 'errors', 'VP011',
                                            'Lapsi already has 3 overlapping Varhaiskasvatuspaatos on the given date range.')
                else:
                    assert_status_code(resp_post, status.HTTP_201_CREATED)
                    vakapaatos_id_list.append(json.loads(resp_post.content)['id'])

            for vakapaatos_id in vakapaatos_id_list:
                resp_delete = client.delete(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/')
                assert_status_code(resp_delete, status.HTTP_204_NO_CONTENT)

    def test_varhaiskasvatuspaatos_not_unique(self):
        client = SetUpTestClient('tester2').client()
        vakapaatos = {
            'lapsi': '/api/v1/lapset/3/',
            'tuntimaara_viikossa': 40,
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2018-09-15',
            'alkamis_pvm': '2018-10-20',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': '1',
        }

        resp_1 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        resp_2 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'errors', 'VP015', 'Identical Varhaiskasvatuspaatos already exists.')

        vakapaatos['alkamis_pvm'] = '2018-10-21'
        resp_3 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_3, status.HTTP_201_CREATED)
        vakapaatos_id = json.loads(resp_3.content)['id']

        resp_4 = client.patch(f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_id}/', {'alkamis_pvm': '2018-10-20'})
        assert_status_code(resp_4, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_4, 'errors', 'VP015', 'Identical Varhaiskasvatuspaatos already exists.')

    def test_api_push_too_many_varhaiskasvatussuhde(self):
        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'varhaiskasvatuspaatos': 'http://testserver/api/v1/varhaiskasvatuspaatokset/10/',
            'alkamis_pvm': '2020-05-01',
            'lahdejarjestelma': '1',
        }
        client = SetUpTestClient('tester').client()
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'VS013',
                                'Lapsi already has 3 overlapping Varhaiskasvatussuhde on the given date range.')

    @patch('varda.viewsets.datetime')
    def test_api_get_vakajarjestaja_yhteenveto(self, mock_datetime):
        # Freeze date used in reporting
        mock_datetime.datetime.now.return_value = datetime(2020, 9, 1)

        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/vakajarjestajat/2/yhteenveto/')
        accepted_response = {
            'vakajarjestaja_nimi': 'Tester organisaatio',
            'lapset_lkm': 5,
            'lapset_vakapaatos_voimassaoleva': 6,
            'lapset_vakasuhde_voimassaoleva': 5,
            'lapset_vuorohoidossa': 0,
            'lapset_palveluseteli_ja_ostopalvelu': 3,
            'lapset_maksutieto_voimassaoleva': 3,
            'toimipaikat_voimassaolevat': 4,
            'toimipaikat_paattyneet': 0,
            'toimintapainotukset_maara': 2,
            'kielipainotukset_maara': 2,
            'tyontekijat_lkm': 1,
            'palvelussuhteet_voimassaoleva': 1,
            'palvelussuhteet_maaraaikaiset': 0,
            'varhaiskasvatusalan_tutkinnot': 1,
            'tyoskentelypaikat_kelpoiset': 2,
            'taydennyskoulutukset_kuluva_vuosi': 0,
            'tilapainen_henkilosto_maara_kuluva_vuosi': None,
            'tilapainen_henkilosto_tunnit_kuluva_vuosi': None
        }
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content), accepted_response)

    """ organisaatiopalvelu-integraatio
    def test_api_multiple_asiointikieli(self):
        toimipaikka = {
            'vakajarjestaja': 'http://testserver/api/v1/vakajarjestajat/1/',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI', 'SV', 'EN'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2018-01-01'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)  # TODO: Change this when Org.palvelu-mocking is done! (Original: 201)
    """

    def test_api_filter_asiointikieli_1(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/?asiointikieli_koodi=SV')
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_filter_asiointikieli_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/?asiointikieli_koodi=SE')
        self.assertEqual(json.loads(resp.content)['count'], 0)

    def test_api_filter_jarjestamismuotokoodi_1(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/?jarjestamismuoto_koodi=jm01')
        self.assertEqual(json.loads(resp.content)['count'], 3)

    def test_api_filter_jarjestamismuotokoodi_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/?jarjestamismuoto_koodi=jm06')
        self.assertEqual(json.loads(resp.content)['count'], 0)

    @mock.patch('varda.organisaatiopalvelu.check_if_toimipaikka_exists_by_name',
                mock_check_if_toimipaikka_exists_by_name)
    @mock.patch('varda.organisaatiopalvelu.create_organisaatio',
                mock_create_organisaatio)
    def test_api_toimipaikka_add_valid(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        toimipaikka = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
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

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_201_CREATED)

    @mock.patch('varda.organisaatiopalvelu.check_if_toimipaikka_exists_by_name',
                mock_check_if_toimipaikka_exists_by_name)
    def test_api_toimipaikka_add_duplicate_name(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        toimipaikka = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'nimi': 'Tester2 toimipaikka',
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

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'TP001', 'Combination of nimi and vakajarjestaja fields should be unique.')

    def test_api_vakapaatos_tilapainen_vaka_kytkin_required(self):
        lapsi_kunta = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.49084901392',
                                        vakatoimija__organisaatio_oid='1.2.246.562.10.34683023489')
        vakapaatos_kunta = {
            'lapsi': f'/api/v1/lapset/{lapsi_kunta.id}/',
            'vuorohoito_kytkin': False,
            'paivittainen_vaka_kytkin': True,
            'kokopaivainen_vaka_kytkin': True,
            'tuntimaara_viikossa': '39.0',
            'jarjestamismuoto_koodi': 'jm01',
            'alkamis_pvm': '2020-12-01',
            'hakemus_pvm': '2020-12-01',
            'lahdejarjestelma': '1',
        }

        client_kunta = SetUpTestClient('tester2').client()

        resp_kunta_1 = client_kunta.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_kunta)
        assert_status_code(resp_kunta_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_kunta_1, 'tilapainen_vaka_kytkin', 'VP014',
                                'tilapainen_vaka_kytkin is required for kunnallinen Lapsi.')

        vakapaatos_kunta['tilapainen_vaka_kytkin'] = False
        resp_kunta_2 = client_kunta.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_kunta)
        assert_status_code(resp_kunta_2, status.HTTP_201_CREATED)

        lapsi_yksityinen = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.47279942650',
                                             vakatoimija__organisaatio_oid='1.2.246.562.10.93957375488')
        vakapaatos_yksityinen = {
            'lapsi': f'/api/v1/lapset/{lapsi_yksityinen.id}/',
            'vuorohoito_kytkin': False,
            'paivittainen_vaka_kytkin': True,
            'kokopaivainen_vaka_kytkin': True,
            'tuntimaara_viikossa': '39.0',
            'jarjestamismuoto_koodi': 'jm04',
            'alkamis_pvm': '2020-12-01',
            'hakemus_pvm': '2020-12-01',
            'lahdejarjestelma': '1',
        }

        client_yksityinen = SetUpTestClient('tester').client()
        resp_yksityinen = client_yksityinen.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_yksityinen)
        assert_status_code(resp_yksityinen, status.HTTP_201_CREATED)

    def test_api_toiminnallinen_painotus_update_kytkin(self):
        toimipaikka_oid = '1.2.246.562.10.2565458382544'
        toimipaikka_qs = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_oid)
        toimipaikka_id = toimipaikka_qs.first().id

        self.assertFalse(toimipaikka_qs.first().toiminnallisetpainotukset.exists())
        self.assertFalse(toimipaikka_qs.first().toiminnallinenpainotus_kytkin)

        client = SetUpTestClient('tester10').client()

        painotus_json_1 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        resp_1 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_json_1)
        painotus_1_id = json.loads(resp_1.content)['id']
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        self.assertTrue(toimipaikka_qs.first().toiminnallinenpainotus_kytkin)

        toimipaikka_obj = toimipaikka_qs.first()
        toimipaikka_obj.toiminnallinenpainotus_kytkin = False
        toimipaikka_obj.save()

        painotus_update_json = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_2 = client.put(f'/api/v1/toiminnallisetpainotukset/{painotus_1_id}/', painotus_update_json)
        assert_status_code(resp_2, status.HTTP_200_OK)

        painotus_json_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'toimintapainotus_koodi': 'TP02',
            'alkamis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        resp_3 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_json_2)
        painotus_2_id = json.loads(resp_3.content)['id']
        assert_status_code(resp_3, status.HTTP_201_CREATED)

        resp_4 = client.delete(f'/api/v1/toiminnallisetpainotukset/{painotus_2_id}/')
        assert_status_code(resp_4, status.HTTP_204_NO_CONTENT)
        self.assertTrue(toimipaikka_qs.first().toiminnallinenpainotus_kytkin)

        resp_5 = client.delete(f'/api/v1/toiminnallisetpainotukset/{painotus_1_id}/')
        assert_status_code(resp_5, status.HTTP_204_NO_CONTENT)
        self.assertFalse(toimipaikka_qs.first().toiminnallinenpainotus_kytkin)

    def test_api_kielipainotus_update_kytkin(self):
        toimipaikka_oid = '1.2.246.562.10.2565458382544'
        toimipaikka_qs = Toimipaikka.objects.filter(organisaatio_oid=toimipaikka_oid)
        toimipaikka_id = toimipaikka_qs.first().id

        self.assertFalse(toimipaikka_qs.first().kielipainotukset.exists())
        self.assertFalse(toimipaikka_qs.first().kielipainotus_kytkin)

        client = SetUpTestClient('tester10').client()

        painotus_json_1 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        resp_1 = client.post('/api/v1/kielipainotukset/', painotus_json_1)
        painotus_1_id = json.loads(resp_1.content)['id']
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        self.assertTrue(toimipaikka_qs.first().kielipainotus_kytkin)

        toimipaikka_obj = toimipaikka_qs.first()
        toimipaikka_obj.kielipainotus_kytkin = False
        toimipaikka_obj.save()

        painotus_update_json = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_2 = client.put(f'/api/v1/kielipainotukset/{painotus_1_id}/', painotus_update_json)
        assert_status_code(resp_2, status.HTTP_200_OK)

        painotus_json_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_id}/',
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-01',
            'lahdejarjestelma': '1',
        }
        resp_3 = client.post('/api/v1/kielipainotukset/', painotus_json_2)
        painotus_2_id = json.loads(resp_3.content)['id']
        assert_status_code(resp_3, status.HTTP_201_CREATED)

        resp_4 = client.delete(f'/api/v1/kielipainotukset/{painotus_2_id}/')
        assert_status_code(resp_4, status.HTTP_204_NO_CONTENT)
        self.assertTrue(toimipaikka_qs.first().kielipainotus_kytkin)

        resp_5 = client.delete(f'/api/v1/kielipainotukset/{painotus_1_id}/')
        assert_status_code(resp_5, status.HTTP_204_NO_CONTENT)
        self.assertFalse(toimipaikka_qs.first().kielipainotus_kytkin)

    @mock.patch('varda.organisaatiopalvelu.check_if_toimipaikka_exists_by_name',
                mock_check_if_toimipaikka_exists_by_name)
    def test_api_toimipaikka_lahdejarjestelma_tunniste_not_unique(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        toimipaikka = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'nimi': 'Testitoimipaikka',
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
            'tunniste': 'testing-toimipaikka1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    @mock.patch('varda.organisaatiopalvelu.check_if_toimipaikka_exists_by_name',
                mock_check_if_toimipaikka_exists_by_name)
    def test_api_toimipaikka_missing_lahdejarjestelma(self):
        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid='1.2.246.562.10.34683023489')

        toimipaikka = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{vakajarjestaja.id}/',
            'nimi': 'Testitoimipaikka',
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
            'tunniste': 'testing-toimipaikka',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_toimipaikka_lahdejarjestelma_tunniste_get_put_patch(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-toimipaikka2'
        new_tunniste = 'testing-toimipaikka'

        toimipaikka = Toimipaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)
        toimipaikka_url = f'/api/v1/toimipaikat/{lahdejarjestelma}:{tunniste}/'

        client = SetUpTestClient('tester2').client()
        resp_toimipaikka_get = client.get(toimipaikka_url)
        assert_status_code(resp_toimipaikka_get, status.HTTP_200_OK)
        self.assertEqual(toimipaikka.id, json.loads(resp_toimipaikka_get.content)['id'])

        resp_toimipaikka_get_404 = client.get('/api/v1/toimipaikat/5:no/')
        assert_status_code(resp_toimipaikka_get_404, status.HTTP_404_NOT_FOUND)

        toimipaikka_put = {
            'vakajarjestaja': f'/api/v1/vakajarjestajat/{toimipaikka.vakajarjestaja.id}/',
            'nimi': 'Testitoimipaikka',
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
            'tunniste': new_tunniste,
        }
        resp_toimipaikka_put = client.put(toimipaikka_url, toimipaikka_put)
        assert_status_code(resp_toimipaikka_put, status.HTTP_200_OK)

        toimipaikka_patch = {
            'tunniste': tunniste
        }
        toimipaikka_url_patch = f'/api/v1/toimipaikat/{lahdejarjestelma}:{new_tunniste}/'
        resp_toimipaikka_patch = client.patch(toimipaikka_url_patch, toimipaikka_patch)
        assert_status_code(resp_toimipaikka_patch, status.HTTP_200_OK)

    def test_api_toiminnallinen_painotus_lahdejarjestelma_tunniste_not_unique(self):
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        painotus = {
            'toimipaikka_oid': toimipaikka_oid,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-toiminnallinenpainotus1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', painotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_toiminnallinen_painotus_missing_lahdejarjestelma(self):
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        painotus = {
            'toimipaikka_oid': toimipaikka_oid,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'tunniste': 'testing-toiminnallinenpainotus',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', painotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_toiminnallinen_painotus_toimipaikka_tunniste(self):
        lahdejarjestelma = '1'
        toimipaikka_tunniste = 'testing-toimipaikka2'

        toimipaikka = Toimipaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=toimipaikka_tunniste)

        painotus_1 = {
            'toimipaikka_tunniste': toimipaikka_tunniste,
            'toimintapainotus_koodi': 'TP02',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_1_json = json.loads(resp_1.content)
        painotus_object = ToiminnallinenPainotus.objects.get(id=resp_1_json['id'])
        self.assertEqual(painotus_object.toimipaikka.id, toimipaikka.id)
        self.assertEqual(resp_1_json['toimipaikka_oid'], toimipaikka.organisaatio_oid)

        painotus_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka.id}/',
            'toimintapainotus_koodi': 'TP03',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_2 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp_2.content)['toimipaikka_tunniste'], toimipaikka_tunniste)

        painotus_3 = {
            'toimipaikka_tunniste': 'no',
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_3 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'toimipaikka_tunniste', 'RF003', 'Could not find matching object.')

    def test_api_toiminnallinen_painotus_toimipaikka_related_match(self):
        toimipaikka_1 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')
        toimipaikka_2 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548811')
        toimipaikka_3 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548817')
        lahdejarjestelma = '1'

        painotus_1 = {
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_2.organisaatio_oid,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_1 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_1)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_3.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_2 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_3 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_3.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_1.organisaatio_oid,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_3 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_4 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_1.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_1.organisaatio_oid,
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_4 = client.post('/api/v1/toiminnallisetpainotukset/', painotus_4)
        assert_status_code(resp_4, status.HTTP_201_CREATED)

    def test_api_toiminnallinen_painotus_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-toiminnallinenpainotus98'
        new_tunniste = 'testing-toiminnallinenpainotus99'

        client = SetUpTestClient('tester2').client()
        painotus_post = {
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_painotus_post = client.post('/api/v1/toiminnallisetpainotukset/', painotus_post)
        assert_status_code(resp_painotus_post, status.HTTP_201_CREATED)
        painotus = ToiminnallinenPainotus.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        painotus_url = f'/api/v1/toiminnallisetpainotukset/{lahdejarjestelma}:{tunniste}/'
        resp_painotus_get = client.get(painotus_url)
        assert_status_code(resp_painotus_get, status.HTTP_200_OK)
        self.assertEqual(painotus.id, json.loads(resp_painotus_get.content)['id'])

        resp_painotus_get_404 = client.get('/api/v1/toiminnallisetpainotukset/5:no/')
        assert_status_code(resp_painotus_get_404, status.HTTP_404_NOT_FOUND)

        painotus_put = {
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'toimintapainotus_koodi': 'TP01',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_painotus_put = client.put(painotus_url, painotus_put)
        assert_status_code(resp_painotus_put, status.HTTP_200_OK)

        painotus_patch = {
            'tunniste': tunniste
        }
        painotus_url_patch = f'/api/v1/toiminnallisetpainotukset/{lahdejarjestelma}:{new_tunniste}/'
        resp_painotus_patch = client.patch(painotus_url_patch, painotus_patch)
        assert_status_code(resp_painotus_patch, status.HTTP_200_OK)

        resp_painotus_delete = client.delete(painotus_url)
        assert_status_code(resp_painotus_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(ToiminnallinenPainotus.objects.filter(id=painotus.id).exists())

    def test_api_kielipainotus_lahdejarjestelma_tunniste_not_unique(self):
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        painotus = {
            'toimipaikka_oid': toimipaikka_oid,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-kielipainotus1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/kielipainotukset/', painotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_kielipainotus_missing_lahdejarjestelma(self):
        toimipaikka_oid = '1.2.246.562.10.9395737548815'
        painotus = {
            'toimipaikka_oid': toimipaikka_oid,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'tunniste': 'testing-kielipainotus1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/kielipainotukset/', painotus)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_kielipainotus_toimipaikka_tunniste(self):
        lahdejarjestelma = '1'
        toimipaikka_tunniste = 'testing-toimipaikka2'

        toimipaikka = Toimipaikka.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=toimipaikka_tunniste)

        painotus_1 = {
            'toimipaikka_tunniste': toimipaikka_tunniste,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/kielipainotukset/', painotus_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_1_json = json.loads(resp_1.content)
        painotus_object = KieliPainotus.objects.get(id=resp_1_json['id'])
        self.assertEqual(painotus_object.toimipaikka.id, toimipaikka.id)
        self.assertEqual(resp_1_json['toimipaikka_oid'], toimipaikka.organisaatio_oid)

        painotus_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka.id}/',
            'kielipainotus_koodi': 'EN',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_2 = client.post('/api/v1/kielipainotukset/', painotus_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp_2.content)['toimipaikka_tunniste'], toimipaikka_tunniste)

        painotus_3 = {
            'toimipaikka_tunniste': 'no',
            'kielipainotus_koodi': 'FR',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
        }
        resp_3 = client.post('/api/v1/kielipainotukset/', painotus_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'toimipaikka_tunniste', 'RF003', 'Could not find matching object.')

    def test_api_kielipainotus_toimipaikka_related_match(self):
        toimipaikka_1 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')
        toimipaikka_2 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548811')
        toimipaikka_3 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548817')
        lahdejarjestelma = '1'

        painotus_1 = {
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_2.organisaatio_oid,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_1 = client.post('/api/v1/kielipainotukset/', painotus_1)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_2 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_3.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_2 = client.post('/api/v1/kielipainotukset/', painotus_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_3 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_3.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_1.organisaatio_oid,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_3 = client.post('/api/v1/kielipainotukset/', painotus_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        painotus_4 = {
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_1.id}/',
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'toimipaikka_oid': toimipaikka_1.organisaatio_oid,
            'kielipainotus_koodi': 'SV',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_4 = client.post('/api/v1/kielipainotukset/', painotus_4)
        assert_status_code(resp_4, status.HTTP_201_CREATED)

    def test_api_kielipainotus_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-keilipainotus98'
        new_tunniste = 'testing-kielipainotus99'

        client = SetUpTestClient('tester2').client()
        painotus_post = {
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_painotus_post = client.post('/api/v1/kielipainotukset/', painotus_post)
        assert_status_code(resp_painotus_post, status.HTTP_201_CREATED)
        painotus = KieliPainotus.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        painotus_url = f'/api/v1/kielipainotukset/{lahdejarjestelma}:{tunniste}/'
        resp_painotus_get = client.get(painotus_url)
        assert_status_code(resp_painotus_get, status.HTTP_200_OK)
        self.assertEqual(painotus.id, json.loads(resp_painotus_get.content)['id'])

        resp_painotus_get_404 = client.get('/api/v1/kielipainotukset/5:no/')
        assert_status_code(resp_painotus_get_404, status.HTTP_404_NOT_FOUND)

        painotus_put = {
            'toimipaikka_oid': '1.2.246.562.10.9395737548815',
            'kielipainotus_koodi': 'FI',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_painotus_put = client.put(painotus_url, painotus_put)
        assert_status_code(resp_painotus_put, status.HTTP_200_OK)

        painotus_patch = {
            'tunniste': tunniste
        }
        painotus_url_patch = f'/api/v1/kielipainotukset/{lahdejarjestelma}:{new_tunniste}/'
        resp_painotus_patch = client.patch(painotus_url_patch, painotus_patch)
        assert_status_code(resp_painotus_patch, status.HTTP_200_OK)

        resp_painotus_delete = client.delete(painotus_url)
        assert_status_code(resp_painotus_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(KieliPainotus.objects.filter(id=painotus.id).exists())

    def test_api_lapsi_lahdejarjestelma_tunniste_not_unique(self):
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        henkilo_oid = '1.2.246.562.24.4338669286936'
        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-lapsi1',
        }

        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_lapsi_missing_lahdejarjestelma(self):
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        henkilo_oid = '1.2.246.562.24.4338669286936'
        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'tunniste': 'testing-lapsi',
        }

        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_lapsi_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        new_lahdejarjestelma = '2'
        tunniste = 'testing-lapsi98'
        new_tunniste = 'testing-lapsi99'

        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        henkilo_oid = '1.2.246.562.24.4338669286936'

        client = SetUpTestClient('tester2').client()
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)
        lapsi_post = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_lapsi_post = client.post('/api/v1/lapset/', lapsi_post)
        assert_status_code(resp_lapsi_post, status.HTTP_201_CREATED)
        lapsi = Lapsi.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        lapsi_url = f'/api/v1/lapset/{lahdejarjestelma}:{tunniste}/'
        resp_lapsi_get = client.get(lapsi_url)
        assert_status_code(resp_lapsi_get, status.HTTP_200_OK)
        self.assertEqual(lapsi.id, json.loads(resp_lapsi_get.content)['id'])

        resp_lapsi_get_404 = client.get('/api/v1/lapset/5:no/')
        assert_status_code(resp_lapsi_get_404, status.HTTP_404_NOT_FOUND)

        lapsi_put = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'lahdejarjestelma': new_lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_lapsi_put = client.put(lapsi_url, lapsi_put)
        assert_status_code(resp_lapsi_put, status.HTTP_200_OK)

        lapsi_patch = {
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        lapsi_url_patch = f'/api/v1/lapset/{new_lahdejarjestelma}:{new_tunniste}/'
        resp_lapsi_patch = client.patch(lapsi_url_patch, lapsi_patch)
        assert_status_code(resp_lapsi_patch, status.HTTP_200_OK)

        resp_lapsi_delete = client.delete(lapsi_url)
        assert_status_code(resp_lapsi_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Lapsi.objects.filter(id=lapsi.id).exists())

    def test_api_vakapaatos_lahdejarjestelma_tunniste_not_unique(self):
        lapsi_tunniste = 'testing-lapsi3'
        vakapaatos = {
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': '1',
            'tunniste': 'testing-varhaiskasvatuspaatos1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_vakapaatos_missing_lahdejarjestelma(self):
        lahdejarjestelma = '1'
        lapsi_tunniste = 'testing-lapsi3'
        lapsi = Lapsi.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=lapsi_tunniste)

        vakapaatos = {
            'lapsi': f'/api/v1/lapset/{lapsi.id}/',
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'tunniste': 'testing-varhaiskasvatuspaatos',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_vakapaatos_lapsi_tunniste(self):
        lahdejarjestelma = '1'
        lapsi_tunniste = 'testing-lapsi3'

        lapsi = Lapsi.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=lapsi_tunniste)

        vakapaatos_1 = {
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_1_json = json.loads(resp_1.content)
        vakapaatos_object = Varhaiskasvatuspaatos.objects.get(id=resp_1_json['id'])
        self.assertEqual(vakapaatos_object.lapsi.id, lapsi.id)

        vakapaatos_2 = {
            'lapsi': f'/api/v1/lapset/{lapsi.id}/',
            'tuntimaara_viikossa': '38.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': 'testing-varhaiskasvatuspaatos',
        }
        resp_2 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp_2.content)['lapsi_tunniste'], lapsi_tunniste)

        vakapaatos_3 = {
            'lapsi_tunniste': 'no',
            'tuntimaara_viikossa': '39.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
        }
        resp_3 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'lapsi_tunniste', 'RF003', 'Could not find matching object.')

    def test_api_vakapaatos_lapsi_related_match(self):
        lapsi_1 = Lapsi.objects.get(tunniste='testing-lapsi3')
        lapsi_2 = Lapsi.objects.get(tunniste='testing-lapsi6')
        lahdejarjestelma = '1'

        vakapaatos_1 = {
            'lapsi': f'/api/v1/lapset/{lapsi_1.id}/',
            'lapsi_tunniste': lapsi_2.tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': 'testing-varhaiskasvatuspaatos',
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_1)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'lapsi_tunniste', 'RF004', 'Differs from parent field.')

        vakapaatos_2 = {
            'lapsi': f'/api/v1/lapset/{lapsi_1.id}/',
            'lapsi_tunniste': lapsi_1.tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': 'testing-varhaiskasvatuspaatos',
        }

        resp_2 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)

    def test_api_vakapaatos_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-varhaiskasvatuspaatos98'
        new_tunniste = 'testing-varhaiskasvatuspaatos99'

        lapsi_tunniste = 'testing-lapsi3'

        client = SetUpTestClient('tester2').client()
        vakapaatos_post = {
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_vakapaatos_post = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos_post)
        assert_status_code(resp_vakapaatos_post, status.HTTP_201_CREATED)
        vakapaatos = Varhaiskasvatuspaatos.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        vakapaatos_url = f'/api/v1/varhaiskasvatuspaatokset/{lahdejarjestelma}:{tunniste}/'
        resp_vakapaatos_get = client.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_get, status.HTTP_200_OK)
        self.assertEqual(vakapaatos.id, json.loads(resp_vakapaatos_get.content)['id'])

        resp_vakapaatos_get_404 = client.get('/api/v1/varhaiskasvatuspaatokset/5:no/')
        assert_status_code(resp_vakapaatos_get_404, status.HTTP_404_NOT_FOUND)

        vakapaatos_put = {
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_vakapaatos_put = client.put(vakapaatos_url, vakapaatos_put)
        assert_status_code(resp_vakapaatos_put, status.HTTP_200_OK)

        vakapaatos_patch = {
            'tunniste': tunniste
        }
        vakapaatos_url_patch = f'/api/v1/varhaiskasvatuspaatokset/{lahdejarjestelma}:{new_tunniste}/'
        resp_vakapaatos_patch = client.patch(vakapaatos_url_patch, vakapaatos_patch)
        assert_status_code(resp_vakapaatos_patch, status.HTTP_200_OK)

        resp_vakapaatos_delete = client.delete(vakapaatos_url)
        assert_status_code(resp_vakapaatos_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Varhaiskasvatuspaatos.objects.filter(id=vakapaatos.id).exists())

    def test_api_vakasuhde_lahdejarjestelma_tunniste_not_unique(self):
        vakapaatos_tunniste = 'testing-varhaiskasvatuspaatos2'
        toimipaikka_oid = '1.2.246.562.10.9395737548810'

        vakasuhde = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'toimipaikka_oid': toimipaikka_oid,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-varhaiskasvatussuhde1',
        }

        client = SetUpTestClient('tester5').client()
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_vakasuhde_missing_lahdejarjestelma(self):
        vakapaatos = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos2')
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')

        vakasuhde = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka.id}/',
            'alkamis_pvm': '2021-01-02',
            'tunniste': 'testing-varhaiskasvatussuhde',
        }

        client = SetUpTestClient('tester5').client()
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_vakasuhde_vakapaatos_toimipaikka_tunniste(self):
        lahdejarjestelma = '1'
        vakapaatos = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos2')
        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')

        vakasuhde_1 = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos.tunniste,
            'toimipaikka_tunniste': toimipaikka.tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_1 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_1)
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_1_json = json.loads(resp_1.content)
        vakasuhde_object = Varhaiskasvatussuhde.objects.get(id=resp_1_json['id'])
        self.assertEqual(vakasuhde_object.varhaiskasvatuspaatos.id, vakapaatos.id)
        self.assertEqual(vakasuhde_object.toimipaikka.id, toimipaikka.id)
        self.assertEqual(resp_1_json['toimipaikka_oid'], toimipaikka.organisaatio_oid)

        vakasuhde_2 = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka.id}/',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }
        resp_2 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_2)
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        resp_2_json = json.loads(resp_2.content)
        self.assertEqual(resp_2_json['toimipaikka_tunniste'], toimipaikka.tunniste)
        self.assertEqual(resp_2_json['toimipaikka_oid'], toimipaikka.organisaatio_oid)
        self.assertEqual(resp_2_json['varhaiskasvatuspaatos_tunniste'], vakapaatos.tunniste)

        vakasuhde_3 = {
            'varhaiskasvatuspaatos_tunniste': 'no',
            'toimipaikka_tunniste': 'no',
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }
        resp_3 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'varhaiskasvatuspaatos_tunniste', 'RF003', 'Could not find matching object.')
        assert_validation_error(resp_3, 'toimipaikka_tunniste', 'RF003', 'Could not find matching object.')

    def test_api_vakasuhde_vakapaatos_toimipaikka_related_match(self):
        vakapaatos_1 = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos1')
        vakapaatos_2 = Varhaiskasvatuspaatos.objects.get(tunniste='testing-varhaiskasvatuspaatos2')
        toimipaikka_1 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')
        toimipaikka_2 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548811')
        toimipaikka_3 = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548817')
        lahdejarjestelma = '1'

        vakasuhde_1 = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_1.id}/',
            'varhaiskasvatuspaatos_tunniste': vakapaatos_2.tunniste,
            'toimipaikka_oid': toimipaikka_2.organisaatio_oid,
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_1 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_1)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'varhaiskasvatuspaatos_tunniste', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_1, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        vakasuhde_2 = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_1.id}/',
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_1.id}/',
            'toimipaikka_oid': toimipaikka_2.organisaatio_oid,
            'toimipaikka_tunniste': toimipaikka_3.tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_2 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_2)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'toimipaikka_oid', 'RF004', 'Differs from parent field.')
        assert_validation_error(resp_2, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        vakasuhde_3 = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_2.tunniste,
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_1.id}/',
            'toimipaikka_tunniste': toimipaikka_3.tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester5').client()
        resp_3 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_3)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'toimipaikka_tunniste', 'RF004', 'Differs from parent field.')

        vakasuhde_4 = {
            'varhaiskasvatuspaatos': f'/api/v1/varhaiskasvatuspaatokset/{vakapaatos_2.id}/',
            'varhaiskasvatuspaatos_tunniste': vakapaatos_2.tunniste,
            'toimipaikka': f'/api/v1/toimipaikat/{toimipaikka_1.id}/',
            'toimipaikka_oid': toimipaikka_1.organisaatio_oid,
            'toimipaikka_tunniste': toimipaikka_1.tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_4 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_4)
        assert_status_code(resp_4, status.HTTP_201_CREATED)

    def test_api_vakasuhde_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-varhaiskasvatussuhde98'
        new_tunniste = 'testing-varhaiskasvatussuhde99'

        vakapaatos_tunniste = 'testing-varhaiskasvatuspaatos3'
        toimipaikka_tunniste = 'testing-toimipaikka2'

        client = SetUpTestClient('tester2').client()
        vakasuhde_post = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'toimipaikka_tunniste': toimipaikka_tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_vakasuhde_post = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde_post)
        assert_status_code(resp_vakasuhde_post, status.HTTP_201_CREATED)
        vakasuhde = Varhaiskasvatussuhde.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        vakasuhde_url = f'/api/v1/varhaiskasvatussuhteet/{lahdejarjestelma}:{tunniste}/'
        resp_vakasuhde_get = client.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_get, status.HTTP_200_OK)
        self.assertEqual(vakasuhde.id, json.loads(resp_vakasuhde_get.content)['id'])

        resp_vakasuhde_get_404 = client.get('/api/v1/varhaiskasvatussuhteet/5:no/')
        assert_status_code(resp_vakasuhde_get_404, status.HTTP_404_NOT_FOUND)

        vakasuhde_put = {
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'toimipaikka_tunniste': toimipaikka_tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_vakasuhde_put = client.put(vakasuhde_url, vakasuhde_put)
        assert_status_code(resp_vakasuhde_put, status.HTTP_200_OK)

        vakasuhde_patch = {
            'tunniste': tunniste
        }
        vakasuhde_url_patch = f'/api/v1/varhaiskasvatussuhteet/{lahdejarjestelma}:{new_tunniste}/'
        resp_vakasuhde_patch = client.patch(vakasuhde_url_patch, vakasuhde_patch)
        assert_status_code(resp_vakasuhde_patch, status.HTTP_200_OK)

        resp_vakasuhde_delete = client.delete(vakasuhde_url)
        assert_status_code(resp_vakasuhde_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Varhaiskasvatussuhde.objects.filter(id=vakasuhde.id).exists())

    def test_api_maksutieto_lahdejarjestelma_tunniste_not_unique(self):
        lapsi_tunniste = 'testing-lapsi3'
        maksutieto = {
            'lapsi_tunniste': lapsi_tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-02-01',
            'lahdejarjestelma': '1',
            'tunniste': 'testing-maksutieto1',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'errors', 'MI013', 'Combination of lahdejarjestelma and tunniste fields should be unique.')

    def test_api_maksutieto_missing_lahdejarjestelma(self):
        lahdejarjestelma = '1'
        lapsi_tunniste = 'testing-lapsi3'
        lapsi = Lapsi.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=lapsi_tunniste)

        maksutieto = {
            'lapsi': f'/api/v1/lapset/{lapsi.id}/',
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-02-01',
            'tunniste': 'testing-maksutieto',
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'lahdejarjestelma', 'GE001', 'This field is required.')

    def test_api_maksutieto_lapsi_tunniste(self):
        lahdejarjestelma = '1'
        lapsi_tunniste = 'testing-lapsi3'

        lapsi = Lapsi.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=lapsi_tunniste)

        maksutieto_1 = {
            'lapsi_tunniste': lapsi_tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-02-01',
            'paattymis_pvm': '2021-02-02',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_1), content_type='application/json')
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_1_json = json.loads(resp_1.content)
        maksutieto_object = Maksutieto.objects.get(id=resp_1_json['id'])
        self.assertEqual(maksutieto_object.huoltajuussuhteet.first().lapsi.id, lapsi.id)

        maksutieto_2 = {
            'lapsi': f'/api/v1/lapset/{lapsi.id}/',
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-02-04',
            'paattymis_pvm': '2021-02-05',
            'lahdejarjestelma': lahdejarjestelma,
        }
        resp_2 = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_2), content_type='application/json')
        assert_status_code(resp_2, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp_2.content)['lapsi_tunniste'], lapsi_tunniste)

        maksutieto_3 = {
            'lapsi_tunniste': 'no',
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-03-01',
            'lahdejarjestelma': lahdejarjestelma,
        }
        resp_3 = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_3), content_type='application/json')
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'lapsi_tunniste', 'RF003', 'Could not find matching object.')

    def test_api_maksutieto_lapsi_related_match(self):
        lapsi_1 = Lapsi.objects.get(tunniste='testing-lapsi3')
        lapsi_2 = Lapsi.objects.get(tunniste='testing-lapsi6')
        lahdejarjestelma = '1'

        maksutieto_1 = {
            'lapsi': f'/api/v1/lapset/{lapsi_1.id}/',
            'lapsi_tunniste': lapsi_2.tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-03-01',
            'lahdejarjestelma': lahdejarjestelma,
        }

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_1), content_type='application/json')
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'lapsi_tunniste', 'RF004', 'Differs from parent field.')

        maksutieto_2 = {
            'lapsi': f'/api/v1/lapset/{lapsi_1.id}/',
            'lapsi_tunniste': lapsi_1.tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-03-01',
            'lahdejarjestelma': lahdejarjestelma,
        }

        resp_2 = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_2), content_type='application/json')
        assert_status_code(resp_2, status.HTTP_201_CREATED)

    def test_api_maksutieto_lahdejarjestelma_tunniste_get_put_patch_delete(self):
        lahdejarjestelma = '1'
        tunniste = 'testing-maksutieto98'
        new_tunniste = 'testing-maksutieto99'

        lapsi_tunniste = 'testing-lapsi3'

        client = SetUpTestClient('tester2').client()
        maksutieto_post = {
            'lapsi_tunniste': lapsi_tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-03-01',
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': tunniste,
        }
        resp_maksutieto_post = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_post), content_type='application/json')
        assert_status_code(resp_maksutieto_post, status.HTTP_201_CREATED)
        maksutieto = Maksutieto.objects.get(lahdejarjestelma=lahdejarjestelma, tunniste=tunniste)

        maksutieto_url = f'/api/v1/maksutiedot/{lahdejarjestelma}:{tunniste}/'
        resp_maksutieto_get = client.get(maksutieto_url)
        assert_status_code(resp_maksutieto_get, status.HTTP_200_OK)
        self.assertEqual(maksutieto.id, json.loads(resp_maksutieto_get.content)['id'])

        resp_maksutieto_get_404 = client.get('/api/v1/maksutiedot/5:no/')
        assert_status_code(resp_maksutieto_get_404, status.HTTP_404_NOT_FOUND)

        maksutieto_put = {
            'lapsi_tunniste': lapsi_tunniste,
            'huoltajat': [{
                'henkilotunnus': '120386-109V',
                'etunimet': 'Pertti',
                'sukunimi': 'Virtanen',
            }],
            'maksun_peruste_koodi': 'mp01',
            'palveluseteli_arvo': 0,
            'asiakasmaksu': 10,
            'perheen_koko': 2,
            'alkamis_pvm': '2021-03-01',
            'paattymis_pvm': None,
            'lahdejarjestelma': lahdejarjestelma,
            'tunniste': new_tunniste,
        }
        resp_maksutieto_put = client.put(maksutieto_url, json.dumps(maksutieto_put), content_type='application/json')
        assert_status_code(resp_maksutieto_put, status.HTTP_200_OK)

        maksutieto_patch = {
            'tunniste': tunniste
        }
        maksutieto_url_patch = f'/api/v1/maksutiedot/{lahdejarjestelma}:{new_tunniste}/'
        resp_maksutieto_patch = client.patch(maksutieto_url_patch, json.dumps(maksutieto_patch), content_type='application/json')
        assert_status_code(resp_maksutieto_patch, status.HTTP_200_OK)

        resp_maksutieto_delete = client.delete(maksutieto_url)
        assert_status_code(resp_maksutieto_delete, status.HTTP_204_NO_CONTENT)

        self.assertFalse(Maksutieto.objects.filter(id=maksutieto.id).exists())

    @responses.activate
    def test_toimipaikka_lapsi_create_all(self):
        vakajarjestaja_oid = '1.2.246.562.10.93957375488'
        toimipaikka_oid_1 = '1.2.246.562.10.9395737548810'
        toimipaikka_oid_2 = '1.2.246.562.10.9395737548815'
        toimipaikka_oid_3 = '1.2.246.562.10.9395737548811'
        henkilo_oid = '1.2.246.562.24.47279942111'

        responses.add(responses.GET,
                      f'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/{henkilo_oid}/master',
                      json={'hetu': '030518A055C', 'yksiloityVTJ': True},
                      status=status.HTTP_200_OK)

        client = SetUpTestClient('vakatietojen_toimipaikka_tallentaja').client()

        henkilo = {
            'henkilo_oid': henkilo_oid,
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        resp_henkilo = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp_henkilo, status.HTTP_201_CREATED)

        lapsi_tunniste = 'testing-lapsi'
        lapsi = {
            'toimipaikka_oid': toimipaikka_oid_3,
            'vakatoimija_oid': vakajarjestaja_oid,
            'henkilo_oid': henkilo_oid,
            'lahdejarjestelma': 1,
            'tunniste': lapsi_tunniste
        }
        resp_lapsi_1 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_lapsi_1, 'toimipaikka_oid', 'RF003', 'Could not find matching object.')

        lapsi['toimipaikka_oid'] = toimipaikka_oid_2
        resp_lapsi_2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_lapsi_2, 'toimipaikka', 'MI019', 'Given Toimipaikka does not belong to the correct Organisaatio.')

        lapsi['toimipaikka_oid'] = toimipaikka_oid_1
        resp_lapsi_3 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_lapsi_3, status.HTTP_201_CREATED)

        vakapaatos_tunniste = 'testing-varhaiskasvatuspaatos'
        vakapaatos = {
            'toimipaikka_oid': toimipaikka_oid_2,
            'lapsi_tunniste': lapsi_tunniste,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm04',
            'hakemus_pvm': '2021-01-02',
            'alkamis_pvm': '2021-01-02',
            'tilapainen_vaka_kytkin': False,
            'lahdejarjestelma': '1',
            'tunniste': vakapaatos_tunniste
        }
        resp_vakapaatos_1 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_vakapaatos_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_vakapaatos_1, 'toimipaikka', 'MI019', 'Given Toimipaikka does not belong to the correct Organisaatio.')

        vakapaatos['toimipaikka_oid'] = toimipaikka_oid_1
        resp_vakapaatos_2 = client.post('/api/v1/varhaiskasvatuspaatokset/', vakapaatos)
        assert_status_code(resp_vakapaatos_2, status.HTTP_201_CREATED)

        vakasuhde = {
            'toimipaikka_oid': toimipaikka_oid_2,
            'varhaiskasvatuspaatos_tunniste': vakapaatos_tunniste,
            'alkamis_pvm': '2021-01-02',
            'lahdejarjestelma': '1'
        }
        resp_vakasuhde_1 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_vakasuhde_1, 'toimipaikka', 'MI019', 'Given Toimipaikka does not belong to the correct Organisaatio.')

        vakasuhde['toimipaikka_oid'] = toimipaikka_oid_1
        resp_vakasuhde_2 = client.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp_vakasuhde_2, status.HTTP_201_CREATED)

    def _add_post_henkilo_responses(self, henkilo_hetu, henkilo_oid):
        responses.reset()
        henkilo_response_oid = {
            'method': responses.GET,
            'url': f'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/{henkilo_oid}/master',
            'json': {'hetu': henkilo_hetu, 'yksiloityVTJ': True, 'yksiloity': True},
            'status': status.HTTP_200_OK
        }
        henkilo_response_hetu = {
            'method': responses.GET,
            'url': f'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/hetu={henkilo_hetu}',
            'json': {'oidHenkilo': henkilo_oid, 'hetu': henkilo_hetu},
            'status': status.HTTP_200_OK
        }
        responses.add(**henkilo_response_oid)
        responses.add(**henkilo_response_hetu)

    def mock_validate_henkilo_uniqueness_henkilotunnus(self, *args, **kwargs):
        return None

    def mock_validate_henkilo_uniqueness_oid(self, *args, **kwargs):
        return None

    @responses.activate
    @patch.object(HenkiloViewSet, 'validate_henkilo_uniqueness_henkilotunnus',
                  mock_validate_henkilo_uniqueness_henkilotunnus)
    @patch.object(HenkiloViewSet, 'validate_henkilo_uniqueness_oid', mock_validate_henkilo_uniqueness_oid)
    def test_henkilo_unique_constraint(self):
        henkilo_oid = '1.2.246.562.24.47279942111'
        henkilo_hetu = '030518A055C'
        self._add_post_henkilo_responses(henkilo_hetu, henkilo_oid)

        henkilo_base = {
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }
        client = SetUpTestClient('tester2').client()

        henkilo_with_oid = {**henkilo_base, 'henkilo_oid': henkilo_oid}
        resp_1 = client.post('/api/v1/henkilot/', henkilo_with_oid)
        assert_status_code(resp_1, status.HTTP_201_CREATED)
        resp_2 = client.post('/api/v1/henkilot/', henkilo_with_oid)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'henkilo_oid', 'HE015', 'Henkilo with this henkilo_oid already exists.')

        henkilo_with_hetu = {**henkilo_base, 'henkilotunnus': henkilo_hetu}
        resp_3 = client.post('/api/v1/henkilot/', henkilo_with_hetu)
        assert_status_code(resp_3, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_3, 'henkilotunnus', 'HE014', 'Henkilo with this henkilotunnus already exists.')

        self._add_post_henkilo_responses(henkilo_hetu, '1.2.246.562.24.47279942112')
        henkilo_with_hetu = {**henkilo_base, 'henkilotunnus': henkilo_hetu}
        resp_4 = client.post('/api/v1/henkilot/', henkilo_with_hetu)
        assert_status_code(resp_4, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_4, 'henkilotunnus', 'HE014', 'Henkilo with this henkilotunnus already exists.')

        # Can add two Henkilo objects without hetu and different OID:s
        self._add_post_henkilo_responses(None, '1.2.246.562.24.47279942113')
        henkilo_with_oid = {**henkilo_base, 'henkilo_oid': '1.2.246.562.24.47279942113'}
        resp_5 = client.post('/api/v1/henkilot/', henkilo_with_oid)
        assert_status_code(resp_5, status.HTTP_201_CREATED)

        self._add_post_henkilo_responses(None, '1.2.246.562.24.47279942114')
        henkilo_with_oid = {**henkilo_base, 'henkilo_oid': '1.2.246.562.24.47279942114'}
        resp_6 = client.post('/api/v1/henkilot/', henkilo_with_oid)
        assert_status_code(resp_6, status.HTTP_201_CREATED)

    def mock_return_lapsi_if_already_created(self, *args, **kwargs):
        pass

    @patch.object(LapsiViewSet, 'return_lapsi_if_already_created', mock_return_lapsi_if_already_created)
    def test_lapsi_unique_constraint(self):
        client = SetUpTestClient('tester2').client()

        henkilo_oid = '1.2.246.562.24.4473262898463'
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        vakajarjestaja_paos_oid = '1.2.246.562.10.93957375488'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)

        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': vakajarjestaja_oid,
            'lahdejarjestelma': '1'
        }
        resp_1 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_1, status.HTTP_201_CREATED)

        # TODO: Activate this test in https://jira.eduuni.fi/browse/OPHVARDA-2255
        """
        resp_2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'errors', 'LA009',
                                'Combination of henkilo and vakatoimija fields should be unique.')
        """

        lapsi_paos = {
            'henkilo_oid': henkilo_oid,
            'oma_organisaatio_oid': vakajarjestaja_oid,
            'paos_organisaatio_oid': vakajarjestaja_paos_oid,
            'lahdejarjestelma': '1'
        }
        resp_3 = client.post('/api/v1/lapset/', lapsi_paos)
        assert_status_code(resp_3, status.HTTP_201_CREATED)

        resp_4 = client.post('/api/v1/lapset/', lapsi_paos)
        assert_status_code(resp_4, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_4, 'errors', 'LA010', 'Combination of henkilo, oma_organisaatio and '
                                                           'paos_organisaatio fields should be unique.')

    def test_lapsi_tyontekija(self):
        client = SetUpTestClient('tester2').client()
        henkilo_oid = '1.2.246.562.24.2431884920041'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)

        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilo', 'LA012', 'This Henkilo is already referenced by Tyontekija objects.')

    def test_lapsi_huoltaja(self):
        client = SetUpTestClient('tester2').client()
        henkilo_oid = '1.2.246.562.24.2395579772672'
        post_henkilo_to_get_permissions(client, henkilo_oid=henkilo_oid)

        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1'
        }

        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'henkilo', 'LA013', 'This Henkilo is already referenced by Huoltaja object.')

    @mock_date_decorator_factory('varda.serializers.datetime', '2021-06-01')
    def test_toimipaikka_dates_within_vakajarjestaja(self):
        vakajarjestaja_oid = '1.2.246.562.10.34683023489'
        toimipaikka = {
            'vakajarjestaja_oid': '1.2.246.562.10.34683023489',
            'nimi': 'Testila',
            'kunta_koodi': '091',
            'puhelinnumero': '+35892323234',
            'kayntiosoite': 'Testerkatu 2',
            'kayntiosoite_postinumero': '00001',
            'kayntiosoite_postitoimipaikka': 'Testilä',
            'postiosoite': 'Testerkatu 2',
            'postitoimipaikka': 'Testilä',
            'postinumero': '00001',
            'sahkopostiosoite': 'hel1234@helsinki.fi',
            'kasvatusopillinen_jarjestelma_koodi': 'kj03',
            'toimintamuoto_koodi': 'tm01',
            'asiointikieli_koodi': ['FI'],
            'jarjestamismuoto_koodi': ['jm01', 'jm03'],
            'varhaiskasvatuspaikat': 1000,
            'alkamis_pvm': '2021-08-01',
            'lahdejarjestelma': '1',
        }

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid=vakajarjestaja_oid)
        vakajarjestaja.paattymis_pvm = '2021-07-01'
        vakajarjestaja.save()

        client = SetUpTestClient('tester2').client()
        resp_1 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp_1, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_1, 'alkamis_pvm', 'TP025', 'alkamis_pvm must be before or equal to Organisaatio paattymis_pvm.')

        vakajarjestaja.paattymis_pvm = '2021-05-31'
        vakajarjestaja.save()
        toimipaikka['alkamis_pvm'] = '2021-05-01'
        resp_2 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'paattymis_pvm', 'TP024', 'Toimipaikka must have paattymis_pvm because Organisaatio is not active.')

        vakajarjestaja.paattymis_pvm = '2021-07-01'
        vakajarjestaja.save()
        toimipaikka['paattymis_pvm'] = '2021-08-01'
        resp_2 = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp_2, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_2, 'paattymis_pvm', 'TP026', 'paattymis_pvm must be before or equal to Organisaatio paattymis_pvm.')

    @responses.activate
    def test_henkilo_lapsi_duplicate_already_exists(self):
        henkilo_oid = '1.2.246.562.24.47279942111'
        responses.add(responses.GET,
                      f'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/{henkilo_oid}/master',
                      json={'hetu': '100382-456R', 'yksiloityVTJ': True},
                      status=status.HTTP_200_OK)
        henkilo = {
            'henkilo_oid': henkilo_oid,
            'etunimet': 'Erkki',
            'kutsumanimi': 'Erkki',
            'sukunimi': 'Esimerkki'
        }

        client_vakajarjestaja = SetUpTestClient('vakatietojen_tallentaja').client()
        client_toimipaikka = SetUpTestClient('vakatietojen_toimipaikka_tallentaja').client()

        resp = client_vakajarjestaja.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_201_CREATED)
        henkilo_id_1 = json.loads(resp.content)['id']
        resp = client_vakajarjestaja.get(f'/api/v1/henkilot/{henkilo_id_1}/')
        assert_status_code(resp, status.HTTP_200_OK)

        lapsi = {
            'henkilo_oid': henkilo_oid,
            'vakatoimija_oid': '1.2.246.562.10.34683023489',
            'lahdejarjestelma': '1'
        }

        resp = client_vakajarjestaja.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_201_CREATED)
        lapsi_id_1 = json.loads(resp.content)['id']
        resp = client_vakajarjestaja.get(f'/api/v1/lapset/{lapsi_id_1}/')
        assert_status_code(resp, status.HTTP_200_OK)

        resp = client_toimipaikka.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, status.HTTP_200_OK)
        henkilo_id_2 = json.loads(resp.content)['id']
        self.assertEqual(henkilo_id_1, henkilo_id_2)
        resp = client_toimipaikka.get(f'/api/v1/henkilot/{henkilo_id_2}/')
        assert_status_code(resp, status.HTTP_200_OK)

        lapsi['toimipaikka_oid'] = '1.2.246.562.10.9395737548815'
        resp = client_toimipaikka.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)
        lapsi_id_2 = json.loads(resp.content)['id']
        self.assertEqual(lapsi_id_1, lapsi_id_2)
        resp = client_toimipaikka.get(f'/api/v1/lapset/{lapsi_id_2}/')
        assert_status_code(resp, status.HTTP_200_OK)

    def test_code_active_validation(self):
        client = SetUpTestClient('tester2').client()

        code_instance = Z2_Code.objects.get(code_value__iexact='jm01')
        vakapaatos_patch_url = '/api/v1/varhaiskasvatuspaatokset/1:testing-varhaiskasvatuspaatos3/'

        vakapaatos_post = {
            'vuorohoito_kytkin': False,
            'pikakasittely_kytkin': False,
            'tuntimaara_viikossa': '39.0',
            'paivittainen_vaka_kytkin': True,
            'kokopaivainen_vaka_kytkin': True,
            'tilapainen_vaka_kytkin': False,
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2018-09-05',
            'lahdejarjestelma': '1',
            'lapsi_tunniste': 'testing-lapsi3',
            'tunniste': 'testing-varhaiskasvatuspaatos'
        }

        # (((code_alkamis_pvm, code_paattymis_pvm,), ((invalid_alkamis_pvm, invalid_paattymis_pvm,)),
        # ((valid_alkamis_pvm, valid_paattymis_pvm,)),))
        test_list = (
            (
                ('2019-01-01', '2020-01-01'),
                (('2018-12-01', '2020-01-02'), ('2019-01-02', '2020-01-02'), ('2020-01-02', None)),
                (('2019-01-01', None), ('2019-01-01', '2020-01-01'), ('2020-01-01', '2020-01-01'),
                 ('2018-12-01', None), ('2018-12-01', '2019-06-01'),),
            ),
            (
                ('2019-01-01', None),
                (),
                (('2019-01-01', None), ('2019-01-01', '2020-01-01'), ('2018-12-01', None), ('2018-12-01', '2019-06-01'))
            )
        )

        for test_set in test_list:
            code_dates = test_set[0]
            invalid_cases = test_set[1]
            valid_cases = test_set[2]

            code_instance.alkamis_pvm = code_dates[0]
            code_instance.paattymis_pvm = code_dates[1]
            code_instance.save()

            for invalid_case in invalid_cases:
                vakapaatos_post['alkamis_pvm'] = invalid_case[0]
                vakapaatos_post['paattymis_pvm'] = invalid_case[1]
                invalid_resp_post = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(vakapaatos_post),
                                                content_type='application/json')
                assert_status_code(invalid_resp_post, status.HTTP_400_BAD_REQUEST)
                assert_validation_error(invalid_resp_post, 'jarjestamismuoto_koodi', 'KO005',
                                        'Code is not active during the time period.')
                invalid_resp_patch = client.patch(vakapaatos_patch_url, json.dumps({'alkamis_pvm': invalid_case[0],
                                                                                    'paattymis_pvm': invalid_case[1]}),
                                                  content_type='application/json')
                assert_status_code(invalid_resp_patch, status.HTTP_400_BAD_REQUEST)
                assert_validation_error(invalid_resp_patch, 'jarjestamismuoto_koodi', 'KO005',
                                        'Code is not active during the time period.')

            for valid_case in valid_cases:
                vakapaatos_post['alkamis_pvm'] = valid_case[0]
                vakapaatos_post['paattymis_pvm'] = valid_case[1]
                valid_resp_post = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(vakapaatos_post),
                                              content_type='application/json')
                assert_status_code(valid_resp_post, status.HTTP_201_CREATED)
                client.delete(f'/api/v1/varhaiskasvatuspaatokset/{json.loads(valid_resp_post.content)["id"]}/')
                valid_resp_patch = client.patch(vakapaatos_patch_url, json.dumps({'alkamis_pvm': valid_case[0],
                                                                                  'paattymis_pvm': valid_case[1]}),
                                                content_type='application/json')
                assert_status_code(valid_resp_patch, status.HTTP_200_OK)

    def test_maksutieto_add_duplicate_huoltaja(self):
        client = SetUpTestClient('tester10').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi11')

        maksutieto = {
            'lapsi': f'/api/v1/lapset/{lapsi.id}/',
            'huoltajat': [
                {'henkilo_oid': '1.2.246.562.24.2434693467574', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'},
                {'henkilo_oid': '1.2.246.562.24.2434693467574', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'}
            ],
            'maksun_peruste_koodi': 'mp03',
            'palveluseteli_arvo': '0.00',
            'asiakasmaksu': '50.00',
            'perheen_koko': 3,
            'alkamis_pvm': '2020-01-11',
            'lahdejarjestelma': '1'
        }
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat', 'MA017', 'Duplicate huoltajat detected.')

        maksutieto_patch = {
            'huoltajat_add': [
                {'henkilo_oid': '1.2.246.562.24.2434693467574', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'},
                {'henkilotunnus': '130780-753Y', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'}
            ]
        }
        patch_url = '/api/v1/maksutiedot/1:testing-maksutieto6/'
        resp = client.patch(patch_url, json.dumps(maksutieto_patch), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat_add', 'MA017', 'Duplicate huoltajat detected.')

    def test_maksutieto_update_huoltajat_add_correct(self):
        client = SetUpTestClient('tester10').client()

        # Delete Huoltaja so that we can potentially add it again
        MaksutietoHuoltajuussuhde.objects.get(maksutieto__tunniste='testing-maksutieto6',
                                              huoltajuussuhde__huoltaja__henkilo__henkilo_oid='1.2.246.562.24.3367432256266').delete()

        maksutieto_put = {
            'lapsi_tunniste': 'testing-lapsi11',
            'huoltajat_add': [
                {'henkilo_oid': '1.2.246.562.24.3367432256266', 'etunimet': 'Kirsi', 'sukunimi': 'Taavetti'}
            ],
            'maksun_peruste_koodi': 'mp03',
            'palveluseteli_arvo': '0.00',
            'asiakasmaksu': '50.00',
            'perheen_koko': 3,
            'alkamis_pvm': '2020-01-11',
            'paattymis_pvm': None,
            'lahdejarjestelma': '1'
        }
        resp = client.put('/api/v1/maksutiedot/1:testing-maksutieto6/', json.dumps(maksutieto_put),
                          content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)
        maksutieto_huoltajuussuhde_qs = Maksutieto.objects.get(tunniste='testing-maksutieto6').maksutiedot_huoltajuussuhteet.order_by('id')
        self.assertEqual(maksutieto_huoltajuussuhde_qs[0].huoltajuussuhde.huoltaja.henkilo.henkilo_oid, '1.2.246.562.24.2434693467574')
        self.assertEqual(maksutieto_huoltajuussuhde_qs[1].huoltajuussuhde.huoltaja.henkilo.henkilo_oid, '1.2.246.562.24.3367432256266')

    def test_maksutieto_update_huoltajat_add_incorrect(self):
        client = SetUpTestClient('tester10').client()
        url = '/api/v1/maksutiedot/1:testing-maksutieto6/'

        # Already exists
        maksutieto_patch = {
            'huoltajat_add': [
                {'henkilo_oid': '1.2.246.562.24.3367432256266', 'etunimet': 'Kirsi', 'sukunimi': 'Taavetti'}
            ]
        }

        resp = client.patch(url, json.dumps(maksutieto_patch), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat_add', 'MA018', 'Huoltaja is already linked to this Maksutieto.')

        # Missing etunimet and sukunimi
        maksutieto_patch = {
            'huoltajat_add': [
                {'henkilo_oid': '1.2.246.562.24.2434693467574'}
            ]
        }
        resp = client.patch(url, json.dumps(maksutieto_patch), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, ['huoltajat_add', '0', 'etunimet'], 'GE001', 'This field is required.')
        assert_validation_error(resp, ['huoltajat_add', '0', 'sukunimi'], 'GE001', 'This field is required.')

    def test_maksutieto_too_many_huoltaja(self):
        client = SetUpTestClient('tester10').client()
        huoltaja_list = [
            {'henkilo_oid': '1.2.246.562.24.3367432256266', 'etunimet': 'Kirsi', 'sukunimi': 'Taavetti'},
            {'henkilo_oid': '1.2.246.562.24.2434693467574', 'etunimet': 'Taneli', 'sukunimi': 'Tattinen'}
        ]
        extra_huoltaja_list = [
            {'henkilo_oid': '1.2.246.562.24.3367432256100', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256101', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256102', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256103', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256104', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256105', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'},
            {'henkilo_oid': '1.2.246.562.24.3367432256106', 'etunimet': 'Kalle', 'sukunimi': 'Kalevi'}
        ]

        maksutieto_post = {'lapsi_tunniste': 'testing-lapsi11', 'maksun_peruste_koodi': 'mp03',
                           'palveluseteli_arvo': '0.00', 'asiakasmaksu': '50.00', 'perheen_koko': 3,
                           'alkamis_pvm': '2020-01-12', 'paattymis_pvm': None, 'lahdejarjestelma': '1',
                           'huoltajat': [huoltaja_list[0], *extra_huoltaja_list]}
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_post), content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat', 'MA011', 'Maximum number of huoltajat is 7.')

        maksutieto_post['huoltajat'] = [huoltaja_list[0]]
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto_post), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        maksutieto_id = json.loads(resp.content)['id']

        maksutieto_patch = {
            'huoltajat_add': [huoltaja_list[1], *extra_huoltaja_list]
        }
        resp = client.patch(f'/api/v1/maksutiedot/{maksutieto_id}/', json.dumps(maksutieto_patch),
                            content_type='application/json')
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, 'huoltajat_add', 'MA011', 'Maximum number of huoltajat is 7.')

        maksutieto_patch['huoltajat_add'] = [huoltaja_list[1], extra_huoltaja_list[0], extra_huoltaja_list[1]]
        resp = client.patch(f'/api/v1/maksutiedot/{maksutieto_id}/', json.dumps(maksutieto_patch),
                            content_type='application/json')
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(1, json.loads(resp.content)['tallennetut_huoltajat_count'])
        self.assertEqual(2, json.loads(resp.content)['ei_tallennetut_huoltajat_count'])

    def test_lapsi_delete_all_palvelukayttaja(self):
        client = SetUpTestClient('pkvakajarjestaja1').client()
        invalid_client = SetUpTestClient('pkvakajarjestaja2').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi3')
        lapsi_data = self._get_data_ids_for_lapsi(lapsi)

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = invalid_client.delete(url)
        assert_status_code(resp, status.HTTP_404_NOT_FOUND)

        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def test_lapsi_delete_all_paos(self):
        client = SetUpTestClient('pkvakajarjestaja1').client()
        invalid_client = SetUpTestClient('pkvakajarjestaja2').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi4')
        lapsi_data = self._get_data_ids_for_lapsi(lapsi)

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = invalid_client.delete(url)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def test_lapsi_delete_all_paos_jarjestaja(self):
        mock_admin_user('tester2')
        admin_client = SetUpTestClient('tester2').client()

        paos_oikeus = PaosOikeus.objects.get(jarjestaja_kunta_organisaatio__organisaatio_oid='1.2.246.562.10.34683023489',
                                             tuottaja_organisaatio__organisaatio_oid='1.2.246.562.10.93957375488')
        paos_oikeus_patch = {
            'tallentaja_organisaatio_oid': '1.2.246.562.10.93957375488'
        }
        assert_status_code(admin_client.patch(f'/api/v1/paos-oikeudet/{paos_oikeus.id}/', paos_oikeus_patch), status.HTTP_200_OK)

        client = SetUpTestClient('pkvakajarjestaja1').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi4')

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = client.delete(url)
        # No delete permission to Lapsi object
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE006', 'User does not have permission to perform this action.')

        paos_oikeus_patch = {
            'tallentaja_organisaatio_oid': '1.2.246.562.10.34683023489'
        }
        assert_status_code(admin_client.patch(f'/api/v1/paos-oikeudet/{paos_oikeus.id}/', paos_oikeus_patch), status.HTTP_200_OK)

        lapsi_data = self._get_data_ids_for_lapsi(lapsi)
        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def test_lapsi_delete_all_paos_tuottaja(self):
        mock_admin_user('tester2')
        admin_client = SetUpTestClient('tester2').client()
        paos_oikeus = PaosOikeus.objects.get(jarjestaja_kunta_organisaatio__organisaatio_oid='1.2.246.562.10.93957375484',
                                             tuottaja_organisaatio__organisaatio_oid='1.2.246.562.10.93957375488')
        paos_oikeus_patch = {
            'tallentaja_organisaatio_oid': '1.2.246.562.10.93957375488'
        }
        assert_status_code(admin_client.patch(f'/api/v1/paos-oikeudet/{paos_oikeus.id}/', paos_oikeus_patch), status.HTTP_200_OK)

        client = SetUpTestClient('pkvakajarjestaja2').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi5')

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE002', 'User does not have permissions to delete this object.')

        for maksutieto in Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi):
            maksutieto.maksutiedot_huoltajuussuhteet.all().delete()
            maksutieto.delete()

        lapsi_data = self._get_data_ids_for_lapsi(lapsi)
        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def test_lapsi_delete_all_vakajarjestaja(self):
        user = User.objects.get(username='tester5')
        client = SetUpTestClient('tester5').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi1')
        lapsi_data = self._get_data_ids_for_lapsi(lapsi)

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = client.delete(url)
        # Missing HUOLTAJATIEDOT_TALLENTAJA permission
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE002', 'User does not have permissions to delete this object.')

        organisaatio_oid = '1.2.246.562.10.93957375488'
        maksutieto_group = Group.objects.get(name=f'{Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA}_{organisaatio_oid}')
        user.groups.add(maksutieto_group)

        resp = client.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def test_lapsi_delete_all_toimipaikka(self):
        client_vakajarjestaja = SetUpTestClient('pkvakajarjestaja2').client()
        user_toimipaikka = User.objects.get(username='user_toimipaikka_9395737548810')
        client_toimipaikka = SetUpTestClient('user_toimipaikka_9395737548810').client()
        lapsi = Lapsi.objects.get(tunniste='testing-lapsi1')

        toimipaikka_oid = '1.2.246.562.10.9395737548811'
        vakasuhde = {
            'varhaiskasvatuspaatos_tunniste': 'testing-varhaiskasvatuspaatos1',
            'toimipaikka_oid': toimipaikka_oid,
            'alkamis_pvm': '2017-02-11',
            'paattymis_pvm': '2018-02-24',
            'lahdejarjestelma': '1'
        }
        resp = client_vakajarjestaja.post('/api/v1/varhaiskasvatussuhteet/', vakasuhde)
        assert_status_code(resp, status.HTTP_201_CREATED)

        lapsi_data = self._get_data_ids_for_lapsi(lapsi)

        url = f'/api/v1/lapset/{lapsi.lahdejarjestelma}:{lapsi.tunniste}/delete-all/'
        resp = client_toimipaikka.delete(url)
        # Missing permission to second Toimipaikka
        assert_status_code(resp, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp, 'errors', 'PE002', 'User does not have permissions to delete this object.')

        tallentaja_group = Group.objects.get(name=f'{Z4_CasKayttoOikeudet.TALLENTAJA}_{toimipaikka_oid}')
        user_toimipaikka.groups.add(tallentaja_group)

        resp = client_toimipaikka.delete(url)
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self._verify_lapsi_data_deletion(lapsi_data)

    def _get_data_ids_for_lapsi(self, lapsi):
        return {
            'lapsi_id': lapsi.id,
            'vakapaatos_id_list': list(lapsi.varhaiskasvatuspaatokset.all().values_list('id', flat=True)),
            'vakasuhde_id_list': list(Varhaiskasvatussuhde.objects.filter(varhaiskasvatuspaatos__lapsi=lapsi)
                                      .values_list('id', flat=True)),
            'huoltajuussuhde_id_list': list(lapsi.huoltajuussuhteet.all().values_list('id', flat=True)),
            'maksutieto_huoltajuussuhde_id_list': list(MaksutietoHuoltajuussuhde.objects
                                                       .filter(huoltajuussuhde__lapsi=lapsi)
                                                       .values_list('id', flat=True)),
            'maksutieto_id_list': list(Maksutieto.objects.filter(huoltajuussuhteet__lapsi=lapsi)
                                       .values_list('id', flat=True))
        }

    def _verify_lapsi_data_deletion(self, lapsi_data):
        self.assertEqual(Lapsi.objects.filter(id=lapsi_data['lapsi_id']).count(), 0)
        self.assertEqual(Varhaiskasvatuspaatos.objects.filter(id__in=lapsi_data['vakapaatos_id_list']).count(), 0)
        self.assertEqual(Varhaiskasvatussuhde.objects.filter(id__in=lapsi_data['vakasuhde_id_list']).count(), 0)
        self.assertEqual(Huoltajuussuhde.objects.filter(id__in=lapsi_data['huoltajuussuhde_id_list']).count(), 0)
        self.assertEqual(MaksutietoHuoltajuussuhde.objects
                         .filter(id__in=lapsi_data['maksutieto_huoltajuussuhde_id_list']).count(), 0)
        self.assertEqual(Maksutieto.objects.filter(id__in=lapsi_data['maksutieto_id_list']).count(), 0)
