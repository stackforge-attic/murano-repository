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
from flask import Blueprint, make_response, send_file
from flask import jsonify, request, abort
from werkzeug import secure_filename

from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.archiver import Archiver
from muranorepository.consts import DATA_TYPES, MANIFEST
from oslo.config import cfg
CONF = cfg.CONF

v1_api = Blueprint('v1', __name__)


@v1_api.route('/client/ui')
def get_ui_data():
    parser = ManifestParser(CONF.manifests)
    manifests = parser.parse()
    archive_name = Archiver().create(manifests, "ui")

    return send_file(archive_name)


@v1_api.route('/client/conductor')
def get_conductor_data():
    parser = ManifestParser(CONF.manifests)
    manifests = parser.parse()
    archive_name = Archiver().create(manifests,
                                     "heat",
                                     "agent",
                                     "scripts")
    return send_file(archive_name)


@v1_api.route('/admin/<data_type>', methods=['GET', 'POST'])
def get_data_type_locations(data_type):
    ####### validation ########
    if data_type not in DATA_TYPES:
        abort(404)
    result_path = os.path.join(CONF.manifests, getattr(CONF, data_type))
    ####### end validation ########
    if request.method == 'GET':
        locations = []
        if data_type == MANIFEST:
            for item in os.listdir(result_path):
                if '-manifest' in item:
                    locations.append(item)
        else:
            for path, subdirs, files in os.walk(result_path):
                for name in files:
                    locations.append(name)
        result = {data_type: locations}
        return jsonify(result)

    if request.method == 'POST':
        try:
            file_to_upload = request.files.get('files')
            if file_to_upload:
                filename = secure_filename(file_to_upload.filename)
                file_to_upload.save(os.path.join(result_path, filename))
                return jsonify(result="success")
        except:
            abort(403)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['GET', 'POST'])
def get_data_type_locations_by_path_or_get_file(data_type, path):
    if data_type not in DATA_TYPES:
        abort(404)
    result_path = os.path.join(os.path.join(CONF.manifests,
                                            getattr(CONF, data_type),
                                            path))
    if not os.path.exists(result_path):
        abort(404)

    if request.method == 'GET':
        locations = []
        if os.path.isfile(result_path):
            return send_file(result_path)
        else:
            for file in os.listdir(result_path):
                locations.append(file)
            result = {data_type: locations}
            return jsonify(result)

    if request.method == 'POST':
        file_to_upload = request.files.get('files')
        if file_to_upload:
            filename = secure_filename(file_to_upload.filename)
            file_to_upload.save(os.path.join(result_path, filename))
            return jsonify(result="success")
        else:
            abort(403)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT', 'DELETE'])
def create_dirs(data_type, path):
    if data_type not in DATA_TYPES:
        abort(404)
    result_path = os.path.join(CONF.manifests, getattr(CONF, data_type), path)
    if request.method == 'PUT':
        resp = make_response()
        if os.path.exists(result_path):
            return resp
        if data_type == MANIFEST:
            abort(403)
        try:
            os.makedirs(result_path)
        except Exception as e:
            abort(403)
        return resp

    if request.method == 'DELETE':
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
        resp = make_response()
        return resp
