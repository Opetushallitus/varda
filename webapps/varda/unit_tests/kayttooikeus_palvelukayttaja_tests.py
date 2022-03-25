import responses
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from varda import kayttooikeuspalvelu
from varda.enums.kayttajatyyppi import Kayttajatyyppi
from varda.enums.tietosisalto_ryhma import TietosisaltoRyhma
from varda.models import Z4_CasKayttoOikeudet, Organisaatio
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
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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

        expected_group_names = ['VARDA-PALVELUKAYTTAJA_1.2.246.562.10.27580498759']
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        self.assertEqual(jarjestaja.integraatio_organisaatio, [TietosisaltoRyhma.VAKATIEDOT.value])

    @responses.activate
    def test_palvelukayttaja_luovutuspalvelu(self):
        username = 'palvelukayttaja'
        organisaatio_oid = settings.OPETUSHALLITUS_ORGANISAATIO_OID
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.LUOVUTUSPALVELU,
                    },
                ]
            }
        ]
        headers = {
            'HTTP_X_SSL_Authenticated': 'SUCCESS',
            'HTTP_X_SSL_User_DN': 'CN=kela cert,O=user1 company,ST=Some-State,C=FI',
        }
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/', **headers)
        assert_status_code(resp_apikey, status.HTTP_200_OK)
        token = resp_apikey.json().get('token')
        self.assertIsNotNone(token)

        client.credentials(HTTP_AUTHORIZATION='Token {}'.format(token))
        resp = client.get('/api/user/data/', **headers)
        assert_status_code(resp, status.HTTP_200_OK)

        expected_group_names = ['VARDA_LUOVUTUSPALVELU_{}'.format(organisaatio_oid)]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        self.assertEqual(jarjestaja.integraatio_organisaatio, [])

        kela_api_response = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/', **headers)
        self.assertEqual(kela_api_response.status_code, status.HTTP_200_OK)

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
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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
            'HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.27580498759',
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        expected_integraatio = [
            TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT.value,
            TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
            TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
        ]
        self.assertCountEqual(jarjestaja.integraatio_organisaatio, expected_integraatio)

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
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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
            'HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.27580498759',
            'VARDA-TALLENTAJA_1.2.246.562.10.27580498759',
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
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
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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
            'HUOLTAJATIETO_TALLENNUS_1.2.246.562.10.27580498759',
            'VARDA-TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TILAPAISET_TALLENTAJA_1.2.246.562.10.27580498759',
            'HENKILOSTO_TAYDENNYSKOULUTUS_TALLENTAJA_1.2.246.562.10.27580498759'
        ]
        self._assert_user_permissiongroups(expected_group_names, username)

        jarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        expected_integraatio = [
            TietosisaltoRyhma.TYONTEKIJATIEDOT.value,
            TietosisaltoRyhma.TAYDENNYSKOULUTUSTIEDOT.value,
            TietosisaltoRyhma.TILAPAINENHENKILOSTOTIEDOT.value,
            TietosisaltoRyhma.VAKATIEDOT.value,
        ]
        self.assertCountEqual(jarjestaja.integraatio_organisaatio, expected_integraatio)

    @responses.activate
    def test_palvelukayttaja_no_active_organisaatio(self):
        username = 'palvelukayttaja'
        organisaatiot = []
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
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
                        'palvelu': 'KOSKI',
                        'oikeus': Z4_CasKayttoOikeudet.KATSELIJA,
                    },
                ]
            }
        ]
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
        basic_auth_token = base64_encoding('{}:password'.format(username))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_403_FORBIDDEN)
        assert_validation_error(resp_apikey, 'errors', 'PE008', 'User does not have permissions to just one active organization.')

    @responses.activate
    def test_multiple_palvelukayttaja_different_permissions(self):
        organisaatio_oid = '1.2.246.562.10.27580498759'
        vakajarjestaja_qs = Organisaatio.objects.filter(organisaatio_oid=organisaatio_oid)
        client = APIClient()

        username_1 = 'palvelukayttaja1'
        mock_response_1 = [
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

        mock_cas_palvelukayttaja_responses(mock_response_1, username_1)
        basic_auth_token_1 = base64_encoding(f'{username_1}:password')

        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token_1))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)

        expected_group_names_1 = ['VARDA-PALVELUKAYTTAJA_1.2.246.562.10.27580498759']
        self._assert_user_permissiongroups(expected_group_names_1, username_1)
        self.assertCountEqual(vakajarjestaja_qs.first().integraatio_organisaatio, [TietosisaltoRyhma.VAKATIEDOT.value])

        username_2 = 'palvelukayttaja2'
        mock_response_2 = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA,
                    },
                ]
            }
        ]

        responses.reset()
        mock_cas_palvelukayttaja_responses(mock_response_2, username_2)
        basic_auth_token_2 = base64_encoding(f'{username_2}:password')

        client.credentials(HTTP_AUTHORIZATION='Basic {}'.format(basic_auth_token_2))
        resp_apikey = client.get('/api/user/apikey/')
        assert_status_code(resp_apikey, status.HTTP_200_OK)

        expected_group_names_2 = ['HENKILOSTO_TYONTEKIJA_TALLENTAJA_1.2.246.562.10.27580498759']
        self._assert_user_permissiongroups(expected_group_names_2, username_2)
        self.assertCountEqual(vakajarjestaja_qs.first().integraatio_organisaatio,
                              [TietosisaltoRyhma.VAKATIEDOT.value, TietosisaltoRyhma.TYONTEKIJATIEDOT.value])

    @responses.activate
    def test_service_user_cas_login(self):
        organisaatio_oid = '1.2.246.562.10.27580498759'
        username = 'tester-no-known-privileges'
        organisaatiot = [
            {
                'organisaatioOid': organisaatio_oid,
                'kayttooikeudet': [
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.TALLENTAJA
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA
                    },
                    {
                        'palvelu': 'VARDA',
                        'oikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA
                    }
                ]
            }
        ]
        mock_cas_palvelukayttaja_responses(organisaatiot, username)
        user = User.objects.get(username=username)
        kayttooikeuspalvelu.set_permissions_for_cas_user(user.id)

        expected_group_names = (f'{Z4_CasKayttoOikeudet.PALVELUKAYTTAJA}_{organisaatio_oid}',
                                f'{Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA}_{organisaatio_oid}',
                                f'{Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA}_{organisaatio_oid}',
                                f'{Z4_CasKayttoOikeudet.TALLENTAJA}_{organisaatio_oid}',)
        self._assert_user_permissiongroups(expected_group_names, username)

        cas_permissions = Z4_CasKayttoOikeudet.objects.filter(user=user).values('kayttooikeus', 'organisaatio_oid')
        expected_cas_permissions = (
            {'kayttooikeus': Z4_CasKayttoOikeudet.TALLENTAJA, 'organisaatio_oid': organisaatio_oid},
            {'kayttooikeus': Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA, 'organisaatio_oid': organisaatio_oid},
            {'kayttooikeus': Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA, 'organisaatio_oid': organisaatio_oid},
            {'kayttooikeus': Z4_CasKayttoOikeudet.PALVELUKAYTTAJA, 'organisaatio_oid': organisaatio_oid},
        )
        self.assertCountEqual(cas_permissions, expected_cas_permissions)

        vakajarjestaja = Organisaatio.objects.get(organisaatio_oid=organisaatio_oid)
        expected_integraatio = (TietosisaltoRyhma.TYONTEKIJATIEDOT.value, TietosisaltoRyhma.VAKATIEDOT.value,)
        self.assertCountEqual(vakajarjestaja.integraatio_organisaatio, expected_integraatio)

    def _assert_user_permissiongroups(self, expected_group_names, username):
        user = User.objects.get(username=username)
        group_names = Group.objects.filter(user=user).values_list('name', flat=True)
        self.assertCountEqual(expected_group_names, group_names)


def mock_cas_palvelukayttaja_responses(organisaatiot, username, henkilo_oid='1.2.246.562.24.10000000001'):
    responses.add(responses.GET,
                  'https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/current/omattiedot',
                  json=_get_kayttooikeudet_json(organisaatiot, username, henkilo_oid),
                  status=status.HTTP_200_OK)
    responses.add(responses.POST,
                  'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/findbyoids',
                  json=[{'oid': organisaatio['organisaatioOid'], 'tyypit': ['organisaatiotyyppi_07'], 'status': 'AKTIIVINEN'}
                        for organisaatio in organisaatiot],
                  status=status.HTTP_200_OK)
    responses.add(responses.GET,
                  f'https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?oidHenkilo={henkilo_oid}',
                  json=[_get_kayttooikeudet_json(organisaatiot, username, henkilo_oid)],
                  status=status.HTTP_200_OK)
    responses.add(responses.GET,
                  f'https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/kayttajatunnus={username}',
                  json={'oid': henkilo_oid, 'kayttajaTyyppi': Kayttajatyyppi.PALVELU.value},
                  status=status.HTTP_200_OK)
    responses.add(responses.GET,
                  f'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/{henkilo_oid}',
                  json={},
                  status=status.HTTP_200_OK)


def _get_kayttooikeudet_json(organisaatiot, username, henkilo_oid):
    kayttooikeus_json = {
        'oidHenkilo': henkilo_oid,
        'username': username,
        'kayttajaTyyppi': 'PALVELU',
        'organisaatiot': organisaatiot,
    }
    return kayttooikeus_json
