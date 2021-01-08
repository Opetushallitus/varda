import json

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from varda.models import Z3_AdditionalCasUserFields, Z5_AuditLog, VakaJarjestaja
from varda.unit_tests.test_utils import assert_status_code
from django.contrib.auth.models import User
from varda.custom_auth import _oppija_post_login_handler


class SetUpTestClient:

    def __init__(self, name):
        self.name = name

    def client(self):
        user = User.objects.filter(username=self.name)[0]
        api_c = APIClient()
        api_c.force_authenticate(user=user)
        return api_c


class VardaOppijaViewsTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_api_lapsen_huoltaja_get_data(self):
        # Mock Huoltaja login
        user_suomifi = User.objects.create(username='suomi.fi#010280-952L#010215A951T', is_staff=False, is_active=True)
        user_suomifi.personOid = '1.2.246.562.24.86012997950'
        user_suomifi.impersonatorPersonOid = '1.2.246.562.24.1234567890'
        _oppija_post_login_handler(user_suomifi)

        client_suomifi_tester = SetUpTestClient('suomi.fi#010280-952L#010215A951T').client()
        accepted_response = {
            "henkilo": {
                "henkilo_oid": "1.2.246.562.24.86012997950",
                "henkilotunnus": "010215A951T",
                "etunimet": "Teila Aamu Runelma",
                "kutsumanimi": "Teila",
                "sukunimi": "Testilä",
                "aidinkieli_koodi": "FI",
                "sukupuoli_koodi": "1",
                "syntyma_pvm": "2018-03-11",
                "kotikunta_koodi": "915",
                "katuosoite": "Koivukuja 4",
                "postinumero": "01230",
                "postitoimipaikka": "Vantaa"
            },
            "voimassaolevia_varhaiskasvatuspaatoksia": 1,
            "lapset": [
                {
                    "yhteysosoite": "frontti@end.com",
                    "varhaiskasvatuksen_jarjestaja": "Frontti organisaatio",
                    "aktiivinen_toimija": True,
                    "varhaiskasvatuspaatokset": [
                        {
                            "alkamis_pvm": "2019-11-11",
                            "hakemus_pvm": "2019-01-01",
                            "paattymis_pvm": "2019-12-22",
                            "paivittainen_vaka_kytkin": True,
                            "kokopaivainen_vaka_kytkin": False,
                            "tilapainen_vaka_kytkin": False,
                            "jarjestamismuoto_koodi": "jm04",
                            "vuorohoito_kytkin": False,
                            "pikakasittely_kytkin": True,
                            "tuntimaara_viikossa": 30.5,
                            "varhaiskasvatussuhteet": []
                        }
                    ]
                },
                {
                    "yhteysosoite": "organization@domain.com",
                    "varhaiskasvatuksen_jarjestaja": "Tester organisaatio",
                    "aktiivinen_toimija": True,
                    "varhaiskasvatuspaatokset": [
                        {
                            "alkamis_pvm": "2019-11-11",
                            "hakemus_pvm": "2019-11-01",
                            "paattymis_pvm": "2019-12-22",
                            "paivittainen_vaka_kytkin": True,
                            "kokopaivainen_vaka_kytkin": False,
                            "tilapainen_vaka_kytkin": False,
                            "jarjestamismuoto_koodi": "jm03",
                            "vuorohoito_kytkin": False,
                            "pikakasittely_kytkin": True,
                            "tuntimaara_viikossa": 30.5,
                            "varhaiskasvatussuhteet": [
                                {
                                    "alkamis_pvm": "2018-05-01",
                                    "paattymis_pvm": "2019-10-24",
                                    "toimipaikka": {
                                        "toimipaikka_nimi": "Espoo",
                                        "toimipaikka_kunta_koodi": "091"
                                    },
                                    "yhteysosoite": "test1@espoo.fi"
                                },
                                {
                                    "alkamis_pvm": "2018-09-05",
                                    "paattymis_pvm": "2019-04-20",
                                    "toimipaikka": {
                                        "toimipaikka_nimi": "Espoo_2",
                                        "toimipaikka_kunta_koodi": "091"
                                    },
                                    "yhteysosoite": "organization@domain.com"
                                },
                            ]
                        }
                    ]
                },
                {
                    "yhteysosoite": "organization@domain.com",
                    "varhaiskasvatuksen_jarjestaja": "Tester2 organisaatio",
                    "aktiivinen_toimija": True,
                    "varhaiskasvatuspaatokset": [
                        {
                            "alkamis_pvm": "2018-10-05",
                            "hakemus_pvm": "2018-10-05",
                            "paattymis_pvm": None,
                            "paivittainen_vaka_kytkin": True,
                            "kokopaivainen_vaka_kytkin": True,
                            "tilapainen_vaka_kytkin": False,
                            "jarjestamismuoto_koodi": "jm03",
                            "vuorohoito_kytkin": False,
                            "pikakasittely_kytkin": False,
                            "tuntimaara_viikossa": 39.0,
                            "varhaiskasvatussuhteet": [
                                {
                                    "alkamis_pvm": "2019-11-11",
                                    "paattymis_pvm": None,
                                    "toimipaikka": {
                                        "toimipaikka_nimi": "Espoo_3",
                                        "toimipaikka_kunta_koodi": "091"
                                    },
                                    "yhteysosoite": "organization@domain.com"
                                }
                            ]
                        }
                    ]
                },
                {
                    "yhteysosoite": "organization@domain.com",
                    "varhaiskasvatuksen_jarjestaja": "Tester2 organisaatio",
                    "aktiivinen_toimija": True,
                    "varhaiskasvatuspaatokset": [
                        {
                            "alkamis_pvm": "2019-02-11",
                            "hakemus_pvm": "2019-01-01",
                            "paattymis_pvm": "2019-10-24",
                            "paivittainen_vaka_kytkin": None,
                            "kokopaivainen_vaka_kytkin": None,
                            "tilapainen_vaka_kytkin": False,
                            "jarjestamismuoto_koodi": "jm03",
                            "vuorohoito_kytkin": True,
                            "pikakasittely_kytkin": True,
                            "tuntimaara_viikossa": 37.5,
                            "varhaiskasvatussuhteet": [
                                {
                                    "alkamis_pvm": "2018-02-11",
                                    "paattymis_pvm": "2019-02-24",
                                    "toimipaikka": {
                                        "toimipaikka_nimi": "Tester2 toimipaikka",
                                        "toimipaikka_kunta_koodi": "091"
                                    },
                                    "yhteysosoite": "test2@domain.com"
                                }
                            ]
                        }
                    ]
                },
            ]
        }
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/1.2.246.562.24.86012997950/',
                                                            content_type='application/json')
        resp_json = json.loads(resp_huoltajanlapsi_api.content)
        # Remove ID:s because they tend to change and sort for expected behaviour
        resp_json['lapset'] = sorted(resp_json['lapset'], key=lambda key: (key['varhaiskasvatuksen_jarjestaja'], key['varhaiskasvatuspaatokset'][0]['alkamis_pvm']))
        for lapsi in resp_json['lapset']:
            del lapsi['id']
            lapsi['varhaiskasvatuspaatokset'] = sorted(lapsi['varhaiskasvatuspaatokset'], key=lambda key: key['alkamis_pvm'])
            for vakapaatos in lapsi['varhaiskasvatuspaatokset']:
                del vakapaatos['id']
                vakapaatos['varhaiskasvatussuhteet'] = sorted(vakapaatos['varhaiskasvatussuhteet'], key=lambda key: key['alkamis_pvm'])
                for vakasuhde in vakapaatos['varhaiskasvatussuhteet']:
                    del vakasuhde['id']

        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_200_OK)
        self.assertEqual(resp_json, accepted_response)
        request_count = Z5_AuditLog.objects.filter(user__username='suomi.fi#010280-952L#010215A951T').count()
        self.assertEqual(request_count, 1)

    def test_get_huoltajanlapsi_data_no_permission(self):
        client = SetUpTestClient('tester2').client()
        resp_huoltajanlapsi_api = client.get('/api/oppija/v1/huoltajanlapsi/1.2.246.562.24.86012997950/',
                                             content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_403_FORBIDDEN)

    def test_api_lapsen_huoltaja_cant_access_wrong_lapsi(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        other_lapsi_oid = '1.2.246.562.24.47279942650'
        huoltaja_oid = ''
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/{}/'.format(other_lapsi_oid),
                                                            content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_403_FORBIDDEN)

    def test_api_lapsen_huoltaja_no_oid(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = ''
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/{}/'.format(lapsi_oid),
                                                            content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_200_OK)

        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = None
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/{}/'.format(lapsi_oid),
                                                            content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_200_OK)

        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = None
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid, is_set_huoltaja_oid=False)
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/{}/'.format(lapsi_oid),
                                                            content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_200_OK)

        request_count = Z5_AuditLog.objects.filter(user__username='suomi.fi#010280-952L#010215A951T').count()
        self.assertEqual(request_count, 3)

    def test_vakajarjestaja_paattymis_pvm_yhteystieto_osoite(self):
        lapsi_oid = '1.2.246.562.24.86012997950'
        huoltaja_oid = ''
        vakajarjestaja_oid = '1.2.246.562.10.93957375484'
        client_suomifi_tester = self._create_oppija_cas_user_and_assert_huoltaja_oid(huoltaja_oid, lapsi_oid)
        # add end date
        vakajarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=vakajarjestaja_oid)
        vakajarjestaja_nimi = vakajarjestaja.nimi
        vakajarjestaja.paattymis_pvm = '2019-01-01'
        vakajarjestaja.save()
        resp_huoltajanlapsi_api = client_suomifi_tester.get('/api/oppija/v1/huoltajanlapsi/{}/'.format(lapsi_oid),
                                                            content_type='application/json')
        assert_status_code(resp_huoltajanlapsi_api, status.HTTP_200_OK)
        resp_json = json.loads(resp_huoltajanlapsi_api.content)
        for lapsi in resp_json['lapset']:
            if lapsi['varhaiskasvatuksen_jarjestaja'] == vakajarjestaja_nimi:
                self.assertEqual(lapsi['yhteysosoite'], None)
                self.assertFalse(lapsi['aktiivinen_toimija'])

    def _create_oppija_cas_user_and_assert_huoltaja_oid(self, huoltaja_oid, lapsi_oid, is_set_huoltaja_oid=True):
        user_suomifi, is_created = User.objects.get_or_create(username='suomi.fi#010280-952L#010215A951T',
                                                              is_staff=False,
                                                              is_active=True)
        user_suomifi.personOid = lapsi_oid
        if is_set_huoltaja_oid:
            user_suomifi.impersonatorPersonOid = huoltaja_oid
        _oppija_post_login_handler(user_suomifi)
        expected_huoltaja_oid = (Z3_AdditionalCasUserFields.objects
                                 .filter(user=user_suomifi)
                                 .values_list('huoltaja_oid', flat=True)
                                 .first()
                                 )
        self.assertEqual(expected_huoltaja_oid, huoltaja_oid)
        return SetUpTestClient(user_suomifi.username).client()
