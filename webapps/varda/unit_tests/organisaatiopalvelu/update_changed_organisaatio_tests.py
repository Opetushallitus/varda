import datetime

import responses
from django.test import TestCase

from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.enums.lahdejarjestelma import Lahdejarjestelma
from varda.models import Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Aikaleima
from varda.organisaatiopalvelu import update_all_organisaatio_service_organisations
from varda.unit_tests.organisaatiopalvelu.fetch_and_save_tests import TestFetchAndSaveToimipaikkaData


class TestUpdateChangedOrganisaatio(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    @responses.activate
    def test_update_changed_organisaatios(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v2/muutetut/oid',
                      json={"oids": ["1.2.246.562.10.9395737548810"]},
                      status=200)
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/findbyoids',
                      json=[TestFetchAndSaveToimipaikkaData.get_organisaatio_json()],
                      status=200)
        update_all_organisaatio_service_organisations()

        toimipaikka = Toimipaikka.objects.get(organisaatio_oid='1.2.246.562.10.9395737548810')
        self.assertEqual(toimipaikka.vakajarjestaja_id, 2)
        self.assertEqual(toimipaikka.nimi, 'Päiväkoti nallekarhu')
        self.assertEqual(toimipaikka.nimi_sv, '')
        self.assertEqual(toimipaikka.organisaatio_oid, '1.2.246.562.10.9395737548810')
        self.assertEqual(toimipaikka.kayntiosoite, 'Jokukatu 1')
        self.assertEqual(toimipaikka.kayntiosoite_postinumero, '00520')
        self.assertEqual(toimipaikka.kayntiosoite_postitoimipaikka, 'uusi_postitoimipaikka')
        self.assertEqual(toimipaikka.postiosoite, 'Jokukatu 1')
        self.assertEqual(toimipaikka.postinumero, '00000')
        self.assertEqual(toimipaikka.postitoimipaikka, 'Inte känd')
        self.assertEqual(toimipaikka.kunta_koodi, '018')
        self.assertEqual(toimipaikka.puhelinnumero, '1234567788')
        self.assertEqual(toimipaikka.sahkopostiosoite, 'testi@testi.fi')
        self.assertEqual(toimipaikka.kasvatusopillinen_jarjestelma_koodi, 'kj03')
        self.assertEqual(toimipaikka.toimintamuoto_koodi, 'tm01')
        self.assertEqual(toimipaikka.asiointikieli_koodi, ['FI', 'SV'])
        self.assertEqual(toimipaikka.jarjestamismuoto_koodi, ['jm01'])
        self.assertEqual(toimipaikka.varhaiskasvatuspaikat, 2)
        self.assertEqual(toimipaikka.toiminnallinenpainotus_kytkin, True)
        self.assertEqual(toimipaikka.kielipainotus_kytkin, True)
        self.assertEqual(toimipaikka.alkamis_pvm, datetime.date(2018, 10, 1))
        self.assertEqual(toimipaikka.paattymis_pvm, None)
        # Not assigned in this method but when toimipaikka is created
        self.assertEqual(toimipaikka.changed_by_id, 3)
        self.assertEqual(toimipaikka.lahdejarjestelma, str(Lahdejarjestelma.ORGANISAATIO))

        painotus_dicts = list((ToiminnallinenPainotus.objects
                               .all()
                               .filter(toimipaikka=toimipaikka)
                               .values('toimintapainotus_koodi', 'alkamis_pvm', 'paattymis_pvm', 'changed_by_id')))
        painotus_expected = [self.__create_painotus_dict('tp01', datetime.date(2018, 10, 1), None, 3)]
        self.assertCountEqual(painotus_dicts, painotus_expected)
        kieli_dicts = list((KieliPainotus.objects
                            .all()
                            .filter(toimipaikka=toimipaikka)
                            .values('kielipainotus_koodi', 'alkamis_pvm', 'paattymis_pvm', 'changed_by_id')))
        kieli_expected = [
            self.__create_kieli_dict('BH', datetime.date(2018, 10, 1), datetime.date(2018, 10, 18), 3),
            self.__create_kieli_dict('BG', datetime.date(2018, 10, 1), None, 3)
        ]
        self.assertCountEqual(kieli_dicts, kieli_expected)

        aikaleima = Aikaleima.objects.get(avain=AikaleimaAvain.ORGANISAATIOS_LAST_UPDATE.value)
        self.assertIsNotNone(aikaleima)

    @responses.activate
    def test_nothing_changed(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v2/muutetut/oid',
                      json={"oids": []},
                      status=200)
        update_all_organisaatio_service_organisations()

    def __create_painotus_dict(self, toimintapainotus_koodi, alkamis_pvm, paattymis_pvm, changed_by_id):
        return {"toimintapainotus_koodi": toimintapainotus_koodi, "alkamis_pvm": alkamis_pvm, "paattymis_pvm": paattymis_pvm, "changed_by_id": changed_by_id}

    def __create_kieli_dict(self, kielipainotus_koodi, alkamis_pvm, paattymis_pvm, changed_by_id):
        return {"kielipainotus_koodi": kielipainotus_koodi, "alkamis_pvm": alkamis_pvm, "paattymis_pvm": paattymis_pvm, "changed_by_id": changed_by_id}
