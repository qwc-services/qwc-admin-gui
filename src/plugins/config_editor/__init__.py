import os

from plugins.config_editor.controllers import ConfigsController
from utils import i18n


name = i18n('plugins.config_editor.title')


def load_plugin(app, handler):
    # check required config
    config = handler().config()
    input_config_path = config.get('input_config_path')
    if input_config_path is None or not os.path.isdir(input_config_path):
        app.logger.error(
            "Config Editor plugin: "
            "Required config option 'input_config_path' is not set or invalid"
        )

    # create controller (including routes)
    ConfigsController(app, handler)
