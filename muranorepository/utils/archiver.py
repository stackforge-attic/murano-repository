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
from oslo.config import cfg
from muranorepository.consts import DATA_TYPES
CONF = cfg.CONF


class Archiver(object):
    def _copy_data(self, file_lists, src, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)

        for path in file_lists:
            source = os.path.join(src, path)
            destination = os.path.join(dst, path)
            base_dir = os.path.dirname(destination)

            if (base_dir != dst) \
               and (not os.path.exists(base_dir)):
                os.makedirs(os.path.dirname(destination))
            try:
                shutil.copyfile(source, destination)
            except IOError:
                log.error("Unable to copy file "
                          "{0}".format(file))

    def _compose_archive(self, path):
        target_archive = "service_metadata.tar"
        with tarfile.open(target_archive, "w") as tar:
            for item in os.listdir(path):
                tar.add(os.path.join(path, item), item)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            log.error("Unable to delete temp directory: {0}".format(e))
        return os.path.abspath(target_archive)

    def create(self, manifests, *types):
        """
        manifests -- list of Manifest objects
        *types - desired data types to be added to archive

        return: absolute path to created archive
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
                    file_list = getattr(manifest, data_type)
                    dst_directory = os.path.join(temp_dir,
                                                 getattr(CONF.output,
                                                         data_type))
                    scr_directory = os.path.join(CONF.manifests,
                                                 getattr(CONF, data_type))
                    self._copy_data(file_list, scr_directory, dst_directory)
                else:
                    log.info(
                        "Manifest for {0} service has no file definitions for "
                        "{1}".format(manifest.service_display_name, data_type))

        return self._compose_archive(temp_dir)




