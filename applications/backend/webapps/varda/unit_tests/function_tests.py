import unittest

from varda.unit_tests.test_utils import (
    assert_expected_result_in_list_of_dicts_with_slight_time_difference_allowed,
    get_allowed_time_diff,
)


class TestVardaMethods(unittest.TestCase):
    def test_live_record_and_history_record_are_same_1(self):
        expected_result = {"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.001000Z"}
        list_of_dicts = [{"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.004000Z"}]
        assert_expected_result_in_list_of_dicts_with_slight_time_difference_allowed(expected_result, list_of_dicts)

    def test_live_record_and_history_record_are_same_2(self):
        expected_result = {"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.001000Z"}
        list_of_dicts = [
            {"id": 2, "vakasuhde_muutos_pvm": "2020-02-02T06:01:06.004000Z"},
            {"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.004000Z"},
        ]
        assert_expected_result_in_list_of_dicts_with_slight_time_difference_allowed(expected_result, list_of_dicts)

    def test_live_record_and_history_record_are_not_same_1(self):
        # Wrong id
        expected_result = {"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.001000Z"}
        list_of_dicts = [{"id": 2, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.004000Z"}]
        try:
            assert_expected_result_in_list_of_dicts_with_slight_time_difference_allowed(expected_result, list_of_dicts)
        except AssertionError as e:
            expected_error = (
                "{'id': 1, 'vakasuhde_muutos_pvm': '2024-02-02T06:01:06.001000Z'} not in "
                "[{'id': 2, 'vakasuhde_muutos_pvm': '2024-02-02T06:01:06.004000Z'}]"
            )
            if str(e) == str(expected_error):
                return None
        self.fail(msg=f"Failed with expected result: {expected_result} and list of dicts: {list_of_dicts}.")

    def test_live_record_and_history_record_are_not_same_2(self):
        # Time difference bigger than allowed
        expected_result = {"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.001000Z"}
        list_of_dicts = [{"id": 1, "vakasuhde_muutos_pvm": "2024-02-02T06:01:06.107000Z"}]
        try:
            assert_expected_result_in_list_of_dicts_with_slight_time_difference_allowed(expected_result, list_of_dicts)
        except AssertionError as e:
            _, time_diff_ms = get_allowed_time_diff()
            expected_error = (
                (
                    "{'id': 1, 'vakasuhde_muutos_pvm': '2024-02-02T06:01:06.001000Z'} and {'id': 1, "
                    "'vakasuhde_muutos_pvm': '2024-02-02T06:01:06.107000Z'} have a greater than allowed "
                )
                + time_diff_ms
                + "ms time difference."
            )
            if str(e) == str(expected_error):
                return None
        self.fail(msg=f"Failed with expected result: {expected_result} and list of dicts: {list_of_dicts}.")
