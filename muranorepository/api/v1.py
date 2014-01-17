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
import tarfile
import tempfile
import json
from flask import Blueprint, send_file
from flask import jsonify, request, abort
from flask import make_response
from muranorepository.api import utils as api_utils
from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.archiver import Archiver
from muranorepository.consts import DATA_TYPES, MANIFEST
from muranorepository.consts import CLIENTS_DICT
from muranorepository.openstack.common.gettextutils import _  # noqa
from oslo.config import cfg
import logging as log
v1_api = Blueprint('v1', __name__)
CONF = cfg.CONF


@v1_api.route('/client/<path:client_type>')
def get_archive_data(client_type):
    if client_type not in CLIENTS_DICT.keys():
        abort(404)
    path_to_archive = api_utils.get_archive(client_type,
                                            request.args.get('hash'))
    if path_to_archive:
        return send_file(path_to_archive, mimetype='application/octet-stream')
    else:
        return make_response('Not modified', 304)


@v1_api.route('/client/services/<service_name>')
def download_service_archive(service_name):
    # In the future service name may contains dots
    api_utils.check_service_name(service_name)
    manifests = ManifestParser().parse()
    services_for_download = [manifest for manifest in manifests
                             if manifest.full_service_name == service_name]
    if not services_for_download:
        abort(404)
    if len(services_for_download) != 1:
        return make_response(_('Fully qualified service name is not unique'),
                             500)
    archive_manager = Archiver(dst_by_data_type=True)
    #ToDo: Create new class to prevent opening twice the same file for writing
    with tempfile.NamedTemporaryFile() as tempf:
        try:
            file = archive_manager.create_service_archive(
                services_for_download[0], tempf.name)
        except:
            log.exception(_('Unable to create service archive'))
            abort(500)
        return send_file(file, mimetype='application/octet-stream')


@v1_api.route('/admin/<data_type>')
def get_data_type_locations(data_type):
    api_utils.check_data_type(data_type)
    result_path = api_utils.compose_path(data_type)
    return api_utils.get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>', methods=['POST'])
def upload_file(data_type):
    api_utils.check_data_type(data_type)
    filename = request.args.get('filename')
    return api_utils.save_file(request, data_type,
                               path=None, filename=filename)


@v1_api.route('/admin/<data_type>/<path:path>')
def get_locations_in_nested_path_or_get_file(data_type, path):
    api_utils.check_data_type(data_type)
    result_path = api_utils.compose_path(data_type, path)
    if os.path.isfile(result_path):
        return send_file(result_path, mimetype='application/octet-stream')
    else:
        return api_utils.get_locations(data_type, result_path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['POST'])
def upload_file_in_nested_path(data_type, path):
    api_utils.check_data_type(data_type)

    if data_type == MANIFEST:
        return make_response(_('It is forbidden to upload '
                               'manifests to subfolders'), 403)
    return api_utils.save_file(request, data_type, path)


@v1_api.route('/admin/<data_type>/<path:path>', methods=['PUT'])
def create_dirs(data_type, path):
    api_utils.check_data_type(data_type)
    result_path = api_utils.compose_path(data_type, path)
    resp = jsonify(result='success')
    if os.path.exists(result_path):
        return resp
    if data_type == MANIFEST:
        return make_response(_('It is forbidden to create '
                               'directories for manifest files'), 403)
    try:
        os.makedirs(result_path)
    except OSError:
        log.exception(_("Error during creating folders"))
        abort(403)
    return resp


@v1_api.route('/admin/<data_type>/<path:path>', methods=['DELETE'])
def delete_directory_or_file(data_type, path):
    api_utils.check_data_type(data_type)
    result_path = api_utils.compose_path(data_type, path)
    if not os.path.exists(result_path):
        log.info(_("Attempt to delete '{0}' failed:"
                   "specified path doesn't exist"))
        abort(404)
    if os.path.isfile(result_path):
        try:
            os.remove(result_path)
        except OSError:
            log.exception(_("Something went wrong during deletion"
                            " '{0}' file".format(result_path)))
            abort(500)
    else:
        try:
            # enable to delete only empty directories
            os.rmdir(result_path)
        except OSError:
            return make_response(_('Directory must be empty to be deleted'),
                                 403)
    api_utils.reset_cache()
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
    api_utils.check_service_name(service_name)
    manifest = ManifestParser().parse_manifest(service_name)
    if not manifest:
        abort(404)
    data = api_utils.get_manifest_files(manifest)
    return jsonify(data)


@v1_api.route('/admin/services/<service_name>/info')
def get_service_info(service_name):
    api_utils.check_service_name(service_name)
    manifest = ManifestParser().parse_manifest(service_name)
    if not manifest:
        abort(404)
    data = api_utils.get_manifest_info(manifest)
    return jsonify(data)


@v1_api.route('/admin/services', methods=['POST'])
def upload_new_service():
    path_to_archive = api_utils.save_archive(request)
    if not tarfile.is_tarfile(path_to_archive):
        return make_response(_('Uploading file should be a tar.gz archive'),
                             400)
    archive_manager = Archiver()
    result = archive_manager.extract(path_to_archive)
    if result:
        api_utils.reset_cache()
        return jsonify(result='success')
    else:
        return make_response(_('Uploading file failed.'), 400)


@v1_api.route('/admin/services/<service_name>', methods=['DELETE'])
def delete_service(service_name):
    api_utils.check_service_name(service_name)
    manifests = ManifestParser().parse()
    manifest_for_deletion = None
    # Search for manifest to delete
    for manifest in manifests:
        if manifest.full_service_name == service_name:
            manifest_for_deletion = manifest
            files_for_deletion = api_utils.get_manifest_files(
                manifest_for_deletion)
            manifests.remove(manifest_for_deletion)
            break
    if not manifest_for_deletion:
        abort(404)

    files_for_deletion = api_utils.exclude_common_files(files_for_deletion,
                                                        manifests)

    return api_utils.perform_deletion(files_for_deletion,
                                      manifest_for_deletion)


@v1_api.route('/admin/services/<service_name>/toggle_enabled',
              methods=['POST'])
def toggleEnabled(service_name):
    api_utils.check_service_name(service_name)
    parser = ManifestParser()
    result = parser.toggle_enabled(service_name)
    if result:
        api_utils.reset_cache()
        return jsonify(result='success')
    else:
        return make_response(_('Unable to toggle '
                               'enable parameter for specified service'), 500)


@v1_api.route('/admin/reset_caches', methods=['POST'])
def reset_caches():
    api_utils.reset_cache()
    return jsonify(result='success')


@v1_api.route('/admin/services/<service_name>', methods=['PUT'])
def create_or_update_service(service_name):
    if not request.data:
        return make_response(_('JSON data expected', 400))
    try:
        service_data = json.loads(request.data)
    except:
        return make_response(_('Unable to load json data. '
                               'Validate json object', 400))

    service_id = service_data.get('full_service_name', service_name)
    #TODO: Pass service_name instead of service_id
    if not service_id or service_id != service_name:
        return make_response(
            _("Body attribute 'full_service_name' value is {0} which doesn't "
              "correspond to 'service_name' part of URL "
              "(equals to {1})".format(service_id, service_name)), 400)
    resp = api_utils.create_or_update_service(service_name, service_data)
    api_utils.reset_cache()
    return resp
