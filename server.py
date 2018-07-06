from flask import Flask, render_template
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

from qwc_config_db.config_models import ConfigModels
from qwc_services_core.database import DatabaseEngine
from controllers import UsersController, GroupsController, RolesController, \
    ResourcesController, PermissionsController


# load ORM models for ConfigDB
db_engine = DatabaseEngine()
config_models = ConfigModels(db_engine)

# Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = '8JGL6Kc9UA69p6E8'

# enable CSRF protection
CSRFProtect(app)
# load Bootstrap extension
Bootstrap(app)

# create controllers (including their routes)
UsersController(app, config_models)
GroupsController(app, config_models)
RolesController(app, config_models)
ResourcesController(app, config_models)
PermissionsController(app, config_models)


# routes
@app.route('/')
def home():
    return render_template('home.html')


# local webserver
if __name__ == '__main__':
    print("Starting QWC Admin GUI...")
    app.run(host='localhost', port=5031, debug=True)
