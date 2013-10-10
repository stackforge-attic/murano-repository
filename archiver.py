# Copyright (c) 2013 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os
import tarfile
import tempfile
import shutil
import logging as log

from consts import DATA_TYPES


class Archiver(object):
    def __init__(self,
                 ui_forms_target="service_forms",
                 workflows_target="workflows",
                 heat_templates_target="templates/cf",
                 agent_templates_target="templates/agent",
                 scripts_target="templates/agent/scripts"):
        """
        ui_forms_target -- relative path for a ui_forms location in
                                                            resulted archive
        workflows_target -- relative path for a desired workflow location in
                                                            resulted archive
        heat_templates_target -- relative path for a desired heat templates
                                                location in resulted archive
        agent_templates_target -- relative path for a heat templates location
        scripts_target -- relative path for a agent script location
        """
        self.archive_structure = {"ui_forms": ui_forms_target,
                                     "workflows": workflows_target,
                                     "heat_templates": heat_templates_target,
                                     "agent_templates": agent_templates_target,
                                     "scripts": scripts_target
                                  }

    def create(self, manifests, *types):
        """
        manifests -- list of Manifest objects
        *types - desired data types to be added to archive
        """
        temp_dir = tempfile.mkdtemp()
        for data_type in types:
            if data_type not in DATA_TYPES:
                raise Exception("Please, specify one of the supported data "
                                "types: {0}".format(DATA_TYPES))

            for manifest in manifests:
                if not manifest.enabled and not manifest.valid:
                    continue
                if hasattr(manifest, data_type):
                    dst_directory = os.path.join(temp_dir,
                                                 self.archive_structure[
                                                     data_type])
                    if not os.path.exists(dst_directory):
                        os.makedirs(dst_directory)

                    for file_path in getattr(manifest, data_type):
                        basedir, filename = os.path.split(file_path)
                        destination = os.path.join(dst_directory,
                                                   filename)
                        try:
                            shutil.copyfile(file_path, destination)
                        except IOError:
                            log.error("Unable to copy file "
                                      "{0}".format(file))
                else:
                    log.info(
                        "Manifest for {0} service has no file definitions for "
                        "{1}").format(manifest.service_display_name, data_type)

        target_archeve = "service_metadata.tar"
        with tarfile.open(target_archeve, "w") as tar:
            for item in os.listdir(temp_dir):
                tar.add(os.path.join(temp_dir, item), item)
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception as e:
            log.error("Unable to delete temp directory: {0}".format(e))
        return target_archeve




