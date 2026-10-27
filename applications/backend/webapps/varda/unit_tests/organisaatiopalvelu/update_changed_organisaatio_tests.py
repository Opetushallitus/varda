import datetime

import responses

from django.test import TestCase

from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.models import Aikaleima, KieliPainotus, ToiminnallinenPainotus, Toimipaikka, User
from varda.organisaatiopalvelu import update_all_organisaatio_service_organisations
from varda.unit_tests.organisaatiopalvelu.fetch_and_save_tests import TestFetchAndSaveToimipaikkaData


class TestUpdateChangedOrganisaatio(TestCase):
    fixtures = ["fixture_basics"]

    @responses.activate
    def test_update_changed_organisaatios(self):
        oid_with_changes = "1.2.246.562.10.9395737548810"
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/organisaatio-service/api/muutetut/oid",
            json=[oid_with_changes],
            status=200,
        )
        # Reuse data defined for another test.
        # The organization service will fetch data for all organizations using this,
        # and notice that the response doesn't match what is in the database.
        # It should then update the data to match what we supplied, and we check to confirm.
        responses.add(
            responses.POST,
            "https://virkailija.testiopintopolku.fi/organisaatio-service/api/findbyoids",
            json=[TestFetchAndSaveToimipaikkaData.get_organisaatio_json(oid=oid_with_changes)],
            status=200,
        )
        update_all_organisaatio_service_organisations()

        varda_system_user = User.objects.get(username="varda_system")
        varda_system_user_id = varda_system_user.id

        toimipaikka = Toimipaikka.objects.get(organisaatio_oid=oid_with_changes)
        self.assertEqual(toimipaikka.vakajarjestaja_id, 2)
        self.assertEqual(toimipaikka.nimi, "Päiväkoti nallekarhu")
        self.assertEqual(toimipaikka.nimi_sv, "")
        self.assertEqual(toimipaikka.organisaatio_oid, oid_with_changes)
        self.assertEqual(toimipaikka.kayntiosoite, "Jokukatu 1")
        self.assertEqual(toimipaikka.kayntiosoite_postinumero, "00520")
        self.assertEqual(toimipaikka.kayntiosoite_postitoimipaikka, "uusi_postitoimipaikka")
        self.assertEqual(toimipaikka.postiosoite, "Jokukatu 1")
        self.assertEqual(toimipaikka.postinumero, "00000")
        self.assertEqual(toimipaikka.postitoimipaikka, "Inte känd")
        self.assertEqual(toimipaikka.kunta_koodi, "018")
        self.assertEqual(toimipaikka.puhelinnumero, "1234567788")
        self.assertEqual(toimipaikka.sahkopostiosoite, "testi@testi.fi")
        self.assertEqual(toimipaikka.kasvatusopillinen_jarjestelma_koodi, "kj03")
        self.assertEqual(toimipaikka.toimintamuoto_koodi, "tm01")
        self.assertEqual(toimipaikka.toimintakieli_koodi, ["FI", "SV"])
        self.assertEqual(toimipaikka.jarjestamismuoto_koodi, ["jm01"])
        self.assertEqual(toimipaikka.varhaiskasvatuspaikat, 2)
        self.assertEqual(toimipaikka.toiminnallinenpainotus_kytkin, True)
        self.assertEqual(toimipaikka.kielipainotus_kytkin, True)
        self.assertEqual(toimipaikka.alkamis_pvm, datetime.date(2018, 10, 1))
        self.assertEqual(toimipaikka.paattymis_pvm, None)
        # Not assigned in this method but when toimipaikka is created
        # IF a toimipaikka is managed in Organisaatiopalvelu it will be kept up to date by system
        self.assertEqual(toimipaikka.history.last().history_user_id, varda_system_user_id)
        self.assertEqual(toimipaikka.hallinnointijarjestelma, str(Hallinnointijarjestelma.ORGANISAATIO))

        painotus_dicts = list(
            (
                ToiminnallinenPainotus.objects.all()
                .filter(toimipaikka=toimipaikka)
                .values("toimintapainotus_koodi", "alkamis_pvm", "paattymis_pvm")
            )
        )
        painotus_expected = [self.__create_painotus_dict("tp01", datetime.date(2018, 10, 1), None)]
        self.assertCountEqual(painotus_dicts, painotus_expected)
        kieli_dicts = list(
            (
                KieliPainotus.objects.all()
                .filter(toimipaikka=toimipaikka)
                .values("kielipainotus_koodi", "alkamis_pvm", "paattymis_pvm")
            )
        )
        kieli_expected = [
            self.__create_kieli_dict("BH", datetime.date(2018, 10, 1), datetime.date(2018, 10, 18)),
            self.__create_kieli_dict("BG", datetime.date(2018, 10, 1), None),
        ]
        self.assertCountEqual(kieli_dicts, kieli_expected)

        aikaleima = Aikaleima.objects.get(avain=AikaleimaAvain.ORGANISAATIOS_LAST_UPDATE.value)
        self.assertIsNotNone(aikaleima)

    @responses.activate
    def test_nothing_changed(self):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/organisaatio-service/api/muutetut/oid",
            json={"oids": []},
            status=200,
        )
        update_all_organisaatio_service_organisations()

    @responses.activate
    def test_invalid_toimipaikka_does_not_stop_update(self):
        invalid_oid = "1.2.246.562.10.9395737548810"
        valid_oid = "1.2.246.562.10.9395737548815"
        Toimipaikka.objects.filter(organisaatio_oid=valid_oid).update(
            hallinnointijarjestelma=Hallinnointijarjestelma.ORGANISAATIO.name
        )
        # First update creates painotukset for the toimipaikka that gets invalid data next
        self.__add_responses([TestFetchAndSaveToimipaikkaData.get_organisaatio_json(oid=invalid_oid)])
        update_all_organisaatio_service_organisations()
        invalid_toimipaikka = Toimipaikka.objects.get(organisaatio_oid=invalid_oid)
        kielipainotus_ids = set(invalid_toimipaikka.kielipainotukset.values_list("id", flat=True))
        toiminnallinenpainotus_ids = set(invalid_toimipaikka.toiminnallisetpainotukset.values_list("id", flat=True))
        self.assertTrue(kielipainotus_ids)
        self.assertTrue(toiminnallinenpainotus_ids)
        aikaleima_before = Aikaleima.objects.get(avain=AikaleimaAvain.ORGANISAATIOS_LAST_UPDATE.value).aikaleima

        # Invalid kielipainotus koodi fails after the painotukset of the toimipaikka have been deleted,
        # missing puhelinnumero fails before that
        invalid_koodi_json = TestFetchAndSaveToimipaikkaData.get_organisaatio_json(oid=invalid_oid)
        invalid_koodi_json["nimi"] = {"fi": "Ei saa tallentua"}
        invalid_koodi_json["varhaiskasvatuksenToimipaikkaTiedot"]["varhaiskasvatuksenKielipainotukset"].append(
            {"kielipainotus": "invalid", "alkupvm": "2018-10-01"}
        )
        no_puhelinnumero_json = TestFetchAndSaveToimipaikkaData.get_organisaatio_json(oid=invalid_oid)
        no_puhelinnumero_json["nimi"] = {"fi": "Ei saa tallentua"}
        no_puhelinnumero_json["yhteystiedot"] = [y for y in no_puhelinnumero_json["yhteystiedot"] if y.get("tyyppi") != "puhelin"]

        for case, invalid_json in (("invalid koodi", invalid_koodi_json), ("no puhelinnumero", no_puhelinnumero_json)):
            with self.subTest(case=case):
                responses.reset()
                valid_json = TestFetchAndSaveToimipaikkaData.get_organisaatio_json(oid=valid_oid)
                valid_json["nimi"] = {"fi": "Paivitetty toimipaikka"}
                self.__add_responses([invalid_json, valid_json])
                with self.assertLogs("varda.organisaatiopalvelu", level="ERROR") as logs:
                    update_all_organisaatio_service_organisations()
                self.assertIn(invalid_oid, logs.output[0])

                invalid_toimipaikka.refresh_from_db()
                self.assertEqual(invalid_toimipaikka.nimi, "Päiväkoti nallekarhu")
                self.assertEqual(set(invalid_toimipaikka.kielipainotukset.values_list("id", flat=True)), kielipainotus_ids)
                self.assertEqual(
                    set(invalid_toimipaikka.toiminnallisetpainotukset.values_list("id", flat=True)), toiminnallinenpainotus_ids
                )
                self.assertEqual(Toimipaikka.objects.get(organisaatio_oid=valid_oid).nimi, "Paivitetty toimipaikka")
                aikaleima = Aikaleima.objects.get(avain=AikaleimaAvain.ORGANISAATIOS_LAST_UPDATE.value).aikaleima
                self.assertGreater(aikaleima, aikaleima_before)
                aikaleima_before = aikaleima

    def __add_responses(self, organisaatio_json_list):
        responses.add(
            responses.GET,
            "https://virkailija.testiopintopolku.fi/organisaatio-service/api/muutetut/oid",
            json=[organisaatio_json["oid"] for organisaatio_json in organisaatio_json_list],
            status=200,
        )
        responses.add(
            responses.POST,
            "https://virkailija.testiopintopolku.fi/organisaatio-service/api/findbyoids",
            json=organisaatio_json_list,
            status=200,
        )

    def __create_painotus_dict(self, toimintapainotus_koodi, alkamis_pvm, paattymis_pvm):
        return {"toimintapainotus_koodi": toimintapainotus_koodi, "alkamis_pvm": alkamis_pvm, "paattymis_pvm": paattymis_pvm}

    def __create_kieli_dict(self, kielipainotus_koodi, alkamis_pvm, paattymis_pvm):
        return {"kielipainotus_koodi": kielipainotus_koodi, "alkamis_pvm": alkamis_pvm, "paattymis_pvm": paattymis_pvm}
