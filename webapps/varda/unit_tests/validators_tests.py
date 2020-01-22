import unittest
from django.conf import settings
from rest_framework.exceptions import ErrorDetail, ValidationError as ValidationErrorRest
from varda.validators import validate_henkilotunnus


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
        self.assertEqual(error.exception.detail, {'henkilotunnus': [ErrorDetail(string='180207-913F : Temporary personal identification is not permitted.', code='invalid')]})

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
