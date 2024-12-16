from datetime import datetime
import logging
import os
import re
import requests
from shutil import copyfile
import time
import urllib.parse
import importlib

from flask import abort, Flask, json, redirect, render_template, request, \
    Response, stream_with_context, jsonify, send_from_directory
from flask_bootstrap import Bootstrap5
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail

from qwc_services_core.auth import auth_manager, optional_auth, get_identity
from qwc_services_core.tenant_handler import TenantHandler, \
    TenantPrefixMiddleware, TenantSessionInterface
from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.database import DatabaseEngine
from access_control import AccessControl
from controllers import UsersController, GroupsController, RolesController, \
    ResourcesController, PermissionsController, RegistrableGroupsController, \
    RegistrationRequestsController
from utils import i18n

AUTH_PATH = os.environ.get('AUTH_PATH', '/auth')
SKIP_LOGIN = os.environ.get('SKIP_LOGIN', False)

# Flask application
app = Flask(__name__, template_folder='.')

jwt = auth_manager(app)
app.secret_key = app.config['JWT_SECRET_KEY']

app.config['BOOTSTRAP_SERVE_LOCAL'] = True
app.config['QWC_GROUP_REGISTRATION_ENABLED'] = os.environ.get(
    'GROUP_REGISTRATION_ENABLED', 'True').lower() == 'true'
app.config['IDLE_TIMEOUT'] = os.environ.get('IDLE_TIMEOUT', 0)

# JWT CSRF protection conflicts with WTF CSRF protection
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['WTF_CSRF_SSL_STRICT'] = os.environ.get(
    'WTF_CSRF_SSL_STRICT', 'True').lower() == 'true'

# enable CSRF protection
CSRFProtect(app)
# load Bootstrap extension
Bootstrap5(app)


# Setup mailer
def mail_config_from_env(app):
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', '127.0.0.1')
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 25))
    app.config['MAIL_USE_TLS'] = os.environ.get(
        'MAIL_USE_TLS', 'False').lower() == 'true'
    app.config['MAIL_USE_SSL'] = os.environ.get(
        'MAIL_USE_SSL', 'False').lower() == 'true'
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    app.config['MAIL_DEBUG'] = int(os.environ.get('MAIL_DEBUG', app.debug))
    app.config['MAIL_MAX_EMAILS'] = os.environ.get('MAIL_MAX_EMAILS')
    app.config['MAIL_SUPPRESS_SEND'] = os.environ.get(
        'MAIL_SUPPRESS_SEND', str(app.testing)).lower() == 'true'
    app.config['MAIL_ASCII_ATTACHMENTS'] = os.environ.get(
        'MAIL_ASCII_ATTACHMENTS', 'False').lower() == 'true'


mail_config_from_env(app)
mail = Mail(app)

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

    def qwc_config_schema(self):
        return self._config.get('qwc_config_schema', 'qwc_config')


def handler():
    tenant = tenant_handler.tenant()
    handler = tenant_handler.handler('adminGui', 'handler', tenant)
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
    RegistrationRequestsController(app, handler, mail)

access_control = AccessControl(handler, app.logger)


plugins_loaded = False
@app.before_request
def load_plugins():
    global plugins_loaded
    if not plugins_loaded:
        # HACK to work around
        #     The setup method 'add_url_rule' can no longer be called on the application.
        #     It has already handled its first request, any changes will not be applied consistently.
        # From the flask code, before_request is called immediately after _got_first_request=True, so
        # there should be no harm clearing the flag again temporarily
        app._got_first_request = False
        plugins_loaded = True
        app.config['PLUGINS'] = []
        for plugin in handler().config().get("plugins", []):
            app.logger.info("Loading plugin '%s'" % plugin)
            try:
                mod = importlib.import_module("plugins." + plugin)
                mod.load_plugin(app, handler)
                app.config['PLUGINS'].append({"id": plugin, "name": mod.name})
            except Exception as e:
                app.logger.warning("Could not load plugin %s: %s" % (plugin, str(e)))
        app._got_first_request = True


@app.before_request
@optional_auth
def assert_admin_role():
    if request.path.startswith(('/bootstrap/static/', '/ready', '/healthz')):
        return

    identity = get_identity()
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
                config = handler().config()
                admin_gui_title = config.get('admin_gui_title', i18n('interface.main.title'))
                favicon = config.get('favicon')
                return render_template(
                    'templates/access_denied.html',
                    admin_gui_title=admin_gui_title,
                    favicon=favicon,
                    i18n=i18n,
                    login_url=prefix + '/logout?url=%s' % request.url
                )
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
    config = handler().config()
    admin_gui_title = config.get('admin_gui_title', i18n('interface.main.title'))
    admin_gui_subtitle = config.get('admin_gui_subtitle', i18n('interface.main.subtitle'))
    favicon = config.get('favicon')
    have_config_generator = True if config.get(
        "config_generator_service_url",
        "http://qwc-config-service:9090"
    ) else False
    have_qgis_server = True if config.get(
        "default_qgis_server_url",
        "http://qwc-qgis-server/ows"
    ) else False
    solr_index_update_enabled = True if config.get('solr_service_url', '') else False
    return render_template(
        'templates/home.html',
        admin_gui_title=admin_gui_title,
        admin_gui_subtitle=admin_gui_subtitle,
        favicon=favicon,
        have_config_generator=have_config_generator,
        have_qgis_server=have_qgis_server,
        solr_index_update_enabled=solr_index_update_enabled, i18n=i18n
    )


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
        "http://qwc-config-service:9090").rstrip('/') + '/'

    params = {
        "tenant": current_handler.tenant,
    }
    params.update(request.args)
    response = requests.post(
        urllib.parse.urljoin(config_generator_url, "generate_configs"),
        params=params
    )

    return (response.text, response.status_code)

@app.route('/qgis_server_logs', methods=['POST'])
def qgis_server_logs():
    """ Return qgis server logs """

    current_handler = handler()
    default_qgis_server_url = current_handler.config().get(
        "default_qgis_server_url",
        "http://qwc-qgis-server/ows").rstrip('/')
    ows_prefix = current_handler.config().get(
        "ows_prefix",
        "/ows").rstrip('/')
    if default_qgis_server_url.endswith(ows_prefix):
        default_qgis_server_url = default_qgis_server_url[:-len(ows_prefix)]

    params = {
        "n": request.args.get('qgis_server_log_lines', '100')
    }
    response = requests.post(
        urllib.parse.urljoin(default_qgis_server_url, "logs"),
        params=params
    )

    def colorize(line):
        if line[9:16] == "WARNING":
            return f'<b style="color: orange">{line}</b>'
        elif line[9:17] == "CRITICAL" or line.startswith("Traceback"):
            return f'<b style="color: red">{line}</b>'
        else:
            return line
    text = "\n".join(map(colorize, response.text.split("\n")))

    return (text, response.status_code)

@app.route('/update_solr_index', methods=['POST'])
def update_solr_index():
    """Update Solr index for a tenant."""
    config = handler().config()
    tenant = handler().tenant

    solr_service_url = config.get('solr_service_url', '')
    if not solr_service_url:
        abort(404, "Missing config for 'solr_service_url'")

    # get DataImportHandler for tenant
    solr_tenant_dih = config.get('solr_tenant_dih', '')
    if not solr_tenant_dih:
        abort(500, "Missing config for 'solr_tenant_dih'")

    # get optional source DataImportHandler config file for tenant
    solr_tenant_dih_config_file = config.get('solr_tenant_dih_config_file', '')
    # get optional target path for Solr configs
    solr_config_path = config.get('solr_config_path', '')

    if solr_tenant_dih_config_file and solr_config_path:
        try:
            # copy tenant config file to Solr configs dir
            file_name = os.path.basename(solr_tenant_dih_config_file)
            app.logger.info(
                "Updating Solr config file '%s' for tenant '%s'" %
                (file_name, tenant)
            )
            copyfile(
                solr_tenant_dih_config_file,
                os.path.join(solr_config_path, file_name)
            )
        except Exception as e:
            msg = "Could not copy Solr tenant config:\n%s" % e
            app.logger.error(msg)
            abort(500, msg)

    try:
        timeout = config.get('proxy_timeout', 60)

        # clear search index for tenant
        url = urllib.parse.urljoin(solr_service_url, "update?commitWithin=1000")
        data = {'delete': {'query': "tenant:%s" % tenant}}
        headers = {'content-type': 'application/json'}
        app.logger.info("Clearing Solr search index for tenant '%s'" % tenant)
        response = requests.post(
            url, data=json.dumps(data), headers=headers, timeout=timeout
        )
        if response.status_code != 200:
            abort(
                response.status_code,
                "Could not clear Solr search index:\n%s" % response.text
            )

        # wait until index has been cleared
        solr_update_check_max_retries = config.get(
            'solr_update_check_max_retries', 10
        )
        solr_update_check_wait = config.get('solr_update_check_wait', 5)
        num_found = -1
        for i in range(solr_update_check_max_retries):
            time.sleep(solr_update_check_wait)

            # send dummy query with tenant filter
            url = urllib.parse.urljoin(
                solr_service_url,
                "select?omitHeader=true&q=tenant:%s&rows=0" % tenant
            )
            app.logger.info("Checking result count for tenant '%s'" % tenant)
            response = requests.get(url, timeout=timeout)

            # check if result count is 0
            num_found = json.loads(response.text) \
                .get('response', {}).get('numFound', -1)
            if num_found == 0:
                break

        if num_found != 0:
            abort(
                500,
                "Solr search index could not be cleared (%s results)" %
                num_found
            )

        # update search index for tenant
        url = urllib.parse.urljoin(
            solr_service_url,
            "%s?command=full-import&clean=false" % solr_tenant_dih
        )
        app.logger.info(
            "Updating Solr search index for '%s' for tenant '%s'" %
            (solr_tenant_dih, tenant)
        )
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            abort(
                response.status_code,
                "Could not create Solr search index:\n%s" % response.text
            )

        # wait until index has been updated
        for i in range(solr_update_check_max_retries):
            time.sleep(solr_update_check_wait)

            # check status for tenant
            url = urllib.parse.urljoin(
                solr_service_url,
                "%s?command=status" % solr_tenant_dih
            )
            app.logger.info("Checking Solr status for tenant '%s'" % tenant)
            response = requests.get(url, timeout=timeout)

            status_response = json.loads(response.text)
            status = status_response.get('status')
            if status == 'idle':
                import_failed = 'Full Import failed' in status_response.get(
                    'statusMessages', {}
                )
                if not import_failed:
                    msg = (
                        "Solr search index for tenant '%s' "
                        "has been successfully updated" % tenant
                    )
                    app.logger.info(msg)
                    return (msg)
                else:
                    abort(
                        500,
                        "Solr full import failed. Check Solr logs for errors."
                    )

        # if still updating
        return ("Started Solr search index update for tenant '%s'" % tenant)
    except Exception as e:
        msg = "Could not update Solr search index:\n%s" % e
        app.logger.error(msg)
        abort(500, msg)


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
