import os
from plugins.themes.controllers import BackgroundLayersController, MapthumbsController, ThemesController
from plugins.themes.utils import ThemeUtils

__background_layers_controller = None
__mapthumbs_controller = None
__themes_controller = None


name = "Themes"

def load_plugin(app, handler):

    # Check required settings
    config = handler().config()
    for setting in ["input_config_path", "qwc2_path", "qgs_resources_path"]:
        if not os.path.isdir(config.get(setting, "")):
            raise RuntimeError("%s is not set or invalid" % setting)
    if not config.get("ogc_service_url", None):
        raise RuntimeError("ogc_service_url is not set")

    global __background_layers_controller
    global __mapthumbs_controller
    global __themes_controller

    themesconfig = ThemeUtils.load_themesconfig(app, handler)
    __background_layers_controller = BackgroundLayersController(app, handler, themesconfig)
    __mapthumbs_controller = MapthumbsController(app, handler)
    __themes_controller = ThemesController(app, handler, themesconfig)

