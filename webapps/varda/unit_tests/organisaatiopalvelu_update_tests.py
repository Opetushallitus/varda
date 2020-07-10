import json
import re
import responses

from django.conf import settings
from django.test import TestCase
from django.forms.models import model_to_dict
from varda.enums.aikaleima_avain import AikaleimaAvain
from varda.models import Aikaleima, Toimipaikka
from varda.organisaatiopalvelu import (get_toimipaikka_update_json, get_toimipaikka_json,
                                       update_toimipaikat_in_organisaatiopalvelu)


class VardaOrganisaatiopalveluTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    toimipaikka_1_organisaatio_oid = '1.2.246.562.10.9395737548810'
    toimipaikka_2_organisaatio_oid = '1.2.246.562.10.9395737548815'
    toimipaikka_4_organisaatio_oid = '1.2.246.562.10.9395737548811'

    org_palvelu_url = settings.OPINTOPOLKU_DOMAIN + '/organisaatio-service/rest/organisaatio/v4/'
    oid_regex = '([0-2])((\\.0)|(\\.[1-9][0-9]*))*'
    toimipaikka_1_4_regex = '(' + toimipaikka_1_organisaatio_oid + '|' + toimipaikka_4_organisaatio_oid + ')'
    toimipaikka_2_regex = toimipaikka_2_organisaatio_oid

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
                "varhaiskasvatuksenJarjestamismuodot": [
                    "vardajarjestamismuoto_jm02",
                    "vardajarjestamismuoto_jm03",
                    "vardajarjestamismuoto_jm04",
                    "vardajarjestamismuoto_jm05"
                ],
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
            'piilotettu': False,
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
                    "vardajarjestamismuoto_jm02",
                    "vardajarjestamismuoto_jm03",
                    "vardajarjestamismuoto_jm04",
                    "vardajarjestamismuoto_jm05"
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
            'piilotettu': False,
            "status": "AKTIIVINEN",
            "lakkautusPvm": None
        }

        toimipaikka_obj = Toimipaikka.objects.get(id=1)
        result_json = get_toimipaikka_update_json(toimipaikka_obj, old_toimipaikka_json)

        self.assertJSONEqual(result_json, expected_result_toimipaikka_json)

    def test_organisaatio_update_toimintamuoto_to_hidden_json(self):
        toimipaikka_obj = Toimipaikka.objects.get(id=1)
        toimipaikka_dict = model_to_dict(toimipaikka_obj)

        old_toimipaikka_json = json.loads(get_toimipaikka_json(toimipaikka_dict, toimipaikka_obj.vakajarjestaja.id))

        old_piilotettu_kytkin = old_toimipaikka_json['piilotettu']
        self.assertFalse(old_piilotettu_kytkin)

        toimipaikka_obj.toimintamuoto_koodi = 'tm03'
        result_json = get_toimipaikka_update_json(toimipaikka_obj, old_toimipaikka_json)
        result_piilotettu_kytkin = json.loads(result_json)['piilotettu']
        self.assertTrue(result_piilotettu_kytkin)

    def test_organisaatio_update_toimintamuoto_to_public_json(self):
        toimipaikka_obj = Toimipaikka.objects.get(id=1)
        toimipaikka_obj.toimintamuoto_koodi = 'tm03'  # toimipaikka is public so need to mock it to private
        toimipaikka_dict = model_to_dict(toimipaikka_obj)

        old_toimipaikka_json = json.loads(get_toimipaikka_json(toimipaikka_dict, toimipaikka_obj.vakajarjestaja.id))

        old_piilotettu_kytkin = old_toimipaikka_json['piilotettu']
        self.assertTrue(old_piilotettu_kytkin)

        toimipaikka_obj.toimintamuoto_koodi = 'tm01'  # return toimipaikka to public
        result_json = get_toimipaikka_update_json(toimipaikka_obj, old_toimipaikka_json)
        result_piilotettu_kytkin = json.loads(result_json)['piilotettu']
        self.assertFalse(result_piilotettu_kytkin)

    def _get_organisaatio_oid_from_url(self, url):
        return url.split('/')[-1]

    @responses.activate
    def test_toimipaikat_organisaatiopalveluun(self):
        """
        First, fetch changed toimipaikat and update changes in Organisaatiopalvelu.
        Then modify one toimipaikka (id=2), and do the same as above. This will result
        to one more organization to be updated in Organisaatiopalvelu.

        Currently this creates 20 requests:
        - POST /cas/v1/tickets (for each request separately),

        - GET org1 + PUT org1
        - GET org2 + PUT org2

        - GET org1 + PUT org1
        - GET org2 + PUT org2
        - GET org3 + PUT org3
        """
        responses.add(responses.POST, settings.OPINTOPOLKU_DOMAIN + '/cas/v1/tickets',
                      json={}, status=200)
        responses.add(responses.GET, re.compile(self.org_palvelu_url + self.oid_regex + '\\?includeImage=false'),
                      json={}, status=200)
        responses.add(responses.PUT, re.compile(self.org_palvelu_url + self.toimipaikka_1_4_regex),
                      json={}, status=200)
        responses.add(responses.PUT, re.compile(self.org_palvelu_url + self.toimipaikka_2_regex),
                      json={}, status=200)

        aikaleima_before_update = '2020-03-05 12:00:00+0000'
        aikaleima, created = Aikaleima.objects.get_or_create(avain=AikaleimaAvain.ORGANISAATIOS_VARDA_LAST_UPDATE.name)
        aikaleima.aikaleima = aikaleima_before_update
        aikaleima.save()

        update_toimipaikat_in_organisaatiopalvelu()

        organizations_before_update = []
        organizations_after_update = []

        for call in responses.calls:
            oid = self._get_organisaatio_oid_from_url(call.request.url)
            if call.request.method == 'PUT' and oid not in organizations_before_update:
                organizations_before_update.append(oid)

        aikaleima.aikaleima = aikaleima_before_update
        aikaleima.save()

        toimipaikka = Toimipaikka.objects.get(id=2)
        toimipaikka.varhaiskasvatuspaikat = 140  # change random stuff on the toimipaikka
        toimipaikka.save()

        update_toimipaikat_in_organisaatiopalvelu()

        for call in responses.calls:
            oid = self._get_organisaatio_oid_from_url(call.request.url)
            if call.request.method == 'PUT' and oid not in organizations_after_update:
                organizations_after_update.append(oid)

        organizations_1_4 = [self.toimipaikka_1_organisaatio_oid, self.toimipaikka_4_organisaatio_oid]
        organizations_1_2_4 = organizations_1_4 + [self.toimipaikka_2_organisaatio_oid]

        self.assertListEqual(organizations_1_4, sorted(organizations_before_update))
        self.assertListEqual(organizations_1_2_4, sorted(organizations_after_update))  # one more org after the update
