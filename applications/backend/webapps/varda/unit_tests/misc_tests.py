import datetime
import json

import responses
from django.test import TestCase
from rest_framework import status

from varda import misc
from varda.misc import (calculate_tilastointi_pvm, calculate_next_start_end_date, is_date_within_timeframe,
                        adjust_dates_for_current_year)
from varda.models import Henkilo, TukipaatosAikavali
from varda.unit_tests.test_utils import assert_status_code, assert_validation_error, SetUpTestClient


class MiscTests(TestCase):
    fixtures = ['fixture_basics']

    @responses.activate
    def test_hetu_crypting(self):
        hetu = '210669-043K'
        henkilo_id = self._create_henkilo(hetu)
        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))

        new_hetu = '111299-913S'
        new_henkilo_id = self._create_henkilo(new_hetu)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(hetu_encrypted)
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        misc.decrypt_henkilotunnus(new_hetu_encrypted)

        hetu_encrypted = Henkilo.objects.get(id=henkilo_id).henkilotunnus
        self.assertEqual(hetu, misc.decrypt_henkilotunnus(hetu_encrypted))
        new_hetu_encrypted = Henkilo.objects.get(id=new_henkilo_id).henkilotunnus
        self.assertEqual(new_hetu, misc.decrypt_henkilotunnus(new_hetu_encrypted))

        new_key_only_hetu = '111299-9255'
        new_key_only_henkilo_id = self._create_henkilo(new_key_only_hetu)
        new_key_only_hetu_encrypted = Henkilo.objects.get(id=new_key_only_henkilo_id).henkilotunnus
        self.assertEqual(new_key_only_hetu, misc.decrypt_henkilotunnus(new_key_only_hetu_encrypted))

    def _create_henkilo(self, hetu):
        responses.add(responses.POST,
                      'https://virkailija.testiopintopolku.fi/oppijanumerorekisteri-service/henkilo/',
                      json='1.2.987654321',
                      status=status.HTTP_201_CREATED)
        henkilo = {
            'henkilotunnus': hetu,
            'etunimet': 'Pauliina',
            'kutsumanimi': 'Pauliina',
            'sukunimi': 'Virtanen'
        }
        client = SetUpTestClient('tester').client()
        resp = client.post('/api/v1/henkilot/', henkilo)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        return resp.json()['id']

    def test_request_path_type(self):
        request_path_string = '/api/v1/toimipaikat/55/'
        request_path_bytes = b'/api/v1/toimipaikat/55/'
        request_path_empty_string = ''
        request_path_empty_byte = b''

        url_string, params_string = misc.path_parse(request_path_string)
        url_bytes, params_bytes = misc.path_parse(request_path_bytes)
        url_empty_string, params_empty_string = misc.path_parse(request_path_empty_string)
        url_empty_byte, params_empty_byte = misc.path_parse(request_path_empty_byte)

        self.assertEqual(url_string, request_path_string)
        self.assertEqual(url_bytes, request_path_string)
        self.assertEqual(url_empty_string, '')
        self.assertEqual(url_empty_byte, '')

    def test_dy011_error(self):
        client = SetUpTestClient('tester10').client()

        test_cases = [
            ('', 'Invalid JSON payload. Expected a dictionary, but got str.',),
            (1, 'Invalid JSON payload. Expected a dictionary, but got int.',),
            (1.1, 'Invalid JSON payload. Expected a dictionary, but got float.',),
            (False, 'Invalid JSON payload. Expected a dictionary, but got bool.',),
            ([''], 'Invalid JSON payload. Expected a dictionary, but got list.',)
        ]
        for test_case in test_cases:
            resp = client.post('/api/henkilosto/v1/tyoskentelypaikat/', json.dumps(test_case[0]),
                               content_type='application/json')
            assert_status_code(resp, status.HTTP_400_BAD_REQUEST)
            assert_validation_error(resp, 'errors', 'DY011', test_case[1])

    def test_calculate_tilastointi_pvm(self):
        """Test calculate_tilastointi_pvm function when within a timeframe."""
        date = datetime.date

        # Timeframe goes over the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 12, 1),
            paattymis_pvm=date(1901, 1, 31),
            tilastointi_pvm=date(1900, 12, 31)
        )

        selected_date = date(2023, 12, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe)
        self.assertEqual(statistical_date, date(2023, 12, 31))

        selected_date = date(2024, 1, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe)
        self.assertEqual(statistical_date, date(2023, 12, 31))

        selected_date = date(2023, 12, 31)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe)
        self.assertEqual(statistical_date, date(2023, 12, 31))

        # Timeframe in the middle of the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 5, 1),
            paattymis_pvm=date(1901, 6, 30),
            tilastointi_pvm=date(1900, 5, 31)
        )

        selected_date = date(2023, 5, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe)
        self.assertEqual(statistical_date, date(2023, 5, 31))

        selected_date = date(2023, 6, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe)
        self.assertEqual(statistical_date, date(2023, 5, 31))

    def test_calculate_next_tilastointi_pvm(self):

        date = datetime.date

        # Timeframe in the middle of the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 5, 1),
            paattymis_pvm=date(1901, 6, 30),
            tilastointi_pvm=date(1900, 5, 31)
        )

        selected_date = date(2023, 12, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2024, 5, 31))

        selected_date = date(2023, 10, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2024, 5, 31))

        selected_date = date(2023, 5, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2023, 5, 31))

        selected_date = date(2023, 6, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2023, 5, 31))

        # Timeframe goes over the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 12, 1),
            paattymis_pvm=date(1901, 1, 31),
            tilastointi_pvm=date(1900, 12, 31)
        )

        selected_date = date(2023, 12, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2023, 12, 31))

        selected_date = date(2024, 1, 15)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2023, 12, 31))

        selected_date = date(2023, 12, 31)
        statistical_date = calculate_tilastointi_pvm(selected_date, timeframe, next_timeframe=True)
        self.assertEqual(statistical_date, date(2023, 12, 31))

    def test_calculate_next_timeframe(self):

        date = datetime.date

        # Timeframe in the middle of the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 5, 1),
            paattymis_pvm=date(1901, 6, 30),
            tilastointi_pvm=date(1900, 5, 31)
        )

        selected_date = date(2023, 12, 15)  # Current date before timeframe and the year before
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 5, 1))  # Next timeframe dates should be next year
        self.assertEqual(end_date, date(2024, 6, 30))   # Next timeframe dates should be next year

        selected_date = date(2024, 3, 15)  # Current date before timeframe, same year
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 5, 1))
        self.assertEqual(end_date, date(2024, 6, 30))

        selected_date = date(2024, 5, 15)  # Current date in timeframe
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 5, 1))
        self.assertEqual(end_date, date(2024, 6, 30))

        # Timeframe crosses the year
        timeframe = TukipaatosAikavali.objects.create(
            alkamis_pvm=date(1900, 12, 1),
            paattymis_pvm=date(1901, 1, 31),
            tilastointi_pvm=date(1900, 12, 31)
        )

        selected_date = date(2024, 12, 15)  # Current date in timeframe, timeframe crosses year
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 12, 1))
        self.assertEqual(end_date, date(2025, 1, 31))

        selected_date = date(2025, 1, 15)  # Current date in timeframe, timeframe crosses year
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 12, 1))
        self.assertEqual(end_date, date(2025, 1, 31))

        selected_date = date(2024, 10, 15)  # Current date outside timeframe, next timeframe crosses year
        start_date, end_date = calculate_next_start_end_date(selected_date, timeframe.alkamis_pvm, timeframe.paattymis_pvm)
        self.assertEqual(start_date, date(2024, 12, 1))
        self.assertEqual(end_date, date(2025, 1, 31))

    # Test is_date_within_timeframe
    def test_within_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(1901, 1, 1)
        end_date = datetime.date(1901, 12, 31)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))

    def test_outside_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(1901, 1, 1)
        end_date = datetime.date(1901, 2, 1)
        self.assertFalse(is_date_within_timeframe(today, start_date, end_date))

    def test_on_timeframe(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(1901, 2, 2)
        end_date = datetime.date(1901, 2, 2)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))

    def test_within_timeframe_span_across_two_years(self):
        today = datetime.date(2024, 12, 15)
        start_date = datetime.date(1901, 12, 1)
        end_date = datetime.date(1901, 1, 31)
        self.assertTrue(is_date_within_timeframe(today, start_date, end_date))

    def test_adjust_dates_for_current_year(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(1901, 1, 1)
        end_date = datetime.date(1901, 12, 31)
        adjusted_start, adjusted_end = adjust_dates_for_current_year(today, start_date, end_date)
        self.assertEqual(adjusted_start, datetime.date(2024, 1, 1))
        self.assertEqual(adjusted_end, datetime.date(2024, 12, 31))

    def test_adjust_dates_for_current_year_spanning_two_years(self):
        today = datetime.date(2024, 2, 2)
        start_date = datetime.date(1901, 12, 1)
        end_date = datetime.date(1901, 1, 31)
        adjusted_start, adjusted_end = adjust_dates_for_current_year(today, start_date, end_date)
        self.assertEqual(adjusted_start, datetime.date(2023, 12, 1))
        self.assertEqual(adjusted_end, datetime.date(2024, 1, 31))
