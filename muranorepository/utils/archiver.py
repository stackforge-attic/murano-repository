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
import hashlib
import logging as log
from oslo.config import cfg
from muranorepository.consts import DATA_TYPES
CONF = cfg.CONF

ARCHIVE_PKG_NAME = 'data.tar.gz'
CHUNK_SIZE = 1 << 20  # 1MB


class Archiver(object):
    def _copy_data(self, file_lists, src, dst):
        if not os.path.exists(dst):
            os.makedirs(dst)

        for path in file_lists:
            source = os.path.join(src, path)
            destination = os.path.join(dst, path)
            base_dir = os.path.dirname(destination)

            if (base_dir != dst) and (not os.path.exists(base_dir)):
                os.makedirs(os.path.dirname(destination))
            try:
                shutil.copyfile(source, destination)
            except IOError:
                log.error("Unable to copy file "
                          "{0}".format(file))

    def _get_hash(self, archive_path):
        """Calculate SHA1-hash of archive file.

        SHA-1 take a bit more time than MD5
        (see http://tinyurl.com/kpj5jy7), but is more secure.
        """
        # Copy-pasted from muranodashboard/panel/services/metadata.py
        if os.path.exists(archive_path):
            sha1 = hashlib.sha1()
            with open(archive_path) as f:
                buf = f.read(CHUNK_SIZE)
                while buf:
                    sha1.update(buf)
                    buf = f.read(CHUNK_SIZE)
            hsum = sha1.hexdigest()
            log.debug("Archive '{0}' has hash-sum {1}".format(
                archive_path, hsum))
            return hsum
        else:
            log.info(
                "Archive '{0}' doesn't exist, no hash to calculate".format(
                    archive_path))
            return None

    def _compose_archive(self, path, cache_dir):
        with tarfile.open(ARCHIVE_PKG_NAME, "w:gz") as tar:
            for item in os.listdir(path):
                tar.add(os.path.join(path, item), item)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            log.error("Unable to delete temp directory: {0}".format(e))
        hash_sum = self._get_hash(ARCHIVE_PKG_NAME)
        pkg_dir = os.path.join(cache_dir, hash_sum)
        os.mkdir(pkg_dir)
        shutil.move(ARCHIVE_PKG_NAME, os.path.join(pkg_dir, ARCHIVE_PKG_NAME))
        return os.path.abspath(os.path.join(pkg_dir, ARCHIVE_PKG_NAME))

    def _is_data_cached(self, cache_dir, hash_sum):
        if not hash_sum:
            return False
        existing_caches = os.listdir(cache_dir)
        if len(existing_caches) == 1:
            if existing_caches[0] == hash_sum:
                path = os.path.join(cache_dir, hash_sum, ARCHIVE_PKG_NAME)
                if not os.path.exists(path):
                    raise RuntimeError(
                        'Archive package is missing at dir {0}'.format(
                            os.path.join(cache_dir, hash_sum)))
                log.debug('Archive package already exists at {0} and it ' +
                          'matches hash-sum {1}.'.format(path, hash_sum))
                return True
            else:
                path = os.path.join(cache_dir, hash_sum)
                log.info('Archive package already exists at {0}, but it '
                         "doesn't match requested hash-sum {1}. "
                         'Deleting it.'.format(path))
                shutil.rmtree(path)
                return False
        elif len(existing_caches) == 0:
            return False
        else:
            raise RuntimeError('Too many cached archives at {0}'.format(
                cache_dir))

    def create(self, client_type, cache_root, manifests, hash_sum, types):
        """
        manifests -- list of Manifest objects
        *types - desired data types to be added to archive

        return: absolute path to created archive
        """
        #TODO: temporary hack for mockfs
        try:
            temp_dir = tempfile.mkdtemp()
        except:
            temp_dir = '/tmp'

        cache_dir = os.path.join(cache_root, client_type)
        if not os.path.exists(cache_dir):
            os.mkdir(cache_dir)

        if self._is_data_cached(cache_dir, hash_sum):
            return None

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

        return self._compose_archive(temp_dir, cache_dir)
