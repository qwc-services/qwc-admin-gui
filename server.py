import logging
import os
import re
import requests

from flask import abort, Flask, json, redirect, render_template, request, \
    Response, stream_with_context
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import jwt_optional, get_jwt_identity
from flask_mail import Mail

from qwc_config_db.config_models import ConfigModels
from qwc_services_core.database import DatabaseEngine
from qwc_services_core.jwt import jwt_manager
from access_control import AccessControl
from controllers import UsersController, GroupsController, RolesController, \
    ResourcesController, PermissionsController, RegistrableGroupsController, \
    RegistrationRequestsController


# load ORM models for ConfigDB
db_engine = DatabaseEngine()
config_models = ConfigModels(db_engine)

# Flask application
app = Flask(__name__)
app.secret_key = os.environ.get(
    'JWT_SECRET_KEY',
    'CHANGE-ME-8JGL6Kc9UA69p6E88JGL6Kc9UA69p6E8')
app.config['QWC_GROUP_REGISTRATION_ENABLED'] = os.environ.get(
    'GROUP_REGISTRATION_ENABLED', 'True') == 'True'

# enable CSRF protection
CSRFProtect(app)
# load Bootstrap extension
Bootstrap(app)

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app)


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

# settings for proxy to internal services
PROXY_TIMEOUT = int(os.environ.get('PROXY_TIMEOUT', 60))
try:
    PROXY_URL_WHITELIST = json.loads(
        os.environ.get('PROXY_URL_WHITELIST', '[]')
    )
except Exception as e:
    app.logger.error("Could not load PROXY_URL_WHITELIST:\n%s" % e)
    PROXY_URL_WHITELIST = []


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


# create controllers (including their routes)
UsersController(app, config_models)
GroupsController(app, config_models)
RolesController(app, config_models)
ResourcesController(app, config_models)
PermissionsController(app, config_models)
if app.config.get('QWC_GROUP_REGISTRATION_ENABLED'):
    RegistrableGroupsController(app, config_models)
    RegistrationRequestsController(app, config_models, i18n, mail)

access_control = AccessControl(config_models, app.logger)


@app.before_request
@jwt_optional
def assert_admin_role():
    identity = get_jwt_identity()
    app.logger.debug("Access with identity %s" % identity)
    if not access_control.is_admin(identity):
        app.logger.info("Access denied for user %s" % identity)
        if app.debug:
            pass  # Allow access in debug mode
        else:
            if identity:
                # Already logged in, but not with admin role
                return redirect('/auth/logout?url=%s' % request.url)
            else:
                return redirect('/auth/login?url=%s' % request.url)


# routes
@app.route('/')
def home():
    return render_template('home.html')


@app.route("/proxy", methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy():
    """Proxy for calling whitelisted internal services.

    Parameter:
        url: Target URL
    """
    url = request.args.get('url')

    # check if URL is in whitelist
    url_permitted = False
    for expr in PROXY_URL_WHITELIST:
        if re.match(expr, url):
            url_permitted = True
            break
    if not url_permitted:
        app.logger.info("Proxy forbidden for URL '%s'" % url)
        abort(403)

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


# local webserver
if __name__ == '__main__':
    print("Starting QWC Admin GUI...")
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=5031, debug=True)
