import os
import subprocess
from django.test import LiveServerTestCase


class AddXToimipaikkaaTests(LiveServerTestCase):

    def setUp(self):
        from django.core.management import call_command
        call_command('loaddata', 'varda/unit_tests/fixture_basics.json')

    def test_as_program(self):
        """
        LiveServer gets a (new) free port from OS every time this test is run.
        e.g. VARDA_HOST == "http://localhost:4590"
        """
        os.environ["VARDA_HOST"] = self.live_server_url

        """
        Result message from server includes several lines of output. Choose (split) only the first line for assertEqual.
        9/10 successful is correct because 1 same Toimipaikka is included in the load_testing_data() already.
        """
        self.assertEqual(subprocess.check_output(
            ["python", "varda/examples/add_toimipaikka/add_x_toimipaikkaa.py", "--input", "varda/examples/add_toimipaikka/10_toimipaikkaa.json"])
            .decode('ascii', 'ignore')
            .split('\n', 1)[0],
            "Successful POST-requests: 0 / 10")  # TODO: Original: 9/10; Fix this when Org.palvelu-mocking is done!
