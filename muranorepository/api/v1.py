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

from flask import Blueprint, make_response, send_file
from flask import jsonify, request, abort
from werkzeug import secure_filename

from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.archiver import Archiver
from muranorepository.consts import DATA_TYPES, MANIFEST
from oslo.config import cfg
CONF = cfg.CONF

v1_api = Blueprint('v1', __name__)


def get_archive(client):
    parser = ManifestParser(CONF.manifests)
    manifests = parser.parse()
    if client == 'conductor':
        return Archiver().create(manifests,
                                 'heat',
                                 'agent',
                                 'scripts')
    else:
        return Archiver().create(manifests, client)


def get_locations(data_type, result_path):
    locations = []
    if data_type == MANIFEST:
        for item in os.listdir(result_path):
            if '-manifest' in item and os.path.isfile(item):
                locations.append(item)
    else:
        for path, subdirs, files in os.walk(result_path):
            for name in files:
                if path != result_path:
                    base, diff = path.rsplit(result_path, 2)
                    # split base path and remove slash
                    locations.append(os.path.join(diff[1:], name))
                else:
                    locations.append(name)
    return jsonify({data_type: locations})


def save_file(request, result_path):
    file_to_upload = request.files.get('files')
    if file_to_upload:
        filename = secure_filename(file_to_upload.filename)
        file_to_upload.save(os.path.join(result_path, filename))
        return jsonify(result='success')
    else:
        abort(400)


def compose_path(data_type, path=None):
    if path:
        return os.path.join(CONF.manifests, getattr(CONF, data_type), path)
    else:
        return os.path.join(CONF.manifests, getattr(CONF, data_type))


def check_data_type(data_type):
    if data_type not in DATA_TYPES:
        abort(404)


@v1_api.route('/client/ui')
def get_ui_data():
    return send_file(get_archive('ui'))


@v1_api.route('/client/conductor')
def get_conductor_data():
    return send_file(get_archive('conductor'))


@v1_api.route('/admin/<data_type>')
def get_data_type_locations(data_type):
    check_data_type(data_type)
    result_path = compose_path(data_type)
    return get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>', methods=['POST'])
def upload_file(data_type):
    check_data_type(data_type)
    result_path = compose_path(data_type)
    try:
        return save_file(request, result_path)
    except:
        abort(403)


@v1_api.route('/admin/<data_type>/<path:path>')
def get_locations_in_nested_path_or_get_file(data_type, path):
    check_data_type(data_type)
    result_path = compose_path(data_type, path)
    if os.path.isfile(result_path):
        return send_file(result_path)
    else:
        return get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['POST'])
def upload_file_in_nested_path(data_type, path):
    check_data_type(data_type)
    result_path = compose_path(data_type, path)
    return save_file(request, result_path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT'])
def create_dirs(data_type, path):
    check_data_type(data_type)
    result_path = compose_path(data_type, path)
    resp = jsonify(result='success')
    if os.path.exists(result_path):
        return resp
    if data_type == MANIFEST:
        abort(403)
    try:
        os.makedirs(result_path)
    except Exception as e:
        abort(403)
    return resp

@v1_api.route('/admin/<data_type>/<path:path>', methods=['DELETE'])
def delete_dirictory_or_file(data_type, path):
    check_data_type(data_type)
    result_path = compose_path(data_type, path)
    if not os.path.exists(result_path):
        abort(404)
    if os.path.isfile(result_path):
        try:
            os.remove(result_path)
        except Exception as e:
            abort(404)
    else:
        try:
            os.rmdir(result_path)
        except Exception as e:
            abort(403)
    return jsonify(result='success')
