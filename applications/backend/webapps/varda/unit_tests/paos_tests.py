import json

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from guardian.models import GroupObjectPermission
from rest_framework import status

from varda.misc import decrypt_henkilotunnus
from varda.models import Organisaatio, Toimipaikka, PaosOikeus, Huoltaja, Huoltajuussuhde, Henkilo, Lapsi
from varda.unit_tests.test_utils import assert_status_code, SetUpTestClient, assert_validation_error


class VardaPaosTests(TestCase):
    fixtures = ["fixture_basics"]

    def test_paos_toiminnat_with_same_toimipaikka_names(self):
        client = SetUpTestClient("tester4").client()
        resp = client.get("/api/v1/vakajarjestajat/1/paos-toimipaikat/")
        assert_status_code(resp, status.HTTP_200_OK)
        self.assertEqual(json.loads(resp.content)["count"], 2)

    def test_assign_organisaatio_paos_vaka_permissions(self):
        client_tester2 = SetUpTestClient("tester2").client()  # tallentaja, huoltaja tallentaja vakajarjestaja_1
        client_tester5 = SetUpTestClient("tester5").client()  # tallentaja vakajarjestaja_2
        client_palvelukayttaja_vakajarjestaja1 = SetUpTestClient("pkvakajarjestaja1").client()  # palvelukayttaja vakajarjestaja_1
        client_tester6 = SetUpTestClient("huoltajatietojen_tallentaja").client()  # huoltaja_tallentaja_vakajarjestaja_1
        client_tester7 = SetUpTestClient("tester7").client()  # huoltaja_tallentaja_vakajarjestaja_2
        client_tester8 = SetUpTestClient("tester8").client()  # tallentaja toimipaikka_5

        henkilo = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.7777777777766")
        data_henkilo = {
            "henkilotunnus": decrypt_henkilotunnus(henkilo.henkilotunnus),
            "etunimet": "Minna Maija",
            "kutsumanimi": "Maija",
            "sukunimi": "Suroinen",
        }
        resp_henkilo = client_tester2.post("/api/v1/henkilot/", data_henkilo)
        assert_status_code(resp_henkilo, status.HTTP_200_OK)
        henkilo_url = json.loads(resp_henkilo.content)["url"]

        data_lapsi = {
            "henkilo": henkilo_url,
            "oma_organisaatio": "/api/v1/vakajarjestajat/1/",
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
            "lahdejarjestelma": "1",
        }
        resp_lapsi = client_tester2.post("/api/v1/lapset/", data_lapsi)
        assert_status_code(resp_lapsi, status.HTTP_201_CREATED)

        lapsi_url = json.loads(resp_lapsi.content)["url"]

        data_vakapaatos = {
            "lapsi": lapsi_url,
            "tuntimaara_viikossa": 45,
            "jarjestamismuoto_koodi": "jm03",
            "tilapainen_vaka_kytkin": False,
            "vuorohoito": True,
            "alkamis_pvm": "2020-01-05",
            "hakemus_pvm": "2020-01-01",
            "lahdejarjestelma": "1",
        }

        resp_vakapaatos = client_tester2.post("/api/v1/varhaiskasvatuspaatokset/", data_vakapaatos)
        assert_status_code(resp_vakapaatos, status.HTTP_201_CREATED)

        vakapaatos_url = json.loads(resp_vakapaatos.content)["url"]

        data_vakasuhde = {
            "varhaiskasvatuspaatos": vakapaatos_url,
            "toimipaikka": "/api/v1/toimipaikat/5/",
            "alkamis_pvm": "2020-01-05",
            "paattymis_pvm": "2021-01-01",
            "lahdejarjestelma": "1",
        }

        resp_vakasuhde = client_tester2.post("/api/v1/varhaiskasvatussuhteet/", data_vakasuhde)
        assert_status_code(resp_vakasuhde, status.HTTP_201_CREATED)

        vakasuhde_url = json.loads(resp_vakasuhde.content)["url"]

        resp_vakapaatos_tester5 = client_tester5.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_tester5, status.HTTP_200_OK)

        resp_vakasuhde_tester5 = client_tester5.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_tester5, status.HTTP_200_OK)

        resp_vakapaatos_tester6 = client_tester6.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_tester6, status.HTTP_403_FORBIDDEN)

        resp_vakasuhde_tester6 = client_tester6.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_tester6, status.HTTP_403_FORBIDDEN)

        resp_vakapaatos_tester7 = client_tester7.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_tester7, status.HTTP_403_FORBIDDEN)

        resp_vakasuhde_tester7 = client_tester7.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_tester7, status.HTTP_403_FORBIDDEN)

        resp_vakapaatos_tester8 = client_tester8.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_tester8, status.HTTP_200_OK)

        resp_vakasuhde_tester8 = client_tester8.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_tester8, status.HTTP_200_OK)

        resp_vakapaatos_palvelukayttaja_vakajarjestaja1 = client_palvelukayttaja_vakajarjestaja1.get(vakapaatos_url)
        assert_status_code(resp_vakapaatos_palvelukayttaja_vakajarjestaja1, status.HTTP_200_OK)

        resp_vakasuhde_palvelukayttaja_vakajarjestaja1 = client_palvelukayttaja_vakajarjestaja1.get(vakasuhde_url)
        assert_status_code(resp_vakasuhde_palvelukayttaja_vakajarjestaja1, status.HTTP_200_OK)

    def test_assign_organisaatio_paos_maksutieto_permissions(self):
        client_tester2 = SetUpTestClient("tester2").client()  # tallentaja, huoltaja tallentaja vakajarjestaja 1
        client_tester6 = SetUpTestClient("huoltajatietojen_tallentaja").client()  # huoltaja_tallentaja_vakajarjestaja_1
        client_tester7 = SetUpTestClient("tester7").client()  # huoltaja_tallentaja_vakajarjestaja_2
        client_tester9 = SetUpTestClient("tester9").client()  # huoltaja_tallentaja toimipaikka_5
        client_pk_vakajarjestaja_1 = SetUpTestClient("pkvakajarjestaja1").client()  # vakajarjestaja_1 palvelukayttaja
        client_pk_vakajarjestaja_2 = SetUpTestClient("pkvakajarjestaja2").client()  # vakajarjestaja_2 palvelukayttaja

        henkilo = Henkilo.objects.get(henkilo_oid="1.2.246.562.24.7777777777766")
        data_henkilo = {
            "henkilotunnus": decrypt_henkilotunnus(henkilo.henkilotunnus),
            "etunimet": "Minna Maija",
            "kutsumanimi": "Maija",
            "sukunimi": "Suroinen",
        }
        resp_henkilo = client_tester2.post("/api/v1/henkilot/", data_henkilo)
        assert_status_code(resp_henkilo, status.HTTP_200_OK)
        henkilo_url = json.loads(resp_henkilo.content)["url"]

        data_lapsi = {
            "henkilo": henkilo_url,
            "oma_organisaatio": "/api/v1/vakajarjestajat/1/",
            "paos_organisaatio": "/api/v1/vakajarjestajat/2/",
            "lahdejarjestelma": "1",
        }
        resp_lapsi = client_tester2.post("/api/v1/lapset/", data_lapsi)
        assert_status_code(resp_lapsi, status.HTTP_201_CREATED)

        lapsi_url = json.loads(resp_lapsi.content)["url"]
        lapsi_id = json.loads(resp_lapsi.content)["id"]

        data_vakapaatos = {
            "lapsi": lapsi_url,
            "tuntimaara_viikossa": 45,
            "jarjestamismuoto_koodi": "jm03",
            "tilapainen_vaka_kytkin": False,
            "vuorohoito": True,
            "alkamis_pvm": "2020-01-05",
            "hakemus_pvm": "2020-01-01",
            "lahdejarjestelma": "1",
        }

        resp_vakapaatos = client_tester2.post("/api/v1/varhaiskasvatuspaatokset/", data_vakapaatos)
        assert_status_code(resp_vakapaatos, status.HTTP_201_CREATED)

        vakapaatos_url = json.loads(resp_vakapaatos.content)["url"]

        data_vakasuhde = {
            "varhaiskasvatuspaatos": vakapaatos_url,
            "toimipaikka": "/api/v1/toimipaikat/5/",
            "alkamis_pvm": "2020-01-05",
            "paattymis_pvm": "2021-01-01",
            "lahdejarjestelma": "1",
        }

        resp_vakasuhde = client_tester2.post("/api/v1/varhaiskasvatussuhteet/", data_vakasuhde)
        assert_status_code(resp_vakasuhde, status.HTTP_201_CREATED)

        henkilo_huoltaja = Henkilo.objects.get(id=14)
        lapsi_obj = Lapsi.objects.get(id=lapsi_id)

        huoltaja_obj = Huoltaja.objects.create(henkilo=henkilo_huoltaja)

        Huoltajuussuhde.objects.create(huoltaja=huoltaja_obj, lapsi=lapsi_obj)

        data_maksutieto = {
            "huoltajat": [
                {"henkilotunnus": "291180-7071", "etunimet": "Jouni", "sukunimi": "Suroinen"},
                {"henkilotunnus": "240780-717W", "etunimet": "Puuttuva", "sukunimi": "Huoltaja"},
            ],
            "lapsi": lapsi_url,
            "maksun_peruste_koodi": "mp02",
            "palveluseteli_arvo": 120,
            "asiakasmaksu": 0,
            "perheen_koko": 2,
            "alkamis_pvm": "2020-01-05",
            "paattymis_pvm": "2021-05-05",
            "lahdejarjestelma": "1",
        }

        # No view permission to Lapsi because only Huoltajatieto group
        resp_maksutieto_tester7 = client_tester7.post(
            "/api/v1/maksutiedot/", json.dumps(data_maksutieto), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_tester7, status.HTTP_400_BAD_REQUEST)
        assert_validation_error(resp_maksutieto_tester7, "lapsi", "GE008", "Invalid hyperlink, object does not exist.")

        resp_maksutieto_pk_vakajarjestaja_2 = client_pk_vakajarjestaja_2.post(
            "/api/v1/maksutiedot/", json.dumps(data_maksutieto), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_pk_vakajarjestaja_2, status.HTTP_403_FORBIDDEN)

        resp_maksutieto_pk_vakajarjestaja_1 = client_pk_vakajarjestaja_1.post(
            "/api/v1/maksutiedot/", json.dumps(data_maksutieto), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_pk_vakajarjestaja_1, status.HTTP_201_CREATED)

        resp_maksutieto_tester6 = client_tester6.post(
            "/api/v1/maksutiedot/", json.dumps(data_maksutieto), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_tester6, status.HTTP_201_CREATED)

        maksutieto_url = json.loads(resp_maksutieto_tester6.content)["url"]

        resp_maksutieto_tester7 = client_tester7.get(maksutieto_url)
        assert_status_code(resp_maksutieto_tester7, status.HTTP_404_NOT_FOUND)

        resp_maksutieto_tester9 = client_tester9.get(maksutieto_url)
        assert_status_code(resp_maksutieto_tester9, status.HTTP_404_NOT_FOUND)

        resp_maksutieto_pk_vakajarjestaja_2 = client_pk_vakajarjestaja_2.get(maksutieto_url)
        assert_status_code(resp_maksutieto_pk_vakajarjestaja_2, status.HTTP_404_NOT_FOUND)

        patch_maksutieto_data = {"paattymis_pvm": "2021-02-10"}

        resp_maksutieto_tester7 = client_tester7.patch(
            maksutieto_url, json.dumps(patch_maksutieto_data), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_tester7, status.HTTP_404_NOT_FOUND)

        resp_maksutieto_tester9 = client_tester9.patch(
            maksutieto_url, json.dumps(patch_maksutieto_data), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_tester9, status.HTTP_404_NOT_FOUND)

        resp_maksutieto_pk_vakajarjestaja_2 = client_pk_vakajarjestaja_2.patch(
            maksutieto_url, json.dumps(patch_maksutieto_data), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_pk_vakajarjestaja_2, status.HTTP_404_NOT_FOUND)

        resp_maksutieto_pk_vakajarjestaja_1 = client_pk_vakajarjestaja_1.patch(
            maksutieto_url, json.dumps(patch_maksutieto_data), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_pk_vakajarjestaja_1, status.HTTP_200_OK)

        resp_maksutieto_tester6 = client_tester6.patch(
            maksutieto_url, json.dumps(patch_maksutieto_data), content_type="application/json"
        )
        assert_status_code(resp_maksutieto_tester6, status.HTTP_200_OK)

    def test_paos_permissions_when_organization_link_disables(self):
        """
        Toimipaikka_5 is a PAOS-toimipaikka, and tester2 has a view_permission to it.

        Let's first remove all the permissions for toimipaikka_5 so that tester2
        doesn't have permissions to it anymore from anywhere.

        Next disable the paos-link between the organizations vaka_1 and vaka_2 and
        check that tester2 doesn't see toimipaikka_5.

        Finally enable the paos-link again, and verify that tester2 has a view_permission to toimipaikka_5.
        """
        tester2 = User.objects.get(username="tester2")
        toimipaikka_5 = Toimipaikka.objects.get(id=5)
        client = SetUpTestClient("tester3").client()

        model_name = "toimipaikka"
        content_type = ContentType.objects.filter(model=model_name).first()
        (
            GroupObjectPermission.objects.filter(object_pk=toimipaikka_5, content_type=content_type).delete()
        )  # delete all the (group)permissions for toimipaikka_5.
        self.assertFalse(tester2.has_perm("view_toimipaikka", toimipaikka_5))  # tester2 cannot see toimipaikka_5

        resp = client.get("/api/v1/paos-toiminnat/1/")
        assert_status_code(resp, status.HTTP_200_OK)
        data = json.loads(resp.content)
        paos_toiminta = {"oma_organisaatio": data["oma_organisaatio"], "paos_organisaatio": data["paos_organisaatio"]}
        resp = client.delete("/api/v1/paos-toiminnat/1/")
        assert_status_code(resp, status.HTTP_204_NO_CONTENT)
        self.assertFalse(PaosOikeus.objects.get(id=1).voimassa_kytkin)  # link is now disabled

        resp = client.post("/api/v1/paos-toiminnat/", paos_toiminta)
        assert_status_code(resp, status.HTTP_201_CREATED)
        self.assertTrue(PaosOikeus.objects.get(id=1).voimassa_kytkin)  # link is now enabled again
        self.assertTrue(tester2.has_perm("view_toimipaikka", toimipaikka_5))  # tester2 can see toimipaikka_5

    def test_change_paos_tallentaja(self):
        """
        In test data we have the following PAOS-agreement/link.
         * jarjestaja = vakajarjestaja_1
         * tuottaja = vakajarjestaja_2
         * paos_toimipaikka = toimipaikka_5
         * tallentaja = vakajarjestaja_1

        Let's check first tester2 (vakajarjestaja_1) can modify a vakasuhde connected to toimipaikka_5.
        And tester5 (vakajarjestaja_2) cannot.

        Then change the paos_tallentaja, and verify that these work the opposite way.

        PAOS-tallentaja change affects vakapaatokset also. This is also tested below.

        Finally, disable the paos-link between the organizations, and verify that either
        vakajarjestaja cannot make updates anymore.

        Test that GET works even if PUT fails.
        """
        # tallentaja_vakajarjestaja_1
        tester2_client = SetUpTestClient("tester2").client()
        # paakayttaja_vakajarjestaja_1
        tester_4_client = SetUpTestClient("tester4").client()
        # tallentaja_vakajarjestaja_2
        tester5_client = SetUpTestClient("tester5").client()
        # tallentaja_toimipaikka_5
        tester8_client = SetUpTestClient("tester8").client()

        resp = tester2_client.get("/api/v1/varhaiskasvatussuhteet/4/")
        vakasuhde_4 = resp.content

        resp = tester2_client.get("/api/v1/varhaiskasvatuspaatokset/4/")
        vakapaatos_4 = resp.content

        self._test_paos_get_put(
            "/api/v1/varhaiskasvatussuhteet/4/",
            vakasuhde_4,
            edit_client_list=(tester2_client,),
            no_edit_client_list=(
                tester5_client,
                tester8_client,
            ),
        )
        self._test_paos_get_put(
            "/api/v1/varhaiskasvatuspaatokset/4/",
            vakapaatos_4,
            edit_client_list=(tester2_client,),
            no_edit_client_list=(
                tester5_client,
                tester8_client,
            ),
        )

        # Change paos-tallentaja
        jarjestaja_organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.34683023489")
        tuottaja_organisaatio = Organisaatio.objects.get(organisaatio_oid="1.2.246.562.10.93957375488")
        paos_oikeus = PaosOikeus.objects.get(
            jarjestaja_kunta_organisaatio=jarjestaja_organisaatio, tuottaja_organisaatio=tuottaja_organisaatio
        )
        paos_oikeus_patch = {"tallentaja_organisaatio_oid": tuottaja_organisaatio.organisaatio_oid}
        assert_status_code(
            tester_4_client.patch(f"/api/v1/paos-oikeudet/{paos_oikeus.id}/", paos_oikeus_patch), status.HTTP_200_OK
        )

        self._test_paos_get_put(
            "/api/v1/varhaiskasvatussuhteet/4/",
            vakasuhde_4,
            edit_client_list=(
                tester5_client,
                tester8_client,
            ),
            no_edit_client_list=(tester2_client,),
        )
        self._test_paos_get_put(
            "/api/v1/varhaiskasvatuspaatokset/4/",
            vakapaatos_4,
            edit_client_list=(
                tester5_client,
                tester8_client,
            ),
            no_edit_client_list=(tester2_client,),
        )

        # Disable the paos-link between the organizations
        paos_oikeus.delete()

        self._test_paos_get_put(
            "/api/v1/varhaiskasvatussuhteet/4/",
            vakasuhde_4,
            no_edit_client_list=(
                tester2_client,
                tester5_client,
                tester8_client,
            ),
        )
        self._test_paos_get_put(
            "/api/v1/varhaiskasvatuspaatokset/4/",
            vakapaatos_4,
            no_edit_client_list=(
                tester2_client,
                tester5_client,
                tester8_client,
            ),
        )

    def _test_paos_get_put(self, url, json_message, edit_client_list=(), no_edit_client_list=()):
        for edit_client in edit_client_list:
            resp = edit_client.put(url, json_message, content_type="application/json")
            assert_status_code(resp, status.HTTP_200_OK)

        for no_edit_client in no_edit_client_list:
            resp_put = no_edit_client.put(url, json_message, content_type="application/json")
            assert_status_code(resp_put, status.HTTP_403_FORBIDDEN)
            assert_validation_error(resp_put, "errors", "PE006", "User does not have permission to perform this action.")

            resp_get = no_edit_client.get(url)
            assert_status_code(resp_get, status.HTTP_200_OK)
