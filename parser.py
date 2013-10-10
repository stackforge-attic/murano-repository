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
import yaml
import logging as log
from manifest import Manifest


class ManifestParser(object):
    def __init__(self,
                 manifest_directory,
                 ui_forms_directory="ui_forms",
                 workflows_directory="workflows",
                 heat_templates_directory="heat_templates",
                 agent_templates_directory="agent_templates",
                 scripts_directory="scripts"
                 ):
        """
        manifest_directory -- absolute path to the directory with manifests
        ui_forms_directory -- absolute or relative path to ui forms definitions
        workflows_directory -- absolute or relative path to workflow
                                                                    definitions
        heat_templates_directory -- absolute or relative path to heat templates
        agent_templates_directory --absolute or relative path to agent
                                                                      templates
        scripts_directory -- absolute or relative path to scripts
        """
        if not os.path.isabs(ui_forms_directory):
            ui_forms_directory = os.path.join(manifest_directory,
                                              ui_forms_directory)
        if not os.path.isabs(workflows_directory):
            workflows_directory = os.path.join(manifest_directory,
                                               workflows_directory)
        if not os.path.isabs(heat_templates_directory):
            heat_templates_directory = os.path.join(manifest_directory,
                                                    heat_templates_directory)
        if not os.path.isabs(agent_templates_directory):
            agent_templates_directory = os.path.join(manifest_directory,
                                                     agent_templates_directory)
        if not os.path.isabs(scripts_directory):
            scripts_directory = os.path.join(manifest_directory, 
                                             scripts_directory)

        self.manifest_directory = manifest_directory
        self.directory_mapping = {"ui_forms": ui_forms_directory,
                                  "workflows": workflows_directory,
                                  "heat_templates":
                                  heat_templates_directory,
                                  "agent_templates": agent_templates_directory,
                                  "scripts": scripts_directory
                                  }

    def parse(self):
        manifests = []
        for file in os.listdir(self.manifest_directory):
            manifest_file = os.path.join(self.manifest_directory, file)
            if os.path.isfile(manifest_file):
                if not file.endswith(".yaml"):
                    log.warning("Extention of {0} file is not yaml. "
                                "Only yaml file supported for "
                                "service manifest files.".format(file))
                    continue

                try:
                    with open(manifest_file) as stream:
                        service_manifest_data = yaml.load(stream)
                except yaml.YAMLError, exc:
                        log.warn("Failed to load manifest file. {0}. "
                                 "The reason: {1!s}".format(manifest_file,
                                                            exc))
                        continue

                for key, value in service_manifest_data.iteritems():
                    valid_file_info = True
                    directory_location = self.directory_mapping.get(key)
                    if directory_location:
                        if not isinstance(value, list):
                            log.error("{0} section should represent a file"
                                      " listing in manifest {1}"
                                      "".format(directory_location, file))
                            valid_file_info = False
                            continue
                        for i, filename in enumerate(value):
                            absolute_path = os.path.join(directory_location,
                                                         filename)

                            service_manifest_data[key][i] = absolute_path

                            if not os.path.exists(absolute_path):
                                valid_file_info = False
                                log.warning(
                                    "File {0} specified in manifest {1} "
                                    "doesn't exist at {2}".format(filename,
                                                                  file,
                                                                  absolute_path
                                                                  ))
                service_manifest_data["valid"] = valid_file_info

                manifests.append(Manifest(service_manifest_data))
        return manifests
