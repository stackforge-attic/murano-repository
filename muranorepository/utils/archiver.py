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
import glob
import tarfile
import tempfile
import shutil
import hashlib
import yaml
import logging as log
from oslo.config import cfg
from .parser import serialize
from muranorepository.consts import DATA_TYPES, ARCHIVE_PKG_NAME
from muranorepository.consts import UI, UI_FIELDS_IN_MANIFEST
from muranorepository.utils import utils
from muranorepository.openstack.common.gettextutils import _  # noqa
CONF = cfg.CONF

CHUNK_SIZE = 1 << 20  # 1MB


def clean_dir(dir_path):
    """Removes all files and dirs inside a directory."""
    for entry_name in os.listdir(dir_path):
        path = os.path.join(dir_path, entry_name)
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)


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
                raise IOError(_('File {0} already exists'.format(destination)))
            try:
                shutil.copy(source, destination)
            except IOError:
                log.error(_('Unable to copy file {0}'.format(file)))

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
            log.debug(_('Archive {0} has hash-sum {1}'.format(archive_path,
                                                              hsum)))
            return hsum
        else:
            log.info(_("Archive '{0}' doesn't exist,"
                       " no hash to calculate".format(archive_path)))
            return None

    def _compose_archive(self, arch_name, path, hash=False, data_dir=None):
        tar = tarfile.open(arch_name, 'w:gz')
        try:
            for item in os.listdir(path):
                tar.add(os.path.join(path, item), item)
        finally:
            tar.close()
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            log.exception(_('Unable to delete temp directory'))
        if not hash:
            return arch_name
        else:
            if not data_dir:
                raise ValueError(_('data_dir parameter should not be None. '
                                   'It is needed to create hash directory'))
            clean_dir(data_dir)
            hash_folder = self._create_hash_folder(arch_name, data_dir)
            try:
                shutil.move(arch_name, os.path.join(hash_folder,
                                                    ARCHIVE_PKG_NAME))
            except Exception:
                log.exception(_('Unable to move created archive {0} to hash '
                                'folder {1}'.format(arch_name, hash_folder)))

        return os.path.abspath(os.path.join(hash_folder, ARCHIVE_PKG_NAME))

    def _create_hash_folder(self, archive_name, data_dir):
        """
        Creates folder with data archive inside that has
        name equals to hash calculated from archive
        Return path to created hash folder
        """
        hash_sum = self._get_hash(archive_name)
        pkg_dir = os.path.join(data_dir, hash_sum)
        if not os.path.exists(pkg_dir):
            os.mkdir(pkg_dir)
        return pkg_dir

    def _compose_ui_forms(self, manifest, ui_definitions, src, dst):
        """
        Extends ui_forms before sending to client.
        Some parameters defined UI_FIELDS_IN_MANIFEST that are required
        for ui forms are specified in manifest.
        """
        new_dst = os.path.join(os.path.dirname(dst),
                               manifest.full_service_name)
        if not os.path.exists(new_dst):
            os.makedirs(new_dst)
        for file in ui_definitions:
            with open(os.path.join(src, file)) as ui_form:
                content = yaml.load(ui_form)
            for ui_name, manifest_name in UI_FIELDS_IN_MANIFEST.iteritems():
                content[ui_name] = getattr(manifest, manifest_name)
            with open(os.path.join(new_dst, file), 'w') as ui_form:
                ui_form.write(serialize(content))

    def get_existing_hash(self, data_dir):
        existing_caches = os.listdir(data_dir)
        if not len(existing_caches):
            return None

        path = os.path.join(data_dir,
                            existing_caches[0],
                            ARCHIVE_PKG_NAME)
        if not os.path.exists(path):
            raise IOError(_('Archive package is missing '
                            'at dir {0}'.format(data_dir)))
        return existing_caches[0]

    def hashes_match(self, data_dir, existing_hash, hash_to_check):
        if hash_to_check is None or existing_hash is None:
            return False
        if existing_hash == hash_to_check:
            log.debug(_('Archive package matches hash-sum {0}.'.format(
                hash_to_check)))
            return True
        else:
            self.remove_existing_hash(data_dir, existing_hash)
            return False

    def create(self, data_dir, manifests, types):
        """
        data_dir - full path to dir where cache contains
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
                raise ValueError(_('{0} data type specified for archiving is '
                                   'not valid. Supported data types are: '
                                   '{1}'.format(data_type, DATA_TYPES)))

            for manifest in manifests:
                if not manifest.enabled or not manifest.valid:
                    continue

                if hasattr(manifest, data_type):
                    file_list = getattr(manifest, data_type)
                    src_directory = os.path.join(
                        utils.get_tenant_folder(),
                        self.src_directories[data_type])
                    dst_directory = os.path.join(
                        temp_dir, self.dst_directories[data_type])
                    if data_type == UI:
                        self._compose_ui_forms(manifest, file_list,
                                               src_directory, dst_directory)
                    else:
                        self._copy_data(file_list,
                                        src_directory,
                                        dst_directory)
                else:
                    log.info(
                        _('Manifest for {0} service has no file definitions '
                          'for {1}'.format(manifest.service_display_name,
                                           data_type)))

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            return self._compose_archive(temp_file.name,
                                         temp_dir,
                                         hash=True,
                                         data_dir=data_dir)

    def create_service_archive(self, manifest, file_name):
        temp_dir = tempfile.mkdtemp()
        for data_type in DATA_TYPES:
            if hasattr(manifest, data_type):
                file_list = getattr(manifest, data_type)
                src_directory = os.path.join(
                    utils.get_tenant_folder(), self.src_directories[data_type])
                dst_directory = os.path.join(
                    temp_dir, self.dst_directories[data_type])
                self._copy_data(file_list, src_directory, dst_directory)
            else:
                log.info(
                    _('{0} manifest has no file definitions for '
                      '{1}'.format(manifest.service_display_name, data_type)))
        #Add manifest file into archive
        manifest_filename = manifest.full_service_name + '-manifest.yaml'
        self._copy_data([manifest_filename],
                        utils.get_tenant_folder(),
                        temp_dir)
        return self._compose_archive(file_name, temp_dir)

    def remove_existing_hash(self, data_dir, hash):
        path = os.path.join(data_dir, hash)
        log.info('Deleting archive package from {0}.'.format(path))
        shutil.rmtree(path, ignore_errors=True)

    def extract(self, path_to_archive):
        """
        path_to_archive - path to archive to extract from
        ---
        return value - True if succeeded , False otherwise
        """
        try:
            root_folder = utils.get_tenant_folder()
            path_to_extract = tempfile.mkdtemp()
            archive = tarfile.open(path_to_archive)
            try:
                archive.extractall(path_to_extract)
            finally:
                archive.close()
            # assert manifest file
            manifests = glob.glob(os.path.join(path_to_extract,
                                               '*-manifest.yaml'))
            if not manifests:
                log.error(_('There is no manifest file in archive'))
                return False
            if len(manifests) != 1:
                log.error(_('There are more then one manifest '
                            'file in archive'))
                return False

            shutil.copy(manifests[0], root_folder)
            #Todo: Check manifest is valid
            for item in os.listdir(path_to_extract):
                item_path = os.path.join(path_to_extract, item)
                if os.path.isdir(item_path):
                    if item in DATA_TYPES:
                        file_list = []
                        for path, subdirs, files in os.walk(item_path):
                            # ToDo: Extract to a separate
                            # function and use in v1.py also
                            nested = False
                            if path != item_path:
                                base, subfolder = path.rsplit(item_path, 2)
                                nested = True
                            for name in files:
                                if nested:
                                    name = os.path.join(subfolder[1:], name)
                                file_list.append(name)
                        self._copy_data(file_list,
                                        item_path,
                                        os.path.join(
                                            root_folder,
                                            self.src_directories[item]),
                                        overwrite=False)
                    else:
                        log.warning(
                            _('Uploading archive contents folder {0} that does'
                              ' not correspond to supported data types: {1}. '
                              'It will be ignored'.format(item, DATA_TYPES)))
            return True
        except Exception:
            log.exception(_('Unable to extract archive'))
            return False
        finally:
            os.remove(path_to_archive)
            shutil.rmtree(path_to_extract, ignore_errors=True)
