from unittest import mock

from django.test import TestCase

from varda import lokalisointipalvelu
from varda.enums.lokalisointi import Lokalisointi
from varda.models import Z2_Koodisto, Z2_Code, Z2_CodeTranslation


def mock_get_lokalisointi(category, locale):
    result = []
    for i in range(2):
        result += [
            {"key": f"{category}_{i}", "modified": 1667385000, "locale": "fi", "value": f"{category}_{i}_nimi"},
            {"key": f"{category}_{i}", "modified": 1667385000, "locale": "sv", "value": f"{category}_{i}_nimi"},
        ]
    return result


def mock_get_lokalisointi_empty(category, locale):
    return []


class LokalisointipalveluTests(TestCase):
    fixtures = ["fixture_basics"]

    @mock.patch("varda.lokalisointipalvelu.get_lokalisointi", mock_get_lokalisointi)
    def test_simple_update(self):
        lokalisointi_count = len(Lokalisointi.list())

        koodisto_qs = Z2_Koodisto.objects.filter(name__in=Lokalisointi.list())
        code_qs = Z2_Code.objects.filter(koodisto__name__in=Lokalisointi.list())
        translation_qs = Z2_CodeTranslation.objects.filter(code__koodisto__name__in=Lokalisointi.list())

        code_id_qs = koodisto_qs.values_list("id", flat=True)
        code_id_list_old = list(code_id_qs)

        lokalisointipalvelu.update_lokalisointi_data()

        self.assertEqual(koodisto_qs.count(), lokalisointi_count)
        self.assertEqual(code_qs.count(), lokalisointi_count * 2)
        self.assertEqual(translation_qs.count(), lokalisointi_count * 2 * 2)

        # Assert old codes have been deleted
        self.assertFalse(code_qs.filter(id__in=code_id_list_old).exists())

    @mock.patch("varda.lokalisointipalvelu.get_lokalisointi", mock_get_lokalisointi_empty)
    def test_empty_lokalisointi_result(self):
        code_id_qs = Z2_Code.objects.filter(koodisto__name__in=Lokalisointi.list()).values_list("id", flat=True)
        code_id_list_old = list(code_id_qs)

        lokalisointipalvelu.update_lokalisointi_data()

        # Assert old codes still exist
        self.assertListEqual(list(code_id_qs), code_id_list_old)
