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
from muranorepository.consts import DATA_TYPES, ARCHIVE_PKG_NAME
CONF = cfg.CONF

CHUNK_SIZE = 1 << 20  # 1MB


class Archiver(object):
    def __init__(self, src_by_data_type=False, dst_by_data_type=False):
        self.dst_directories = {}
        self.src_directories = {}
        if src_by_data_type:
             # Use data_type key as destination folder
            for data_type in DATA_TYPES:
                self.src_directories[data_type] = data_type
        else:
            for data_type in DATA_TYPES:
                self.src_directories[data_type] = getattr(CONF, data_type)

        if dst_by_data_type:
            for data_type in DATA_TYPES:
                self.dst_directories[data_type] = data_type
        else:
            for data_type in DATA_TYPES:
                self.dst_directories[data_type] = getattr(CONF.output,
                                                          data_type)

    def _copy_data(self, file_lists, src, dst, overwrite=True):
        if not os.path.exists(dst):
            os.makedirs(dst)

        for path in file_lists:
            source = os.path.join(src, path)
            destination = os.path.join(dst, path)
            base_dir = os.path.dirname(destination)

            if (base_dir != dst) and (not os.path.exists(base_dir)):
                os.makedirs(os.path.dirname(destination))
            if os.path.exists(destination) and not overwrite:
                raise IOError('File {0} already exists'.format(destination))
            try:
                shutil.copy(source, destination)
            except IOError:
                log.error('Unable to copy file {0}'.format(file))

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
            log.debug('Archive {0} has hash-sum {1}'.format(archive_path,
                                                            hsum))
            return hsum
        else:
            log.info(
                'Archive {0} does not exist, no hash to calculate'.format(
                    archive_path))
            return None

    def _compose_archive(self, arch_name, path, hash=False, cache_dir=None):
        with tarfile.open(arch_name, 'w:gz') as tar:
            for item in os.listdir(path):
                tar.add(os.path.join(path, item), item)
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception as e:
            log.error('Unable to delete temp directory: {0}'.format(e))
        if not hash:
            return arch_name
        else:
            if not cache_dir:
                raise ValueError('cache_dir parameter should not be None. '
                                 'It is needed to create hash directory')
            hash_folder = self._create_hash_folder(arch_name, cache_dir)
            try:
                shutil.move(ARCHIVE_PKG_NAME, os.path.join(hash_folder,
                                                           arch_name))
            except Exception as e:
                log.error('Unable to move created archive {0}'
                          ' to hash folder {1} due to {2}'.format(arch_name,
                                                                  hash_folder,
                                                                  e))
            return os.path.abspath(os.path.join(hash_folder, arch_name))

    def _create_hash_folder(self, archive_name, cache_dir):
        """
        Creates folder with data archive inside that has
        name equals to hash calculated from archive
        Return path to created hash folder
        """
        hash_sum = self._get_hash(archive_name)
        pkg_dir = os.path.join(cache_dir, hash_sum)
        if not os.path.exists(pkg_dir):
            os.mkdir(pkg_dir)
        return pkg_dir

    def get_existing_hash(self, cache_dir):
        existing_caches = os.listdir(cache_dir)
        log.debug('Asserting there is just one archive in cache folder. Clear '
                  'folder {0} in case of Assertion Error'.format(cache_dir))
        assert len(existing_caches) < 2
        if not len(existing_caches):
            return None
        else:
            path = os.path.join(cache_dir,
                                existing_caches[0],
                                ARCHIVE_PKG_NAME)
            if not os.path.exists(path):
                raise RuntimeError(
                    'Archive package is missing at dir {0}'.format(
                        os.path.join(cache_dir)))
            return existing_caches[0]

    def hashes_match(self, cache_dir, existing_hash, hash_to_check):
        if hash_to_check is None or existing_hash is None:
            return False
        if existing_hash == hash_to_check:
            log.debug('Archive package matches hash-sum {0}.'.format(
                hash_to_check))
            return True
        else:
            self.remove_existing_hash(cache_dir, existing_hash)
            return False

    def create(self, cache_dir, manifests, types):
        """
        cache_dir - full path to dir where cache contains
        manifests -- list of Manifest objects
        types -- desired data types to be added to archive
        return: absolute path to created archive
        """
        #TODO: temporary hack for mockfs
        try:
            temp_dir = tempfile.mkdtemp()
        except:
            temp_dir = '/tmp'
        for data_type in types:
            if data_type not in DATA_TYPES:
                raise Exception(' {0} data type specified for archiving is not'
                                ' valid. Supported data types are: '
                                '{1}'.format(data_type, DATA_TYPES))

            for manifest in manifests:
                if not manifest.enabled and not manifest.valid:
                    continue

                if hasattr(manifest, data_type):
                    file_list = getattr(manifest, data_type)
                    scr_directory = os.path.join(
                        CONF.manifests, self.src_directories[data_type])
                    dst_directory = os.path.join(
                        temp_dir, self.dst_directories[data_type])
                    self._copy_data(file_list, scr_directory, dst_directory)
                else:
                    log.info(
                        'Manifest for {0} service has no file definitions for '
                        '{1}'.format(manifest.service_display_name, data_type))
        return self._compose_archive(ARCHIVE_PKG_NAME,
                                     temp_dir,
                                     hash=True,
                                     cache_dir=cache_dir)

    def create_service_archive(self, manifest, file_name):
        temp_dir = tempfile.mkdtemp()
        for data_type in DATA_TYPES:
            if hasattr(manifest, data_type):
                file_list = getattr(manifest, data_type)
                scr_directory = os.path.join(
                    CONF.manifests, self.src_directories[data_type])
                dst_directory = os.path.join(
                    temp_dir, self.dst_directories[data_type])
                self._copy_data(file_list, scr_directory, dst_directory)
            else:
                log.info(
                    '{0} manifest has no file definitions for '
                    '{1}'.format(manifest.service_display_name, data_type))
        return self._compose_archive(file_name, temp_dir)

    def remove_existing_hash(self, cache_dir, hash):
        path = os.path.join(cache_dir, hash)
        log.info('Deleting archive package from {0}.'.format(path))
        shutil.rmtree(path, ignore_errors=True)
