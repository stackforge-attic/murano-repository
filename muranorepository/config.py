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
from oslo.config import cfg
from muranorepository.openstack.common import log
from muranorepository.consts import *

server_opts = [
    cfg.StrOpt('host', default='127.0.0.1'),
    cfg.IntOpt('port', default=5000)]

keystone_opts = [
    cfg.StrOpt('auth_host', default='localhost'),
    cfg.IntOpt('auth_port', default=5000),
    cfg.StrOpt('auth_protocol', default='http'),
    cfg.StrOpt('admin_user', default='admin'),
    cfg.StrOpt('admin_password', default=None),
    cfg.StrOpt('admin_tenant_name', default='admin')]

type_dirs_opts = [cfg.StrOpt(x) for x in DATA_TYPES]


cfg.set_defaults(log.log_opts,
                 default_log_levels=['qpid.messaging=INFO',
                                     'keystoneclient=INFO',
                                     'eventlet.wsgi.server=WARN'])
CONF = cfg.CONF
CONF.register_cli_opts(server_opts)
CONF.register_opts(type_dirs_opts)
CONF.register_opts(type_dirs_opts, group='output')
CONF.register_opts(keystone_opts, group='keystone')


ARGV = []


def parse_configs(argv=None, conf_files=None):
    if argv is not None:
        global ARGV
        ARGV = argv
    try:
        CONF(ARGV, project='murano_service', version="0.1",
             default_config_files=conf_files)
    except cfg.RequiredOptError as roe:
        raise RuntimeError("Option '%s' is required for config group "
                           "'%s'" % (roe.opt_name, roe.group.name))
