import os
from plugins.themes.controllers import BackgroundLayersController, MapthumbsController, ThemesController, FilesController, InfoTemplatesController
from plugins.themes.utils import ThemeUtils
from utils import i18n

__background_layers_controller = None
__mapthumbs_controller = None
__themes_controller = None
__files_controller = None
__info_templates_controller = None


name = i18n('plugins.themes.common.title')

def load_plugin(app, handler):

    # Check required settings
    config = handler().config()
    for setting in ["input_config_path", "qwc2_path", "qgs_resources_path", "info_templates_path"]:
        if not os.path.isdir(config.get(setting, "")):
            raise RuntimeError("%s is not set or invalid" % setting)
    if not config.get("ows_prefix", None):
        raise RuntimeError("ows_prefix is not set")
    if not config.get("default_qgis_server_url", None):
        raise RuntimeError("default_qgis_server_url is not set")

    global __background_layers_controller
    global __mapthumbs_controller
    global __themes_controller
    global __files_controller
    global __info_templates_controller

    themesconfig = ThemeUtils.load_themesconfig(app, handler)
    featureInfoconfig = ThemeUtils.load_featureinfo_config(app, handler)
    __background_layers_controller = BackgroundLayersController(app, handler, themesconfig)
    __mapthumbs_controller = MapthumbsController(app, handler)
    __themes_controller = ThemesController(app, handler, themesconfig)
    __files_controller = FilesController(app, handler)
    __info_templates_controller = InfoTemplatesController(app, handler, featureInfoconfig)

