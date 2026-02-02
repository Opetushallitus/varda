import datetime

from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from varda.validators import (
    validate_henkilotunnus,
    validate_paivamaara1_before_paivamaara2,
    validate_paivamaara1_after_paivamaara2,
    validate_vaka_date,
)


class ValidatorsTests(TestCase):
    fixtures = ["fixture_basics"]

    @override_settings(PRODUCTION_ENV=True)
    def test_validate_henkilotunnus_production_permanent_hetu(self):
        try:
            validate_henkilotunnus("010397-1232")
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly!")

    @override_settings(PRODUCTION_ENV=True)
    def test_validate_henkilotunnus_production_tilapainen_hetu(self):
        with self.assertRaises(ValidationError) as error:
            validate_henkilotunnus("180207-913F")
        self.assertEqual(
            error.exception.detail,
            {"henkilotunnus": [{"error_code": "HE009", "description": "Temporary henkilotunnus is not permitted."}]},
        )

    def test_validate_henkilotunnus_non_production_permanent_hetu(self):
        try:
            validate_henkilotunnus("010397-1232")
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly!")

    def test_validate_henkilotunnus_non_production_tilapainen_hetu(self):
        try:
            validate_henkilotunnus("180207-913F")
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly!")

    def test_validate_henkilotunnus_2023_reform(self):
        hetu_list = [
            "010594Y9021",
            "020594X903P",
            "020594X902N",
            "030594W903B",
            "030694W9024",
            "040594V9030",
            "040594V902Y",
            "050594U903M",
            "050594U902L",
            "010516B903X",
            "010516B902W",
            "020516C903K",
            "020516C902J",
            "030516D9037",
            "030516D9026",
            "010501E9032",
            "020502E902X",
            "020503F9037",
            "020504A902E",
            "020504B904H",
        ]

        try:
            for hetu in hetu_list:
                validate_henkilotunnus(hetu)
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly!")

    def test_validate_henkilotunnus_invalid(self):
        invalid_length_cases = ["010594Y902", "010594Y90211"]
        for hetu in invalid_length_cases:
            with self.assertRaises(ValidationError) as error:
                validate_henkilotunnus(hetu)
            self.assertEqual(
                error.exception.detail,
                {"henkilotunnus": [{"error_code": "HE005", "description": "Incorrect henkilotunnus length."}]},
            )

        invalid_intermediate_character_cases = ["150699G5305", "141099.378U"]
        for hetu in invalid_intermediate_character_cases:
            with self.assertRaises(ValidationError) as error:
                validate_henkilotunnus(hetu)
            self.assertEqual(
                error.exception.detail,
                {"henkilotunnus": [{"error_code": "HE006", "description": "Incorrect century character."}]},
            )

        invalid_date_cases = ["150699A5305", "141099C378U"]
        for hetu in invalid_date_cases:
            with self.assertRaises(ValidationError) as error:
                validate_henkilotunnus(hetu)
            self.assertEqual(
                error.exception.detail,
                {"henkilotunnus": [{"error_code": "HE007", "description": "Incorrect henkilotunnus date."}]},
            )

        invalid_control_character_cases = ["020420E128V", "250720A212T"]
        for hetu in invalid_control_character_cases:
            with self.assertRaises(ValidationError) as error:
                validate_henkilotunnus(hetu)
            self.assertEqual(
                error.exception.detail,
                {"henkilotunnus": [{"error_code": "HE008", "description": "ID number or control character is incorrect."}]},
            )

    def test_validate_paivamaara(self):
        self.assertEqual(validate_paivamaara1_before_paivamaara2("2019-10-14", "2019-10-15", True), True)
        self.assertEqual(validate_paivamaara1_before_paivamaara2("2019-10-15", "2019-10-15", True), True)
        self.assertEqual(validate_paivamaara1_before_paivamaara2("2019-10-15", "2019-10-15", False), False)

        self.assertEqual(validate_paivamaara1_after_paivamaara2("2019-10-16", "2019-10-15", True), True)
        self.assertEqual(validate_paivamaara1_after_paivamaara2("2019-10-15", "2019-10-15", True), True)
        self.assertEqual(validate_paivamaara1_after_paivamaara2("2019-10-15", "2019-10-15", False), False)

    def test_validate_date(self):
        self.assertRaises(ValidationError, validate_vaka_date, datetime.date(1999, 1, 1))

        try:
            validate_vaka_date(datetime.date(2000, 1, 1))
            validate_vaka_date(datetime.date(2010, 1, 1))
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly!")
