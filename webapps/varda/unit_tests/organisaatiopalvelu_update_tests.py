from django.test import TestCase

from varda.models import Toimipaikka
from varda.organisaatiopalvelu import get_toimipaikka_update_json


class VardaOrganisaatiopalveluTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    def test_organisaatio_update_json(self):
        self.maxDiff = None
        old_toimipaikka_json = {
            "oid": "1.2.246.562.10.29565860110",
            "nimi": {
                "fi": "Päiväkoti nallekarhu"
            },
            "alkuPvm": "2018-10-01",
            "toimipistekoodi": "",
            "tyypit": ["organisaatiotyyppi_08"],
            "vuosiluokat": [],
            "kieletUris": ["oppilaitoksenopetuskieli_1#1"],
            "kotipaikkaUri": "kunta_018",
            "maaUri": "maatjavaltiot1_fin",
            "parentOid": "1.2.246.562.10.346830761110",
            "postiosoite": {
                "osoiteTyyppi": "posti",
                "yhteystietoOid": "1.2.246.562.5.46256382329",
                "osoite": "Jokukatu 1"
            },
            "ryhmatyypit": [],
            "kayttoryhmat": [],
            "lisatiedot": [],
            "kuvaus2": {},
            "metadata": {
                "nimi": {},
                "hakutoimistonNimi": {},
                "yhteystiedot": [],
                "hakutoimistoEctsEmail": {},
                "hakutoimistoEctsNimi": {},
                "hakutoimistoEctsPuhelin": {},
                "hakutoimistoEctsTehtavanimike": {},
                "luontiPvm": 1538736721763,
                "muokkausPvm": 1538686800000,
                "data": {
                    "YLEISKUVAUS": {},
                    "KANSAINVALISET_KOULUTUSOHJELMAT": {},
                    "KIELIOPINNOT": {},
                    "TERVEYDENHUOLTOPALVELUT": {},
                    "TEHTAVANIMIKE": {},
                    "SAHKOPOSTIOSOITE": {},
                    "RAHOITUS": {},
                    "AIEMMIN_HANKITTU_OSAAMINEN": {},
                    "sosiaalinenmedia_7#1": {},
                    "sosiaalinenmedia_5#1": {},
                    "sosiaalinenmedia_6#1": {},
                    "OPISKELIJALIIKKUVUUS": {},
                    "VAKUUTUKSET": {},
                    "OPISKELIJA_JARJESTOT": {},
                    "VALINTAMENETTELY": {},
                    "sosiaalinenmedia_3#1": {},
                    "sosiaalinenmedia_4#1": {},
                    "VASTUUHENKILOT": {},
                    "KUSTANNUKSET": {},
                    "sosiaalinenmedia_1#1": {},
                    "OPPIMISYMPARISTO": {},
                    "sosiaalinenmedia_2#1": {},
                    "PUHELINNUMERO": {},
                    "NIMI": {},
                    "OPISKELIJALIIKUNTA": {},
                    "VUOSIKELLO": {},
                    "OPISKELIJARUOKAILU": {},
                    "ESTEETOMYYS": {},
                    "VAPAA_AIKA": {},
                    "TIETOA_ASUMISESTA": {},
                    "TYOHARJOITTELU": {}
                }
            },
            "nimet": [
                {
                    "nimi": {
                        "fi": "Päiväkoti nallekarhu"
                    },
                    "alkuPvm": "2018-10-01",
                    "version": 0
                },
                {
                    "nimi": {
                        "fi": "Old Päiväkoti nallekarhu",
                        "sv": "Old Päiväkoti nallekarhu",
                        "en": "Old Päiväkoti nallekarhu"
                    },
                    "alkuPvm": "2018-09-01",
                    "version": 0
                }
            ],
            "yhteystiedot": [{
                "osoiteTyyppi": "ulkomainen_posti",
                "kieli": "kieli_en#1",
                "yhteystietoOid": "1.2.246.562.5.60611374459",
                "id": "2190919",
                "osoite": "tyy"
            }, {
                "osoiteTyyppi": "kaynti",
                "kieli": "kieli_fi#1",
                "postinumeroUri": "posti_00520",
                "yhteystietoOid": "1.2.246.562.5.60873990620",
                "id": "2190926",
                "postitoimipaikka": "HELSINKI",
                "osoite": "Jokukatu 1"
            }, {
                "kieli": "kieli_fi#1",
                "numero": "1234567788",
                "tyyppi": "puhelin",
                "yhteystietoOid": "1.2.246.562.5.51704648487",
                "id": "2190923"
            }, {
                "kieli": "kieli_fi#1",
                "yhteystietoOid": "15387367218030.261311521272767",
                "id": "2190924",
                "email": "testi@testi.fi"
            }, {
                "osoiteTyyppi": "posti",
                "kieli": "kieli_fi#1",
                "postinumeroUri": "posti_00520",
                "yhteystietoOid": "1.2.246.562.5.26171259448",
                "id": "2190925",
                "postitoimipaikka": "HELSINKI",
                "osoite": "Jokukatu 1"
            }, {
                "osoiteTyyppi": "kaynti",
                "kieli": "kieli_sv#1",
                "yhteystietoOid": "1.2.246.562.5.63222798397",
                "id": "2190922",
                "osoite": "Jokukatu 1"
            }
            ],
            "kayntiosoite": {
                "osoiteTyyppi": "kaynti",
                "yhteystietoOid": "1.2.246.562.5.63222798397",
                "osoite": "Jokukatu 1"
            },
            "parentOidPath": "|1.2.246.562.10.00000000001|1.2.246.562.10.346830761110|",
            "yhteystietoArvos": [],
            "varhaiskasvatuksenToimipaikkaTiedot": {
                "toimintamuoto": "vardatoimintamuoto_tm01",
                "kasvatusopillinenJarjestelma": "vardakasvatusopillinenjarjestelma_kj03",
                "varhaiskasvatuksenJarjestamismuodot": ["vardajarjestamismuoto_jm01"],
                "paikkojenLukumaara": 1,
                "varhaiskasvatuksenKielipainotukset": [{
                    "kielipainotus": "kieli_bh",
                    "alkupvm": "2018-10-01",
                    "loppupvm": "2018-10-18"
                }, {
                    "kielipainotus": "kieli_bg",
                    "alkupvm": "2018-10-01"
                }
                ],
                "varhaiskasvatuksenToiminnallinenpainotukset": [{
                    "toiminnallinenpainotus": "vardatoiminnallinenpainotus_tp01",
                    "alkupvm": "2018-10-01"
                }
                ]
            },
            "version": 32,
            "status": "AKTIIVINEN"
        }

        expected_result_toimipaikka_json = {
            "oid": "1.2.246.562.10.29565860110",
            "nimi": {
                "fi": "Espoo",
                "sv": "Espoo",
                "en": "Espoo"
            },
            "alkuPvm": "2017-02-03",
            "toimipistekoodi": "",
            "tyypit": [
                "organisaatiotyyppi_08"
            ],
            "vuosiluokat": [],
            "kieletUris": [
                "oppilaitoksenopetuskieli_1#1"
            ],
            "kotipaikkaUri": "kunta_091",
            "maaUri": "maatjavaltiot1_fin",
            "parentOid": "1.2.246.562.10.346830761110",
            "ryhmatyypit": [],
            "kayttoryhmat": [],
            "lisatiedot": [],
            "kuvaus2": {},
            "metadata": {
                "nimi": {},
                "hakutoimistonNimi": {},
                "yhteystiedot": [],
                "hakutoimistoEctsEmail": {},
                "hakutoimistoEctsNimi": {},
                "hakutoimistoEctsPuhelin": {},
                "hakutoimistoEctsTehtavanimike": {},
                "data": {
                    "YLEISKUVAUS": {},
                    "KANSAINVALISET_KOULUTUSOHJELMAT": {},
                    "KIELIOPINNOT": {},
                    "TERVEYDENHUOLTOPALVELUT": {},
                    "TEHTAVANIMIKE": {},
                    "SAHKOPOSTIOSOITE": {},
                    "RAHOITUS": {},
                    "AIEMMIN_HANKITTU_OSAAMINEN": {},
                    "sosiaalinenmedia_7#1": {},
                    "sosiaalinenmedia_5#1": {},
                    "sosiaalinenmedia_6#1": {},
                    "OPISKELIJALIIKKUVUUS": {},
                    "VAKUUTUKSET": {},
                    "OPISKELIJA_JARJESTOT": {},
                    "VALINTAMENETTELY": {},
                    "sosiaalinenmedia_3#1": {},
                    "sosiaalinenmedia_4#1": {},
                    "VASTUUHENKILOT": {},
                    "KUSTANNUKSET": {},
                    "sosiaalinenmedia_1#1": {},
                    "OPPIMISYMPARISTO": {},
                    "sosiaalinenmedia_2#1": {},
                    "PUHELINNUMERO": {},
                    "NIMI": {},
                    "OPISKELIJALIIKUNTA": {},
                    "VUOSIKELLO": {},
                    "OPISKELIJARUOKAILU": {},
                    "ESTEETOMYYS": {},
                    "VAPAA_AIKA": {},
                    "TIETOA_ASUMISESTA": {},
                    "TYOHARJOITTELU": {}
                }
            },
            "nimet": [
                {
                    "nimi": {
                        "fi": "Espoo",
                        "sv": "Espoo",
                        "en": "Espoo"
                    },
                    "alkuPvm": "2018-10-01",
                    "version": 0
                },
                {
                    "nimi": {
                        "fi": "Old Päiväkoti nallekarhu",
                        "sv": "Old Päiväkoti nallekarhu",
                        "en": "Old Päiväkoti nallekarhu"
                    },
                    "alkuPvm": "2018-09-01",
                    "version": 0
                }
            ],
            "yhteystiedot": [
                {
                    "osoiteTyyppi": "ulkomainen_posti",
                    "kieli": "kieli_en#1",
                    "yhteystietoOid": "1.2.246.562.5.60611374459",
                    "id": "2190919",
                    "osoite": "Keilaranta 14, 02100 Espoo"
                },
                {
                    "osoiteTyyppi": "kaynti",
                    "kieli": "kieli_fi#1",
                    "postinumeroUri": "posti_02100",
                    "yhteystietoOid": "1.2.246.562.5.60873990620",
                    "id": "2190926",
                    "postitoimipaikka": "Espoo",
                    "osoite": "Keilaranta 14"
                },
                {
                    "kieli": "kieli_fi#1",
                    "numero": "+35810123456",
                    "tyyppi": "puhelin",
                    "yhteystietoOid": "1.2.246.562.5.51704648487",
                    "id": "2190923"
                },
                {
                    "kieli": "kieli_fi#1",
                    "yhteystietoOid": "15387367218030.261311521272767",
                    "id": "2190924",
                    "email": "test1@espoo.fi"
                },
                {
                    "osoiteTyyppi": "posti",
                    "kieli": "kieli_fi#1",
                    "postinumeroUri": "posti_02100",
                    "yhteystietoOid": "1.2.246.562.5.26171259448",
                    "id": "2190925",
                    "postitoimipaikka": "Espoo",
                    "osoite": "Keilaranta 14"
                },
                {
                    "osoiteTyyppi": "kaynti",
                    "kieli": "kieli_sv#1",
                    "yhteystietoOid": "1.2.246.562.5.63222798397",
                    "id": "2190922",
                    "osoite": "Keilaranta 14",
                    "postinumeroUri": "posti_02100",
                    "postitoimipaikka": "Espoo"
                },
                {
                    "email": "test1@espoo.fi",
                    "kieli": "kieli_sv#1"
                },
                {
                    "email": "test1@espoo.fi",
                    "kieli": "kieli_en#1"
                },
                {
                    "numero": "+35810123456",
                    "tyyppi": "puhelin",
                    "kieli": "kieli_sv#1"
                },
                {
                    "numero": "+35810123456",
                    "tyyppi": "puhelin",
                    "kieli": "kieli_en#1"
                },
                {
                    "osoite": "Keilaranta 14",
                    "postinumeroUri": "posti_02100",
                    "postitoimipaikka": "Espoo",
                    "osoiteTyyppi": "posti",
                    "kieli": "kieli_sv#1"
                },
                {
                    "osoiteTyyppi": "ulkomainen_kaynti",
                    "osoite": "Keilaranta 14, 02100 Espoo",
                    "kieli": "kieli_en#1"
                }
            ],
            "parentOidPath": "|1.2.246.562.10.00000000001|1.2.246.562.10.346830761110|",
            "yhteystietoArvos": [],
            "varhaiskasvatuksenToimipaikkaTiedot": {
                "toimintamuoto": "vardatoimintamuoto_tm01",
                "kasvatusopillinenJarjestelma": "vardakasvatusopillinenjarjestelma_kj02",
                "varhaiskasvatuksenJarjestamismuodot": [
                    "vardajarjestamismuoto_jm01"
                ],
                "paikkojenLukumaara": 120,
                "varhaiskasvatuksenKielipainotukset": [
                    {
                        "kielipainotus": "kieli_fi",
                        "alkupvm": "2017-02-10",
                        "loppupvm": None
                    }
                ],
                "varhaiskasvatuksenToiminnallinenpainotukset": [
                    {
                        "toiminnallinenpainotus": "vardatoiminnallinenpainotus_tp01",
                        "alkupvm": "2017-02-10",
                        "loppupvm": None
                    }
                ]
            },
            "version": 32,
            "status": "AKTIIVINEN",
            "lakkautusPvm": None
        }

        toimipaikka_obj = Toimipaikka.objects.get(id=1)
        result_json = get_toimipaikka_update_json(toimipaikka_obj, old_toimipaikka_json)

        self.assertJSONEqual(result_json, expected_result_toimipaikka_json)
