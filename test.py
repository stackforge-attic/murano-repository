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

from flask import Flask, make_response, send_from_directory, send_file, \
                jsonify, request
import os
from parser import ManifestParser
from archiver import Archiver

app = Flask(__name__)
app.config.from_pyfile('consts.py')

@app.route('/client/ui')
def get_ui_data():
    parser = ManifestParser(app.config["ROOT_DIRECTORY"])
    manifests = parser.parse()
    archive_name = Archiver().create(manifests, "ui_forms")

    # resp = make_response()
    # resp.mimetype = 'application/z-gzip'
    # resp.headers["Content-Disposition"] = "attachment; " \
    #                                       "filename={0}".format(location)
    return send_from_directory(os.path.dirname(__file__), archive_name)


@app.route('/client/conductor')
def get_conductor_data():
    parser = ManifestParser(app.config["ROOT_DIRECTORY"])
    manifests = parser.parse()
    archive_name = Archiver().create(manifests,
                                "heat_templates",
                                "agent_templates",
                                "scripts")

    return send_from_directory(os.path.dirname(__file__), archive_name)


@app.route('/admin/<data_type>', methods=['GET', 'POST'])
def get_data_type_locations(data_type):
    if request.method == 'GET':
        parser = ManifestParser(app.config["ROOT_DIRECTORY"])
        manifests = parser.parse()
        locations = []
        if data_type not in app.config['DATA_TYPES']:
            #return 404
            pass

        for manifest in manifests:
            if hasattr(manifest, data_type):
                for file_path in getattr(manifest, data_type):
                    locations.append(file_path)
    if request.method == 'POST':

    return jsonify(data_type=locations)


@app.route('/admin/<data_type>/<path>', methods=['GET', 'POST'])
def get_data_type_locations_by_path_or_get_file(data_type, path):
    locations = []
    result_path = os.path.join(app.config["ROOT_DIRECTORY"],
                               app.config["DIRECTORIES_BY_TYPE"][data_type],
                               path)
    if not os.path.exists(result_path):
        #throw 404
        pass
    #return file content or directory content
    if os.path.isfile(result_path):
        return send_file(result_path)
    else:
        for file in os.listdir(result_path):
            locations.append(os.path.join(path, file))
        return jsonify(data_type=locations)



if __name__ == '__main__':
    app.run(debug=True)