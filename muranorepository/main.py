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
import flask
from api.v1 import v1_api
from keystoneclient.middleware import auth_token


def make_app(kwargs):
    """
    App builder (wsgi)
    Entry point
    """

    app = flask.Flask(__name__)
    app.register_blueprint(v1_api, url_prefix='/v1')
    app.wsgi_app = auth_token.filter_factory(
        app.config, **kwargs)(app.wsgi_app)
    return app
