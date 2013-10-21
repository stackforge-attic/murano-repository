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
from muranorepository.consts import UI, WORKFLOW, AGENT, SCRIPTS, HEAT
from muranorepository.tests.fixtures import FIXTURE
from muranorepository import config
from muranorepository.main import make_app


class TestDataTypeListing(FlaskTestCase):
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
        self.mfs.add_entries(FIXTURE)

    def tearDown(self):
        mockfs.restore_builtins()

    def test_list_manifests_files(self):
        response = self.client.get(self.url.format(MANIFEST))
        self.assert200(response)
        expected_result = {MANIFEST: ['test-manifest.yaml']}
        self.assertEquals(response.json, expected_result)

    def test_list_ui_files(self):
        response = self.client.get(self.url.format(UI))
        self.assert200(response)
        expected_result = {UI: ['test1.yaml']}
        self.assertEquals(response.json, expected_result)

    def test_list_workflows(self):
        response = self.client.get(self.url.format(WORKFLOW))
        self.assert200(response)
        expected_result = {WORKFLOW: ['test1.xml']}
        self.assertEquals(response.json, expected_result)

    def test_list_heat_templates(self):
        response = self.client.get(self.url.format(HEAT))
        expected_result = {HEAT: ['Windows.template']}
        self.assert200(response)
        self.assertEquals(response.json, expected_result)

    def test_list_agent_templates(self):
        response = self.client.get(self.url.format(AGENT))
        self.assert200(response)
        expected_result = {AGENT: ['test1.template',
                                   'subfolder/test12.template',
                                   'subfolder/test11.template',
                                   'subfolder/subsubfolder/test21.template']}
        self.assertEquals(response.json, expected_result)

    def test_list_scripts(self):
        response = self.client.get(self.url.format(SCRIPTS))
        self.assert200(response)
        expected_result = {SCRIPTS: ['test1.sh']}
        self.assertEquals(response.json, expected_result)

    def test_list_agent_templates_from_subfolder(self):
        url = self.url_with_path.format(AGENT, 'subfolder')
        response = self.client.get(url)
        self.assert200(response)
        expected_result = {AGENT: ['test12.template',
                                   'test11.template',
                                   'subsubfolder/test21.template']}
        self.assertEquals(response.json, expected_result)

    def test_list_agent_templates_from_subsubfolder(self):
        url = self.url_with_path.format(AGENT, 'subfolder/subsubfolder')
        response = self.client.get(url)
        self.assert200(response)
        expected_result = {AGENT: ['test21.template']}
        self.assertEquals(response.json, expected_result)
