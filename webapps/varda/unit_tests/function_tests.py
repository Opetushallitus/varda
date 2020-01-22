import unittest
from varda.pagination import get_full_path_without_page_number


class TestVardaMethods(unittest.TestCase):
    def test_get_full_path_without_page_number(self):
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/'), '/api/v1/toimipaikat/')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?'), '/api/v1/toimipaikat/')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?&'), '/api/v1/toimipaikat/')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?page='), '/api/v1/toimipaikat/?page=')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?page=&'), '/api/v1/toimipaikat/?page=')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?page=1&'), '/api/v1/toimipaikat/')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?foo=1&page=2&'), '/api/v1/toimipaikat/?foo=1')
        self.assertEqual(get_full_path_without_page_number('/api/v1/toimipaikat/?foo=1&page=2&bar=something'), '/api/v1/toimipaikat/?foo=1&bar=something')
