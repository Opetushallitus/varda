from unittest import mock

from django.test import TestCase

from varda import koodistopalvelu
from varda.enums.koodistot import Koodistot
from varda.models import Z2_Koodisto, Z2_Code, Z2_CodeTranslation


def mock_get_koodisto(koodisto_name):
    return {
        'versio': '1',
        'paivitysPvm': '2020-05-25'
    }


def mock_get_koodisto_codes(koodisto_name):
    result = []
    for i in range(2):
        result.append({
            'koodiArvo': '{0}_{1}'.format(koodisto_name, i),
            'voimassaAlkuPvm': '1990-01-01',
            'voimassaLoppuPvm': None,
            'metadata': [
                {
                    'kieli': 'fi',
                    'nimi': '{0}_{1}_nimi'.format(koodisto_name, i),
                    'kuvaus': '{0}_{1}_kuvaus'.format(koodisto_name, i),
                    'lyhytNimi': '{0}_{1}_lyhytNimi'.format(koodisto_name, i)
                },
                {
                    'kieli': 'sv',
                    'nimi': '{0}_{1}_nimi'.format(koodisto_name, i),
                    'kuvaus': '{0}_{1}_kuvaus'.format(koodisto_name, i),
                    'lyhytNimi': '{0}_{1}_lyhytNimi'.format(koodisto_name, i)
                }
            ]
        })
    return result


def mock_get_koodisto_codes_empty(koodisto_name):
    return []


class KoodistopalveluTests(TestCase):
    fixtures = ['fixture_basics']

    @mock.patch('varda.clients.koodistopalvelu_client.get_koodisto', mock_get_koodisto)
    @mock.patch('varda.clients.koodistopalvelu_client.get_koodisto_codes', mock_get_koodisto_codes)
    def test_simple_update(self):
        koodistot_count = len(Koodistot.list())
        code_id_qs = Z2_Code.objects.all().values_list('id', flat=True)
        code_id_list_old = list(code_id_qs)

        koodistopalvelu.update_koodistot()

        self.assertEqual(Z2_Koodisto.objects.count(), koodistot_count)
        self.assertEqual(Z2_Code.objects.count(), koodistot_count * 2)
        self.assertEqual(Z2_CodeTranslation.objects.count(), koodistot_count * 2 * 2)

        # Assert old codes have been deleted
        self.assertFalse(Z2_Code.objects.filter(id__in=code_id_list_old).exists())

    @mock.patch('varda.clients.koodistopalvelu_client.get_koodisto', mock_get_koodisto)
    @mock.patch('varda.clients.koodistopalvelu_client.get_koodisto_codes', mock_get_koodisto_codes_empty)
    def test_empty_codes_result(self):
        code_id_qs = Z2_Code.objects.all().values_list('id', flat=True)
        code_id_list_old = list(code_id_qs)

        koodistopalvelu.update_koodistot()

        # Assert old codes still exist
        self.assertListEqual(list(code_id_qs), code_id_list_old)
