import sys
import os
from flask.ext.testing import TestCase as FlaskTestCase
import shutil
from StringIO import StringIO
import mockfs
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                                os.pardir,
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir,
                               'muranorepository',
                               '__init__.py')):
    sys.path.insert(0, possible_topdir)
from muranorepository.consts import MANIFEST
from muranorepository.tests.fixtures.consts import MANIFEST_FILE
from muranorepository import config
from muranorepository.main import make_app


class TestAdminAPI(FlaskTestCase):
    url = "/v1/admin/{0}"
    url_with_path = "/v1/admin/{0}/{1}"

    def create_app(self):
        test_app = make_app()
        test_app.config['TESTING'] = True
        return test_app

    def setUp(self):
        config_files = [os.path.join(possible_topdir,
                                     'muranorepository',
                                     'tests',
                                     'test.conf')]

        config.parse_configs(None, config_files)
        self.mfs = mockfs.replace_builtins()
        self.mfs.add_entries(
            {
                '/bin/server': {
                    'test-manifest.yaml': MANIFEST_FILE,
                    'ui': {'test1.yaml': ''},
                    'heat':
                          {'Windows.template': '',
                           'folder_to_delete': {}
                           }
                }
            })

    def tearDown(self):
        mockfs.restore_builtins()

    def test_list_manifests(self):
        response = self.client.get(self.url.format(MANIFEST))
        expected_result = {MANIFEST: ['test-manifest.yaml']}
        self.assert200(response)
        self.assertEquals(response.json, expected_result)

    def test_list_ui(self):
        response = self.client.get(self.url.format('ui'))
        expected_result = {'ui': ['test1.yaml']}
        self.assert200(response)
        self.assertEquals(response.json, expected_result)

    def test_create_ui_subfolder(self):
        response = self.client.put(self.url_with_path.format('ui', 'test'))
        expected_result = {'result': 'success'}
        self.assert200(response)
        self.assertEquals(response.json, expected_result)
        shutil.rmtree('bin/server/ui/test')

    def test_delete_heat_subfolder(self):
        url = self.url_with_path.format('heat',
                                        'folder_to_delete')
        response = self.client.delete(url)
        self.assert200(response)
        expected_result = {'result': 'success'}
        self.assertEquals(response.json, expected_result)

    def test_upload_ui_file(self):
        upload_data = {'file': (StringIO('content'), 'test.yaml')}
        response = self.client.post(self.url.format('ui'),
                                    data=upload_data)
        'test.yaml' in os.listdir('bin/server/ui')
        self.assert200(response)
        expected_result = {'result': 'success'}
        self.assertEquals(response.json, expected_result)
