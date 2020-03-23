import ast
import unittest

from varda.audit_log import audit_log


class VardaAuditLogTests(unittest.TestCase):

    def test_audit_log_end_index(self):
        with open('varda/unit_tests/audit_log_events.json') as f:
            data = ast.literal_eval(f.read())

        self.assertEqual(len(data), 1246)

        """
        Check against size (in bytes)
        """
        end_index_size_bytes = audit_log.get_batch_end_index_size_bytes(data, 0)
        self.assertEqual(end_index_size_bytes, 1245)

        end_index_size_bytes = audit_log.get_batch_end_index_size_bytes(data, 1000)
        self.assertEqual(end_index_size_bytes, 1245)

        new_log_batch_limit_in_bytes = 9346
        audit_log.AWS_LOG_BATCH_MAX_BYTES = new_log_batch_limit_in_bytes
        end_index_size_bytes = audit_log.get_batch_end_index_size_bytes(data, 0)
        self.assertEqual(end_index_size_bytes, 30)

        end_index_size_bytes = audit_log.get_batch_end_index_size_bytes(data, 30)
        self.assertEqual(end_index_size_bytes, 60)

        new_batch = data[30:end_index_size_bytes]
        batch_size = audit_log.get_batch_size_in_bytes(new_batch)
        self.assertEqual(batch_size, new_log_batch_limit_in_bytes)

        """
        Check against time
        """
        end_index_time = audit_log.get_batch_end_index_time(data, 0)
        self.assertEqual(end_index_time, 200)

        end_index_time = audit_log.get_batch_end_index_time(data, 300)
        self.assertEqual(end_index_time, 350)

        end_index_time = audit_log.get_batch_end_index_time(data, 1163)
        self.assertEqual(end_index_time, 1245)

        start_time_a = data[1163]['timestamp']
        start_time_b = data[1162]['timestamp']
        end_time = data[1245]['timestamp']

        self.assertLessEqual(end_time - start_time_a, audit_log.TWENTY_FOUR_HOURS_IN_MS)
        self.assertGreater(end_time - start_time_b, audit_log.TWENTY_FOUR_HOURS_IN_MS)
