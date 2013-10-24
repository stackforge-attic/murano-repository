#!/usr/bin/env python

# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import eventlet
from eventlet import wsgi
from oslo.config import cfg
# If ../murano_service/__init__.py exists, add ../ to Python search path,
# so that it will override what happens to be installed in
# /usr/(local/)lib/python...
possible_topdir = os.path.normpath(os.path.join(os.path.abspath(__file__),
                                                os.pardir,
                                                os.pardir,
                                                os.pardir))
if os.path.exists(os.path.join(possible_topdir,
                               'muranorepository',
                               '__init__.py')):
    sys.path.insert(0, possible_topdir)

from muranorepository import config
import muranorepository.main as server
from muranorepository.openstack.common import log


LOG = log.getLogger(__name__)


def main():
    dev_conf = os.path.join(possible_topdir,
                            'etc',
                            'murano-repository.conf')
    config_files = None
    if os.path.exists(dev_conf):
        config_files = [dev_conf]

    config.parse_configs(sys.argv[1:], config_files)
    log.setup('muranorepository')

    app = server.make_app({
        'auth_host': cfg.CONF.keystone.auth_host,
        'auth_port': cfg.CONF.keystone.auth_port,
        'auth_protocol': cfg.CONF.keystone.auth_protocol,
        'admin_user': cfg.CONF.keystone.admin_user,
        'admin_password': cfg.CONF.keystone.admin_password,
        'admin_tenant_name': cfg.CONF.keystone.admin_tenant_name
    })
    if not os.path.isabs(config.CONF.manifests):
        config.CONF.manifests = os.path.join(possible_topdir,
                                             config.CONF.manifests)
    wsgi.server(eventlet.listen((cfg.CONF.host, cfg.CONF.port),
                                backlog=500),
                app)

if __name__ == '__main__':
    main()
