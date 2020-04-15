import re
import responses
from django.test import TestCase
from rest_framework import status

from varda import oppijanumerorekisteri
from varda.models import Lapsi, Huoltaja


class TestOppijanumerorekisteriLogic(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']
    date_time_regex = r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+0[2|3]00'  # E.g 2020-02-18T18:23:11+0200

    @responses.activate
    def test_update_huoltajuussuhteet_uusi_huoltaja(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'hetu': '120619A973V', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5', 'hetu': '120619A973V'},
                      status=status.HTTP_200_OK)

        lapsi = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.6815981182311')
        self.assertEqual(len(lapsi.huoltajuussuhteet.all()), 1)

        oppijanumerorekisteri.update_huoltajuussuhteet()

        expected1 = {
            'voimassa_kytkin': False,
            'huoltaja__henkilo__henkilo_oid': '',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
        }
        expected2 = {
            'voimassa_kytkin': True,
            'huoltaja__henkilo__henkilo_oid': '1.2.3.4.5',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
        }
        actuals = list(lapsi.huoltajuussuhteet.all().values('voimassa_kytkin',
                                                            'huoltaja__henkilo__henkilo_oid',
                                                            'lapsi__henkilo__henkilo_oid'))
        self.assertCountEqual(actuals, [expected1, expected2])

    @responses.activate
    def test_update_huoltajuussuhteet_hetuton_hetu_none(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'hetu': None, 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5', 'hetu': None},
                      status=status.HTTP_200_OK)

        lapsi = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.6815981182311')
        self.assertEqual(len(lapsi.huoltajuussuhteet.all()), 1)

        oppijanumerorekisteri.update_huoltajuussuhteet()

        expected1 = {
            'voimassa_kytkin': False,
            'huoltaja__henkilo__henkilo_oid': '',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
            'huoltaja__henkilo__henkilotunnus': 'gAAAAABbo6X6VW8yiNVQqpFKGl_4JS-VEA12mMn-ajatHro5RR1_fYyocLrV1197TvFU5J0Yz51LZ6_1TyU7Erb3UasXVtUR6Q==',
            'huoltaja__henkilo__henkilotunnus_unique_hash': 'cb31a7a3d13fbb0e1419e5c4cdf8e93d6c67a2274659266a8d51c44896ddd292',
        }
        expected2 = {
            'voimassa_kytkin': True,
            'huoltaja__henkilo__henkilo_oid': '1.2.3.4.5',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
            'huoltaja__henkilo__henkilotunnus': '',
            'huoltaja__henkilo__henkilotunnus_unique_hash': '',
        }
        actuals = list(lapsi.huoltajuussuhteet.all().values('voimassa_kytkin',
                                                            'huoltaja__henkilo__henkilo_oid',
                                                            'lapsi__henkilo__henkilo_oid',
                                                            'huoltaja__henkilo__henkilotunnus',
                                                            'huoltaja__henkilo__henkilotunnus_unique_hash'))
        self.assertCountEqual(actuals, [expected1, expected2])

    @responses.activate
    def test_update_huoltajuussuhteet_hetuton_hetu_field_missing(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'},
                      status=status.HTTP_200_OK)

        lapsi = Lapsi.objects.get(henkilo__henkilo_oid='1.2.246.562.24.6815981182311')
        self.assertEqual(len(lapsi.huoltajuussuhteet.all()), 1)

        oppijanumerorekisteri.update_huoltajuussuhteet()

        expected1 = {
            'voimassa_kytkin': False,
            'huoltaja__henkilo__henkilo_oid': '',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
            'huoltaja__henkilo__henkilotunnus': 'gAAAAABbo6X6VW8yiNVQqpFKGl_4JS-VEA12mMn-ajatHro5RR1_fYyocLrV1197TvFU5J0Yz51LZ6_1TyU7Erb3UasXVtUR6Q==',
            'huoltaja__henkilo__henkilotunnus_unique_hash': 'cb31a7a3d13fbb0e1419e5c4cdf8e93d6c67a2274659266a8d51c44896ddd292',
        }
        expected2 = {
            'voimassa_kytkin': True,
            'huoltaja__henkilo__henkilo_oid': '1.2.3.4.5',
            'lapsi__henkilo__henkilo_oid': '1.2.246.562.24.6815981182311',
            'huoltaja__henkilo__henkilotunnus': '',
            'huoltaja__henkilo__henkilotunnus_unique_hash': '',
        }
        actuals = list(lapsi.huoltajuussuhteet.all().values('voimassa_kytkin',
                                                            'huoltaja__henkilo__henkilo_oid',
                                                            'lapsi__henkilo__henkilo_oid',
                                                            'huoltaja__henkilo__henkilotunnus',
                                                            'huoltaja__henkilo__henkilotunnus_unique_hash'))
        self.assertCountEqual(actuals, [expected1, expected2])

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_with_oid_and_hetu(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321', 'hetu': '020476-321F'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.987654321/master',
                      json={'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321', 'hetu': '020476-321F'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_existing_with_oid_and_hetu_twice(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321', 'hetu': '020476-321F'},
                            {'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321', 'hetu': '020476-321F'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.987654321/master',
                      json={'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321', 'hetu': '020476-321F'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_new_with_oid_and_hetu_twice(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'},
                            {'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before + 1, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_with_oid(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.987654321/master',
                      json={'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_with_siblings_existing_huoltaja(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311', '1.2.246.562.24.49084901393'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.49084901393/huoltajat',
                      json=[{'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.987654321/master',
                      json={'etunimet': 'Pauliina', 'sukunimi': 'Virtanen', 'kutsumanimi': 'Pauliina', 'oidHenkilo': '1.2.987654321'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_with_siblings_new_huoltaja(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311', '1.2.246.562.24.49084901393'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.49084901393/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before + 1, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_does_not_create_multiple_when_huoltaja_oid_changes(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311', '1.2.246.562.24.49084901393'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.49084901393/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': 'newOid'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before + 1, all_huoltajat_after)

    @responses.activate
    def test_update_huoltajuussuhde_not_create_duplicate_when_existing_huoltaja_hetu_changes(self):
        responses.add(responses.GET,
                      re.compile('https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/huoltajasuhdemuutokset/alkaen/' + self.date_time_regex),
                      json=['1.2.246.562.24.6815981182311'],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.246.562.24.6815981182311/huoltajat',
                      json=[{'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.3.4.5'}],
                      status=status.HTTP_200_OK
                      )
        responses.add(responses.GET, 'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/1.2.3.4.5/master',
                      json={'etunimet': 'Arpa', 'sukunimi': 'Kuutio', 'kutsumanimi': 'Arpa', 'oidHenkilo': '1.2.987654321', 'hetu': 'newHetu'},
                      status=status.HTTP_200_OK)
        all_huoltajat_before = Huoltaja.objects.all().count()
        oppijanumerorekisteri.update_huoltajuussuhteet()
        all_huoltajat_after = Huoltaja.objects.all().count()
        self.assertEqual(all_huoltajat_before, all_huoltajat_after)
