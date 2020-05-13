import json
import responses

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from guardian.core import ObjectPermissionChecker
from rest_framework import status

from varda.misc import hash_string, encrypt_henkilotunnus
from varda.models import (VakaJarjestaja, Toimipaikka, PaosOikeus, Huoltaja, Huoltajuussuhde, Henkilo,
                          Lapsi, Varhaiskasvatuspaatos, Varhaiskasvatussuhde, Maksutieto)
from varda.permission_groups import assign_object_level_permissions
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient

# Well known test organizations (name corresponds to id)
test_org1 = "1.2.246.562.10.34683023489"  # "Tester2 organisaatio"
test_org2 = "1.2.246.562.10.93957375488"  # "Tester organisaatio"
test_org3 = "1.2.246.562.10.93957375486"  # "varda-testi organisaatio"
test_org4 = "1.2.246.562.10.93957375484"  # "Frontti organisaatio"


class VardaViewsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_index(self):
        resp = self.client.get('/')
        assert_status_code(resp, 200)

    def test_authentication_page(self):
        resp = self.client.get('/api-auth/login/')
        assert_status_code(resp, 200)

    def test_release_notes(self):
        resp = self.client.get('/varda/release-notes/')
        assert_status_code(resp, 200)

    def test_swagger_not_authenticated(self):
        resp = self.client.get('/varda/swagger/')
        assert_status_code(resp, 200)

    def test_swagger_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/varda/swagger/')
        assert_status_code(resp, 200)

    def test_varda_index(self):
        resp = self.client.get('/varda/')
        assert_status_code(resp, 200)

    def test_api_root_not_authenticated(self):
        resp = self.client.get('/api/v1/')
        assert_status_code(resp, 403)

    def test_api_root_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/')
        api_root = {
            "vakajarjestajat": "http://testserver/api/v1/vakajarjestajat/",
            "toimipaikat": "http://testserver/api/v1/toimipaikat/",
            "toiminnallisetpainotukset": "http://testserver/api/v1/toiminnallisetpainotukset/",
            "kielipainotukset": "http://testserver/api/v1/kielipainotukset/",
            "hae-henkilo": "http://testserver/api/v1/hae-henkilo/",
            "henkilot": "http://testserver/api/v1/henkilot/",
            "lapset": "http://testserver/api/v1/lapset/",
            "maksutiedot": "http://testserver/api/v1/maksutiedot/",
            "varhaiskasvatuspaatokset": "http://testserver/api/v1/varhaiskasvatuspaatokset/",
            "varhaiskasvatussuhteet": "http://testserver/api/v1/varhaiskasvatussuhteet/",
            "paos-toiminnat": "http://testserver/api/v1/paos-toiminnat/",
            "paos-oikeudet": "http://testserver/api/v1/paos-oikeudet/"
        }
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), api_root)

    def test_api_schema(self):
        resp = self.client.get('/api/v1/schema/')
        assert_status_code(resp, 403)

    def test_api_wrong_address(self):
        resp = self.client.get('/api/v1/wrong_address/')
        assert_status_code(resp, 404)

    def test_api_users_admin(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/users/')
        assert_status_code(resp, 200)

    def test_api_users_authenticated_but_not_admin(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/admin/users/')
        assert_status_code(resp, 403)

    def test_api_users_not_authenticated(self):
        resp = self.client.get('/api/admin/users/')
        assert_status_code(resp, 403)

    def test_api_get_user_data_anonymous(self):
        resp = self.client.get('/api/user/data/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'Authentication credentials were not provided.'})

    def test_api_get_user_data_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/user/data/')
        result_json = {'asiointikieli_koodi': 'sv',
                       'email': '',
                       'henkilo_oid': '1.2.345678910',
                       'kayttajatyyppi': 'VIRKAILIJA',
                       'kayttooikeudet': [
                           {
                               "organisaatio": "1.2.246.562.10.9395737548810",
                               "kayttooikeus": "VARDA-TALLENTAJA"
                           },
                           {
                               "organisaatio": "1.2.246.562.10.9395737548811",
                               "kayttooikeus": "VARDA-KATSELIJA"
                           },
                           {
                               "organisaatio": "1.2.246.562.10.9395737548810",
                               "kayttooikeus": "HUOLTAJATIETO_TALLENNUS"
                           },
                           {
                               "organisaatio": "1.2.246.562.10.34683023489",
                               "kayttooikeus": "HUOLTAJATIETO_TALLENNUS"
                           }
                       ],
                       'username': 'tester'
                       }
        assert_status_code(resp, 200)
        self.assertCountEqual(json.loads(resp.content), result_json)

    def test_api_get_token_anonymous(self):
        resp = self.client.get('/api/user/apikey/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {"detail": "Authentication credentials were not provided."})

    def test_api_get_token_authenticated(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/user/apikey/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), {"token": "916b7ca8f1687ec3462b4a35d0c5c6da0dbeedf3"})

    def test_api_refresh_token_anonymous(self):
        data = {
            "refresh_token": True
        }
        resp = self.client.post('/api/user/apikey/', data)
        assert_status_code(resp, 403)

    def test_api_refresh_token_authenticated(self):
        data = {
            "refresh_token": True
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/user/apikey/', data)
        assert_status_code(resp, 201)
        self.assertNotEqual(json.loads(resp.content)["token"], "916b7ca8f1687ec3462b4a35d0c5c6da0dbeedf3")

    def test_api_refresh_token_authenticated_faulty_input(self):
        data = {
            "refresh_token": False
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/user/apikey/', data)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"non_field_errors": ["Token was not refreshed."]})

    def test_api_refresh_token_authenticated_faulty_input_2(self):
        data = {}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/user/apikey/', data)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"non_field_errors": ["Token was not refreshed."]})

    def test_api_vakajarjestajat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/vakajarjestajat/')
        assert_status_code(resp, 200)

    def test_api_toimipaikat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/')
        assert_status_code(resp, 200)

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
        self.assertEqual(json.loads(resp.content)["count"], 5)

    def test_api_toimipaikat_permissions_2(self):
        """
        Keep this different than the test_api_toimipaikat_permissions_1, so that the
        permissions can be tested (different amount of objects visible to different users).
        """
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/')
        self.assertEqual(json.loads(resp.content)["count"], 4)

    def test_api_toimipaikat_permissions_3(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/1/')
        assert_status_code(resp, 200)

    def test_api_toimipaikat_permissions_4(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/toimipaikat/1/')
        assert_status_code(resp, 404)

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
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_toiminnallisetpainotukset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toiminnallisetpainotukset/')
        assert_status_code(resp, 200)

    def test_api_toiminnallisetpainotukset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toiminnallisetpainotukset/?toimintapainotus_koodi=tp01&muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_api_kielipainotukset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/kielipainotukset/')
        assert_status_code(resp, 200)

    def test_api_kielipainotukset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/kielipainotukset/?kielipainotus_koodi=EN&muutos_pvm=2017-02-10')
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_api_varhaiskasvatuspaatos_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/?jarjestamismuoto_koodi=jm02')
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_post_vakajarjestaja_with_invalid_yritysmuoto(self):
        user = User.objects.get(username='tester')
        with self.assertRaises(ValidationError) as validation_error:
            VakaJarjestaja.objects.create(
                nimi="Tester2 organisaatio",
                y_tunnus="8500570-7",
                organisaatio_oid="1.2.246.562.10.34683023489",
                kunta_koodi="091",
                sahkopostiosoite="organization@domain.com",
                tilinumero="FI37 1590 3000 0007 76",
                kayntiosoite="Testerkatu 2",
                kayntiosoite_postinumero="00001",
                kayntiosoite_postitoimipaikka="Testilä",
                postiosoite="Testerkatu 2",
                postitoimipaikka="Testilä",
                postinumero="00001",
                puhelinnumero="+358101234567",
                yritysmuoto='INVALID_OPTION',
                alkamis_pvm="2017-02-03",
                paattymis_pvm=None,
                changed_by=user
            )
        self.assertIn('Yritysmuoto INVALID_OPTION is not one of the permitted values.', str(validation_error.exception))

    def test_api_push_non_unique_henkilo_etunimi_correct_sukunimi_wrong(self):
        henkilo = {
            "henkilotunnus": "130266-915J",
            "etunimet": "Lasse Eemeli",
            "kutsumanimi": "Lasse",
            "sukunimi": "Palomäki"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 200)
        self.assertEqual(json.loads(resp2.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_correct_sukunimi_wrong_small_letters(self):
        henkilo = {
            "henkilotunnus": "130266-915J",
            "etunimet": "lasse eemeli",
            "kutsumanimi": "lasse",
            "sukunimi": "Palomäki"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 200)
        self.assertEqual(json.loads(resp2.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_correct(self):
        henkilo = {
            "henkilotunnus": "130266-915J",
            "etunimet": "Ville",
            "kutsumanimi": "Ville",
            "sukunimi": "Manner"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 200)
        self.assertEqual(json.loads(resp2.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_correct_small_letters(self):
        henkilo = {
            "henkilotunnus": "130266-915J",
            "etunimet": "Ville",
            "kutsumanimi": "Ville",
            "sukunimi": "manner"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/6/',
            'id': 6,
            'etunimet': 'Lasse',
            'kutsumanimi': 'Lasse',
            'sukunimi': 'Manner',
            'henkilo_oid': '',
            'syntyma_pvm': '1966-02-13',
            'lapsi': [],
            'tyontekija': []
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 200)
        self.assertEqual(json.loads(resp2.content), expected_response)

    def test_api_push_non_unique_henkilo_etunimi_wrong_sukunimi_wrong(self):
        henkilo = {
            "henkilotunnus": "130266-915J",
            "etunimet": "Hanna Karin",
            "kutsumanimi": "Karin",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester2').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {'detail': 'Person data does not match with the entered data'})

    def test_api_push_incorrect_varhaiskasvatuspaatos_date_sequence(self):
        vaka_paatos = {
            "lapsi": "/api/v1/lapset/3/",
            "vuorohoito_kytkin": False,
            "tuntimaara_viikossa": 33,
            "paivittainen_vaka_kytkin": True,
            "kokopaivainen_vaka_kytkin": True,
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2020-04-06",
            "alkamis_pvm": "2009-02-02",
            "paattymis_pvm": "2008-01-05"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', vaka_paatos)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"hakemus_pvm": ["hakemus_pvm must be before alkamis_pvm (or same)."]})

    def test_api_push_incorrect_varhaiskasvatussuhde_date_sequence(self):
        vaka_suhde = {
            "varhaiskasvatuspaatos": "/api/v1/varhaiskasvatuspaatokset/1/",
            "toimipaikka": "/api/v1/toimipaikat/1/",
            "alkamis_pvm": "2018-02-02",
            "paattymis_pvm": "2018-01-02",
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', vaka_suhde)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"paattymis_pvm": ["paattymis_pvm must be after alkamis_pvm (or same)"]})

    def test_api_push_incorrect_henkilo(self):  # wrong henkilotunnus-beginning
        henkilo = {
            "henkilotunnus": "123465-123P",
            "etunimet": "Hanna Karin",
            "kutsumanimi": "Karin",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {"henkilotunnus": ["123465-123P : Date incorrect."]})

    def test_api_push_incorrect_henkilo_2(self):  # wrong henkilotunnus-end; should end with P
        henkilo = {
            "henkilotunnus": "120465-123B",
            "etunimet": "Hanna Karin",
            "kutsumanimi": "Hanna",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {"henkilotunnus": ["120465-123B : ID-number or control character incorrect."]})

    def test_api_push_incorrect_henkilo_3(self):  # empty kutsumanimi
        henkilo = {
            "henkilotunnus": "030187-851M",
            "etunimet": "Hanna Karin",
            "kutsumanimi": "",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {'kutsumanimi': ['This field may not be blank.']})

    def test_api_push_incorrect_henkilo_4(self):  # missing kutsumanimi
        henkilo = {
            "henkilotunnus": "030187-851M",
            "etunimet": "Hanna Karin",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {'kutsumanimi': ['This field is required.']})

    def test_api_push_incorrect_henkilo_5(self):  # wrong kutsumanimi
        henkilo = {
            "henkilotunnus": "030187-851M",
            "etunimet": "Hanna Karin",
            "kutsumanimi": "HannaKarin",
            "sukunimi": "Palomäki"
        }
        client = SetUpTestClient('tester').client()
        resp2 = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {'kutsumanimi': ['Kutsumanimi is not valid.']})

    def test_api_push_henkilo_oid_etunimi_correct_sukunimi_wrong(self):
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.58672764848",
            "etunimet": "Susanna Maria",
            "kutsumanimi": "Susanna",
            "sukunimi": "Palomäki"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/3/',
            'id': 3,
            'etunimet': 'Susanna',
            'kutsumanimi': 'Susanna',
            'sukunimi': 'Virtanen',
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'syntyma_pvm': '2016-05-12',
            'lapsi': ['http://testserver/api/v1/lapset/2/'],
            'tyontekija': []
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_henkilo_oid_etunimi_wrong_sukunimi_correct(self):
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.58672764848",
            "etunimet": "Elina",
            "kutsumanimi": "Elina",
            "sukunimi": "Virtanen"
        }
        expected_response = {
            'url': 'http://testserver/api/v1/henkilot/3/',
            'id': 3,
            'etunimet': 'Susanna',
            'kutsumanimi': 'Susanna',
            'sukunimi': 'Virtanen',
            'henkilo_oid': '1.2.246.562.24.58672764848',
            'syntyma_pvm': '2016-05-12',
            'lapsi': ['http://testserver/api/v1/lapset/2/'],
            'tyontekija': []
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_push_henkilo_oid_etunimi_wrong_sukunimi_wrong(self):
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.58672764848",
            "etunimet": "Marko",
            "kutsumanimi": "Marko",
            "sukunimi": "Anttila"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'detail': 'Person data does not match with the entered data'})

    @responses.activate
    def test_api_push_henkilo_oid_not_in_oppijanumerorekisteri(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json="1.2.246.562.24.47279942111",
                      status=status.HTTP_201_CREATED
                      )
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={"hetu": None, "yksiloity": True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.47279942111",
            "etunimet": "Erkki",
            "kutsumanimi": "Erkki",
            "sukunimi": "Esimerkki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

    @responses.activate
    def test_api_push_henkilo_oid_not_yksiloity_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={"hetu": None, "yksiloity": False},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.47279942111",
            "etunimet": "Erkki",
            "kutsumanimi": "Erkki",
            "sukunimi": "Esimerkki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'henkilo_oid': ['Unfortunately this henkilo cannot be added. Is the henkilo yksiloity?']})

    @responses.activate
    def test_api_push_henkilo_oid_has_yksiloimatonhenkilotunnus_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={"hetu": '1', "yksiloityVTJ": False},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.47279942111",
            "etunimet": "Erkki",
            "kutsumanimi": "Erkki",
            "sukunimi": "Esimerkki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

    @responses.activate
    def test_api_push_henkilo_oid_has_yksiloityhenkilotunnus_in_oppijanumerorekisteri(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={"hetu": '1', "yksiloityVTJ": True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.47279942111",
            "etunimet": "Erkki",
            "kutsumanimi": "Erkki",
            "sukunimi": "Esimerkki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)

    @responses.activate
    def test_api_push_henkilo_oid_successful(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.47279942111/master',
                      json={"hetu": None, "yksiloity": True},
                      status=status.HTTP_200_OK
                      )
        henkilo = {
            "henkilo_oid": "1.2.246.562.24.47279942111",
            "etunimet": "Erkki",
            "kutsumanimi": "Erkki",
            "sukunimi": "Esimerkki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)
        self.assertIn('http://testserver/api/v1/henkilot/', json.loads(resp.content)['url'])

    def test_api_varhaiskasvatussuhteet(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatussuhteet/')
        assert_status_code(resp, 200)

    def test_api_varhaiskasvatussuhteet_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatussuhteet/?muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_lapset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/')
        assert_status_code(resp, 200)

    def test_hae_henkilo_empty_data(self):
        data = {}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['Either henkilotunnus or henkilo_oid is needed. But not both.']})

    def test_hae_henkilo_missing_keys(self):
        data = {'foo': 12}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['Either henkilotunnus or henkilo_oid is needed. But not both.']})

    def test_hae_henkilo_faulty_inputs(self):
        data = {'henkilotunnus': 'string', 'henkilo_oid': 'string'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['Either henkilotunnus or henkilo_oid is needed. But not both.']})

    def test_hae_henkilo_not_found_oid(self):
        data = {'henkilo_oid': '1.2.246.562.24.47279942111'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 404)
        self.assertEqual(json.loads(resp.content), {'detail': 'Henkilo was not found.'})

    def test_hae_henkilo_not_found_henkilotunnus(self):
        data = {'henkilotunnus': '290381-213W'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 404)
        self.assertEqual(json.loads(resp.content), {'detail': 'Henkilo was not found.'})

    def test_hae_henkilo_found_oid(self):
        data = {'henkilo_oid': '1.2.246.562.24.47279942650'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['url'], 'http://testserver/api/v1/henkilot/2/')

    def test_hae_henkilo_found_henkilotunnus(self):
        data = {'henkilotunnus': '020476-321F'}
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['url'], 'http://testserver/api/v1/henkilot/4/')

    def test_hae_henkilo_anonymous(self):
        data = {'henkilotunnus': '020476-321F'}
        resp = self.client.post('/api/v1/hae-henkilo/', data)
        assert_status_code(resp, 403)

    def test_api_huoltajat(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/admin/huoltajat/')
        assert_status_code(resp, 403)

    def test_api_huoltajat_filtering(self):
        # TO-DO: fix filtering
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/admin/huoltajat/?sukunimi=Virtane&kayntiosoite=Torikatu%2011&postitoimipaikka=Lappeenranta&kotikunta_koodi=034&muutos_pvm=2017-04-12')
        self.assertEqual(json.loads(resp.content)['count'], 4)

    def test_api_varhaiskasvatuspaatokset(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/')
        assert_status_code(resp, 200)

    def test_api_varhaiskasvatuspaatokset_filtering(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/varhaiskasvatuspaatokset/?hakemus_pvm=2017-01-12')
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_get_lapsi_json(self):
        lapsi_json = {
            "url": "http://testserver/api/v1/lapset/1/?format=json",
            "id": 1,
            "vakatoimija": None,
            "vakatoimija_oid": None,
            'oma_organisaatio': None,
            'oma_organisaatio_oid': None,
            'paos_kytkin': False,
            'paos_organisaatio': None,
            'paos_organisaatio_oid': None,
            "henkilo": "http://testserver/api/v1/henkilot/2/?format=json",
            "varhaiskasvatuspaatokset_top": [
                "http://testserver/api/v1/varhaiskasvatuspaatokset/1/?format=json"
            ]
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/lapset/1/?format=json')
        content = json.loads(resp.content)
        content.pop('muutos_pvm', None)
        self.assertEqual(content, lapsi_json)

    def test_api_oid_related_field_lapsi_nulls_allowed_in_oids(self):
        client = SetUpTestClient("tester2").client()
        data = {
            "henkilo": "/api/v1/henkilot/7/",
            "oma_organisaatio_oid": None,
            "paos_organisaatio_oid": None,
            "oma_organisaatio": "/api/v1/vakajarjestajat/1/",
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
        }

        resp = client.post("/api/v1/lapset/", json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio_oid'], '1.2.246.562.10.34683023489')
        self.assertEqual(json.loads(resp.content)['paos_organisaatio_oid'], '1.2.246.562.10.93957375488')

    def test_api_oid_related_field_lapsi_nulls_allowed_in_urls(self):
        client = SetUpTestClient("tester2").client()
        data = {
            "henkilo": "/api/v1/henkilot/7/",
            "oma_organisaatio_oid": test_org1,
            "paos_organisaatio_oid": test_org2,
            "oma_organisaatio": None,
            "paos_organisaatio": None,
        }

        resp = client.post("/api/v1/lapset/", json.dumps(data), content_type='application/json')
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
            "henkilotunnus": "230315A943J",
            "etunimet": "Pentti Jr",
            "kutsumanimi": "Pentti",
            "sukunimi": "Kivimäki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, 201)
        henkilo_url = json.loads(resp.content)['url']

        lapsi = {
            "henkilo": henkilo_url,
            "oma_organisaatio": None,
            "paos_organisaatio": None,
        }
        resp = client.post("/api/v1/lapset/", json.dumps(lapsi), content_type='application/json')
        self.assertEqual(resp.status_code, 201)

    def test_api_oid_related_field_create_lapsi_with_oids(self):
        client = SetUpTestClient("tester2").client()
        data = {
            "henkilo": "/api/v1/henkilot/7/",
            "oma_organisaatio_oid": test_org1,
            "paos_organisaatio_oid": test_org2,
        }

        resp = client.post("/api/v1/lapset/", json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/1/')
        self.assertEqual(json.loads(resp.content)['paos_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/2/')

    def test_api_oid_related_field_lapsi_change_denied(self):
        client = SetUpTestClient("tester2").client()

        data = {
            "url": "/api/v1/lapset/4/",
            "henkilo": "/api/v1/henkilot/9/",
            "oma_organisaatio_oid": test_org4,
            "paos_organisaatio_oid": test_org2,
        }

        resp = client.put("/api/v1/lapset/4/", json.dumps(data), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'oma_organisaatio': ['Changing of oma_organisaatio is not allowed']})

    def test_api_oid_related_field_lapsi_no_paos_organisaatio(self):
        client = SetUpTestClient("tester2").client()

        data = {
            "url": "/api/v1/lapset/4/",
            "henkilo": "/api/v1/henkilot/9/",
            "oma_organisaatio_oid": test_org4,
            # no paos_organisaatio_oid
        }

        resp = client.put("/api/v1/lapset/4/", json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_api_oid_related_field_lapsi_one_with_oid_one_with_url(self):
        client = SetUpTestClient("tester2").client()
        data = {
            "henkilo": "/api/v1/henkilot/7/",
            "oma_organisaatio_oid": test_org1,
            # no oma_organisaatio as it is via oid
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
        }

        resp = client.post("/api/v1/lapset/", json.dumps(data), content_type='application/json')
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertEqual(json.loads(resp.content)['oma_organisaatio'], 'http://testserver/api/v1/vakajarjestajat/1/')

    def test_api_oid_related_field_lapsi_roundtrip(self):
        client = SetUpTestClient("tester2").client()
        resp = client.get("/api/v1/lapset/4/?format=json")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)

        resp = client.put("/api/v1/lapset/4/", json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, 200)

    def test_api_oid_related_field_lapsi_different_values_error(self):
        client = SetUpTestClient("tester2").client()

        data = {
            "url": "/api/v1/lapset/4/",
            "henkilo": "/api/v1/henkilot/9/",
            "oma_organisaatio_oid": test_org1,  # id=1
            "paos_organisaatio_oid": None,
            "oma_organisaatio": "/api/v1/vakajarjestajat/4/",  # id=4
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
        }

        resp = client.put("/api/v1/lapset/4/", json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_api_oid_related_field_lapsi_invalid_oma_organisaatio_oid(self):
        client = SetUpTestClient("tester2").client()

        data = {
            "url": "/api/v1/lapset/4/",
            "henkilo": "/api/v1/henkilot/9/",
            "oma_organisaatio_oid": "some_invalid_oid",
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
        }

        resp = client.put("/api/v1/lapset/4/", json.dumps(data), content_type='application/json')
        self.assertEqual(resp.status_code, 400)

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
            "henkilotunnus": "180315A901Y",
            "etunimet": "Anton",
            "kutsumanimi": "Anton",
            "sukunimi": "Kivimäki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, 201)
        henkilo_url = json.loads(resp.content)['url']

        lapsi = {
            "henkilo": henkilo_url
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        self.assertEqual(resp2.status_code, 201)
        lapsi_url = json.loads(resp2.content)['url']

        varhaiskasvatuspaatos = {
            "lapsi": lapsi_url,
            "tuntimaara_viikossa": "37.5",
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-08-15",
            "alkamis_pvm": "2018-09-30"
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        self.assertEqual(resp3.status_code, 201)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        varhaiskasvatussuhde = {
            # no toimipaikka
            "varhaiskasvatuspaatos": varhaiskasvatuspaatos_url,
            "alkamis_pvm": "2018-10-01"
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        self.assertEqual(resp.status_code, 400)
        msg = json.loads(resp.content)['toimipaikka_oid']
        self.assertIn('Either this field or toimipaikka is required', msg)

    def test_api_get_lapsi_json_admin(self):
        """
        TODO: Sort nested resources // CSCVARDA-1113
        """
        lapsi_json = {
            "url": "http://testserver/api/v1/lapset/1/?format=json",
            "id": 1,
            "vakatoimija": None,
            "vakatoimija_oid": None,
            'oma_organisaatio': None,
            'oma_organisaatio_oid': None,
            'paos_kytkin': False,
            'paos_organisaatio': None,
            'paos_organisaatio_oid': None,
            "henkilo": "http://testserver/api/v1/henkilot/2/?format=json",
            "varhaiskasvatuspaatokset_top": [
                "http://testserver/api/v1/varhaiskasvatuspaatokset/1/?format=json"
            ],
            "huoltajuussuhteet": [
                "http://testserver/api/admin/huoltajuussuhteet/1/?format=json",
                "http://testserver/api/admin/huoltajuussuhteet/2/?format=json"
            ]
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
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
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
            "henkilotunnus": "210616A028D",
            "etunimet": "Anton",
            "kutsumanimi": "Anton",
            "sukunimi": "Kivimäki"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)
        henkilo_url = json.loads(resp.content)['url']

        lapsi = {
            "henkilo": henkilo_url
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, 201)
        lapsi_url = json.loads(resp2.content)['url']

        varhaiskasvatuspaatos = {
            "lapsi": lapsi_url,
            "tuntimaara_viikossa": "37.5",
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-08-15",
            "alkamis_pvm": "2018-09-30"
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp3, 201)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        varhaiskasvatussuhde = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "varhaiskasvatuspaatos": varhaiskasvatuspaatos_url,
            "alkamis_pvm": "2018-10-01"
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, 201)

    def test_api_push_lapsi_not_found_henkilo(self):
        client = SetUpTestClient('tester').client()
        henkilo_url = '/api/v1/henkilot/11111/'
        resp = client.get(henkilo_url)
        assert_status_code(resp, 404)

        lapsi = {
            "henkilo": henkilo_url
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, 400)
        self.assertEqual(json.loads(resp2.content), {'henkilo': ['Invalid hyperlink - Object does not exist.']})

    def test_api_push_lapsi_under_different_vakajarjestaja(self):
        client = SetUpTestClient('tester2').client()

        varhaiskasvatuspaatos = {
            "lapsi": "/api/v1/lapset/3/",
            "tuntimaara_viikossa": "37.5",
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-08-15",
            "alkamis_pvm": "2018-09-30"
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        vakapaatos_url = json.loads(resp.content)['url']

        varhaiskasvatussuhde = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "varhaiskasvatuspaatos": vakapaatos_url,
            "alkamis_pvm": "2019-10-01"
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['this lapsi is already under other vakajarjestaja. Please create a new one.']})
        assert_status_code(resp, 400)

    def test_api_push_lapsi_incorrect_paos(self):
        client = SetUpTestClient('tester').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['For PAOS-lapsi both oma_organisaatio and paos_organisaatio are needed.']})

        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['For PAOS-lapsi both oma_organisaatio and paos_organisaatio are needed.']})

    def test_api_push_lapsi_incorrect_paos_2(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/2/',
            "paos_organisaatio": '/api/v1/vakajarjestajat/1/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {'detail': 'There is no active paos-agreement.'})

    def test_api_push_lapsi_correct_paos(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, status.HTTP_200_OK)  # already created

    def test_api_push_lapsi_correct_paos_2(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)
        lapsi_url = json.loads(resp.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': 45,
            'jarjestamismuoto_koodi': 'jm02',
            'alkamis_pvm': '2018-09-01',
            'hakemus_pvm': '2018-08-08'
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, 201)
        vakapaatos_url = json.loads(resp.content)['url']

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/2/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01'
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['Vakajarjestaja is different than paos_organisaatio for lapsi.']})

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/1/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01'
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['There is no active paos-agreement to this toimipaikka.']})
        assert_status_code(resp, 400)

        varhaiskasvatussuhde = {
            'toimipaikka': 'http://testserver/api/v1/toimipaikat/5/',
            'varhaiskasvatuspaatos': vakapaatos_url,
            'alkamis_pvm': '2018-12-01'
        }
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, 201)

    def test_api_push_paos_lapsi_duplicate(self):
        client = SetUpTestClient('tester2').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)

        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, 200)  # Lapsi is already added
        self.assertEqual(json.loads(resp2.content)['henkilo'], 'http://testserver/api/v1/henkilot/1/')

    def test_api_push_vakapaatos_paos_lapsi(self):
        """
        Paos-tallentaja needs tallentaja-permissions on vakajarjestaja-level in oma_organisaatio.
        """
        group_obj = Group.objects.get(name='VARDA-TALLENTAJA_1.2.246.562.10.34683023489')
        user = User.objects.get(username='tester')
        user.groups.add(group_obj)

        client = SetUpTestClient('tester').client()
        lapsi = {
            'henkilo': '/api/v1/henkilot/1/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp, 201)
        lapsi_url = json.loads(resp.content)['url']

        varhaiskasvatuspaatos = {
            'lapsi': lapsi_url,
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm01',
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30'
        }
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        self.assertEqual(json.loads(resp.content), {'jarjestamismuoto_koodi': ['Invalid code for paos-lapsi.']})
        assert_status_code(resp, 400)

        varhaiskasvatuspaatos['jarjestamismuoto_koodi'] = 'jm02'
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, 201)

    """
    def test_api_push_vakapaatos_non_paos_lapsi(self):
        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/1/',
            'tuntimaara_viikossa': '37.5',
            'jarjestamismuoto_koodi': 'jm03',
            'hakemus_pvm': '2018-08-15',
            'alkamis_pvm': '2018-09-30'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        self.assertEqual(json.loads(resp.content), {'jarjestamismuoto_koodi': ['Invalid code for non-paos-lapsi.']})
        assert_status_code(resp, 400)
    """

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
            "accessAllowed": False,
            "errorMessage": "loggedInUserOid was not found"
        }
        post_data = {
            "personOidsForSamePerson": ["1", "1.2.246.562.24.47279942650"],
            "organisationOids": ["string"],
            "loggedInUserRoles": ["string"],
            "loggedInUserOid": "1.2.34567891"
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_no_person(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            "accessAllowed": False,
            "errorMessage": "Person not found"
        }
        post_data = {
            "personOidsForSamePerson": ["1", "1.2.246.562.24.490849013939"],
            "organisationOids": ["string"],
            "loggedInUserRoles": ["string"],
            "loggedInUserOid": "1.2.345678910"
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_multiple_person(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            "detail": "A server error occurred. Team is investigating this."
        }
        post_data = {
            "personOidsForSamePerson": ["1.2.246.562.24.49084901392", "1.2.246.562.24.47279942650"],
            "organisationOids": ["string"],
            "loggedInUserRoles": ["string"],
            "loggedInUserOid": "1.2.345678910"
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 500)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_no_permissions(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            "accessAllowed": False,
            "errorMessage": ""
        }
        post_data = {
            "personOidsForSamePerson": ["1", "1.2.246.562.24.47279942650"],
            "organisationOids": ["string"],
            "loggedInUserRoles": ["string"],
            "loggedInUserOid": "1.2.345678911"
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_api_external_permissions_has_permission(self):
        client = SetUpTestClient('tester').client()
        expected_response = {
            "accessAllowed": True,
            "errorMessage": ""
        }
        post_data = {
            "personOidsForSamePerson": ["1", "1.2.246.562.24.47279942650"],
            "organisationOids": ["string"],
            "loggedInUserRoles": ["string"],
            "loggedInUserOid": "1.2.345678910"
        }
        resp = client.post('/api/onr/external-permissions/', post_data)
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    @responses.activate
    def test_api_push_huoltaja_not_allowed(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": "050990-431L",
            "etunimet": "Tobias Jonas",
            "kutsumanimi": "Tobias",
            "sukunimi": "Virkkunen"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)
        henkilo_url = json.loads(resp.content)['url']

        huoltaja = {
            "henkilo": henkilo_url
        }
        client = SetUpTestClient('credadmin').client()
        resp1 = client.post('/api/admin/huoltajat/', huoltaja)
        assert_status_code(resp1, 405)

    def test_api_get_vakajarjestaja_json(self):
        vakajarjestaja_json = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "url": "http://testserver/api/v1/vakajarjestajat/1/?format=json",
                    "id": 1,
                    "nimi": "Tester2 organisaatio",
                    "y_tunnus": "8500570-7",
                    "yritysmuoto": "KUNTA",
                    "kunnallinen_kytkin": True,
                    "organisaatio_oid": "1.2.246.562.10.34683023489",
                    "kunta_koodi": "091",
                    "kayntiosoite": "Testerkatu 2",
                    "kayntiosoite_postinumero": "00001",
                    "kayntiosoite_postitoimipaikka": "Testilä",
                    "postiosoite": "Testerkatu 2",
                    "postinumero": "00001",
                    "postitoimipaikka": "Testilä",
                    "alkamis_pvm": "2017-02-03",
                    "paattymis_pvm": None,
                    "toimipaikat_top": [
                        "http://testserver/api/v1/toimipaikat/2/?format=json",
                        "http://testserver/api/v1/toimipaikat/3/?format=json"
                    ],
                    "sahkopostiosoite": "organization@domain.com",
                    "tilinumero": "FI37 1590 3000 0007 76",
                    "ipv4_osoitteet": None,
                    "ipv6_osoitteet": None,
                    "puhelinnumero": "+358101234567"
                }
            ]
        }
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/v1/vakajarjestajat/?format=json')
        content = json.loads(resp.content)
        content["results"][0].pop('muutos_pvm', None)
        self.assertEqual(content, vakajarjestaja_json)

    def test_api_get_toimipaikat_json(self):
        toimipaikka_json = {
            "url": "http://testserver/api/v1/toimipaikat/1/?format=json",
            "id": 1,
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/2/?format=json",
            "toiminnallisetpainotukset_top": [
                "http://testserver/api/v1/toiminnallisetpainotukset/1/?format=json"
            ],
            "kielipainotukset_top": [
                "http://testserver/api/v1/kielipainotukset/1/?format=json"
            ],
            "varhaiskasvatussuhteet_top": [
                "http://testserver/api/v1/varhaiskasvatussuhteet/1/?format=json",
                "http://testserver/api/v1/varhaiskasvatussuhteet/2/?format=json"
            ],
            "nimi": "Espoo",
            "organisaatio_oid": "1.2.246.562.10.9395737548810",
            "kayntiosoite": "Keilaranta 14",
            "kayntiosoite_postitoimipaikka": "Espoo",
            "kayntiosoite_postinumero": "02100",
            "postiosoite": "Keilaranta 14",
            "postitoimipaikka": "Espoo",
            "postinumero": "02100",
            "kunta_koodi": "091",
            "puhelinnumero": "+35810123456",
            "sahkopostiosoite": "test1@espoo.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj02",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": ["FI", "SV"],
            "jarjestamismuoto_koodi": [
                "jm01"
            ],
            "varhaiskasvatuspaikat": 120,
            "toiminnallinenpainotus_kytkin": True,
            "kielipainotus_kytkin": True,
            "alkamis_pvm": "2017-02-03",
            "paattymis_pvm": None,
            "lahdejarjestelma": 'ORGANISAATIO'
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/toimipaikat/1/?format=json')
        content = json.loads(resp.content)
        content.pop('muutos_pvm', None)
        self.assertEqual(content, toimipaikka_json)

    def test_api_get_toimipaikan_lapset_json(self):
        toimipaikan_lapset_json = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "etunimet": "Arpa Noppa",
                    "sukunimi": "Kuutio",
                    "henkilo_oid": "1.2.246.562.24.6815981182311",
                    "syntyma_pvm": "1948-05-11",
                    "oma_organisaatio_nimi": "Tester2 organisaatio",
                    "paos_organisaatio_nimi": "Tester organisaatio",
                    "lapsi_id": 4,
                    "lapsi_url": "http://testserver/api/v1/lapset/4/"
                }
            ]
        }
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/ui/toimipaikat/5/lapset/?format=json')
        self.assertEqual(json.loads(resp.content), toimipaikan_lapset_json)

    def test_api_toimipaikan_lapset_henkilo_nimi_filter(self):
        toimipaikan_lapset_henkilo_filter_json = {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "etunimet": "Susanna",
                    "sukunimi": "Virtanen",
                    "henkilo_oid": "1.2.246.562.24.58672764848",
                    "syntyma_pvm": "2016-05-12",
                    "oma_organisaatio_nimi": None,
                    "paos_organisaatio_nimi": None,
                    "lapsi_id": 2,
                    "lapsi_url": "http://testserver/api/v1/lapset/2/"
                }
            ]
        }
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/ui/toimipaikat/1/lapset/?search=sUSa+TA&format=json')
        self.assertEqual(json.loads(resp.content), toimipaikan_lapset_henkilo_filter_json)

    def test_api_get_henkilo_syntyma_pvm(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/henkilot/1/')
        henkilo = json.loads(resp.content)
        self.assertEqual(henkilo["syntyma_pvm"], "1956-04-12")

    def test_api_push_without_privilages(self):
        org = {
            "nimi": "Fake-Helsingin kaupunki",
            "y_tunnus": "0201244-2",
            "kunta_koodi": "091",
            "sahkopostiosoite": "fake@helsiki.fi",
            "tilinumero": "FI00 0000 0000 0000 99",
            "puhelinnumero": "112"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, 403)

    def test_api_push_incorrect_ipv4_address(self):
        org = {
            "nimi": "Fake-Helsingin kaupunki",
            "y_tunnus": "0920632-0",
            "sahkopostiosoite": "fake@helsiki.fi",
            "ipv4_osoitteet": ["192.168.0.1/"],
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "tilinumero": "FI59 5542 8540 0041 21",
            "puhelinnumero": "+3589123123"
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"ipv4_osoitteet": {'0': ["192.168.0.1/ : Not a valid IPv4-address."]}})

    def test_api_push_incorrect_ipv6_address(self):
        org = {
            "nimi": "Fake-Helsingin kaupunki",
            "y_tunnus": "0920632-0",
            "sahkopostiosoite": "fake@helsiki.fi",
            "ipv4_osoitteet": ["192.168.0.1/32"],
            "ipv6_osoitteet": ["2001:db8::/480"],
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "tilinumero": "FI59 5542 8540 0041 21",
            "puhelinnumero": "+3589112112"
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', org)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"ipv6_osoitteet": {'0': ["2001:db8::/480 : Not a valid IPv6-address."]}})

    def test_api_push_incorrect_jarjestamismuoto_koodi(self):
        varhaiskasvatuspaatos = {
            "lapsi": "http://testserver/api/v1/lapset/1/",
            "tuntimaara_viikossa": 45,
            "jarjestamismuoto_koodi": "no_code",
            "alkamis_pvm": "2018-09-01",
            "hakemus_pvm": "2018-08-08"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"jarjestamismuoto_koodi": ["Koodi has special characters. Not allowed."]})

    @responses.activate
    def test_api_push_correct_toimipaikka(self):
        # This test relies on organisaatio_client default error handling
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Testila",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj03",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": ["FI"],
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'nimi': ['Could not check toimipaikka-duplicates from Organisaatiopalvelu. Please try again later.']})

    def test_api_push_incorrect_toimipaikka(self):
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Testila",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj03",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": ["FI"],
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }

        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'kayntiosoite': ['This field is required.']})

        toimipaikka["kayntiosoite"] = ""
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'kayntiosoite': ['This field may not be blank.']})

        toimipaikka["kayntiosoite"] = "Jo"
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'kayntiosoite': ['Ensure this field has at least 3 characters.']})

        toimipaikka["kayntiosoite"] = "12345678901234567890123456789012345678901234567890123456789012345678901234567890123456789012345678901"
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'kayntiosoite': ['Ensure this field has no more than 100 characters.']})

    def test_api_push_incorrect_toimintamuoto(self):
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Testila",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj03",
            "toimintamuoto_koodi": "eitoimintaa",
            "asiointikieli_koodi": ["FI"],
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"toimintamuoto_koodi": ["eitoimintaa : Not a valid toimintamuoto_koodi."]})

    def test_api_push_incorrect_kasvatusopillinen_jarjestelma(self):
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Testila",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "ei kasvatusta",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": ["FI"],
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"kasvatusopillinen_jarjestelma_koodi": ["Koodi has spaces. Not allowed."]})

    def test_api_push_incorrect_toimintapainotus_koodi(self):
        toiminnallinenpainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "alkamis_pvm": "2018-07-01",
            "toimintapainotus_koodi": "noc"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"toimintapainotus_koodi": ["noc : Not a valid toimintapainotus_koodi."]})

    def test_push_api_incorrect_kieli_koodi(self):
        kielipainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "alkamis_pvm": "2018-07-01",
            "kielipainotus_koodi": "UU"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"kielipainotus_koodi": ["UU : Not a valid kieli_koodi."]})

    def test_push_api_incorrect_kielipainotus(self):
        kielipainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "kielipainotus_koodi": "FI",
            "alkamis_pvm": "2018-08-09",
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"kielipainotus": ["kielipainotus_koodi FI already exists for toimipaikka 1 on the defined time range."]})

    def test_push_correct_kielipainotus(self):
        kielipainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "kielipainotus_koodi": "SV",
            "alkamis_pvm": "2019-08-09"
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/kielipainotukset/', kielipainotus)
        assert_status_code(resp, 201)

    def test_push_api_incorrect_toiminnallinenpainotus(self):
        toiminnallinenpainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "toimintapainotus_koodi": "tp01",
            "alkamis_pvm": "2018-08-09",
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"toiminnallinenpainotus": ["toimintapainotus_koodi tp01 already exists for toimipaikka 1 on the defined time range."]})

    def test_push_correct_toiminnallinenpainotus(self):
        toiminnallinenpainotus = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "toimintapainotus_koodi": "tp02",
            "alkamis_pvm": "2019-08-09"
        }

        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/toiminnallisetpainotukset/', toiminnallinenpainotus)
        assert_status_code(resp, 201)

    def test_push_incorrect_iban_1(self):
        vakajarjestaja = {
            "nimi": "Testikylä",
            "y_tunnus": "2913769-2",
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "iban@ibanila.iban",
            "tilinumero": "FI92 2046 1800 0628 0",
            "puhelinnumero": "+358400987654"
        }   # too short IBAN
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"tilinumero": ["FI92 2046 1800 0628 0 : Not a valid IBAN code."]})

    def test_push_incorrect_iban_2(self):
        vakajarjestaja = {
            "nimi": "Testikylä",
            "y_tunnus": "2913769-2",
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "iban@ibanila.iban",
            "tilinumero": "IF92 2046 1800 0628 04",
            "puhelinnumero": "+358400987654"
        }  # IBAN country code incorrect
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"tilinumero": ["IF92 2046 1800 0628 04 : Not a valid IBAN code."]})

    def test_push_incorrect_iban_3(self):
        vakajarjestaja = {
            "nimi": "Testikylä",
            "y_tunnus": "2913769-2",
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "iban@ibanila.iban",
            "tilinumero": "FI92 2046 1800 0628 05",
            "puhelinnumero": "+358400987654"
        }   # last number in IBAN code changed
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"tilinumero": ["FI92 2046 1800 0628 05 : Not a valid IBAN code."]})

    def test_api_filter_vakajarjestajat_kunnallinen_kytkin(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/v1/vakajarjestajat/?kunnallinen_kytkin=True')
        result = json.loads(resp.content)
        count = result['count']
        kunnallinen_kytkin = result['results'][0]['kunnallinen_kytkin']
        self.assertEqual(count, 2)
        self.assertEqual(kunnallinen_kytkin, True)

        resp = client.get('/api/v1/vakajarjestajat/?kunnallinen_kytkin=False')
        result = json.loads(resp.content)
        count = result['count']
        kunnallinen_kytkin = result['results'][0]['kunnallinen_kytkin']
        self.assertEqual(count, 2)
        self.assertEqual(kunnallinen_kytkin, False)

        resp = client.get('/api/v1/vakajarjestajat/')
        result = json.loads(resp.content)
        count = result['count']
        self.assertEqual(count, 4)

    def test_push_incorrect_varhaiskasvatuspaatos_tuntimaara(self):
        varhaiskasvatuspaatos = {
            "lapsi": "http://testserver/api/v1/lapset/1/",
            "vuorohoito_kytkin": True,
            "tuntimaara_viikossa": 200,
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-07-30",
            "alkamis_pvm": "2018-10-01"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"tuntimaara_viikossa": ["Ensure this value is less than or equal to 120.0."]})

    def test_push_api_varhaiskasvatuspaatos_pikakasittely_kytkin_true(self):
        varhaiskasvatuspaatos = {
            "lapsi": "/api/v1/lapset/2/",
            "vuorohoito_kytkin": True,
            "tuntimaara_viikossa": 30,
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-01-01",
            "alkamis_pvm": "2018-01-15"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        json_data = json.loads(resp.content)
        assert_status_code(resp, 201)
        self.assertEqual(json_data['pikakasittely_kytkin'], True)

    def test_push_api_varhaiskasvatuspaatos_pikakasittely_kytkin_false(self):
        varhaiskasvatuspaatos = {
            "lapsi": "/api/v1/lapset/2/",
            "vuorohoito_kytkin": True,
            "tuntimaara_viikossa": 30,
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-01-01",
            "alkamis_pvm": "2018-01-16"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', json.dumps(varhaiskasvatuspaatos), content_type='application/json')
        json_data = json.loads(resp.content)
        assert_status_code(resp, 201)
        self.assertEqual(json_data['pikakasittely_kytkin'], False)

    def test_push_api_varhaiskasvatuspaatos_date_validation(self):
        client = SetUpTestClient('tester').client()

        varhaiskasvatuspaatos = {
            'lapsi': '/api/v1/lapset/2/',
            'vuorohoito_kytkin': True,
            'tuntimaara_viikossa': 30,
            'jarjestamismuoto_koodi': 'jm01'
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
            assert_status_code(resp, 201)

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
            assert_status_code(resp, 400)

    def test_delete_varhaiskasvatuspaatos(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/varhaiskasvatuspaatokset/1/')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"detail": "Cannot delete varhaiskasvatuspaatos. There are objects referencing it that need to be deleted first."})

    def test_push_api_varhaiskasvatussuhde_date_validation(self):
        client = SetUpTestClient('tester').client()

        varhaiskasvatussuhde = {
            'varhaiskasvatuspaatos': '/api/v1/varhaiskasvatuspaatokset/1/',
            'toimipaikka': '/api/v1/toimipaikat/1/'
        }

        # varhaiskasvatuspaatos with id 1: alkamis_pvm=2017-02-11, paattymis_pvm=2018-02-24

        ok_cases = [
            ('2017-10-14', '2018-02-12'),  # All correct
        ]

        fail_cases = [
            ('2017-04-01', None),          # No end date (vakapaatos has end date)
            ('2016-02-01', None),          # start before vakapaatos start
            ('2016-02-01', '2019-11-30'),  # start before vakapaatos start and end after vakapaatos end
            ('2017-12-31', '2020-11-30'),  # end after vakapaatos end
            ('1999-03-01', None),          # start before 2000
            ('1998-02-02', '1999-02-02'),  # all before 2000
            (None, '2018-01-01'),          # start missing
            (None, None),                  # all missing
        ]

        for (start, end) in ok_cases:
            varhaiskasvatussuhde.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatussuhde)
            resp = client.post('/api/v1/varhaiskasvatussuhteet/', data=data, content_type='application/json')
            assert_status_code(resp, 201)

            id = json.loads(resp.content)['id']
            Varhaiskasvatussuhde.objects.get(id=id).delete()

        for (start, end) in fail_cases:
            varhaiskasvatussuhde.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            data = json.dumps(varhaiskasvatussuhde)
            resp = client.post('/api/v1/varhaiskasvatussuhteet/', data=data, content_type='application/json')
            assert_status_code(resp, 400)

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
            'maksun_peruste_koodi': 'mp01',
            'paattymis_pvm': None,
            'palveluseteli_arvo': '0.00',
            'perheen_koko': 3,
            'url': 'http://testserver/api/v1/maksutiedot/1/'
        }

        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/maksutiedot/1/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), expected_response)

    def test_push_api_maksutieto_missing_huoltajat(self):
        maksutieto = {
            "huoltajat": [],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp01",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2019-01-01",
            "paattymis_pvm": "2020-01-01"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"huoltajat": {'non_field_errors': ['This list may not be empty.']}})

    def test_push_api_maksutieto_missing_huoltaja_hetu_or_oid(self):
        maksutieto = {
            "huoltajat": [{"etunimet": "Jukka", "sukunimi": "Pekkarinen"}],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp01",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2019-01-01",
            "paattymis_pvm": "2020-01-01"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"huoltajat": [{"non_field_errors": ["Either henkilotunnus or henkilo_oid is needed. But not both."]}]})

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
            'perheen_koko': 1,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 201)

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
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120.0,
            'asiakasmaksu': 0.0,
            'perheen_koko': 1,
            'alkamis_pvm': '2020-01-02',
            'paattymis_pvm': '2021-01-01',
            'tallennetut_huoltajat_count': 1,
            'ei_tallennetut_huoltajat_count': 2,
        }
        self.assertEqual(json.loads(resp.content), accepted_response)

    def test_push_api_maksutieto_correct_format_2(self):
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
            'perheen_koko': 1,
            'alkamis_pvm': '2018-02-23',
            'paattymis_pvm': '2018-02-24'
        }
        client = SetUpTestClient('tester').client()
        client.delete('/api/v1/maksutiedot/1/')  # remove 1 maksutieto, otherwise error: more than two active maksutieto
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 201)

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
            'maksun_peruste_koodi': 'mp02',
            'palveluseteli_arvo': 120.0,
            'asiakasmaksu': 0.0,
            'perheen_koko': 1,
            'alkamis_pvm': '2018-02-23',
            'paattymis_pvm': '2018-02-24',
            'tallennetut_huoltajat_count': 2,
            'ei_tallennetut_huoltajat_count': 1,
        }
        self.assertEqual(json.loads(resp.content), accepted_response)

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
        adminuser = User.objects.filter(username='credadmin')[0]
        client = SetUpTestClient('tester').client()
        oid_of_client = '1.2.246.562.10.9395737548810'

        lapsi_hetu = '180210A9437'
        huoltaja_hetu = '180200A941K'

        lapsi_henkilo = Henkilo.objects.create(
            henkilotunnus=encrypt_henkilotunnus(lapsi_hetu),
            henkilotunnus_unique_hash=hash_string(lapsi_hetu),
            henkilo_oid='1.2.246.562.24.158201550073654912',
            etunimet='Juniori',
            kutsumanimi='Juniori',
            sukunimi='Nieminen',
            changed_by=adminuser
        )
        lapsi = Lapsi.objects.create(
            henkilo=lapsi_henkilo,
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Henkilo, lapsi_henkilo)
        assign_object_level_permissions(oid_of_client, Lapsi, lapsi)

        huoltaja_henkilo = Henkilo.objects.create(
            henkilotunnus=encrypt_henkilotunnus(huoltaja_hetu),
            henkilotunnus_unique_hash=hash_string(huoltaja_hetu),
            henkilo_oid='1.2.246.562.24.158201550073654911',
            etunimet='Seniori',
            kutsumanimi='Seniori',
            sukunimi='Nieminen',
            changed_by=adminuser
        )
        huoltaja_obj = {
            'henkilotunnus': huoltaja_hetu,
            'etunimet': huoltaja_henkilo.etunimet,
            'sukunimi': huoltaja_henkilo.sukunimi,
            'kutsumanimi': huoltaja_henkilo.kutsumanimi
        }
        assign_object_level_permissions(oid_of_client, Henkilo, huoltaja_henkilo)
        huoltaja = Huoltaja.objects.create(
            henkilo=huoltaja_henkilo,
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Huoltaja, huoltaja)

        hs = Huoltajuussuhde.objects.create(
            huoltaja=huoltaja,
            lapsi=lapsi,
            voimassa_kytkin=True,
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Huoltajuussuhde, hs)

        toimipaikka_1 = Toimipaikka.objects.filter(organisaatio_oid='1.2.246.562.10.9395737548810')[0]

        vakapaatos = Varhaiskasvatuspaatos.objects.create(
            lapsi=lapsi,
            tuntimaara_viikossa=45,
            jarjestamismuoto_koodi='jm02',
            alkamis_pvm='2018-01-01',
            paattymis_pvm='2019-12-31',
            hakemus_pvm='2017-11-01',
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatuspaatos, vakapaatos)

        vakasuhde = Varhaiskasvatussuhde.objects.create(
            toimipaikka=toimipaikka_1,
            varhaiskasvatuspaatos=vakapaatos,
            alkamis_pvm='2018-01-01',
            paattymis_pvm='2019-12-31',
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatussuhde, vakasuhde)

        vakapaatos = Varhaiskasvatuspaatos.objects.create(
            lapsi=lapsi,
            tuntimaara_viikossa=45,
            jarjestamismuoto_koodi='jm02',
            alkamis_pvm='2021-01-01',
            hakemus_pvm='2017-11-01',
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatuspaatos, vakapaatos)

        vakasuhde = Varhaiskasvatussuhde.objects.create(
            toimipaikka=toimipaikka_1,
            varhaiskasvatuspaatos=vakapaatos,
            alkamis_pvm='2021-01-01',
            changed_by=adminuser
        )
        assign_object_level_permissions(oid_of_client, Varhaiskasvatussuhde, vakasuhde)

        """
        Now the test setup is finally done.
        Try to add a maksutieto in following cases:
        (And be sure to delete the added maksutieto after each success.)
        """

        ok_cases = [
            ('2018-02-01', '2018-07-01'),  # Within first vaka
            ('2018-01-01', '2018-12-31'),  # Exactly the first vaka
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
            'perheen_koko': 1,
        }

        for (start, end) in ok_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, 201)

            id = json.loads(resp.content)['id']
            Maksutieto.objects.get(id=id).delete()

        for (start, end) in fail_cases:
            maksutieto.update(
                alkamis_pvm=start,
                paattymis_pvm=end
            )

            resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
            assert_status_code(resp, 400)

    def test_push_api_maksutieto_too_many_active(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Pertti", "sukunimi": "Virtanen"},
                {"henkilotunnus": "110548-316P", "etunimet": "Juhani", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2020-01-02",
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'maksutieto': ['lapsi already has 2 active maksutieto during that time period']})

    def test_push_api_maksutieto_duplicate_hetus(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Pertti", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Juhani", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2020-01-02",
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'huoltajat': ['duplicated henkilotunnus given']})

    def test_push_api_maksutieto_duplicate_henkilo_oids(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"},
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pertti", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Juhani", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2020-01-02",
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'huoltajat': ['duplicated henkilo_oid given']})

    def test_push_api_maksutieto_missing_alkamis_pvm(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Pertti", "sukunimi": "Virtanen"},
                {"henkilotunnus": "110548-316P", "etunimet": "Juhani", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 0,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"alkamis_pvm": ['This field is required.']})

    def test_push_api_maksutieto_incorrect_paattymis_pvm(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"},
                {"henkilotunnus": "120386-109V", "etunimet": "Pertti", "sukunimi": "Virtanen"},
                {"henkilotunnus": "110548-316P", "etunimet": "Juhani", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 0,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2022-01-01",
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"paattymis_pvm": ['paattymis_pvm must be after alkamis_pvm (or same)']})

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
            'perheen_koko': 1,
            'alkamis_pvm': '2022-01-01',
            'paattymis_pvm': '2022-01-01'
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 201)

    def test_push_api_maksutieto_too_many_active_long_timeframe(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2008-01-02",
            "paattymis_pvm": "2021-01-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'maksutieto': ['lapsi already has 2 active maksutieto during that time period']})

    def test_push_api_maksutieto_too_many_active_short_timeframe(self):
        maksutieto = {
            "huoltajat": [
                {"henkilo_oid": "1.2.987654321", "etunimet": "Pauliina", "sukunimi": "Virtanen"}
            ],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2019-03-02",
            "paattymis_pvm": "2021-06-01"
        }
        client = SetUpTestClient('tester').client()
        maksutieto = json.dumps(maksutieto)
        client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        resp = client.post('/api/v1/maksutiedot/', maksutieto, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'maksutieto': ['lapsi already has 2 active maksutieto during that time period']})

    def test_push_api_maksutieto_no_matching_huoltajat(self):
        maksutieto = {
            "huoltajat": [{"henkilotunnus": "110494-9153", "etunimet": "Jukka", "sukunimi": "Pekkarinen"}],
            "lapsi": "/api/v1/lapset/1/",
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2019-01-01",
            "paattymis_pvm": "2020-01-01"
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"huoltajat": ['no matching huoltaja found']})

    @responses.activate
    def test_push_api_maksutieto_no_varhaiskasvatuspaatos(self):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED
                      )
        henkilo = {
            "henkilotunnus": "080576-922J",
            "etunimet": "Anni",
            "kutsumanimi": "Anni",
            "sukunimi": "Jussinen"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        assert_status_code(resp, 201)
        henkilo_url = json.loads(resp.content)['url']

        lapsi = {
            "henkilo": henkilo_url
        }
        resp2 = client.post('/api/v1/lapset/', lapsi)
        assert_status_code(resp2, 201)
        lapsi_url = json.loads(resp2.content)['url']
        maksutieto = {
            "huoltajat": [{"henkilotunnus": "110494-9153", "etunimet": "Jukka", "sukunimi": "Pekkarinen"}],
            "lapsi": lapsi_url,
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 1,
            "alkamis_pvm": "2019-01-01",
            "paattymis_pvm": "2020-01-01"
        }
        resp = client.post('/api/v1/maksutiedot/', json.dumps(maksutieto), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'Maksutieto': ['Lapsi has no Varhaiskasvatuspaatos. Add Varhaiskasvatuspaatos before adding maksutieto.']})

    def test_push_duplicate_paos_toiminta(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/2/",
            "paos_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/"
        }
        client = SetUpTestClient('tester3').client()
        resp = client.post('/api/v1/paos-toiminnat/', json.dumps(paos_toiminta), content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['oma_organisaatio and paos_organisaatio pair already exists.']})

    def test_push_duplicate_paos_toiminta_2(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/",
            "paos_toimipaikka": "http://localhost:8000/api/v1/toimipaikat/5/"
        }
        client = SetUpTestClient('tester4').client()
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'non_field_errors': ['oma_organisaatio and paos_toimipaikka pair already exists.']})

    def test_delete_paos_toiminta_with_toimija_and_push_correct_paos_toiminta_organisaatio(self):
        """
        Pre-requisite: Remove all paos-vakasuhteet from toimipaikka 5.
        """
        admin_client = SetUpTestClient('credadmin').client()
        resp = admin_client.delete('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)

        client = SetUpTestClient('tester3').client()
        vakajarjestaja_group = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
        toimipaikka = Toimipaikka.objects.get(id=5)
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should have view access to toimipaikka')
        delete_resp = client.delete('/api/v1/paos-toiminnat/1/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)
        # ObjectPermissionChecker caches results so we need to make sure we init a new one
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertFalse(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should no longer have view access to toimipaikka')
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)

        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/2/",
            "paos_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/"
        }
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta)
        assert_status_code(resp, 201)

    def test_delete_paostoiminta_with_toimija_view_access_stays_if_children_in_toimipaikka(self):
        client = SetUpTestClient('tester2').client()
        lapsi_json = {
            'henkilo': '/api/v1/henkilot/9/',
            'oma_organisaatio': '/api/v1/vakajarjestajat/1/',
            'paos_organisaatio': '/api/v1/vakajarjestajat/2/'
        }
        resp = client.post('/api/v1/lapset/', lapsi_json)
        assert_status_code(resp, status.HTTP_200_OK)  # lapsi is already created
        varhaiskasvatuspaatos = {
            "lapsi": json.loads(resp.content)['url'],
            "vuorohoito_kytkin": True,
            "tuntimaara_viikossa": "37.5",
            "jarjestamismuoto_koodi": "jm03",
            "hakemus_pvm": "2018-08-15",
            "alkamis_pvm": "2018-09-30"
        }
        resp3 = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp3, status.HTTP_201_CREATED)
        varhaiskasvatuspaatos_url = json.loads(resp3.content)['url']

        varhaiskasvatussuhde = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/5/",
            "varhaiskasvatuspaatos": varhaiskasvatuspaatos_url,
            "alkamis_pvm": "2018-10-01"
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
        admin_client = SetUpTestClient('credadmin').client()
        resp = admin_client.delete('/api/v1/varhaiskasvatussuhteet/4/')
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        resp2 = admin_client.delete('/api/v1/varhaiskasvatussuhteet/5/')
        assert_status_code(resp2, status.HTTP_204_NO_CONTENT)

        client = SetUpTestClient('tester4').client()
        vakajarjestaja_group = Group.objects.get(name='VARDA-PAAKAYTTAJA_1.2.246.562.10.34683023489')
        toimipaikka = Toimipaikka.objects.get(id=5)
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertTrue(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should have view access to toimipaikka')
        delete_resp = client.delete('/api/v1/paos-toiminnat/2/')
        assert_status_code(delete_resp, status.HTTP_204_NO_CONTENT)
        # ObjectPermissionChecker caches results so we need to make sure we init a new one
        checker = ObjectPermissionChecker(vakajarjestaja_group)
        self.assertFalse(checker.has_perm('view_toimipaikka', toimipaikka), 'Group should no longer have view access to toimipaikka')
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)

    def test_push_incorrect_paos_toiminta_organisaatio(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/2/",
            "paos_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/3/"
        }
        client = SetUpTestClient('tester3').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'paos_organisaatio': ['paos_organisaatio must be kunta or kuntayhtyma.']})

    def test_push_incorrect_paos_toiminta_toimipaikka(self):  # Not possible to vakajarjestaja's own toimipaikka
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/",
            "paos_toimipaikka": "http://localhost:8000/api/v1/toimipaikat/2/"
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'paos_toimipaikka': 'paos_toimipaikka can not be in oma_organisaatio'})

    def test_push_incorrect_paos_toiminta_toimipaikka_2(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/",
            "paos_toimipaikka": "http://localhost:8000/api/v1/toimipaikat/1/"
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'paos_toimipaikka': 'jarjestamismuoto_koodi is not jm02 or jm03'})

    def test_push_correct_paos_toiminta_toimipaikka(self):
        paos_toiminta = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/",
            "paos_toimipaikka": "http://localhost:8000/api/v1/toimipaikat/4/"
        }
        client = SetUpTestClient('tester4').client()
        paos_toiminta = json.dumps(paos_toiminta)
        resp = client.post('/api/v1/paos-toiminnat/', paos_toiminta, content_type='application/json')
        assert_status_code(resp, 201)

    def test_paos_toiminta_voimassa_kytkin_organisation_first(self):
        """
        VARDA_PAAKAYTTAJA from vakajarjestaja ID=2 (paos_toiminta_organisaatio) adds permission for
        paos_organisaatio to use their toimipaikat
        """
        paos_toiminta_organisaatio = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/2/",
            "paos_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/"
        }
        client_tester3 = SetUpTestClient('tester3').client()
        resp_1 = client_tester3.delete('/api/v1/paos-toiminnat/1/')  # duplicate must be removed first
        assert_status_code(resp_1, 204)

        """
        VARDA_PAAKAYTTAJA from vakajarjestaja ID=1 requests permission for VARDA_TALLENTAJA or VARDA_PALVELUKAYTTAJA
        to add PAOS-lapset to toimipaikka (ID=5)
        """
        paos_toiminta_toimipaikka = {
            "oma_organisaatio": "http://localhost:8000/api/v1/vakajarjestajat/1/",
            "paos_toimipaikka": "http://localhost:8000/api/v1/toimipaikat/5/"
        }
        client_tester4 = SetUpTestClient('tester4').client()
        resp_2 = client_tester4.delete('/api/v1/paos-toiminnat/2/')  # duplicate must be removed first
        assert_status_code(resp_2, 204)

        paos_toiminta_organisaatio = json.dumps(paos_toiminta_organisaatio)
        resp_organisaatio = client_tester3.post('/api/v1/paos-toiminnat/', paos_toiminta_organisaatio, content_type='application/json')
        resp_voimassa_kytkin = client_tester3.get('/api/v1/paos-oikeudet/1/')
        resp_voimassa_kytkin = json.loads(resp_voimassa_kytkin.content)['voimassa_kytkin']
        assert_status_code(resp_organisaatio, 201)
        self.assertEqual(resp_voimassa_kytkin, False)

        paos_toiminta_toimipaikka = json.dumps(paos_toiminta_toimipaikka)
        resp_toimipaikka = client_tester4.post('/api/v1/paos-toiminnat/', paos_toiminta_toimipaikka, content_type='application/json')
        resp_voimassa_kytkin = client_tester4.get('/api/v1/paos-oikeudet/1/')
        resp_voimassa_kytkin = json.loads(resp_voimassa_kytkin.content)['voimassa_kytkin']
        assert_status_code(resp_toimipaikka, 201)
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
        assert_status_code(remove_voimassa_kytkin, 204)

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
        self.assertEqual(resp_paos_toiminnat_count, 2)

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
            "tallentaja_organisaatio": "/api/v1/vakajarjestajat/2/"
        }
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        resp_paos_oikeus_tallentaja_organisaatio = json.loads(resp_paos_oikeus.content)['tallentaja_organisaatio']
        assert_status_code(resp_paos_oikeus, 200)
        self.assertEqual(resp_paos_oikeus_tallentaja_organisaatio, "http://testserver/api/v1/vakajarjestajat/2/")

    def test_paos_oikeus_change_tallentaja_organisaatio_already_is_same(self):
        client_tester4 = SetUpTestClient('tester4').client()
        tallentaja_organisaatio = {"tallentaja_organisaatio": "/api/v1/vakajarjestajat/1/"}
        accepted_response = {
            "tallentaja_organisaatio": "tallentaja is already set for vakajarjestaja 1"
        }
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        resp_paos_oikeus_data = json.loads(resp_paos_oikeus.content)
        assert_status_code(resp_paos_oikeus, 400)
        self.assertEqual(resp_paos_oikeus_data, accepted_response)

    def test_paos_oikeus_change_tallentaja_organisaatio_not_either_organisation(self):
        client_tester4 = SetUpTestClient('tester4').client()
        tallentaja_organisaatio = {"tallentaja_organisaatio": "/api/v1/vakajarjestajat/4/"}
        accepted_response = {
            "tallentaja_organisaatio": "tallentaja_organisaatio must be either jarjestaja_kunta_organisaatio or tuottaja_organisaatio"
        }
        tallentaja_organisaatio = json.dumps(tallentaja_organisaatio)
        resp_paos_oikeus = client_tester4.patch('/api/v1/paos-oikeudet/1/', tallentaja_organisaatio, content_type='application/json')
        resp_paos_oikeus_data = json.loads(resp_paos_oikeus.content)
        assert_status_code(resp_paos_oikeus, 400)
        self.assertEqual(resp_paos_oikeus_data, accepted_response)

    def test_push_incorrect_puhelinnumero(self):
        vakajarjestaja = {
            "nimi": "Testikylä",
            "y_tunnus": "2913769-2",
            "kunta_koodi": "091",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "iban@ibanila.iban",
            "tilinumero": "FI92 2046 1800 0628 04",
            "puhelinnumero": "+359400987654"
        }
        client = SetUpTestClient('credadmin').client()
        resp = client.post('/api/v1/vakajarjestajat/', vakajarjestaja)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"puhelinnumero": ["+359400987654 : Not a valid Finnish phone number."]})

    def test_api_delete_toimipaikka_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/toimipaikat/1/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {"detail": 'You do not have permission to perform this action.'})

    def test_api_delete_toimipaikka_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.delete('/api/v1/toimipaikat/3/')
        assert_status_code(resp, 403)
        self.assertEqual(json.loads(resp.content), {"detail": 'You do not have permission to perform this action.'})

    def test_api_delete_lapsi_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.delete('/api/v1/lapset/1/')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"detail": "Cannot delete lapsi. There are maksutieto/maksutietoja referencing it that need to be deleted first."})

    def test_api_delete_lapsi_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.delete('/api/v1/lapset/4/')
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {"detail": "Cannot delete lapsi. There are objects referencing it that need to be deleted first."})

    def test_api_delete_lapsi_3(self):
        Huoltajuussuhde.objects.get(id=5).delete()  # This is required before lapsi can be removed.
        client = SetUpTestClient('tester2').client()
        client.delete('/api/v1/varhaiskasvatussuhteet/4/')
        client.delete('/api/v1/varhaiskasvatuspaatokset/4/')
        resp = client.delete('/api/v1/lapset/4/')
        assert_status_code(resp, 204)

    def test_api_push_too_many_overlapping_varhaiskasvatuspaatos(self):
        varhaiskasvatuspaatos = {
            "lapsi": "http://testserver/api/v1/lapset/1/",
            "tuntimaara_viikossa": 40,
            "jarjestamismuoto_koodi": "jm01",
            "hakemus_pvm": "2018-09-15",
            "alkamis_pvm": "2018-10-20"
        }
        client = SetUpTestClient('tester').client()
        client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        resp = client.post('/api/v1/varhaiskasvatuspaatokset/', varhaiskasvatuspaatos)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'varhaiskasvatuspaatos': ['Lapsi 1 has already 3 overlapping varhaiskasvatuspaatos on the defined time range.']})

    def test_api_push_too_many_varhaiskasvatussuhde(self):
        varhaiskasvatussuhde = {
            "toimipaikka": "http://testserver/api/v1/toimipaikat/1/",
            "varhaiskasvatuspaatos": "http://testserver/api/v1/varhaiskasvatuspaatokset/2/",
            "alkamis_pvm": "2018-12-01"
        }
        client = SetUpTestClient('tester').client()
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        resp = client.post('/api/v1/varhaiskasvatussuhteet/', varhaiskasvatussuhde)
        assert_status_code(resp, 400)
        self.assertEqual(json.loads(resp.content), {'varhaiskasvatussuhde': ["Lapsi 2 has already 3 overlapping varhaiskasvatussuhde on the defined time range."]})

    def test_api_get_vakajarjestaja_yhteenveto(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/api/v1/vakajarjestajat/2/yhteenveto/')
        accepted_response = {
            "vakajarjestaja_nimi": "Tester organisaatio",
            "lapset_lkm": 3,
            "lapset_vakapaatos_voimassaoleva": 3,
            "lapset_vakasuhde_voimassaoleva": 3,
            "lapset_vuorohoidossa": 0,
            "lapset_palveluseteli_ja_ostopalvelu": 3,
            "lapset_maksutieto_voimassaoleva": 3,
            "toimipaikat_voimassaolevat": 3,
            "toimipaikat_paattyneet": 0,
            "toimintapainotukset_maara": 2,
            "kielipainotukset_maara": 2
        }
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), accepted_response)

    """ organisaatiopalvelu-integraatio
    def test_api_multiple_asiointikieli(self):
        toimipaikka = {
            "vakajarjestaja": "http://testserver/api/v1/vakajarjestajat/1/",
            "nimi": "Testila",
            "kunta_koodi": "091",
            "puhelinnumero": "+35892323234",
            "kayntiosoite": "Testerkatu 2",
            "kayntiosoite_postinumero": "00001",
            "kayntiosoite_postitoimipaikka": "Testilä",
            "postiosoite": "Testerkatu 2",
            "postitoimipaikka": "Testilä",
            "postinumero": "00001",
            "sahkopostiosoite": "hel1234@helsinki.fi",
            "kasvatusopillinen_jarjestelma_koodi": "kj03",
            "toimintamuoto_koodi": "tm01",
            "asiointikieli_koodi": ["FI", "SV", "EN"],
            "jarjestamismuoto_koodi": ["jm01", "jm03"],
            "varhaiskasvatuspaikat": 1000,
            "alkamis_pvm": "2018-01-01"
        }
        client = SetUpTestClient('tester2').client()
        resp = client.post('/api/v1/toimipaikat/', toimipaikka)
        assert_status_code(resp, 400)  # TODO: Change this when Org.palvelu-mocking is done! (Original: 201)
    """

    def test_api_filter_asiointikieli_1(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get("/api/v1/toimipaikat/?asiointikieli_koodi=SV")
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_filter_asiointikieli_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get("/api/v1/toimipaikat/?asiointikieli_koodi=S")
        self.assertEqual(json.loads(resp.content)['count'], 0)

    def test_api_filter_jarjestamismuotokoodi_1(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get("/api/v1/toimipaikat/?jarjestamismuoto_koodi=jm01")
        self.assertEqual(json.loads(resp.content)['count'], 2)

    def test_api_filter_jarjestamismuotokoodi_2(self):
        client = SetUpTestClient('tester2').client()
        resp = client.get("/api/v1/toimipaikat/?jarjestamismuoto_koodi=jm0")
        self.assertEqual(json.loads(resp.content)['count'], 0)

    def test_api_ui_vakajarjestajat(self):
        client = SetUpTestClient('credadmin').client()
        resp = client.get('/api/ui/vakajarjestajat/')
        assert_status_code(resp, 200)

        admin_vakajarjestajat = [
            {
                "nimi": "Frontti organisaatio",
                "id": 4,
                "url": 'http://testserver/api/v1/vakajarjestajat/4/',
                "organisaatio_oid": "1.2.246.562.10.93957375484",
                "kunnallinen_kytkin": True,
                "y_tunnus": "2156233-6"
            },
            {
                "nimi": "Tester organisaatio",
                "id": 2,
                "url": 'http://testserver/api/v1/vakajarjestajat/2/',
                "organisaatio_oid": "1.2.246.562.10.93957375488",
                "kunnallinen_kytkin": False,
                "y_tunnus": "1825748-8"
            },
            {
                "nimi": "Tester2 organisaatio",
                "id": 1,
                "url": 'http://testserver/api/v1/vakajarjestajat/1/',
                "organisaatio_oid": "1.2.246.562.10.34683023489",
                "kunnallinen_kytkin": True,
                "y_tunnus": "8500570-7"
            },
            {
                "nimi": "varda-testi organisaatio",
                "id": 3,
                "url": 'http://testserver/api/v1/vakajarjestajat/3/',
                "organisaatio_oid": "1.2.246.562.10.93957375486",
                "kunnallinen_kytkin": False,
                "y_tunnus": "2617455-1"
            }
        ]
        self.assertCountEqual(json.loads(resp.content), admin_vakajarjestajat)

    """
    Koodisto testit
    """
    def test_api_get_koodisto(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/koodisto/api/v1/koodit/')
        assert_status_code(resp, 200)
        self.assertEqual(len(json.loads(resp.content)), 13)
        self.assertEqual(json.loads(resp.content)['tyoaika_koodit'], ['ta01', 'ta02'])

    # TODO: Reporting related view-tests

    """
    def test_reporting_view(self):
        client = SetUpTestClient("kelaetuusmaksatus").client()
        resp = client.get('/reporting/api/v1/kelaraportti/')
        assert_status_code(resp, 403)

    def test_reporting_api(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/reporting/api/v1/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content), {"kelaraportti": "http://testserver/reporting/api/v1/kelaraportti/"})

    def test_reporting_api_kelaraportti_1(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/reporting/api/v1/kelaraportti/')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_reporting_api_kelaraportti_2(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/reporting/api/v1/kelaraportti/?kotikunta_koodi=034')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['count'], 1)

    def test_reporting_api_kelaraportti_3(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/reporting/api/v1/kelaraportti/?henkilotunnus=010114A0013')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['count'], 1)


    def test_reporting_api_kelaraportti_4(self):
        client = SetUpTestClient('tester').client()
        resp = client.get('/reporting/api/v1/lapset-ryhmittain/?kotikunta_koodi=034&henkilotunnus=010114A0013')
        assert_status_code(resp, 200)
        self.assertEqual(json.loads(resp.content)['count'], 1)
    """
