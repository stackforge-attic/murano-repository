#    Copyright (c) 2013 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import os
import shutil
from oslo.config import cfg
from flask import request
from muranorepository.consts import SERVICE_DEFINITIONS_FOLDER_NAME
from muranorepository.consts import CACHE_FOLDER_NAME
CONF = cfg.CONF


def get_tenant_id():
    return request.environ['keystone.'
                           'token_info']['access']['token']['tenant']['id']


def get_tenant_folder():
    return os.path.join(CONF.data_dir,
                        SERVICE_DEFINITIONS_FOLDER_NAME,
                        get_tenant_id())


def get_cache_folder():
    return os.path.join(CONF.data_dir, CACHE_FOLDER_NAME, get_tenant_id())


def check_tenant_dir_existence(path):
    if not os.path.exists(path):
        shutil.copytree(CONF.manifests, path)
