import os
import shutil
import re
import tempfile
import datetime
import yaml
from flask import jsonify, abort
from flask import make_response
from werkzeug import secure_filename

from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.archiver import Archiver
from muranorepository.consts import DATA_TYPES, MANIFEST
from muranorepository.consts import CLIENTS_DICT
from muranorepository.consts import ARCHIVE_PKG_NAME
from muranorepository.config import cfg
import logging as log
CONF = cfg.CONF


def reset_cache():
    try:
        shutil.rmtree(CONF.cache_dir, ignore_errors=True)
        os.mkdir(CONF.cache_dir)
    except:
        return make_response('Unable to reset cache', 500)


def get_archive(client, hash_sum):
    types = CLIENTS_DICT.get(client)
    archive_manager = Archiver()
    cache_dir = os.path.join(CONF.cache_dir, client)
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


def get_locations(data_type, result_path):
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


def save_file(request, data_type, path=None, filename=None):
    if path:
        path_to_folder = compose_path(data_type, path)
        #subfolder should already exists
        if not os.path.exists(path_to_folder):
            abort(404)
    else:
        path_to_folder = compose_path(data_type)

    if request.content_type == 'application/octet-stream':
        data = request.environ['wsgi.input'].read()
        if not data:
            return make_response('No file to upload', 400)
        if not filename:
            return make_response("'filename' should be in request arguments",
                                 400)

        with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
            uploaded_file.write(data)
        path_to_file = os.path.join(path_to_folder, filename)
        if os.path.exists(path_to_file):
            abort(403)
        shutil.move(uploaded_file.name, path_to_file)
    else:
        file_to_upload = request.files.get('file')
        if file_to_upload:
            filename = secure_filename(file_to_upload.filename)
            path_to_file = os.path.join(path_to_folder, filename)
            if os.path.exists(path_to_file):
                abort(403)
            file_to_upload.save(path_to_file)
        else:
            return make_response('No file to upload', 400)
    reset_cache()
    return jsonify(result='success')


def compose_path(data_type, path=None):
    if path:
        return os.path.join(CONF.manifests, getattr(CONF, data_type), path)
    else:
        return os.path.join(CONF.manifests, getattr(CONF, data_type))


def check_data_type(data_type):
    if data_type not in DATA_TYPES:
        abort(404)


def get_manifest_files(manifest):
    return dict((k, v) for k, v in manifest.__dict__.iteritems()
                if k in DATA_TYPES)


def exclude_common_files(files, manifests):
    all_manifest_files = [get_manifest_files(manifest)
                          for manifest in manifests]
    for data_type in files.keys():
        files[data_type] = set(files[data_type])
        for manifest_files in all_manifest_files:
            if manifest_files.get(data_type):
                files[data_type] -= set(manifest_files[data_type])
    return files


def check_service_name(service_name):
    if not re.match(r'^\w+(\.\w+)*\w+$', service_name):
        abort(404)


def perform_deletion(files_for_deletion, manifest_for_deletion):
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
        if os.path.exists(path_to_manifest):
            log.debug('Deleting manifest file {0}'.format(path_to_manifest))
            os.remove(path_to_manifest)

        for data_type, files in files_for_deletion.iteritems():
            data_type_dir = os.path.join(CONF.manifests, getattr(CONF,
                                                                 data_type))
            for file in files:
                path_to_delete = os.path.join(data_type_dir, file)
                if os.path.exists(path_to_delete):
                    log.debug('Delete {0}: Removing {1} file'.format(
                        service_name, path_to_delete))
                    os.remove(path_to_delete)
    except Exception as e:
        log.exception('Deleting operation failed '
                      'due to {0}'.format(e.message))
        restore_backup(backup_dir)
        abort(500)
    else:
        release_backup(backup_dir)
        reset_cache()
        return jsonify(result='success')


def save_archive(request):
    err_resp = make_response('There is no data to upload', 409)
    if request.content_type == 'application/octet-stream':
        data = request.environ['wsgi.input'].read()
        if not data:
            return err_resp
        with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                uploaded_file.write(data)
        path_to_archive = uploaded_file.name
    else:
        file_to_upload = request.files.get('file')
        if file_to_upload:
            filename = secure_filename(file_to_upload.filename)
        else:
            return err_resp
        path_to_archive = os.path.join(CONF.cache_dir, filename)
        file_to_upload.save(path_to_archive)
    return path_to_archive


def create_service(data):
    for parameter in  ['full_service_name', 'service_display_name']:
        value = data.get(parameter)
        if not value:
            return make_response('There is no {parameter} in json'.format(
                parameter=parameter), 409)
    service_id = data.get('full_service_name')
    path_to_manifest = os.path.join(CONF.manifests, service_id + '-manifest.yaml')
    with open(path_to_manifest, 'w') as service_manifest:
        service_manifest.write(yaml.dump(data, default_flow_style=False))
