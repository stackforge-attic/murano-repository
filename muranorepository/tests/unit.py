import unittest2 as unittest
import sys
import os
from flask.ext.testing import TestCase as FlaskTestCase
from flask import Flask
import mockfs
from urlparse import urljoin
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                                os.pardir,
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir,
                                'muranorepository',
                                '__init__.py')):
    sys.path.insert(0, possible_topdir)
from muranorepository.consts import DATA_TYPES
from muranorepository.api import v1 as api


# class FilesActions(unittest.TestCase):
#     def setUp(self):
#         self.mfs = mockfs.replace_builtins()
#         self.mfs.add_entries({'/home/usr': 'test-manifest.yaml'})
#         self.mfs.add_entries({'/usr/bin/ui': 'test-ui1.yaml'})
#         # self.mfs.add_entries({'/usr/bin/agent': ['agent1.txt', 'agent2.txt', 'nested1'],
#         #                       '/usr/bin/agent/nested1': ['1.txt', '2.txt', 'nest2'],
#         #                       '/usr/bin/agent/nested1/nest2': ['11.txt', '21.txt']})
#
#     def tearDown(self):
#         mockfs.restore_builtins()
#
#     def test_get_single_manifest_file(self):
#         result = api.get_locations('manifests', '/home/usr')
#         self.assertEqual(result, {'manifests': ['test-manifest.yaml']})
#
#
#     def test_get_ui_files(self):
#         result = api.get_locations('ui', '/usr/bin/ui')
#         self.assertEqual(result, {'ui': ['test-ui1.yaml', 'ui2.yaml']})
#
#     def test_get_2_files(unittest.TestCase):
#
class TestSaveFile(FlaskTestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config['TESTING'] = True
        # Default port is 5000
        app.config['LIVESERVER_PORT'] = 8943
        return app




if __name__ == "__main__":
    unittest.main()
