import responses
from django.contrib.auth.models import User, Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from varda.enums.tietosisalto_ryhma import TietosisaltoRyhma
from varda.models import Z4_CasKayttoOikeudet, VakaJarjestaja
from varda.unit_tests.test_utils import assert_status_code, base64_encoding, assert_validation_error


class TestPalvelukayttajaKayttooikeus(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    @responses.activate
    def test_palvelukayttaja_can_fetch_working_apikey(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                    },
                ]
            }
        ]
        self._mock_responses(organisaatiot, organisaatio_oid, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)
        token = resp_apikey.json().get('token')
        self.assertIsNotNone(token)

        client.credentials(HTTP_AUTHORIZATION='Token {}'.format(token))
        resp = client.get('/api/user/data/')
        assert_status_code(resp, status.HTTP_200_OK)

        expected_group_names = ['vakajarjestaja_view_henkilo', 'VARDA-PALVELUKAYTTAJA_1.2.246.562.10.27580498759']
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=organisaatio_oid)
        self.assertEqual(jarjestaja.integraatio_organisaatio, [TietosisaltoRyhma.VAKATIEDOT.value])

    @responses.activate
    def test_palvelukayttaja_henkilosto_only_permissions(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                    },
                ],
            },
        ]
        self._mock_responses(organisaatiot, organisaatio_oid, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)
        token = resp_apikey.json().get('token')
        self.assertIsNotNone(token)

        client.credentials(HTTP_AUTHORIZATION='Token {}'.format(token))
        resp = client.get('/api/user/data/')
        assert_status_code(resp, status.HTTP_200_OK)

        expected_group_names = [
            'vakajarjestaja_view_henkilo',
            'HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.27580498759',
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=organisaatio_oid)
        expected_integraatio = [
            TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT.value,
            TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
            TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
        ]
        self.assertEqual(jarjestaja.integraatio_organisaatio, expected_integraatio)

    @responses.activate
    def test_palvelukayttaja_multiple_permissions(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.TALLENTAJA,
                    },
                ]
            }
        ]
        self._mock_responses(organisaatiot, organisaatio_oid, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)
        token = resp_apikey.json().get('token')
        self.assertIsNotNone(token)

        client.credentials(HTTP_AUTHORIZATION='Token {}'.format(token))
        resp = client.get('/api/user/data/')
        assert_status_code(resp, status.HTTP_200_OK)

        expected_group_names = [
            'vakajarjestaja_view_henkilo',
            'HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.27580498759',
            'VARDA-TALLENTAJA_1.2.246.562.10.27580498759',
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=organisaatio_oid)
        self.assertEqual(jarjestaja.integraatio_organisaatio, [TietosisaltoRyhma.VAKATIEDOT.value])

    @responses.activate
    def test_palvelukayttaja_vaka_and_henkilosto_permissions_mixed(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TILAPAISET_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA,
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.TALLENTAJA,
                    },
                ]
            }
        ]
        self._mock_responses(organisaatiot, organisaatio_oid, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)
        token = resp_apikey.json().get('token')
        self.assertIsNotNone(token)

        client.credentials(HTTP_AUTHORIZATION='Token {}'.format(token))
        resp = client.get('/api/user/data/')
        assert_status_code(resp, status.HTTP_200_OK)

        expected_group_names = [
            'vakajarjestaja_view_henkilo',
            'HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.27580498759',
            'VARDA-TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.27580498759'
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = VakaJarjestaja.objects.get(organisaatio_oid=organisaatio_oid)
        expected_integraatio = [
            TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
            TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
            TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT.value,
            TietosisaltoRyhma.VAKATIEDOT.value,
        ]
        self.assertEqual(jarjestaja.integraatio_organisaatio, expected_integraatio)

    @responses.activate
    def test_palvelukayttaja_no_active_organisaatio(self):
        username = 'palvelukayttaja'
        organisaatiot = []
        self._mock_responses(organisaatiot, None, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_apikey, 'errors', 'PE008', 'User does not have permissions to just one active organization.')

    @responses.activate
    def test_palvelukayttaja_multiple_active_organisaatio(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatio_oid2 = '1.2.246.562.10.346830761110'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                    },
                ],
            },
            {
                'organisaatioOid': organisaatio_oid2,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA,
                    },
                ],
            },
        ]
        self._mock_responses(organisaatiot, organisaatio_oid, username)
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/hae?aktiiviset=true&oid={}'.format(
                          organisaatio_oid2),
                      json={'numHits': 1, 'organisaatiot': self._get_parikkala_organisaatio_json(organisaatio_oid2)},
                      status=status.HTTP_200_OK)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_apikey, 'errors', 'PE008', 'User does not have permissions to just one active organization.')

    @responses.activate
    def test_palvelukayttaja_no_valid_kayttooikeus(self):
        username = 'palvelukayttaja'
        organisaatio_oid = '1.2.246.562.10.27580498759'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.KATSELIJA,
                    },
                ]
            }
        ]
        self._mock_responses(organisaatiot, None, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_apikey, 'errors', 'PE008', 'User does not have permissions to just one active organization.')

    def _mock_responses(self, organisaatiot, organisaatio_oid, username):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/current/omattiedot',
                      json=self._get_kayttooikeudet_json(organisaatiot, username),
                      status=status.HTTP_200_OK)
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/hae?aktiiviset=true&oid={}'.format(
                          organisaatio_oid),
                      json={'numHits': 1, 'organisaatiot': self._get_parikkala_organisaatio_json(organisaatio_oid)},
                      status=status.HTTP_200_OK)
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/hae?aktiiviset=true&suunnitellut=true&lakkautetut=true&oid={}'.format(
                          organisaatio_oid),
                      json={'numHits': 1, 'organisaatiot': self._get_parikkala_organisaatio_json(organisaatio_oid)},
                      status=status.HTTP_200_OK)

    def _get_kayttooikeudet_json(self, organisaatiot, username):
        kayttooikeus_json = {
            'oidHenkilo': 'oid',
            'username': username,
            'kayttajaTyyppi': 'PALVELU',
            'organisaatiot': organisaatiot,
        }
        return kayttooikeus_json

    def _get_parikkala_organisaatio_json(self, organisaatio_oid):
        organisaatio_json = [
            {
                'oid': organisaatio_oid,
                'alkuPvm': 1093467600000,
                'parentOid': '1.2.246.562.10.00000000001',
                'parentOidPath': '1.2.246.562.10.27580498759/1.2.246.562.10.00000000001',
                'ytunnus': '1913642-6',
                'toimipistekoodi': '',
                'match': True,
                'nimi': {
                    'fi': 'PARIKKALAN KUNTA'
                },
                'kieletUris': ['oppilaitoksenopetuskieli_1#1'],
                'kotipaikkaUri': 'kunta_580',
                'children': [],
                'aliOrganisaatioMaara': 290,
                'organisaatiotyypit': ['organisaatiotyyppi_01', 'organisaatiotyyppi_07'],
                'status': 'AKTIIVINEN'
            }
        ]
        return organisaatio_json

    def _assert_user_permissiongroups(self, expected_group_names, username):
        user = User.objects.get(username=username)
        group_names = Group.objects.filter(user=user).values_list('name', flat=True)
        self.assertCountEqual(expected_group_names, group_names)
