import os
import json
import pathlib
import datetime
from collections import OrderedDict
from sqlalchemy.sql import text as sql_text
from urllib.parse import urlparse

from qwc_services_core.database import DatabaseEngine

db_engine = DatabaseEngine()

class ThemeUtils():
    """ Utils for Themes"""

    @staticmethod
    def load_themesconfig(app, handler):
        """Return themesconfig"""
        current_handler = handler()
        config_in_path = os.path.join(current_handler.config().get("input_config_path"), current_handler.tenant)
        tenant_config_path = os.path.join(config_in_path, 'tenantConfig.json')

        try:
            with open(tenant_config_path, encoding='utf-8') as fh:
                tenant_config = json.load(fh, object_pairs_hook=OrderedDict)
        except IOError as e:
            app.logger.error("Error reading tenantConfig.json: {}".format(
                e.strerror))
            return {}

        themes_config = tenant_config.get("themesConfig", None)

        if isinstance(themes_config, str):
            themes_config_path = themes_config
            try:
                if not os.path.isabs(themes_config_path):
                    themes_config_path = os.path.join(config_in_path, themes_config_path)
                with open(themes_config_path) as f:
                    themes_config = json.load(f)
            except:
                msg = "Failed to read themes configuration %s" % themes_config_path
                app.logger.error(msg)
                return {}
        elif not isinstance(themes_config, dict):
            msg = "Missing or invalid themes configuration in tenantConfig.json"
            app.logger.error(msg)
            return {}

        return themes_config

    @staticmethod
    def save_themesconfig(new_themes_config, app, handler):
        """Save themesconfig

        :param Dict new_themes_config: new themesConfig Dictionary
        :param Flask app: Flask application
        """
        current_handler = handler()
        config_in_path = os.path.join(current_handler.config().get("input_config_path"), current_handler.tenant)
        tenant_config_path = os.path.join(config_in_path, 'tenantConfig.json')

        try:
            with open(tenant_config_path, encoding='utf-8') as fh:
                tenant_config = json.load(fh, object_pairs_hook=OrderedDict)
        except IOError as e:
            app.logger.error("Error reading tenantConfig.json: {}".format(
                e.strerror))
            return False

        baksuffix = "%s.bak" % datetime.datetime.now(datetime.UTC).strftime("-%Y%m%d-%H%M%S")
        themes_config = tenant_config.get("themesConfig", None)

        if isinstance(themes_config, str):
            themes_config_path = themes_config
            try:
                if not os.path.isabs(themes_config_path):
                    themes_config_path = os.path.join(config_in_path, themes_config_path)
                with open(themes_config_path) as f:
                    themes_config = json.load(f)

                with open(themes_config_path + baksuffix, "w", encoding="utf-8") as fh:
                    json.dump(themes_config, fh, indent=2, separators=(',', ': '))

                with open(themes_config_path, "w", encoding="utf-8") as fh:
                    json.dump(new_themes_config, fh, indent=2, separators=(',', ': '))

            except IOError as e:
                msg = "Failed to backup/save themes configuration %s: %s" % (themes_config_path, e.strerror)
                app.logger.error(msg)
                return False
        elif isinstance(themes_config, dict):
            try:
                with open(tenant_config_path + baksuffix, "w", encoding="utf-8") as fh:
                    json.dump(tenant_config, fh, indent=2, separators=(',', ': '))

                tenant_config["themesConfig"] = new_themes_config
                with open(tenant_config_path, "w", encoding="utf-8") as fh:
                    json.dump(tenant_config, fh, indent=2, separators=(',', ': '))
            except IOError as e:
                msg = "Failed to backup/save themes configuration %s: %s" % (tenant_config_path, e.strerror)
                app.logger.error(msg)
                return False
        else:
            msg = "Missing or invalid themes configuration in tenantConfig.json"
            app.logger.error(msg)
            return False

        return True

    @staticmethod
    def load_featureinfo_config(app, handler):
        """Load and return the 'resources' configuration for the 'featureInfo' service"""

        current_handler = handler()
        config_in_path = os.path.join(current_handler.config().get("input_config_path"), current_handler.tenant)
        tenant_config_path = os.path.join(config_in_path, 'tenantConfig.json')

        try:
            with open(tenant_config_path, encoding='utf-8') as fh:
                tenant_config = json.load(fh, object_pairs_hook=OrderedDict)
        except IOError as e:
            app.logger.error("Error reading tenantConfig.json: {}".format(e.strerror))
            return {}
        services = tenant_config.get("services", [])
        for service in services:
            if service.get("name") == "featureInfo":
                resources_config = service.get("resources", {})
                return resources_config

        return {}

    @staticmethod
    def save_featureinfo_config(new_featureinfo_config, app, handler):
        """Save featureInfo configuration

        :param Dict new_featureinfo_config: New featureInfo configuration dictionary
        :param Flask app: Flask application
        """
        current_handler = handler()
        config_in_path = os.path.join(current_handler.config().get("input_config_path"), current_handler.tenant)
        tenant_config_path = os.path.join(config_in_path, 'tenantConfig.json')

        try:
            with open(tenant_config_path, encoding='utf-8') as fh:
                tenant_config = json.load(fh, object_pairs_hook=OrderedDict)
        except IOError as e:
            app.logger.error("Error reading tenantConfig.json: {}".format(e.strerror))
            return False

        baksuffix = "%s.bak" % datetime.datetime.now(datetime.UTC).strftime("-%Y%m%d-%H%M%S")
        services = tenant_config.get("services", [])

        for service in services:
            if service.get("name") == "featureInfo":
                featureinfo_config = service.get("resources")
                if isinstance(featureinfo_config, str):
                    featureinfo_config_path = featureinfo_config
                    try:
                        if not os.path.isabs(featureinfo_config_path):
                            featureinfo_config_path = os.path.join(config_in_path, featureinfo_config_path)

                        with open(featureinfo_config_path) as f:
                            featureinfo_config = json.load(f)

                        with open(featureinfo_config_path + baksuffix, "w", encoding="utf-8") as fh:
                            json.dump(featureinfo_config, fh, indent=2, separators=(',', ': '))

                        with open(featureinfo_config_path, "w", encoding="utf-8") as fh:
                            json.dump(new_featureinfo_config, fh, indent=2, separators=(',', ': '))

                    except IOError as e:
                        msg = "Failed to backup/save featureInfo configuration {}: {}".format(
                            featureinfo_config_path, e.strerror)
                        app.logger.error(msg)
                        return False
                elif isinstance(featureinfo_config, dict):
                    try:
                        with open(tenant_config_path + baksuffix, "w", encoding="utf-8") as fh:
                            json.dump(tenant_config, fh, indent=2, separators=(',', ': '))

                        service["resources"] = new_featureinfo_config
                        with open(tenant_config_path, "w", encoding="utf-8") as fh:
                            json.dump(tenant_config, fh, indent=2, separators=(',', ': '))

                    except IOError as e:
                        msg = "Failed to backup/save featureInfo configuration {}: {}".format(
                            tenant_config_path, e.strerror)
                        app.logger.error(msg)
                        return False
                else:
                    msg = "Missing or invalid featureInfo configuration in tenantConfig.json"
                    app.logger.error(msg)
                    return False
            try:
                with open(tenant_config_path + baksuffix, "w", encoding="utf-8") as fh:
                    json.dump(tenant_config, fh, indent=2, separators=(',', ': '))

                with open(tenant_config_path, "w", encoding="utf-8") as fh:
                    json.dump(tenant_config, fh, indent=2, separators=(',', ': '))
            except IOError as e:
                msg = "Failed to backup/save featureInfo configuration {}: {}".format(
                    tenant_config_path, e.strerror)
                app.logger.error(msg)
                return False

        return True

    @staticmethod
    def get_layers(app, handler):
        """Return geospatial file names from QGIS_RESOURCES_PATH"""
        current_handler = handler()
        resources_path = current_handler.config().get("qgs_resources_path")

        layers = []
        app.logger.info(resources_path)
        for ext in ['*.geojson', '*.kml', '*.gpkg', '*.shp']:
            for path in pathlib.Path(resources_path).rglob(ext):
                app.logger.info(str(path))
                app.logger.info(path.relative_to(resources_path))
                layer = str(path.relative_to(resources_path))
                if not layer.startswith("."):
                    layers.append(layer)
        return sorted(layers)

    @staticmethod
    def get_projects(app, handler):
        """Return QGIS project file names from QGIS_RESOURCES_PATH"""
        current_handler = handler()
        resources_path = current_handler.config().get("qgs_resources_path")
        ogc_service_url = current_handler.config().get("ogc_service_url")
        ows_prefix = current_handler.config().get("ows_prefix", urlparse(ogc_service_url).path)
        project_ext = current_handler.config().get("qgis_project_extension", ".qgs")

        projects = []
        app.logger.info(resources_path)
        for path in pathlib.Path(resources_path).rglob("*" + project_ext):
            app.logger.info(str(path))
            app.logger.info(path.relative_to(resources_path))
            project = str(path.relative_to(resources_path))[:-4].replace("\\", "/")
            url = ows_prefix.rstrip("/") + "/" + project
            projects.append((url, project))

        # Look in database
        db_url = 'postgresql:///?service=qgisprojects'
        db = db_engine.db_engine(db_url)
        db_projects = []
        sql = sql_text("SELECT schema_name FROM information_schema.schemata")
        try:
            with db.begin() as connection:
                schema_rows = connection.execute(sql).mappings()
            for schema_row in schema_rows:
                try:
                    sql = sql_text('SELECT name FROM "{schema}"."qgis_projects"'.format(schema=schema_row["schema_name"]))
                    with db.begin() as connection:
                        db_project_rows = connection.execute(sql).mappings()
                    for db_project_row in db_project_rows:
                        db_projects.append({"name": db_project_row["name"], "schema": schema_row["schema_name"]})
                except Exception as e:
                    pass
        except Exception as e:
            pass

        for project in db_projects:
            url = ows_prefix.rstrip("/") + "/pg/" + project["schema"] + "/" + project["name"]
            projects.append((url, project["name"] + " (DB)"))

        return sorted(projects)
    
    @staticmethod
    def get_info_templates(app, handler):
        """Return templates file names from INFO_TEMPLATES_PATH"""
        current_handler = handler()
        info_templates_path = current_handler.config().get("info_templates_path")

        info_templates = []
        app.logger.info(info_templates_path)
        for ext in ['*.html']:
            for path in pathlib.Path(info_templates_path).rglob(ext):
                app.logger.info(str(path))
                app.logger.info(path.relative_to(info_templates_path))
                template = str(path.relative_to(info_templates_path))
                if not template.startswith("."):
                    info_templates.append(template)
        return sorted(info_templates)

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
        mapthumbs.append("")
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

    @staticmethod
    def restore_key_order(original, value):
        """Return a value with the keys of its objects in the order of the
        original value, new keys last, e.g. after a form reordered them.

        :param obj original: Original value
        :param obj value: Value with the same structure, possibly reordered
        """
        if isinstance(value, dict):
            original = original if isinstance(original, dict) else {}
            keys = [key for key in original if key in value] + \
                [key for key in value if key not in original]
            return OrderedDict(
                (key, ThemeUtils.restore_key_order(original.get(key), value[key]))
                for key in keys
            )
        if isinstance(value, list):
            return [
                ThemeUtils.restore_key_order(original_item, item)
                for original_item, item in zip(
                    ThemeUtils.original_items(original, value), value
                )
            ]
        return value

    @staticmethod
    def prune_empty(original, value):
        """Return a value without the object entries left empty ("", [] or
        {}), e.g. by a form when all the items of a list are removed, unless
        the original value holds the same empty entry.

        :param obj original: Original value
        :param obj value: Value, e.g. submitted by a form
        """
        def is_empty(item):
            return isinstance(item, (str, list, dict)) and len(item) == 0

        if isinstance(value, dict):
            original = original if isinstance(original, dict) else {}
            result = OrderedDict()
            for key, item in value.items():
                item = ThemeUtils.prune_empty(original.get(key), item)
                if not is_empty(item) or original.get(key, None) == item:
                    result[key] = item
            return result
        if isinstance(value, list):
            return [
                ThemeUtils.prune_empty(original_item, item)
                for original_item, item in zip(
                    ThemeUtils.original_items(original, value), value
                )
            ]
        return value

    @staticmethod
    def original_items(original, items):
        """Return, for each item of a list, the item of the original list it
        most likely comes from, e.g. after a form moved it, or None: an equal
        original item, else the one with the most equal entries, else the one
        at the same position.

        :param obj original: Original list
        :param list items: Items of the edited list
        """
        def similarity(original_item, item):
            if isinstance(original_item, dict) and isinstance(item, dict):
                return sum(
                    1 for key, value in item.items()
                    if key in original_item and original_item[key] == value
                )
            return 0

        original = original if isinstance(original, list) else []
        available = list(range(len(original)))
        matches = [None] * len(items)

        def match(idx, original_idx):
            matches[idx] = original_idx
            available.remove(original_idx)

        for idx, item in enumerate(items):
            equal = [o for o in available if original[o] == item]
            if equal:
                match(idx, equal[0])
        for idx, item in enumerate(items):
            if matches[idx] is None:
                score, best = max(
                    ((similarity(original[o], item), o) for o in available),
                    default=(0, None), key=lambda candidate: candidate[0]
                )
                if score > 0:
                    match(idx, best)
        for idx in range(len(items)):
            if matches[idx] is None and idx in available:
                match(idx, idx)
        return [original[o] if o is not None else None for o in matches]
