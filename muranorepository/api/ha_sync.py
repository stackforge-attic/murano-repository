# Copyright (c) 2014 Mirantis, Inc.
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

import copy
import socket
import netifaces
import io
import eventlet
from oslo.config import cfg
from flask import request
import werkzeug.datastructures as w
from metadataclient.common import http
import logging as log

CONF = cfg.CONF


def synchronized(func):
    def wrapper(*args, **kwargs):
        res = func(*args, **kwargs)
        if CONF.ha_nodes:
            request_data = RequestData(request)
            eventlet.spawn(_sync, request_data)
        return res

    wrapper.__name__ = "HA_SYNC_" + func.__name__
    return wrapper


def _get_slave_nodes():
    slaves = []
    if CONF.host != '0.0.0.0':
        names_of_this = _get_local_ips()
        names_of_this.append(socket.gethostname())
    else:
        names_of_this = []
    names_of_this.append('localhost')
    for node in CONF.ha_nodes:
        host, port = node.split(":")
        if not host in names_of_this or int(port) != CONF.port:
            slaves.append((host, port))
    return slaves


def _get_local_ips():
    ips = []
    for interface in netifaces.interfaces():
        info = netifaces.ifaddresses(interface).get(netifaces.AF_INET)
        if info:
            for link in info:
                ips.append(link['addr'])
    return ips


class RequestData(object):
    def __init__(self, req):
        self.path = copy.copy(req.full_path)
        self.method = copy.copy(req.method)
        self.headers = w.Headers()
        self.headers.extend(req.headers)
        self.data = copy.copy(req.data)
        request_data = getattr(req, "__uploaded_data", None)
        if request_data:
            self.data = io.BytesIO(request_data)


def _sync(request_data):
    if not request_data.headers.get("X-HA-Sync"):
        log.debug(
            "Synchronizing %s call to %s with slave nodes",
            request_data.method,
            request_data.path)
        token = request_data.headers.get("X-Auth-Token")
        request_data.headers.add("X-HA-Sync", True)

        for host, port in _get_slave_nodes():
            log.debug("Syncing with %s:%s", host, port)
            try:
                client = http.HTTPClient(
                    endpoint="http://{0}:{1}".format(host, port),
                    token=token)
                client.raw_request(request_data.method,
                                   request_data.path,
                                   headers=request_data.headers,
                                   body=request_data.data)
            except Exception as e:
                log.warn("Unable to sync")
                log.exception(e)
    else:
        log.debug("Running on a slave node, will not sync")


