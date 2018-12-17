import logging
import os

from flask import Flask, render_template, redirect
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect
from flask_jwt_extended import jwt_optional, get_jwt_identity

from qwc_config_db.config_models import ConfigModels
from qwc_services_core.database import DatabaseEngine
from qwc_services_core.jwt import jwt_manager
from access_control import AccessControl
from controllers import UsersController, GroupsController, RolesController, \
    ResourcesController, PermissionsController


# load ORM models for ConfigDB
db_engine = DatabaseEngine()
config_models = ConfigModels(db_engine)

# Flask application
app = Flask(__name__)
app.secret_key = os.environ.get(
        'JWT_SECRET_KEY',
        'CHANGE-ME-8JGL6Kc9UA69p6E88JGL6Kc9UA69p6E8')

# enable CSRF protection
CSRFProtect(app)
# load Bootstrap extension
Bootstrap(app)

# Setup the Flask-JWT-Extended extension
jwt = jwt_manager(app)

# create controllers (including their routes)
UsersController(app, config_models)
GroupsController(app, config_models)
RolesController(app, config_models)
ResourcesController(app, config_models)
PermissionsController(app, config_models)

acccess_control = AccessControl(config_models, app.logger)


@app.before_request
@jwt_optional
def assert_admin_role():
    identity = get_jwt_identity()
    app.logger.debug("Access with identity %s" % identity)
    if not acccess_control.is_admin(identity):
        app.logger.info("Access denied for user %s" % identity)
        if app.debug:
            pass  # Allow access in debug mode
        else:
            return redirect('/auth/login')


# routes
@app.route('/')
def home():
    return render_template('home.html')


# local webserver
if __name__ == '__main__':
    print("Starting QWC Admin GUI...")
    app.logger.setLevel(logging.DEBUG)
    app.run(host='localhost', port=5031, debug=True)
