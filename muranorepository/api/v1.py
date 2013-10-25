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
CONF = cfg.CONF

v1_api = Blueprint('v1', __name__)
CACHE_DIR = os.path.join(v1_api.root_path, 'cache')


def _update_hash(data_type):
    client = None
    for client_type, client_data_types in CLIENTS_DICT.iteritems():
        if data_type in client_data_types:
            client = client_type
    if not client:
        abort(404)
    archive = Archiver()
    cache_dir = os.path.join(CACHE_DIR, client)
    if not os.path.exists(cache_dir):
        return None
    existing_hash = archive.get_existing_hash(cache_dir)
    if not existing_hash:
        return None
    else:
        manifests = ManifestParser(CONF.manifests).parse()
        archive_manager = Archiver()
        archive_manager.remove_existing_hash(cache_dir, existing_hash)
        archive_manager.create(cache_dir, manifests, CLIENTS_DICT[client])


def _get_archive(client, hash_sum):
    parser = ManifestParser(CONF.manifests)
    manifests = parser.parse()
    types = CLIENTS_DICT.get(client)
    if not types:
        abort(404)
    archive_manager = Archiver()
    cache_dir = os.path.join(CACHE_DIR, client)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    existing_hash = archive_manager.get_existing_hash(cache_dir)

    if existing_hash and hash_sum is None:
        log.debug('Retiring existing archive')
        return os.path.join(cache_dir, existing_hash, ARCHIVE_PKG_NAME)

    if archive_manager._hashes_match(cache_dir, existing_hash, hash_sum):
        return None

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
        file_to_upload.save(os.path.join(result_path, filename))
        _update_hash(data_type)
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


@v1_api.route('/client/<path:type>')
def get_archive_data(type):
    path = _get_archive(type, request.args.get('hash'))
    if path:
        return send_file(path, mimetype='application/octet-stream')
    else:
        return make_response(('Not modified', 304))


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
    # it's forbidden to upload manifests to subfolders
    if data_type == MANIFEST:
        abort(403)
    return _save_file(request, data_type, path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT'])
def create_dirs(data_type, path):
    _check_data_type(data_type)
    result_path = _compose_path(data_type, path)
    resp = jsonify(result='success')
    if os.path.exists(result_path):
        return resp
    if data_type == MANIFEST:
        abort(403)
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
            _update_hash(data_type)
        except Exception:
            abort(404)
    else:
        try:
            # enable to delete only empty directories
            os.rmdir(result_path)
        except Exception:
            abort(403)
    return jsonify(result='success')
