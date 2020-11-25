import os
import json
import pathlib
from datetime import datetime
from collections import OrderedDict


class ThemeUtils():
    """ Utils for Themes"""

    @staticmethod
    def load_themesconfig(app, handler):
        """Return themesconfig"""
        current_handler = handler()
        config_in_path = current_handler.config().get("input_config_path")
        tenantConfig = os.path.join(config_in_path, current_handler.tenant, 'tenantConfig.json')

        try:
            with open(tenantConfig, encoding='utf-8') as fh:
                config = json.load(fh, object_pairs_hook=OrderedDict)
        except IOError as e:
            app.logger.error("Error reading tenantConfig.json: {}".format(
                e.strerror))

        return config.get("themesConfig", {})

    @staticmethod
    def save_themesconfig(themesConfig, app, handler):
        """Save themesconfig

        :param Dict themesconfig: themesConfig Dictionary
        :param Flask app: Flask application
        """
        current_handler = handler()
        config_in_path = current_handler.config().get("input_config_path")
        tenantConfig = os.path.join(config_in_path, current_handler.tenant, 'tenantConfig.json')

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        backup = "%s.bak%s" % (tenantConfig, timestamp)

        try:
            with open(tenantConfig, "r", encoding="utf-8") as fh:
                config = json.load(fh)

            with open(backup, "w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=2, separators=(',', ': '))

            config["themesConfig"] = themesConfig
            with open(tenantConfig, "w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=2, separators=(',', ': '))

            return True

        except IOError as e:
            app.logger.error("Error writing tenantConfig.json: {}".format(
                e.strerror))

        return False

    @staticmethod
    def get_projects(app, handler):
        """Return QGIS project file names from QGIS_RESOURCES_PATH"""
        current_handler = handler()
        resources_path = current_handler.config().get("qgs_resources_path")
        ogc_service_url = current_handler.config().get("ogc_service_url")

        projects = []
        app.logger.info(resources_path)
        for path in pathlib.Path(resources_path).rglob("*.qgs"):
            app.logger.info(str(path))
            app.logger.info(path.relative_to(resources_path))
            project = str(path.relative_to(resources_path))[:-4].replace("\\", "/")
            url = ogc_service_url.rstrip("/") + "/" + project
            projects.append((url, project))
        return sorted(projects)

    @staticmethod
    def get_mapthumbs(app, handler):
        """Return mapthumbs from qwc2 assets path"""
        current_handler = handler()
        qwc2_path = current_handler.config().get("qwc2_path")
        mapthumbs = []
        thumbs_path = os.path.join(qwc2_path, "assets/img/mapthumbs")
        for mapthumb in os.listdir(thumbs_path):
            if not mapthumb.startswith("."):
                mapthumbs.append(mapthumb)
        return sorted(mapthumbs)

    @staticmethod
    def get_format():
        """Return image formats"""
        return (["", ""],
                ["jpg", "jpg"],
                ["jpeg", "jpeg"],
                ["image/jpeg", "image/jpeg"],
                ["image/png", "image/png"],
                ["image/png; mode=1bit", "image/png; mode=1bit"],
                ["image/png; mode=8bit", "image/png; mode=8bit"],
                ["image/png; mode=16bit", "image/png; mode=16bit"])

    @staticmethod
    def get_crs(app, handler):
        """Return coordinate systems"""
        current_handler = handler()
        tenant_qwc2_config = os.path.join(current_handler.config().get("input_config_path"), current_handler.tenant, "config.json")
        master_qwc2_config = os.path.join(current_handler.config().get("qwc2_path"), "config.json")

        qwc2_config = tenant_qwc2_config if os.path.isfile(tenant_qwc2_config) else master_qwc2_config

        with open(qwc2_config, encoding="utf-8") as fh:
            config = json.load(fh)
            if "projections" in config:
                projections = config["projections"]
                result = [["EPSG:3857", "EPSG:3857"]]
                for p in projections:
                    code = p["code"]
                    result.append([code, code])
                return tuple(result)
        return (["EPSG:3857", "EPSG:3857"],
                ["EPSG:4647", "EPSG:4647"],
                ["EPSG:25832", "EPSG:25832"])
