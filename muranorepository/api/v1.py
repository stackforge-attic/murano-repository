# Copyright (c) 2013 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import os
import shutil
import re
import tarfile
import tempfile
import datetime
from flask import Blueprint, send_file
from flask import jsonify, request, abort
from flask import make_response
from werkzeug import secure_filename

from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.archiver import Archiver
from muranorepository.consts import DATA_TYPES, MANIFEST
from muranorepository.consts import CLIENTS_DICT
from muranorepository.consts import ARCHIVE_PKG_NAME
import logging as log
from oslo.config import cfg
v1_api = Blueprint('v1', __name__)

CONF = cfg.CONF
CACHE_DIR = os.path.join(v1_api.root_path, 'cache')

if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)


def _update_cache(data_type):
    client = None
    for client_type, client_data_types in CLIENTS_DICT.iteritems():
        if data_type in client_data_types:
            client = client_type
            break
    if not client:
        abort(404)
    cache_dir = os.path.join(CACHE_DIR, client)
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    manifests = ManifestParser().parse()
    archive_manager = Archiver()
    existing_hash = archive_manager.get_existing_hash(cache_dir)
    if existing_hash:
        archive_manager.remove_existing_hash(cache_dir, existing_hash)
    archive_manager.create(cache_dir, manifests, CLIENTS_DICT[client])


def _get_archive(client, hash_sum):
    types = CLIENTS_DICT.get(client)
    archive_manager = Archiver()
    cache_dir = os.path.join(CACHE_DIR, client)
    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)
    existing_hash = archive_manager.get_existing_hash(cache_dir)

    if existing_hash and hash_sum is None:
        log.debug('Transferring existing archive')
        return os.path.join(cache_dir, existing_hash, ARCHIVE_PKG_NAME)

    if archive_manager.hashes_match(cache_dir, existing_hash, hash_sum):
        return None
    manifests = ManifestParser().parse()
    return archive_manager.create(cache_dir, manifests, types)


def _get_locations(data_type, result_path):
    locations = []
    if data_type == MANIFEST:
        for item in os.listdir(result_path):
            if '-manifest' in item and \
                    os.path.isfile(os.path.join(result_path, item)):
                locations.append(item)
    else:
        for path, subdirs, files in os.walk(result_path):
            for name in files:
                if path != result_path:
                    # need to add directory names for nested files
                    # add keep path relative to result_path
                    base, diff = path.rsplit(result_path, 2)
                    # split base path and remove slash
                    name = os.path.join(diff[1:], name)
                locations.append(name)
    return jsonify({data_type: locations})


def _save_file(request, data_type, path=None):
    if path:
        result_path = _compose_path(data_type, path)
        #subfolder should already exists
        if not os.path.exists(result_path):
            abort(404)
    else:
        result_path = _compose_path(data_type)
    file_to_upload = request.files.get('file')
    if file_to_upload:
        filename = secure_filename(file_to_upload.filename)
        if os.path.exists(os.path.join(result_path, filename)):
            abort(403)
        file_to_upload.save(os.path.join(result_path, filename))
        _update_cache(data_type)
        return jsonify(result='success')
    else:
        abort(400)


def _compose_path(data_type, path=None):
    if path:
        return os.path.join(CONF.manifests, getattr(CONF, data_type), path)
    else:
        return os.path.join(CONF.manifests, getattr(CONF, data_type))


def _check_data_type(data_type):
    if data_type not in DATA_TYPES:
        abort(404)


def _get_manifest_files(manifest):
    return dict((k, v) for k, v in manifest.__dict__.iteritems()
                if k in DATA_TYPES)


def _exclude_common_files(files_for_deletion, manifests):
    all_manifest_files = [_get_manifest_files(manifest)
                          for manifest in manifests]
    for data_type, files in files_for_deletion.items():
        files_for_deletion[data_type] = set(files_for_deletion[data_type])
        for manifest_files in all_manifest_files:
            files_for_deletion[data_type] -= set(manifest_files[data_type])
    return files_for_deletion


def _check_service_name(service_name):
    if not re.match(r'^\w+(\.\w+)*\w+$', service_name):
        abort(404)


def _perform_deletion(files_for_deletion, manifest_for_deletion):
    def backup_data():
        backup_dir = os.path.join(
            os.path.dirname(CONF.manifests),
            'Backup_{0}'.format(datetime.datetime.utcnow())
        )
        log.debug('Creating service data backup to {0}'.format(backup_dir))
        shutil.copytree(CONF.manifests, backup_dir)
        return backup_dir

    def release_backup(backup):
        try:
            shutil.rmtree(backup, ignore_errors=True)
        except Exception as e:
            log.error(
                'Release Backup: '
                'Backup {0} deletion failed {1}'.format(backup, e.message)
            )

    def restore_backup(backup):
        log.debug('Restore service data after unsuccessful deletion')
        shutil.rmtree(CONF.manifests, ignore_errors=True)
        os.rename(backup, CONF.manifests)

    backup_dir = backup_data()
    service_name = manifest_for_deletion.full_service_name
    path_to_manifest = os.path.join(CONF.manifests,
                                    manifest_for_deletion.manifest_file_name)
    try:
        log.debug('Deleting manifest file {0}'.format(path_to_manifest))
        if os.path.exists(path_to_manifest):
            os.remove(path_to_manifest)
    except Exception:
        log.exception('Delete {0}: Deletion {1} file failed'.format(
            service_name, path_to_manifest))
        restore_backup(backup_dir)
        abort(500)

    for data_type, files in files_for_deletion.iteritems():
        data_type_dir = os.path.join(CONF.manifests, getattr(CONF, data_type))
        for file in files:
            path_to_delete = os.path.join(data_type_dir, file)
            try:
                log.debug('Delete {0}: Removing {1} file'.format(
                    service_name, path_to_delete))
                if os.path.exists(path_to_delete):
                    os.remove(path_to_delete)
            except Exception as e:
                log.exception('Deleting operation failed '
                              'due to {0}'.format(e.message))
                restore_backup(backup_dir)
                abort(500)
    release_backup(backup_dir)
    return jsonify(result='success')


@v1_api.route('/client/<path:client_type>')
def get_archive_data(client_type):
    if client_type not in CLIENTS_DICT.keys():
        abort(404)
    path_to_archive = _get_archive(client_type,
                                   request.args.get('hash'))
    if path_to_archive:
        return send_file(path_to_archive, mimetype='application/octet-stream')
    else:
        return make_response('Not modified', 304)


@v1_api.route('/client/services/<service_name>')
def download_service_archive(service_name):
    # In the future service name may contains dots
    _check_service_name(service_name)
    manifests = ManifestParser().parse()
    service_manifest = [manifest for manifest in manifests
                        if manifest.full_service_name == service_name]
    if not service_manifest:
        abort(404)
    assert len(service_manifest) == 1
    archive_manager = Archiver(dst_by_data_type=True)
    #ToDo: Create new class to prevent opening twice the same file for writing
    with tempfile.NamedTemporaryFile() as tempf:
        try:
            file = archive_manager.create_service_archive(manifest, tempf.name)
        except:
            log.error('Unable to create service archive')
            abort(500)
        return send_file(file, mimetype='application/octet-stream')


@v1_api.route('/admin/<data_type>')
def get_data_type_locations(data_type):
    _check_data_type(data_type)
    result_path = _compose_path(data_type)
    return _get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>', methods=['POST'])
def upload_file(data_type):
    _check_data_type(data_type)
    try:
        return _save_file(request, data_type)
    except:
        abort(403)


@v1_api.route('/admin/<data_type>/<path:path>')
def _get_locations_in_nested_path_or_get_file(data_type, path):
    _check_data_type(data_type)
    result_path = _compose_path(data_type, path)
    if os.path.isfile(result_path):
        return send_file(result_path, mimetype='application/octet-stream')
    else:
        return _get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['POST'])
def upload_file_in_nested_path(data_type, path):
    _check_data_type(data_type)

    if data_type == MANIFEST:
        make_response('It is forbidden to upload manifests to subfolders', 403)
    return _save_file(request, data_type, path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT'])
def create_dirs(data_type, path):
    _check_data_type(data_type)
    result_path = _compose_path(data_type, path)
    resp = jsonify(result='success')
    if os.path.exists(result_path):
        return resp
    if data_type == MANIFEST:
        make_response('It is forbidden to create '
                      'directories for manifest files', 403)
    try:
        os.makedirs(result_path)
    except Exception:
        abort(403)
    return resp


@v1_api.route('/admin/<data_type>/<path:path>', methods=['DELETE'])
def delete_directory_or_file(data_type, path):
    _check_data_type(data_type)
    result_path = _compose_path(data_type, path)
    if not os.path.exists(result_path):
        abort(404)
    if os.path.isfile(result_path):
        try:
            os.remove(result_path)
            _update_cache(data_type)
        except Exception:
            abort(404)
    else:
        try:
            # enable to delete only empty directories
            os.rmdir(result_path)
        except Exception:
            make_response('Directory must be empty to be deleted', 403)
    return jsonify(result='success')


@v1_api.route('/admin/services')
def get_services_list():
    # Do we need to check whether manifest is valid here
    manifests = ManifestParser().parse()
    excluded_fields = set(DATA_TYPES) - set(MANIFEST)
    data = []
    for manifest in manifests:
        data.append(dict((k, v) for k, v in manifest.__dict__.iteritems()
                         if not k in excluded_fields))
    return jsonify(services=data)


@v1_api.route('/admin/services/<service_name>')
def get_files_for_service(service_name):
    _check_service_name(service_name)
    manifests = ManifestParser().parse()
    data = []
    for manifest in manifests:
        if manifest.full_service_name == service_name:
            data = _get_manifest_files(manifest)
            break
    if not data:
        abort(404)
    return jsonify(service_files=data)


@v1_api.route('/admin/services/<service_name>', methods=['POST'])
def upload_new_service(service_name):
    _check_service_name(service_name)
    file_to_upload = request.files.get('file')

    if file_to_upload:
        filename = secure_filename(file_to_upload.filename)
    else:
        return make_response('There is no file to upload', 403)
    path_to_archive = os.path.join(CACHE_DIR, filename)
    file_to_upload.save(path_to_archive)
    if not tarfile.is_tarfile(path_to_archive):
        return make_response('Uploading file should be a tar archive', 403)

    archive_manager = Archiver()
    result = archive_manager.extract(path_to_archive)
    if result:
        return jsonify(result='success')
    else:
        #ToDo: Pass error msg there
        return make_response('Uploading file failed.', 400)


@v1_api.route('/admin/services/<service_name>', methods=['DELETE'])
def delete_service(service_name):
    #TODO: Handle situation when error occurred in the middle of deleting.
    # Need to repair already deleted files
    _check_service_name(service_name)
    manifests = ManifestParser().parse()
    manifest_for_deletion = None
    # Search for manifest to delete
    for manifest in manifests:
        if manifest.full_service_name == service_name:
            manifest_for_deletion = manifest
            files_for_deletion = _get_manifest_files(manifest_for_deletion)
            manifests.remove(manifest_for_deletion)
            break
    if not manifest_for_deletion:
        abort(404)

    files_for_deletion = _exclude_common_files(files_for_deletion, manifests)

    return _perform_deletion(files_for_deletion, manifest_for_deletion)


@v1_api.route('/admin/services/<service_name>/toggleEnabled',
              methods=['POST'])
def toggleEnabled(service_name):
    _check_service_name(service_name)
    parser = ManifestParser()
    result = parser.toggle_enabled(service_name)
    if result:
        return jsonify(result='success')
    else:
        return make_response('Unable to toggle '
                             'enable parameter for specified service', 500)
