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

MANIFEST_FILE = """
version: 0.1
service_display_name: Test

description: >-
  <strong> This goes a description

full_service_name: test_service
author: Mirantis Inc.
service_version: 1.0
enabled: True

ui:
  - test1.yaml

workflows:
  - test1.xml

heat:
  - Windows.template

agents:
  - test1.template

scripts:
  - test1.sh
"""

FIXTURE = {
    '/bin/server': {
        'test-manifest.yaml': MANIFEST_FILE,
        'ui': {'test1.yaml': 'content_ui'},
        'heat': {
            'Windows.template': 'content_heat',
            'folder_to_delete': {}
        },
        'agent': {
            'test1.template': 'content_agent1',
            'subfolder': {'test11.template': 'content_agent2',
                          'test12.template': '',
                          'subsubfolder': {'test21.template': 'content_agent3'}
                          },
        },
        'scripts': {'test1.sh': 'content_script'},
        'workflows': {'test1.xml': 'content_workflow'},
        'subfolder': {}
    }
}
