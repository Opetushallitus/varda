import datetime
import unittest
from django.conf import settings
from rest_framework.exceptions import ValidationError as ValidationErrorRest
from varda.validators import (validate_henkilotunnus, validate_paivamaara1_before_paivamaara2,
                              validate_paivamaara1_after_paivamaara2, validate_vaka_date)


class ValidatorsTests(unittest.TestCase):
    def test_validate_henkilotunnus_production_permanent_hetu(self):
        try:
            settings.PRODUCTION_ENV = True
            validate_henkilotunnus('010397-1232')
        except ValidationErrorRest:
            self.fail('ValidationErrorRest was raised unexpectedly!')

    def test_validate_henkilotunnus_production_tilapainen_hetu(self):
        with self.assertRaises(ValidationErrorRest) as error:
            settings.PRODUCTION_ENV = True
            validate_henkilotunnus('180207-913F')
        self.assertEqual(error.exception.detail, {
            'henkilotunnus': [{'error_code': 'HE009', 'description': 'Temporary henkilotunnus is not permitted.'}]
        })

    def test_validate_henkilotunnus_non_production_permanent_hetu(self):
        try:
            settings.PRODUCTION_ENV = False
            validate_henkilotunnus('010397-1232')
        except ValidationErrorRest:
            self.fail('ValidationErrorRest was raised unexpectedly!')

    def test_validate_henkilotunnus_non_production_tilapainen_hetu(self):
        try:
            settings.PRODUCTION_ENV = False
            validate_henkilotunnus('180207-913F')
        except ValidationErrorRest:
            self.fail('ValidationErrorRest was raised unexpectedly!')

    def test_validate_paivamaara(self):
        self.assertEqual(validate_paivamaara1_before_paivamaara2('2019-10-14', '2019-10-15', True), True)
        self.assertEqual(validate_paivamaara1_before_paivamaara2('2019-10-15', '2019-10-15', True), True)
        self.assertEqual(validate_paivamaara1_before_paivamaara2('2019-10-15', '2019-10-15', False), False)

        self.assertEqual(validate_paivamaara1_after_paivamaara2('2019-10-16', '2019-10-15', True), True)
        self.assertEqual(validate_paivamaara1_after_paivamaara2('2019-10-15', '2019-10-15', True), True)
        self.assertEqual(validate_paivamaara1_after_paivamaara2('2019-10-15', '2019-10-15', False), False)

    def test_validate_date(self):
        self.assertRaises(ValidationErrorRest, validate_vaka_date, datetime.date(1999, 1, 1))

        try:
            validate_vaka_date(datetime.date(2000, 1, 1))
            validate_vaka_date(datetime.date(2010, 1, 1))
        except ValidationErrorRest:
            self.fail('ValidationError was raised unexpectedly!')
