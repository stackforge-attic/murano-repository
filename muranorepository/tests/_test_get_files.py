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
from muranorepository.tests.fixtures import FIXTURE
from muranorepository import config
from muranorepository.main import make_app


class TestGetFiles(FlaskTestCase):
    url = "/v1/admin/{0}/{1}"

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

    def test_get_manifest_file(self):
        data_type = MANIFEST
        file_name = 'test-get-file-manifest.yaml'
        content = 'content-manifest'
        response = self.client.get(self.url.format(data_type,
                                                   file_name))
        #os.path.getmtime is not implemented in Mockfs
        self.assert200(response)
        self.assertEqual(response, content)
