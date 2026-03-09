import datetime
import unittest

from django.db import models
from django.test import TestCase
from rest_framework.exceptions import ValidationError
from unittest.mock import patch

from varda.enums.yhteystieto import Yhteystietoryhmatyyppi, YhteystietoAlkupera, YhteystietoTyyppi
from varda.misc import hash_string
from varda.models import Henkilo, Huoltaja, Tyontekija
from varda.oppijanumerorekisteri import (
    save_henkilo_to_db,
    _create_change_detector,
    _normalize_date,
    _normalize_bool,
    _normalize_value,
    _apply_hetu,
)


class Dummy:
    """
    Fake object that simulates enough of a Django model instance
    for set_if_changed() to work in unit tests.
    """

    class _DummyMeta:
        def __init__(self, instance):
            self.instance = instance

        def get_field(self, attr):
            value = getattr(self.instance, attr, None)

            # Map Python value types to Django fields
            if isinstance(value, bool):
                return models.BooleanField()
            if isinstance(value, datetime.date):
                return models.DateField()
            if isinstance(value, str) or value is None:
                return models.CharField()
            return models.CharField()

    def __init__(self):
        self._meta = Dummy._DummyMeta(self)


def fake_set_if_changed(obj, attr, new_value):
    setattr(obj, attr, new_value)


class TestVardaMethods(unittest.TestCase):
    def test_normalize_date_from_string(self):
        assert _normalize_date("2020-12-05") == datetime.date(2020, 12, 5)

    def test_normalize_datetime_to_date(self):
        dt = datetime.datetime(2023, 2, 1, 12, 30)
        assert _normalize_date(dt) == datetime.date(2023, 2, 1)

    def test_normalize_invalid_string_date_unmodified(self):
        assert _normalize_date("not-a-date") == "not-a-date"

    def test_normalize_bool_true(self):
        assert _normalize_bool("true") is True
        assert _normalize_bool("True") is True
        assert _normalize_bool(True) is True

    def test_normalize_bool_false(self):
        assert _normalize_bool("false") is False
        assert _normalize_bool("False") is False
        assert _normalize_bool(False) is False

    def test_normalize_value_none(self):
        assert _normalize_value(None) == ""

    def test_normalize_value_date(self):
        assert _normalize_value(datetime.date(2020, 12, 1)) == datetime.date(2020, 12, 1)

    def test_normalize_value_string(self):
        assert _normalize_value("abc") == "abc"

    def test_set_if_changed_no_difference(self):
        dummy = Dummy()
        dummy.sukunimi = "Hokkanen"
        changes = {"has_changes": False}
        set_if_changed = _create_change_detector(changes)
        set_if_changed(dummy, "sukunimi", "Hokkanen")

        assert not changes["has_changes"]
        assert dummy.sukunimi == "Hokkanen"

    def test_set_if_changed_with_difference(self):
        dummy = Dummy()
        dummy.sukunimi = "Hokkanen"
        changes = {"has_changes": False}
        set_if_changed = _create_change_detector(changes)
        set_if_changed(dummy, "sukunimi", "Anttola")

        assert changes["has_changes"]
        assert dummy.sukunimi == "Anttola"

    def test_set_if_changed_date_string_equivalent(self):
        dummy = Dummy()
        dummy.syntyma_pvm = datetime.date(2020, 5, 1)
        changes = {"has_changes": False}
        set_if_changed = _create_change_detector(changes)
        set_if_changed(dummy, "syntyma_pvm", "2020-05-01")

        assert not changes["has_changes"]
        assert dummy.syntyma_pvm == datetime.date(2020, 5, 1)

    def test_set_if_changed_bool_equivalent(self):
        dummy = Dummy()
        dummy.vtj_yksiloity = True
        changes = {"has_changes": False}
        set_if_changed = _create_change_detector(changes)
        set_if_changed(dummy, "vtj_yksiloity", "true")

        assert not changes["has_changes"]
        assert dummy.vtj_yksiloity is True


class TestOppijanumerorekisteriLogic(TestCase):
    def setUp(self):
        self.henkilo = Henkilo.objects.create(
            henkilotunnus="",
            henkilotunnus_unique_hash="",
            syntyma_pvm=None,
            henkilo_oid="1.2.246.562.24.00000000001",
            etunimet="Old Etunimet",
            kutsumanimi="Old Kutsu",
            sukunimi="Old Sukunimi",
            turvakielto=False,
            vtj_yksiloity=False,
            vtj_yksilointi_yritetty=False,
            aidinkieli_koodi="",
            kotikunta_koodi="",
            sukupuoli_koodi="",
            katuosoite="",
            postinumero="",
            postitoimipaikka="",
        )

    @patch("varda.misc.hash_string", return_value="HASH123")
    @patch("varda.misc.encrypt_string", return_value="ENC123")
    def test_apply_henkilo_fields_full_json(self, mock_enc, mock_hash):
        json_data = {
            "etunimet": "Airi Testi",
            "syntymaaika": "2013-01-01",
            "hetu": "010113A9127",
            "kutsumanimi": "Airi",
            "oidHenkilo": "1.2.246.562.24.87081324139",
            "sukunimi": "Stenberg-Testi",
            "sukupuoli": "2",
            "kotikunta": None,
            "turvakielto": False,
            "yksiloityVTJ": True,
            "yksilointiYritetty": True,
        }

        save_henkilo_to_db(self.henkilo.id, json_data)
        h = Henkilo.objects.get(id=self.henkilo.id)

        self.assertEqual(h.etunimet, "Airi Testi")
        self.assertEqual(h.kutsumanimi, "Airi")
        self.assertEqual(h.sukunimi, "Stenberg-Testi")
        self.assertEqual(h.henkilo_oid, "1.2.246.562.24.87081324139")
        self.assertEqual(h.sukupuoli_koodi, "2")
        self.assertEqual(h.kotikunta_koodi, "")  # None → ""
        self.assertEqual(h.turvakielto, False)
        self.assertEqual(h.vtj_yksiloity, True)
        self.assertEqual(h.vtj_yksilointi_yritetty, True)
        self.assertEqual(h.syntyma_pvm, datetime.date(2013, 1, 1))


class NoChangeTests(TestCase):
    def setUp(self):
        self.henkilo = Henkilo.objects.create(
            syntyma_pvm=datetime.date(2013, 1, 1),
            etunimet="Airi",
            kutsumanimi="Airi",
            sukunimi="Testi",
            henkilo_oid="1.2.246.562.24.87081324139",
        )

    @patch("django.db.models.Model.save")
    def test_no_changes_produces_no_save(self, mock_save):
        json_data = {
            "syntymaaika": "2013-01-01",
            "etunimet": "Airi",
        }
        save_henkilo_to_db(self.henkilo.id, json_data)
        mock_save.assert_not_called()


class HenkiloSyntymaPvmChangedTests(TestCase):
    def setUp(self):
        self.henkilo = Henkilo.objects.create(
            syntyma_pvm=None,
            etunimet="Airi",
            kutsumanimi="Airi",
            sukunimi="Testi",
            henkilo_oid="1.2.246.562.24.87081324139",
        )

    def test_syntyma_pvm_changed_after_save(self):
        json_data = {
            "syntymaaika": "2013-01-01",
            "etunimet": "Airi",
        }
        save_henkilo_to_db(self.henkilo.id, json_data)
        self.henkilo.refresh_from_db()
        self.assertEqual(self.henkilo.syntyma_pvm, datetime.date(2013, 1, 1))


class HuoltajaTests(TestCase):
    def setUp(self):
        self.henkilo = Henkilo.objects.create(
            syntyma_pvm=datetime.date(2000, 1, 1),
            etunimet="Test",
            kutsumanimi="Test",
            sukunimi="Persson",
            henkilo_oid="1.2.246.562.24.87081324139",
        )
        Huoltaja.objects.create(henkilo=self.henkilo)

    def test_huoltaja_syntyma_pvm_cleared(self):
        json_data = {"syntymaaika": "1983-01-01"}
        save_henkilo_to_db(self.henkilo.id, json_data)
        h = Henkilo.objects.get(id=self.henkilo.id)
        self.assertIsNone(h.syntyma_pvm)


class HetuTests(TestCase):
    def setUp(self):
        self.henkilo = Henkilo.objects.create(
            henkilotunnus="ENC1",
            henkilotunnus_unique_hash="HASH1",
            etunimet="X",
            kutsumanimi="X",
            sukunimi="X",
            henkilo_oid="OID",
        )

    @patch("varda.misc.hash_string", return_value="HASH1")
    @patch("varda.misc.encrypt_string")
    def test_same_hash_skips_reencryption(self, enc_mock, hash_mock):
        save_henkilo_to_db(self.henkilo.id, {"hetu": "010113A9127"})
        enc_mock.assert_not_called()


class DuplicateHetuTests(TestCase):
    def setUp(self):
        self.h1 = Henkilo.objects.create(
            henkilotunnus="010420A453M",
            henkilotunnus_unique_hash="fecfde5932be60b5036616c3097133ccefc106bfbd5d54e752cef9e27c98cf3f",
            etunimet="A",
            kutsumanimi="A",
            sukunimi="A",
            henkilo_oid="1.2.246.562.24.87081324139",
        )
        self.h2 = Henkilo.objects.create(
            etunimet="B",
            kutsumanimi="B",
            sukunimi="B",
            henkilo_oid="1.2.246.562.24.123456789123",
        )

    def test_duplicate_hetu_blocks_update(self):
        try:
            save_henkilo_to_db(self.h2.id, {"hetu": "010420A453M"}, return_not_throw_error=False)
        except ValidationError as e:
            self.assertEqual(e.detail["henkilotunnus"][0]["error_code"], "HE014")
            self.assertEqual(e.detail["henkilotunnus"][0]["description"], "Henkilo with this henkilotunnus already exists.")
        else:
            self.fail("ValidationError not raised")


class AddressTests(TestCase):
    def setUp(self):
        self.h = Henkilo.objects.create(
            etunimet="X",
            kutsumanimi="X",
            sukunimi="X",
            henkilo_oid="OID",
        )

    def test_non_vtj_address_is_ignored(self):
        json_data = {
            "yhteystiedotRyhma": [
                {
                    "ryhmaKuvaus": "foo",
                    "ryhmaAlkuperaTieto": "bar",
                    "yhteystieto": [
                        {"yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KATUOSOITE.value, "yhteystietoArvo": "Joku tie 1"}
                    ],
                }
            ]
        }

        save_henkilo_to_db(self.h.id, json_data)
        self.h.refresh_from_db()
        self.assertEqual(self.h.katuosoite, "")


class VTJAddressUpdateTests(TestCase):
    def setUp(self):
        self.h = Henkilo.objects.create(
            etunimet="Test",
            kutsumanimi="Test",
            sukunimi="User",
            henkilo_oid="OID123",
            katuosoite="",
            postinumero="",
            postitoimipaikka="",
        )

    def test_vtj_address_updates_henkilo(self):
        json_data = {
            "yhteystiedotRyhma": [
                {
                    "ryhmaKuvaus": Yhteystietoryhmatyyppi.VTJ_VAKINAINEN_KOTIMAINEN_OSOITE.value,
                    "ryhmaAlkuperaTieto": YhteystietoAlkupera.VTJ.value,
                    "yhteystieto": [
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KATUOSOITE.value,
                            "yhteystietoArvo": "Katutie 12",
                        },
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_POSTINUMERO.value,
                            "yhteystietoArvo": "00100",
                        },
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KAUPUNKI.value,
                            "yhteystietoArvo": "Helsinki",
                        },
                    ],
                }
            ]
        }

        save_henkilo_to_db(self.h.id, json_data)
        self.h.refresh_from_db()
        self.assertEqual(self.h.katuosoite, "Katutie 12")
        self.assertEqual(self.h.postinumero, "00100")
        self.assertEqual(self.h.postitoimipaikka, "Helsinki")


class TyontekijaAddressRemovalTests(TestCase):
    def setUp(self):
        self.h = Henkilo.objects.create(
            etunimet="Teppo",
            kutsumanimi="Teppo",
            sukunimi="Työntekijä",
            henkilo_oid="OID123",
            katuosoite="Katutie 12",
            postinumero="00100",
            postitoimipaikka="Helsinki",
            kotikunta_koodi="091",
        )
        Tyontekija.objects.create(henkilo=self.h, vakajarjestaja_id=1)

    def test_address_removed_if_tyontekija(self):
        json_data = {
            "yhteystiedotRyhma": [
                {
                    "ryhmaKuvaus": Yhteystietoryhmatyyppi.VTJ_VAKINAINEN_KOTIMAINEN_OSOITE.value,
                    "ryhmaAlkuperaTieto": YhteystietoAlkupera.VTJ.value,
                    "yhteystieto": [
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KATUOSOITE.value,
                            "yhteystietoArvo": "Katutie 12",
                        },
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_POSTINUMERO.value,
                            "yhteystietoArvo": "00100",
                        },
                        {
                            "yhteystietoTyyppi": YhteystietoTyyppi.YHTEYSTIETO_KAUPUNKI.value,
                            "yhteystietoArvo": "Helsinki",
                        },
                    ],
                }
            ]
        }

        save_henkilo_to_db(self.h.id, json_data)
        self.h.refresh_from_db()
        self.assertEqual(self.h.kotikunta_koodi, "")
        self.assertEqual(self.h.katuosoite, "")
        self.assertEqual(self.h.postinumero, "")
        self.assertEqual(self.h.postitoimipaikka, "")


class KotikuntaNullTests(TestCase):
    def setUp(self):
        self.h = Henkilo.objects.create(
            etunimet="Matti",
            kutsumanimi="Matti",
            sukunimi="Meikäläinen",
            henkilo_oid="1.2.246.562.24.87081324139",
            kotikunta_koodi="091",
        )

    def test_kotikunta_null_from_json_stored_as_empty_string(self):
        json_data = {
            "kotikunta": None,
            "etunimet": "Matti",
            "kutsumanimi": "Matti",
            "sukunimi": "Meikäläinen",
            "oidHenkilo": "1.2.246.562.24.87081324139",
        }

        save_henkilo_to_db(self.h.id, json_data)
        self.h.refresh_from_db()
        self.assertEqual(self.h.kotikunta_koodi, "")


class DuplicateHenkiloDetectionTests(TestCase):
    def setUp(self):
        self.h1 = Henkilo.objects.create(
            etunimet="A",
            kutsumanimi="A",
            sukunimi="Test",
            henkilo_oid="1.2.3.4.5",
            henkilotunnus_unique_hash="",
            henkilotunnus="",
        )

        self.h2 = Henkilo.objects.create(
            etunimet="B",
            kutsumanimi="B",
            sukunimi="Test",
            henkilo_oid="9.9.9.9.9",
            henkilotunnus_unique_hash="",
            henkilotunnus="",
        )

    def test_duplicate_by_hetu_hash(self):
        hetu = "291120A716U"
        json_data = {"hetu": hetu}
        self.h2.henkilotunnus_unique_hash = hash_string(hetu)
        self.h2.save()
        result = _apply_hetu(self.h1, json_data, fake_set_if_changed, return_not_throw_error=True)
        self.assertFalse(result, "Duplicate by hetu hash should return False")

    def test_same_record_not_duplicate(self):
        hetu = "291120A716U"
        json_data = {"hetu": hetu}
        self.h1.henkilotunnus_unique_hash = hash_string(hetu)
        self.h1.save()
        result = _apply_hetu(self.h1, json_data, fake_set_if_changed, return_not_throw_error=True)
        self.assertTrue(result)

    def test_no_duplicate_when_hetu_missing_and_oid_unique(self):
        json_data = {"oidHenkilo": "new.oid.123", "hetu": None}
        result = _apply_hetu(self.h1, json_data, fake_set_if_changed, True)
        self.assertTrue(result)

    def test_duplicate_by_hetu_even_with_different_oid(self):
        hetu = "291120A716U"
        json_data = {"hetu": hetu, "oidHenkilo": "different.oid"}
        self.h2.henkilotunnus_unique_hash = hash_string(hetu)
        self.h2.save()
        result = _apply_hetu(self.h1, json_data, fake_set_if_changed, True)
        self.assertFalse(result)

    def test_duplicate_by_oid_detected_when_json_oid_matches_another_person(self):
        json_data = {
            "oidHenkilo": self.h2.henkilo_oid,
            "hetu": None,
        }
        result = _apply_hetu(self.h1, json_data, fake_set_if_changed, True)
        self.assertFalse(result)
