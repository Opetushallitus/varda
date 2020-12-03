import json
from django.test import TestCase
from varda.unit_tests.test_utils import SetUpTestClient, assert_validation_error, mock_admin_user


class VardaViewsReportingTests(TestCase):
    fixtures = ['varda/unit_tests/fixture_basics.json']

    """
    Reporting related view-tests
    """

    def test_reporting_api(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'tiedonsiirtotilasto': 'http://testserver/api/reporting/v1/tiedonsiirtotilasto/'})

    def test_kela_reporting_api(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.content), {'aloittaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/aloittaneet/',
                                                    'lopettaneet': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/lopettaneet/',
                                                    'maaraaikaiset': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/',
                                                    'korjaustiedot': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/',
                                                    'korjaustiedotpoistetut': 'http://testserver/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/'})

    def test_reporting_api_kelaetuusmaksatusaloittaneet_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusaloittaneet_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/aloittaneet/?luonti_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusalopettaneet_get_date_filters(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/lopettaneet/?muutos_pvm=2010-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatusmaaraaikaiset_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/maaraaikaiset/?luonti_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'luonti_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_get_alkamis_pvm_filter(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedot/?muutos_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'muutos_pvm', 'GE019', 'Time period exceeds allowed timeframe.')

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 200)

        client = SetUpTestClient('tester3').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/')
        self.assertEqual(resp.status_code, 403)

    def test_reporting_api_kelaetuusmaksatuskorjaustiedot_poistetut_get_alkamis_pvm(self):
        mock_admin_user('tester2')
        client = SetUpTestClient('tester2').client()
        resp = client.get('/api/reporting/v1/kela/etuusmaksatus/korjaustiedotpoistetut/?poisto_pvm=2018-01-01')
        self.assertEqual(resp.status_code, 400)
        assert_validation_error(resp, 'poisto_pvm', 'GE019', 'Time period exceeds allowed timeframe.')
