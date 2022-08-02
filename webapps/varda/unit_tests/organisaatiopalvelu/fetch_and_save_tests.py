import datetime

import responses
from django.contrib.auth.models import User
from django.test import TestCase

from varda import organisaatiopalvelu
from varda.enums.hallinnointijarjestelma import Hallinnointijarjestelma
from varda.models import Toimipaikka, ToiminnallinenPainotus, KieliPainotus, Organisaatio
from varda.organisaatiopalvelu import fetch_and_save_toimipaikka_data


class TestFetchAndSaveToimipaikkaData(TestCase):
    fixtures = ['fixture_basics']

    @responses.activate
    def test_fetch_and_save_toimipaikka_data(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/1.2.246.562.10.9395737548810',
                      json=self.get_organisaatio_json(),
                      status=200)
        fetch_and_save_toimipaikka_data(Toimipaikka.objects.get(id=1))
        toimipaikka = Toimipaikka.objects.get(id=1)
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
        self.assertEqual(toimipaikka.history.last().history_user_id, User.objects.get(username='varda_system').id)
        self.assertEqual(toimipaikka.hallinnointijarjestelma, str(Hallinnointijarjestelma.ORGANISAATIO))

        painotus_dicts = list((ToiminnallinenPainotus.objects
                               .all()
                               .filter(toimipaikka=toimipaikka)
                               .values('toimintapainotus_koodi', 'alkamis_pvm', 'paattymis_pvm')))
        painotus_expected = [self.__create_painotus_dict('tp01', datetime.date(2018, 10, 1), None)]
        self.assertCountEqual(painotus_dicts, painotus_expected)
        kieli_dicts = list((KieliPainotus.objects
                            .all()
                            .filter(toimipaikka=toimipaikka)
                            .values('kielipainotus_koodi', 'alkamis_pvm', 'paattymis_pvm')))
        kieli_expected = [
            self.__create_kieli_dict('BH', datetime.date(2018, 10, 1), datetime.date(2018, 10, 18)),
            self.__create_kieli_dict('BG', datetime.date(2018, 10, 1), None)
        ]
        self.assertCountEqual(kieli_dicts, kieli_expected)

    @responses.activate
    def test_fetch_and_save_vakajarjestaja_data(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/1.2.246.562.10.34683023489',
                      json=self.get_organisaatio_json(True),
                      status=200)
        vakajarjestaja_id = 1
        organisaatiopalvelu.fetch_organisaatio_info(vakajarjestaja_id)
        vakajarjestaja = Organisaatio.objects.get(id=vakajarjestaja_id)
        self.assertEqual(vakajarjestaja.nimi, 'Päiväkoti nallekarhu')
        self.assertEqual(vakajarjestaja.organisaatio_oid, '1.2.246.562.10.34683023489')
        self.assertEqual(vakajarjestaja.y_tunnus, '8500570-7')
        self.assertEqual(vakajarjestaja.kayntiosoite, 'Jokukatu 1')
        self.assertEqual(vakajarjestaja.kayntiosoite_postinumero, '00520')
        self.assertEqual(vakajarjestaja.kayntiosoite_postitoimipaikka, 'uusi_postitoimipaikka')
        self.assertEqual(vakajarjestaja.postiosoite, 'Jokukatu 1')
        self.assertEqual(vakajarjestaja.postinumero, '00000')
        self.assertEqual(vakajarjestaja.postitoimipaikka, 'Inte känd')
        self.assertEqual(vakajarjestaja.yritysmuoto, '41')
        self.assertEqual(vakajarjestaja.kunta_koodi, '018')
        self.assertEqual(vakajarjestaja.alkamis_pvm, datetime.date(2018, 10, 1))
        self.assertEqual(vakajarjestaja.paattymis_pvm, None)

    @responses.activate
    def test_fetch_and_save_vakajarjestaja_lakkautettu(self):
        responses.add(responses.GET,
                      'https://virkailija.testiopintopolku.fi/organisaatio-service/rest/organisaatio/v4/1.2.246.562.10.34683023489',
                      json=self.get_organisaatio_json(True, '2020-08-01'),
                      status=200)
        vakajarjestaja_id = 1
        organisaatiopalvelu.fetch_organisaatio_info(vakajarjestaja_id)
        vakajarjestaja = Organisaatio.objects.get(id=vakajarjestaja_id)
        self.assertEqual(vakajarjestaja.paattymis_pvm, datetime.date(2020, 8, 1))

    def __create_painotus_dict(self, toimintapainotus_koodi, alkamis_pvm, paattymis_pvm):
        return {'toimintapainotus_koodi': toimintapainotus_koodi, 'alkamis_pvm': alkamis_pvm, 'paattymis_pvm': paattymis_pvm}

    def __create_kieli_dict(self, kielipainotus_koodi, alkamis_pvm, paattymis_pvm):
        return {'kielipainotus_koodi': kielipainotus_koodi, 'alkamis_pvm': alkamis_pvm, 'paattymis_pvm': paattymis_pvm}

    @staticmethod
    def get_organisaatio_json(vakajarjestaja=False, paattymis_pvm=None, oid='1.2.246.562.10.34683023489'):
        org_json = {
            'oid': oid,
            'nimi': {
                'fi': 'Päiväkoti nallekarhu'
            },
            'alkuPvm': '2018-10-01',
            'toimipistekoodi': '',
            'ytunnus': None if not vakajarjestaja else '8500570-7',
            'tyypit': ['organisaatiotyyppi_08' if not vakajarjestaja else 'organisaatiotyyppi_07'],
            'yritysmuoto': 'Ei yritysmuotoa' if not vakajarjestaja else 'Kunta',
            'vuosiluokat': [],
            'kieletUris': ['oppilaitoksenopetuskieli_1#1'],
            'kotipaikkaUri': 'kunta_018',
            'maaUri': 'maatjavaltiot1_fin',
            'parentOid': '1.2.246.562.10.346830761110',
            'postiosoite': {
                'postinumeroUri': 'posti_00000',
                'osoiteTyyppi': 'posti',
                'yhteystietoOid': '1.2.246.562.5.46256382329',
                'postitoimipaikka': 'Inte känd',
                'osoite': 'Jokukatu 1'
            },
            'ryhmatyypit': [],
            'kayttoryhmat': [],
            'lisatiedot': [],
            'kuvaus2': {},
            'metadata': {
                'nimi': {},
                'hakutoimistonNimi': {},
                'yhteystiedot': [],
                'hakutoimistoEctsEmail': {},
                'hakutoimistoEctsNimi': {},
                'hakutoimistoEctsPuhelin': {},
                'hakutoimistoEctsTehtavanimike': {},
                'luontiPvm': 1538736721763,
                'muokkausPvm': 1538686800000,
                'data': {
                    'YLEISKUVAUS': {},
                    'KANSAINVALISET_KOULUTUSOHJELMAT': {},
                    'KIELIOPINNOT': {},
                    'TERVEYDENHUOLTOPALVELUT': {},
                    'TEHTAVANIMIKE': {},
                    'SAHKOPOSTIOSOITE': {},
                    'RAHOITUS': {},
                    'AIEMMIN_HANKITTU_OSAAMINEN': {},
                    'sosiaalinenmedia_7#1': {},
                    'sosiaalinenmedia_5#1': {},
                    'sosiaalinenmedia_6#1': {},
                    'OPISKELIJALIIKKUVUUS': {},
                    'VAKUUTUKSET': {},
                    'OPISKELIJA_JARJESTOT': {},
                    'VALINTAMENETTELY': {},
                    'sosiaalinenmedia_3#1': {},
                    'sosiaalinenmedia_4#1': {},
                    'VASTUUHENKILOT': {},
                    'KUSTANNUKSET': {},
                    'sosiaalinenmedia_1#1': {},
                    'OPPIMISYMPARISTO': {},
                    'sosiaalinenmedia_2#1': {},
                    'PUHELINNUMERO': {},
                    'NIMI': {},
                    'OPISKELIJALIIKUNTA': {},
                    'VUOSIKELLO': {},
                    'OPISKELIJARUOKAILU': {},
                    'ESTEETOMYYS': {},
                    'VAPAA_AIKA': {},
                    'TIETOA_ASUMISESTA': {},
                    'TYOHARJOITTELU': {}
                }
            },
            'nimet': [{
                'nimi': {
                    'fi': 'Päiväkoti nallekarhu'
                },
                'alkuPvm': '2018-10-01',
                'version': 0
            }
            ],
            'yhteystiedot': [{
                'osoiteTyyppi': 'ulkomainen_posti',
                'kieli': 'kieli_en#1',
                'yhteystietoOid': '1.2.246.562.5.60611374459',
                'id': '2190919',
                'osoite': 'tyy'
            }, {
                'osoiteTyyppi': 'kaynti',
                'kieli': 'kieli_fi#1',
                'postinumeroUri': 'posti_00520',
                'yhteystietoOid': '1.2.246.562.5.60873990620',
                'id': '2190926',
                'postitoimipaikka': 'HELSINKI',
                'osoite': 'Jokukatu 1'
            }, {
                'kieli': 'kieli_fi#1',
                'numero': '1234567788',
                'tyyppi': 'puhelin',
                'yhteystietoOid': '1.2.246.562.5.51704648487',
                'id': '2190923'
            }, {
                'kieli': 'kieli_fi#1',
                'yhteystietoOid': '15387367218030.261311521272767',
                'id': '2190924',
                'email': 'testi@testi.fi'
            }, {
                'osoiteTyyppi': 'posti',
                'kieli': 'kieli_fi#1',
                'postinumeroUri': 'posti_00520',
                'yhteystietoOid': '1.2.246.562.5.26171259448',
                'id': '2190925',
                'postitoimipaikka': 'HELSINKI',
                'osoite': 'Jokukatu 1'
            }, {
                'osoiteTyyppi': 'kaynti',
                'kieli': 'kieli_sv#1',
                'yhteystietoOid': '1.2.246.562.5.63222798397',
                'id': '2190922',
                'osoite': 'Jokukatu 1'
            }
            ],
            'kayntiosoite': {
                'postinumeroUri': 'posti_00520',
                'osoiteTyyppi': 'kaynti',
                'yhteystietoOid': '1.2.246.562.5.63222798397',
                'postitoimipaikka': 'uusi_postitoimipaikka',
                'osoite': 'Jokukatu 1'
            },
            'parentOidPath': '|1.2.246.562.10.00000000001|1.2.246.562.10.346830761110|',
            'yhteystietoArvos': [],
            'varhaiskasvatuksenToimipaikkaTiedot': {
                'toimintamuoto': 'vardatoimintamuoto_tm01',
                'kasvatusopillinenJarjestelma': 'vardakasvatusopillinenjarjestelma_kj03',
                'varhaiskasvatuksenJarjestamismuodot': ['vardajarjestamismuoto_jm01'],
                'paikkojenLukumaara': 2,
                'varhaiskasvatuksenKielipainotukset': [{
                    'kielipainotus': 'kieli_bh',
                    'alkupvm': '2018-10-01',
                    'loppupvm': '2018-10-18'
                }, {
                    'kielipainotus': 'kieli_bg',
                    'alkupvm': '2018-10-01'
                }
                ],
                'varhaiskasvatuksenToiminnallinenpainotukset': [{
                    'toiminnallinenpainotus': 'vardatoiminnallinenpainotus_tp01',
                    'alkupvm': '2018-10-01'
                }
                ]
            } if not vakajarjestaja else None,
            'version': 32,
            'status': 'AKTIIVINEN'
        }
        if paattymis_pvm:
            org_json['lakkautusPvm'] = paattymis_pvm
        return org_json
