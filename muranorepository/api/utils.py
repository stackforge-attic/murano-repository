
import os
import shutil
import re
import tempfile
import datetime

from flask import jsonify, abort
from flask import make_response
from werkzeug import secure_filename

from muranorepository.utils.parser import ManifestParser
from muranorepository.utils.parser import serialize
from muranorepository.utils.archiver import Archiver
from muranorepository.utils import utils
from muranorepository.consts import DATA_TYPES, MANIFEST
from muranorepository.consts import CLIENTS_DICT
from muranorepository.consts import ARCHIVE_PKG_NAME
from muranorepository.config import cfg
from muranorepository.openstack.common.gettextutils import _  # noqa
import logging as log
CONF = cfg.CONF


def reset_cache():
    try:
        cache_dir = utils.get_cache_folder()
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir, ignore_errors=True)
            os.mkdir(cache_dir)
    except:
        log.exception(_('Error while cleaning cache'))
        return make_response(_('Unable to reset cache'), 500)


def compose_path(data_type, path=None):
    tenant_dir = utils.get_tenant_folder()
    utils.check_tenant_dir_existence(tenant_dir)
    return os.path.join(tenant_dir,
                        getattr(CONF, data_type),
                        path or '')


def get_archive(client, hash_sum):
    types = CLIENTS_DICT.get(client)
    archive_manager = Archiver()
    cache_dir = os.path.join(utils.get_cache_folder(), client)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        existing_hash = None
    else:
        existing_hash = archive_manager.get_existing_hash(cache_dir)

    if existing_hash and hash_sum is None:
        log.debug(_('Transferring existing archive'))
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
            return make_response(_('No file to upload'), 400)
        if not filename:
            return make_response(_("'filename' should be in "
                                   "request arguments"), 400)

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
            return make_response(_('No file to upload'), 400)
    reset_cache()
    return jsonify(result='success')


def check_data_type(data_type):
    if data_type not in DATA_TYPES:
        abort(404)


def get_manifest_files(manifest):
    return dict((k, v) for k, v in manifest.__dict__.iteritems()
                if k in DATA_TYPES)


def get_manifest_info(manifest):
    return dict((k, v) for k, v in manifest.__dict__.iteritems()
                if k not in DATA_TYPES)


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
            utils.get_cache_folder(),
            'Backup_{0}'.format(datetime.datetime.utcnow()))
        log.debug(_('Creating service data backup to {0}'.format(backup_dir)))
        shutil.copytree(utils.get_tenant_folder(), backup_dir)
        return backup_dir

    def release_backup(backup):
        try:
            shutil.rmtree(backup, ignore_errors=True)
        except OSError:
            log.exception(_('Release Backup: '
                            'Backup {0} deletion failed'.format(backup)))

    def restore_backup(backup):
        log.debug(_('Restore service data after unsuccessful deletion'))
        shutil.rmtree(utils.get_tenant_folder(), ignore_errors=True)
        os.rename(backup, utils.get_tenant_folder())

    backup_dir = backup_data()
    service_name = manifest_for_deletion.full_service_name
    path_to_manifest = os.path.join(utils.get_tenant_folder(),
                                    '{0}-manifest.yaml'.format(service_name))
    try:
        if os.path.exists(path_to_manifest):
            log.debug(_('Deleting manifest file {0}'.format(path_to_manifest)))
            os.remove(path_to_manifest)

        for data_type, files in files_for_deletion.iteritems():
            data_type_dir = os.path.join(utils.get_tenant_folder(),
                                         getattr(CONF, data_type))
            for file in files:
                path_to_delete = os.path.join(data_type_dir, file)
                if os.path.exists(path_to_delete):
                    log.debug(_('Delete {0}: Removing {1} file'.format(
                        service_name, path_to_delete)))
                    os.remove(path_to_delete)
    except:
        log.exception(_('Deleting operation failed'))
        restore_backup(backup_dir)
        abort(500)
    else:
        release_backup(backup_dir)
        reset_cache()
        return jsonify(result='success')


def save_archive(request):
    err_resp = make_response(_('There is no data to upload'), 400)
    if request.content_type == 'application/octet-stream':
        data = request.environ['wsgi.input'].read()
        if not data:
            return err_resp
        with tempfile.NamedTemporaryFile(delete=False) as uploaded_file:
                uploaded_file.write(data)
        path_to_archive = uploaded_file.name
    else:
        file_to_upload = request.files.get('file')
        if not file_to_upload:
            return err_resp
        path_to_archive = tempfile.NamedTemporaryFile(delete=False).name
        file_to_upload.save(path_to_archive)
    return path_to_archive


def create_or_update_service(service_id, data):
    manifest_directory = utils.get_tenant_folder()
    utils.check_tenant_dir_existence(manifest_directory)

    required = ['service_display_name']
    optional = {'enabled': True,
                'version': 0.1,
                'description': '',
                'author': '',
                'service_version': 1}

    for parameter in required:
        if not data.get(parameter):
            return make_response(_('There is no {parameter} in json'.format(
                parameter=parameter)), 400)
    for parameter in optional.keys():
        if not data.get(parameter):
            data[parameter] = optional[parameter]

    path_to_manifest = os.path.join(manifest_directory,
                                    service_id + '-manifest.yaml')

    backup_done = False
    with tempfile.NamedTemporaryFile() as backup:
        # make a backup
        if os.path.exists(path_to_manifest):
            backup_done = True
            shutil.copy(path_to_manifest, backup.name)
    try:
        with open(path_to_manifest, 'w') as service_manifest:
            service_manifest.write(serialize(data))
    except:
        log.exception(_('Unable to write to service '
                        'manifest file {0}'.format(path_to_manifest)))
        if backup_done:
            shutil.move(backup.name, path_to_manifest)
        elif os.path.exists(path_to_manifest):
            os.remove(path_to_manifest)
        return make_response(_('Error during service manifest creation'), 500)
    return jsonify(result='success')
