from datetime import datetime
import logging
import os
import re
import requests
import urllib.parse
import importlib

from flask import abort, Flask, json, redirect, render_template, request, \
    Response, stream_with_context, jsonify, send_from_directory
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import jwt_optional, get_jwt_identity
from flask_mail import Mail

from qwc_services_core.tenant_handler import TenantHandler, \
    TenantPrefixMiddleware, TenantSessionInterface
from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.database import DatabaseEngine
from qwc_services_core.jwt import jwt_manager
from access_control import AccessControl
from controllers import UsersController, GroupsController, RolesController, \
    ResourcesController, PermissionsController, RegistrableGroupsController, \
    RegistrationRequestsController


AUTH_PATH = os.environ.get('AUTH_PATH', '/auth')
SKIP_LOGIN = os.environ.get('SKIP_LOGIN', False)

# Flask application
app = Flask(__name__, template_folder='.')

jwt = jwt_manager(app)
app.secret_key = app.config['JWT_SECRET_KEY']

app.config['QWC_GROUP_REGISTRATION_ENABLED'] = os.environ.get(
    'GROUP_REGISTRATION_ENABLED', 'True') == 'True'
app.config['IDLE_TIMEOUT'] = os.environ.get('IDLE_TIMEOUT', 0)

# enable CSRF protection
CSRFProtect(app)
# load Bootstrap extension
Bootstrap(app)


# Setup mailer
def mail_config_from_env(app):
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '127.0.0.1')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 25))
    app.config['MAIL_USE_TLS'] = os.environ.get(
        'MAIL_USE_TLS', 'False') == 'True'
    app.config['MAIL_USE_SSL'] = os.environ.get(
        'MAIL_USE_SSL', 'False') == 'True'
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    app.config['MAIL_DEBUG'] = int(os.environ.get('MAIL_DEBUG', app.debug))
    app.config['MAIL_MAX_EMAILS'] = os.environ.get('MAIL_MAX_EMAILS')
    app.config['MAIL_SUPPRESS_SEND'] = os.environ.get(
        'MAIL_SUPPRESS_SEND', str(app.testing)) == 'True'
    app.config['MAIL_ASCII_ATTACHMENTS'] = os.environ.get(
        'MAIL_ASCII_ATTACHMENTS', False)


mail_config_from_env(app)
mail = Mail(app)

# Load translation strings
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'en')
translations = {}
try:
    locale = DEFAULT_LOCALE
    path = os.path.join(app.root_path, 'translations/%s.json' % locale)
    with open(path, 'r') as f:
        translations[locale] = json.load(f)
except Exception as e:
    app.logger.error(
        "Failed to load translation strings for locale '%s' from %s\n%s"
        % (locale, path, e)
    )


# Setup translation helper
@app.template_filter('i18n')
def i18n(value, locale=DEFAULT_LOCALE):
    """Lookup string in translations.

    Usage:
        Python: i18n('example.path_to.string')
        Jinja2 filter for templates: 'example.path_to.string' | i18n

    :param str value: Dot-separated path to translation string
    :param str locale: Override locale (optional)
    """
    # traverse translations dict for locale
    parts = value.split('.')
    lookup = translations.get(locale, {})
    for part in parts:
        if isinstance(lookup, dict):
            # get next lookup level
            lookup = lookup.get(part)
        else:
            # lookup level too deep
            lookup = None
        if lookup is None:
            # return input value if not found
            lookup = value
            break

    return lookup


tenant_handler = TenantHandler(app.logger)
db_engine = DatabaseEngine()


class TenantConfigHandler:
    def __init__(self, tenant, db_engine, logger):
        self.tenant = tenant
        self._db_engine = db_engine
        self.logger = logger

        config_handler = RuntimeConfig("adminGui", logger)
        self._config = config_handler.tenant_config(tenant)

    def config(self):
        return self._config

    def db_engine(self):
        return self._db_engine

    def conn_str(self):
        return self._config.get(
            'db_url', 'postgresql:///?service=qwc_configdb')


def handler():
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler('admin-gui', 'handler', tenant)
    if handler is None:
        handler = tenant_handler.register_handler(
            'handler', tenant,
            TenantConfigHandler(tenant, db_engine, app.logger))
    return handler


app.wsgi_app = TenantPrefixMiddleware(app.wsgi_app)
app.session_interface = TenantSessionInterface(os.environ)


def auth_path_prefix():
    # e.g. /admin/org1/auth
    return app.session_interface.tenant_path_prefix().rstrip("/") + "/" + AUTH_PATH.lstrip("/")


# create controllers (including their routes)
UsersController(app, handler)
GroupsController(app, handler)
RolesController(app, handler)
ResourcesController(app, handler)
PermissionsController(app, handler)
if app.config.get('QWC_GROUP_REGISTRATION_ENABLED'):
    RegistrableGroupsController(app, handler)
    RegistrationRequestsController(app, handler, i18n, mail)

access_control = AccessControl(handler, app.logger)

plugins_loaded = False
@app.before_first_request
def load_plugins():
    global plugins_loaded
    if not plugins_loaded:
        plugins_loaded = True
        app.config['PLUGINS'] = []
        for plugin in handler().config().get("plugins", []):
            try:
                mod = importlib.import_module("plugins." + plugin)
                mod.load_plugin(app, handler)
                app.config['PLUGINS'].append({"id": plugin, "name": mod.name})
            except Exception as e:
                app.logger.warning("Could not load plugin %s: %s" % (plugin, str(e)))


@app.before_request
@jwt_optional
def assert_admin_role():
    identity = get_jwt_identity()
    app.logger.debug("Access with identity %s" % identity)
    if not access_control.is_admin(identity):
        if SKIP_LOGIN:
            app.logger.info("Login skipped for user %s" % identity)
            pass  # Allow access without login
        else:
            app.logger.info("Access denied for user %s" % identity)
            prefix = auth_path_prefix()
            if identity:
                # Already logged in, but not with admin role
                return redirect(prefix + '/logout?url=%s' % request.url)
            else:
                return redirect(prefix + '/login?url=%s' % request.url)


@app.route('/logout')
def logout():
    prefix = auth_path_prefix()
    return redirect(prefix + '/logout?url=%s' % request.url.replace(
        "/logout", ""))

# routes
@app.route('/')
def home():
    return render_template('templates/home.html')


@app.route('/pluginstatic/<plugin>/<filename>')
def plugin_static(plugin, filename):
    """ Return assets from plugins """
    return send_from_directory(
        os.path.join("plugins", plugin, "static"), filename)


@app.route('/generate_configs', methods=['POST'])
def generate_configs():
    """ Generate service configurations """

    current_handler = handler()
    config_generator_url = current_handler.config().get(
        "config_generator_service_url",
        "http://qwc-config-service:9090")

    response = requests.post(
        urllib.parse.urljoin(
            config_generator_url,
            "generate_configs?tenant=" + current_handler.tenant))

    return (response.text, response.status_code)


@app.route("/proxy", methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy():
    """Proxy for calling whitelisted internal services.

    Parameter:
        url: Target URL
    """
    url = request.args.get('url')
    current_handler = handler()

    PROXY_URL_WHITELIST = current_handler.config().get(
        "proxy_url_whitelist", [])

    # check if URL is in whitelist
    url_permitted = False
    for expr in PROXY_URL_WHITELIST:
        if re.match(expr, url):
            url_permitted = True
            break
    if not url_permitted:
        app.logger.info("Proxy forbidden for URL '%s'" % url)
        abort(403)

    # settings for proxy to internal services
    PROXY_TIMEOUT = current_handler.config().get(
        "proxy_timeout", 60)

    # forward request
    if request.method == 'GET':
        res = requests.get(url, stream=True, timeout=PROXY_TIMEOUT)
    elif request.method == 'POST':
        headers = {'content-type': request.headers['content-type']}
        res = requests.post(url, stream=True, timeout=PROXY_TIMEOUT,
                            data=request.get_data(), headers=headers)
    elif request.method == 'PUT':
        headers = {'content-type': request.headers['content-type']}
        res = requests.put(url, stream=True, timeout=PROXY_TIMEOUT,
                           data=request.get_data(), headers=headers)
    elif request.method == 'DELETE':
        res = requests.delete(url, stream=True, timeout=PROXY_TIMEOUT)
    else:
        raise "Invalid operation"
    response = Response(stream_with_context(res.iter_content(chunk_size=1024)),
                        status=res.status_code)
    response.headers['content-type'] = res.headers['content-type']
    return response


""" readyness probe endpoint """
@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """
@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == '__main__':
    print("Starting QWC Admin GUI...")
    app.logger.setLevel(logging.DEBUG)
    SKIP_LOGIN = True
    app.run(host='localhost', port=5031, debug=True)
