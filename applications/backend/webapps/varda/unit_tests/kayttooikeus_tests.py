import json

import responses
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework import status

from varda import kayttooikeuspalvelu
from varda.models import Organisaatio, Z4_CasKayttoOikeudet
from varda.unit_tests.test_utils import assert_status_code, assert_validation_error, SetUpTestClient, TEST_CACHE_SETTINGS


class TestKayttooikeus(TestCase):
    fixtures = ["fixture_basics"]

    @responses.activate
    def test_paakayttaja_huoltajatietotallentaja_in_integraatioorganisaatio(self):
        organisaatio_oid = "1.2.246.562.10.34683023489"
        kayttooikeus_json = [
            {
                "oidHenkilo": "1.2.246.562.24.10000000001",
                "username": "tester-no-known-privileges",
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio_oid,
                        "kayttooikeudet": [
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.TALLENTAJA},
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA},
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA},
                        ],
                    }
                ],
            }
        ]
        _mock_cas_responses(kayttooikeus_json)
        tester4 = User.objects.get(username="tester-no-known-privileges")
        kayttooikeuspalvelu.set_permissions_for_cas_user(tester4.id)

        group_names = [group.name for group in tester4.groups.all()]
        expected_group_names = [
            Z4_CasKayttoOikeudet.KATSELIJA + "_" + organisaatio_oid,
            Z4_CasKayttoOikeudet.PAAKAYTTAJA + "_" + organisaatio_oid,
            Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA + "_" + organisaatio_oid,
        ]
        self.assertCountEqual(group_names, expected_group_names)

        cas_kayttooikeudet = Z4_CasKayttoOikeudet.objects.filter(user=tester4).values("kayttooikeus", "organisaatio_oid")
        expected_cas_kayttooikeudet = [
            {"kayttooikeus": Z4_CasKayttoOikeudet.KATSELIJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_KATSELIJA, "organisaatio_oid": organisaatio_oid},
        ]
        self.assertCountEqual(cas_kayttooikeudet, expected_cas_kayttooikeudet)

    @responses.activate
    def test_paakayttaja_huoltajatietotallentaja(self):
        organisaatio_oid = "1.2.246.562.10.93957375488"
        kayttooikeus_json = [
            {
                "oidHenkilo": "1.2.246.562.24.10000000001",
                "username": "tester-no-known-privileges",
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio_oid,
                        "kayttooikeudet": [
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.TALLENTAJA},
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA},
                            {"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA},
                        ],
                    }
                ],
            }
        ]
        _mock_cas_responses(kayttooikeus_json)
        tester4 = User.objects.get(username="tester-no-known-privileges")
        kayttooikeuspalvelu.set_permissions_for_cas_user(tester4.id)

        group_names = [group.name for group in tester4.groups.all()]
        expected_group_names = [
            Z4_CasKayttoOikeudet.TALLENTAJA + "_" + organisaatio_oid,
            Z4_CasKayttoOikeudet.PAAKAYTTAJA + "_" + organisaatio_oid,
            Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA + "_" + organisaatio_oid,
        ]
        self.assertCountEqual(group_names, expected_group_names)

        cas_kayttooikeudet = Z4_CasKayttoOikeudet.objects.filter(user=tester4).values("kayttooikeus", "organisaatio_oid")
        expected_cas_kayttooikeudet = [
            {"kayttooikeus": Z4_CasKayttoOikeudet.TALLENTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.PAAKAYTTAJA, "organisaatio_oid": organisaatio_oid},
            {"kayttooikeus": Z4_CasKayttoOikeudet.HUOLTAJATIEDOT_TALLENTAJA, "organisaatio_oid": organisaatio_oid},
        ]
        self.assertCountEqual(cas_kayttooikeudet, expected_cas_kayttooikeudet)

    @override_settings(CACHES=TEST_CACHE_SETTINGS)
    @responses.activate
    def test_permissions_in_multiple_organizations(self):
        organisaatio_1 = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.34683023489")
        organisaatio_2 = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.93957375488")
        kayttooikeus_json = [
            {
                "oidHenkilo": "1.2.246.562.24.10000000001",
                "username": "tester-no-known-privileges",
                "kayttajaTyyppi": "VIRKAILIJA",
                "organisaatiot": [
                    {
                        "organisaatioOid": organisaatio_1.organisaatio_oid,
                        "kayttooikeudet": [{"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.KATSELIJA}],
                    },
                    {
                        "organisaatioOid": organisaatio_2.organisaatio_oid,
                        "kayttooikeudet": [{"palvelu": "VARDA", "oikeus": Z4_CasKayttoOikeudet.HENKILOSTO_TYONTEKIJA_TALLENTAJA}],
                    },
                ],
            }
        ]
        _mock_cas_responses(kayttooikeus_json)
        user = User.objects.get(username="tester-no-known-privileges")
        kayttooikeuspalvelu.set_permissions_for_cas_user(user.id)

        all_group_names = [
            f'{permission["oikeus"]}_{organisaatio["organisaatioOid"]}'
            for organisaatio in kayttooikeus_json[0]["organisaatiot"]
            for permission in organisaatio["kayttooikeudet"]
        ]

        # additional_cas_user_fields.all_groups should have all the groups
        self.assertListEqual(all_group_names, list(user.additional_cas_user_fields.all_groups.values_list("name", flat=True)))
        # Actual groups should only be the default ones (ordered by ID -> 1.2.246.562.10.34683023489)
        self.assertListEqual(
            [name for name in all_group_names if name.endswith("1.2.246.562.10.34683023489")],
            list(user.groups.values_list("name", flat=True)),
        )

        client = SetUpTestClient("tester-no-known-privileges").client()

        # Get organisaatio from API
        resp = client.get("/api/v1/vakajarjestajat/")
        assert_status_code(resp, status.HTTP_200_OK)
        results = json.loads(resp.content)["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["organisaatio_oid"], "1.2.246.562.10.34683023489")

        # Does not exist
        resp = client.post("/api/ui/active-organisaatio/", {"organisaatio": "/api/v1/vakajarjestajat/0/"})
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, "organisaatio", "GE008", "Invalid hyperlink, object does not exist.")
        # No permissions
        resp = client.post("/api/ui/active-organisaatio/", {"organisaatio_oid": "1.2.246.562.10.52966755795"})
        assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp, "organisaatio_oid", "RF003", "Could not find matching object.")

        # Validate active organisaatio change
        assert_status_code(
            client.post("/api/ui/active-organisaatio/", {"organisaatio_oid": "1.2.246.562.10.93957375488"}), status.HTTP_200_OK
        )
        self.assertListEqual(
            [name for name in all_group_names if name.endswith("1.2.246.562.10.93957375488")],
            list(user.groups.values_list("name", flat=True)),
        )

        # Validate cache has been cleared
        resp = client.get("/api/v1/vakajarjestajat/")
        assert_status_code(resp, status.HTTP_200_OK)
        results = json.loads(resp.content)["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["organisaatio_oid"], "1.2.246.562.10.93957375488")


def _mock_cas_responses(kayttooikeus_json):
    henkilo_oid = kayttooikeus_json[0]["oidHenkilo"]
    responses.add(
        responses.GET,
        "https://virkailija.testiopintopolku.fi/kayttooikeus-service/henkilo/kayttajatunnus=tester-no-known-privileges",
        json={"oid": henkilo_oid, "kayttajaTyyppi": "VIRKAILIJA"},
        status=status.HTTP_200_OK,
    )
    responses.add(
        responses.GET,
        f"https://virkailija.testiopintopolku.fi/kayttooikeus-service/kayttooikeus/kayttaja?oidHenkilo={henkilo_oid}",
        json=kayttooikeus_json,
        status=status.HTTP_200_OK,
    )

    oid_list = [organisaatio["organisaatioOid"] for organisaatio in kayttooikeus_json[0]["organisaatiot"]]
    responses.add(
        responses.POST,
        "https://virkailija.testiopintopolku.fi/organisaatio-service/api/findbyoids",
        json=[
            {"oid": organisaatio_oid, "tyypit": ["organisaatiotyyppi_07"], "status": "AKTIIVINEN"}
            for organisaatio_oid in oid_list
        ],
        status=status.HTTP_200_OK,
    )
