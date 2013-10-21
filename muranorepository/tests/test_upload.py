# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from StringIO import StringIO

import os
from flask.ext.testing import TestCase as FlaskTestCase
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
from muranorepository.consts import UI, WORKFLOW, AGENT, HEAT, SCRIPTS
from muranorepository.tests.fixtures import FIXTURE
from muranorepository import config
from muranorepository.main import make_app


class TestUploadFiles(FlaskTestCase):
    url = '/v1/admin/{0}'
    url_with_path = '/v1/admin/{0}/{1}'
    path_to_upload = 'bin/server/{0}/{1}'
    expected_result = {'result': 'success'}

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
        self.mfs.add_entries(FIXTURE)

    def tearDown(self):
        mockfs.restore_builtins()

    def test_upload_manifest_file(self):
        data_type = MANIFEST
        file_name = 'new_manifest.yaml'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists('bin/server/{0}'.format(file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove('bin/server/{0}'.format(file_name))

    def test_upload_ui_file(self):
        data_type = UI
        file_name = 'new.yaml'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(self.path_to_upload.format(data_type,
                                                                  file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove(self.path_to_upload.format(data_type, file_name))

    def test_upload_workflow_file(self):
        data_type = WORKFLOW
        file_name = 'new.xml'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(self.path_to_upload.format(data_type,
                                                                  file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove(self.path_to_upload.format(data_type, file_name))

    def test_upload_agent_file(self):
        data_type = AGENT
        file_name = 'new.ps1'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(self.path_to_upload.format(data_type,
                                                                  file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove(self.path_to_upload.format(data_type, file_name))

    def test_upload_script(self):
        data_type = SCRIPTS
        file_name = 'new.sh'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(self.path_to_upload.format(data_type,
                                                                  file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove(self.path_to_upload.format(data_type, file_name))

    def test_upload_heat_file(self):
        data_type = HEAT
        file_name = 'new_heat_template.yaml'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(self.url.format(data_type),
                                    data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(self.path_to_upload.format(data_type,
                                                                  file_name)))
        self.assertEquals(response.json, self.expected_result)
        os.remove(self.path_to_upload.format(data_type, file_name))

    def test_upload_agent_template_to_subfolder(self):
        data_type = AGENT
        file_name = 'new_agent1.template'
        folder_name = 'subfolder'
        path_to_upload = 'bin/server/{0}/{1}/{2}'.format(data_type,
                                                         folder_name,
                                                         file_name)

        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(
            self.url_with_path.format(data_type,
                                      folder_name),
            data=upload_data)
        self.assert200(response)
        self.assertTrue(os.path.exists(path_to_upload))
        os.remove(path_to_upload)

    def test_upload_agent_template_to_subsubfolder(self):
        data_type = AGENT
        file_name = 'new_agent2.template'
        folders = 'subfolder/subsubfolder'
        upload_data = {'file': (StringIO('content'), file_name)}
        path_to_upload = 'bin/server/{0}/{1}/{2}'.format(data_type,
                                                         folders,
                                                         file_name)
        response = self.client.post(
            self.url_with_path.format(data_type, folders),
            data=upload_data)
        self.assert200(response)
        self.assertTrue(
            os.path.exists(path_to_upload))
        os.remove(path_to_upload)

    # Negative tests
    def test_upload_manifest_to_subfolder(self):
        data_type = MANIFEST
        file_name = 'new_manifest1.yaml'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(
            self.url_with_path.format(data_type,
                                      'subfolder'),
            data=upload_data)
        self.assert403(response)
        self.assertFalse(os.path.exists(self.path_to_upload.format('subfolder',
                                                                   file_name)))

    def test_upload_ui_file_to_non_existent_folder(self):
        data_type = UI
        file_name = 'new_ui_desc.yaml'
        folder_name = 'subfolder'
        upload_data = {'file': (StringIO('content'), file_name)}
        response = self.client.post(
            self.url_with_path.format(data_type,
                                      folder_name),
            data=upload_data)
        self.assert404(response)
