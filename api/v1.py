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
from flask import current_app
from werkzeug import secure_filename

from parser import ManifestParser
from archiver import Archiver

v1_api = Blueprint('v1', __name__)


@v1_api.route('/client/ui')
def get_ui_data():
    parser = ManifestParser(current_app.config["ROOT_DIRECTORY"])
    manifests = parser.parse()
    archive_name = Archiver().create(manifests, "ui_forms")

    return send_file(archive_name)


@v1_api.route('/client/conductor')
def get_conductor_data():
    parser = ManifestParser(current_app.config["ROOT_DIRECTORY"])
    manifests = parser.parse()
    archive_name = Archiver().create(manifests,
                                "heat_templates",
                                "agent_templates",
                                "scripts")

    return send_file(archive_name)


@v1_api.route('/admin/<data_type>', methods=['GET', 'POST'])
def get_data_type_locations(data_type):
    ####### validation ########
    if data_type not in current_app.config['DATA_TYPES']:
        abort(404)
    result_path = os.path.join(current_app.config["DIRECTORIES_BY_TYPE"][
                               data_type])
    ####### end validation ########
    if request.method == 'GET':
        locations = []

        for path, subdirs, files in os.walk(result_path):
            for name in files:
                locations.append(os.path.join(path, name))
        result = {data_type: locations}
        return jsonify(result)

    if request.method == 'POST':
        file_to_upload = request.files.get('file')
        if file_to_upload:
            filename = secure_filename(file_to_upload.filename)
            file_to_upload.save(os.path.join(result_path, filename))
            return jsonify(result="success")
        else:
            abort(503)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['GET', 'POST'])
def get_data_type_locations_by_path_or_get_file(data_type, path):
    ####### validation ########
    if data_type not in current_app.config['DATA_TYPES']:
        abort(404)
    result_path = os.path.join(current_app.config["DIRECTORIES_BY_TYPE"][
                               data_type],
                               path)
    if not os.path.exists(result_path):
        abort(404)
    ####### end validation ########
    if request.method == 'GET':
        locations = []
        #return file content or directory content
        if os.path.isfile(result_path):
            return send_file(result_path)
        else:
            for file in os.listdir(result_path):
                locations.append(os.path.join(path, file))
            result = {data_type: locations}
            return jsonify(result)

    if request.method == 'POST':
        file_to_upload = request.files.get('file')
        if file_to_upload:
            filename = secure_filename(file_to_upload.filename)
            file_to_upload.save(os.path.join(result_path, filename))
            return jsonify(result="success")
        else:
            abort(403)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT', 'DELETE'])
def create_dirs(data_type, path):
    if data_type not in current_app.config['DATA_TYPES']:
        abort(404)
    result_path = os.path.join(current_app.config["DIRECTORIES_BY_TYPE"][
                               data_type],
                               path)
    if request.method == 'PUT':
        resp = make_response()
        if os.path.exists(result_path):
            return resp
        if data_type == current_app.config['MANIFESTS']:
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
