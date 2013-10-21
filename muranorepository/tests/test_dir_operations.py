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
import shutil
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
from muranorepository.consts import UI, AGENT, HEAT, WORKFLOW, SCRIPTS
from muranorepository.tests.fixtures import FIXTURE
from muranorepository import config
from muranorepository.main import make_app


class TestDirOperations(FlaskTestCase):
    url = "/v1/admin/{0}"
    url_with_path = "/v1/admin/{0}/{1}"
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

    def test_create_ui_subfolder(self):
        response = self.client.put(self.url_with_path.format(UI, 'test'))
        self.assert200(response)
        created_folder = 'bin/server/{0}/test'.format(UI)
        self.assertTrue(os.path.exists(created_folder))

        self.assertEquals(response.json, self.expected_result)
        shutil.rmtree(created_folder)

    def test_create_workflow_subfolder(self):
        response = self.client.put(self.url_with_path.format(WORKFLOW,
                                                             'test'))
        self.assert200(response)
        created_folder = 'bin/server/{0}/test'.format(WORKFLOW)
        self.assertTrue(os.path.exists(created_folder))
        self.assertEquals(response.json, self.expected_result)
        shutil.rmtree(created_folder)

    def test_create_heat_subfolder(self):
        response = self.client.put(self.url_with_path.format(HEAT,
                                                             'test_heat'))
        self.assert200(response)
        created_folder = 'bin/server/{0}/test_heat'.format(HEAT)
        self.assertTrue(os.path.exists(created_folder))
        self.assertEquals(response.json, self.expected_result)
        shutil.rmtree(created_folder)

    def test_create_scripts_subfolder(self):
        response = self.client.put(self.url_with_path.format(SCRIPTS, 'test'))
        self.assert200(response)
        created_folder = 'bin/server/{0}/test'.format(SCRIPTS)
        self.assertTrue(os.path.exists(created_folder))
        self.assertEquals(response.json, self.expected_result)
        shutil.rmtree(created_folder)

    def test_create_nested_agent_folders(self):
        response = self.client.put(self.url_with_path.format(AGENT,
                                                             'sub1/sub2'))
        self.assert200(response)
        self.assertTrue(
            os.path.exists('bin/server/{0}/sub1/sub2'.format(AGENT)))
        self.assertEquals(response.json, self.expected_result)
        shutil.rmtree('bin/server/{0}/sub1'.format(AGENT))

    def test_delete_heat_subfolder(self):
        url = self.url_with_path.format(HEAT, 'folder_to_delete')
        response = self.client.delete(url)
        self.assert200(response)
        self.assertEquals(response.json, self.expected_result)

    #negative tests
    def test_create_root_subfolder(self):
        response = self.client.put(self.url_with_path.format(MANIFEST,
                                                             'test'))
        self.assert403(response)
        created_folder = 'bin/server/{0}/test'.format(MANIFEST)
        self.assertFalse(os.path.exists(created_folder))
