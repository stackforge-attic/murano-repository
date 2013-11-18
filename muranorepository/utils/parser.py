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
import sys
from oslo.config import cfg
import logging as log
from muranorepository.manifest import Manifest
from muranorepository.consts import DATA_TYPES, MANIFEST
CONF = cfg.CONF


def serialize(data):
    def convert(data):
        """
        Convert unicode to regular strings.

        Needed in python 2.x to handle differences in str/unicode processing.
        In python 3.x this can be done much more easily.
        """
        if isinstance(data, dict):
            return dict([(convert(key), convert(value))
                         for key, value in data.iteritems()])
        elif isinstance(data, list):
            return [convert(element) for element in input]
        elif isinstance(data, unicode):
            return data.encode('utf-8')
        else:
            return data

    #if sys.version >= (3,):
    #    return yaml.dump(data, allow_unicode=True, encoding='utf-8',
    #                     default_flow_style=False)
    return yaml.dump(convert(data), default_flow_style=False)


class ManifestParser(object):
    def __init__(self, manifest_directory=None):
        if not manifest_directory:
            manifest_directory = CONF.manifests
        self.manifest_directory = manifest_directory

    def _validate_manifest(self, file, service_manifest_data):
        for key, value in service_manifest_data.iteritems():
            valid_file_info = True
            if key in DATA_TYPES:
                if key != MANIFEST:
                    root_directory = os.path.join(self.manifest_directory,
                                                  getattr(CONF, key))
                else:
                    root_directory = self.manifest_directory

                if not isinstance(value, list):
                    log.error("{0} section should represent a file"
                              " listing in manifest {1}"
                              "".format(root_directory, file))
                    valid_file_info = False
                    continue
                for filename in value:
                    absolute_path = os.path.join(root_directory,
                                                 filename)

                    if not os.path.exists(absolute_path):
                        valid_file_info = False
                        log.warning(
                            "File {0} specified in manifest {1} "
                            "doesn't exist at {2}".format(filename,
                                                          file,
                                                          absolute_path))
        return valid_file_info

    def parse(self):
        manifests = []
        for file in os.listdir(self.manifest_directory):
            manifest_file = os.path.join(self.manifest_directory, file)
            if os.path.isfile(manifest_file):
                if not file.endswith(".yaml"):
                    log.warning("Extension of {0} file is not yaml. "
                                "Only yaml file supported for "
                                "service manifest files.".format(file))
                    continue

                try:
                    with open(manifest_file) as stream:
                        manifest_data = yaml.load(stream)
                except yaml.YAMLError, exc:
                        log.warn("Failed to load manifest file. {0}. "
                                 "The reason: {1!s}".format(manifest_file,
                                                            exc))
                        continue
                manifest_data['manifest_file_name'] = file
                manifest_is_valid = self._validate_manifest(file,
                                                            manifest_data)
                manifest_data["valid"] = manifest_is_valid

                manifests.append(Manifest(manifest_data))
        return manifests

    def _get_manifest_path(self, service_name):
        # ToDO: Rename manifests to it's id and remove this func
        manifests = self.parse()
        for manifest in manifests:
            if manifest.full_service_name == service_name:
                path_to_manifest = os.path.join(self.manifest_directory,
                                                manifest.manifest_file_name)
                return path_to_manifest
        return None

    def toggle_enabled(self, service_name):
        path_to_manifest = self._get_manifest_path(service_name)
        if not path_to_manifest:
            log.error('There is no manifest '
                      'file for {0} service'.format(service_name))
            return False
        with open(path_to_manifest) as stream:
            service_manifest_data = yaml.load(stream)
        service_manifest_data['enabled'] = \
            not service_manifest_data.get('enabled')
        with open(path_to_manifest, 'w') as manifest_file:
            manifest_file.write(yaml.dump(service_manifest_data,
                                          default_flow_style=False))
        return True

    def update_service(self, service_name, data):
        path_to_manifest = self._get_manifest_path(service_name)
        if not path_to_manifest:
            log.error('There is no manifest '
                      'file for {0} service'.format(service_name))
            return False
        with open(path_to_manifest) as stream:
            service_manifest_data = yaml.load(stream)
        for key, value in data.iteritems():
            service_manifest_data[key] = data[key]

        with open(path_to_manifest, 'w') as manifest_file:
            manifest_file.write(serialize(service_manifest_data))
        return True
