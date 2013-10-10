#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os
#---mappings to possible data types in service manifests---
UI_FORMS = u"ui_forms"
WORKFLOWS = u"workflows"
HEAT_TEMPLATES = u"heat_templates"
AGENT_TEMPLATES = u"agent_templates"
SCRIPTS = u"scripts"
MANIFESTS = u"manifests"

DATA_TYPES = [UI_FORMS, WORKFLOWS, HEAT_TEMPLATES, AGENT_TEMPLATES, SCRIPTS, MANIFESTS]


#---main directory - parent for manifests files and data types directories
ROOT_DIRECTORY = os.path.join(os.path.dirname(__file__),
                              u'Services')

#---directory names of data types
UI_FORMS_ROOT_DIR = u"ui_forms"
WORKFLOWS_ROOT_DIR = u"workflows"
HEAT_TEMPLATES_ROOT_DIR = u"heat_templates"
AGENT_TEMPLATES_ROOT_DIR = u"agent_templates"
SCRIPTS_ROOT_DIR = u"scripts"
#root directory should contain manifests files

DIRECTORIES_BY_TYPE = {UI_FORMS: UI_FORMS_ROOT_DIR,
                       WORKFLOWS: WORKFLOWS_ROOT_DIR,
                       HEAT_TEMPLATES: HEAT_TEMPLATES_ROOT_DIR,
                       AGENT_TEMPLATES_ROOT_DIR: AGENT_TEMPLATES_ROOT_DIR,
                       SCRIPTS: SCRIPTS_ROOT_DIR,
                       MANIFESTS: ROOT_DIRECTORY
                       }

