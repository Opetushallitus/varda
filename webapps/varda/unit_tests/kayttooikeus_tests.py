import responses
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework import status

from varda import kayttooikeuspalvelu
from varda.models import Z4_CasKayttoOikeudet


class TestKayttooikeus(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    @responses.activate
    def test_paakayttaja_huoltajatietotallentaja_in_integraatioorganisaatio(self):
        organisaatio_oid = '1.2.246.562.10.34683023489'
        kayttooikeus_json = [
            {
                "oidHenkilo": 'oid',
                "username": 'tester-no-known-privileges',
                "kayttajaTyyppi": 'VIRKAILIJA',
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio_oid,
                        "kayttooikeudet": [
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.TALLENTAJA
                            },
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA
                            },
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
                            }
                        ]
                    }
                ]
            }
        ]
        self._create_responses(kayttooikeus_json, organisaatio_oid)
        tester4 = User.objects.get(username='tester-no-known-privileges')
        kayttooikeuspalvelu.set_permissions_for_cas_user(tester4.id)

        group_names = [group.name for group in tester4.groups.all()]
        expected_group_names = [
            Z4_CasKayttoOikeudet.KATSELIJA + '_' + organisaatio_oid,
            Z4_CasKayttoOikeudet.PAAKAYTTAJA + '_' + organisaatio_oid,
            Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA + '_' + organisaatio_oid,
        ]
        self.assertCountEqual(group_names, expected_group_names)

        cas_kayttooikeudet = Z4_CasKayttoOikeudet.objects.filter(user=tester4).values('kayttooikeus', 'organisaatio_oid')
        expected_cas_kayttooikeudet = [
            {"kayttooikeus": Z4_CasKayttoOikeudet.KATSELIJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA, "organisaatio_oid": organisaatio_oid},
        ]
        self.assertCountEqual(cas_kayttooikeudet, expected_cas_kayttooikeudet)

    @responses.activate
    def test_paakayttaja_huoltajatietotallentaja(self):
        organisaatio_oid = '1.2.246.562.10.93957375488'
        kayttooikeus_json = [
            {
                "oidHenkilo": 'oid',
                "username": 'tester-no-known-privileges',
                "kayttajaTyyppi": 'VIRKAILIJA',
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio_oid,
                        "kayttooikeudet": [
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.TALLENTAJA
                            },
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA
                            },
                            {
                                "palvelu": 'VARDA',
                                "oikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA
                            }
                        ]
                    }
                ]
            }
        ]
        self._create_responses(kayttooikeus_json, organisaatio_oid)
        tester4 = User.objects.get(username='tester-no-known-privileges')
        kayttooikeuspalvelu.set_permissions_for_cas_user(tester4.id)

        group_names = [group.name for group in tester4.groups.all()]
        expected_group_names = [
            Z4_CasKayttoOikeudet.TALLENTAJA + '_' + organisaatio_oid,
            Z4_CasKayttoOikeudet.PAAKAYTTAJA + '_' + organisaatio_oid,
            Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA + '_' + organisaatio_oid,
        ]
        self.assertCountEqual(group_names, expected_group_names)

        cas_kayttooikeudet = Z4_CasKayttoOikeudet.objects.filter(user=tester4).values('kayttooikeus', 'organisaatio_oid')
        expected_cas_kayttooikeudet = [
            {"kayttooikeus": Z4_CasKayttoOikeudet.TALLENTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA, "organisaatio_oid": organisaatio_oid},
        ]
        self.assertCountEqual(cas_kayttooikeudet, expected_cas_kayttooikeudet)

    def _create_responses(self, kayttooikeus_json, organisaatio_oid):
        # NOTE: this first one might be redundant call the implementation makes
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/kayttajatunnus=tester-no-known-privileges',
                      json={"oid": 'oid', "kayttajaTyyppi": 'VIRKAILIJA'},
                      status=status.HTTP_200_OK)
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/oid',
                      json={},
                      status=status.HTTP_200_OK)
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?oidHenkilo=oid',
                      json=kayttooikeus_json,
                      status=status.HTTP_200_OK)
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/findbyoids',
                      json=[{"oid": organisaatio_oid, "tyypit": ['organisaatiotyyppi_07'], "status": 'AKTIIVINEN'}],
                      status=status.HTTP_200_OK)
