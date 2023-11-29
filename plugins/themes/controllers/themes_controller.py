from collections import OrderedDict
from flask import abort, flash, redirect, render_template, request, url_for
from wtforms import ValidationError
from sqlalchemy.exc import IntegrityError, InternalError
from urllib.parse import urlparse
from qwc_services_core.config_models import ConfigModels

from plugins.themes.forms import ThemeForm
from plugins.themes.utils import ThemeUtils


class ThemesController:
    """Controller for theme model"""

    def __init__(self, app, handler, themesconfig):
        """Constructor

        :param Flask app: Flask application
        """

        # index
        app.add_url_rule(
            "/themes", "themes", self.index, methods=["GET"]
        )
        # new
        app.add_url_rule(
            "/themes/new", "new_theme", self.new_theme,
            methods=["GET"]
        )
        app.add_url_rule(
            "/themes/new/<int:gid>", "new_theme", self.new_theme,
            methods=["GET"]
        )
        # create
        app.add_url_rule(
            "/themes/create", "create_theme", self.create_theme,
            methods=["POST"]
        )
        app.add_url_rule(
            "/themes/create/<int:gid>", "create_theme", self.create_theme,
            methods=["POST"]
        )
        # edit
        app.add_url_rule(
            "/themes/edit/<int:tid>", "edit_theme", self.edit_theme,
            methods=["GET"]
        )
        app.add_url_rule(
            "/themes/edit/<int:tid>/<int:gid>", "edit_theme", self.edit_theme,
            methods=["GET"]
        )
        # update
        app.add_url_rule(
            "/themes/update/<int:tid>", "update_theme",
            self.update_theme, methods=["POST"]
        )
        app.add_url_rule(
            "/themes/update/<int:tid>/<int:gid>", "update_theme",
            self.update_theme, methods=["POST"]
        )
        # delete
        app.add_url_rule(
            "/themes/delete/<int:tid>", "delete_theme",
            self.delete_theme, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/delete/<int:tid>/<int:gid>", "delete_theme",
            self.delete_theme, methods=["GET"]
        )
        # move
        app.add_url_rule(
            "/themes/move/<string:direction>/<int:tid>",
            "move_theme", self.move_theme, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/move/<string:direction>/<int:tid>/<int:gid>",
            "move_theme", self.move_theme, methods=["GET"]
        )

        # add group
        app.add_url_rule(
            "/themes/add_theme_group", "add_theme_group", self.add_theme_group,
            methods=["GET"]
        )
        # delete group
        app.add_url_rule(
            "/themes/delete_theme_group/<int:gid>", "delete_theme_group",
            self.delete_theme_group, methods=["GET"]
        )
        # update group
        app.add_url_rule(
            "/themes/update_theme_group/<int:gid>", "update_theme_group",
            self.update_theme_group, methods=["POST"]
        )
        # move group
        app.add_url_rule(
            "/themes/move_theme_group/<string:direction>/<int:gid>",
            "move_theme_group", self.move_theme_group, methods=["GET"]
        )

        # save themesconfig
        app.add_url_rule(
            "/themes/save_themesconfig", "save_themesconfig",
            self.save_themesconfig, methods=["GET"]
        )
        # reset themesconfig
        app.add_url_rule(
            "/themes/reset_themesconfig", "reset_themesconfig",
            self.reset_themesconfig, methods=["GET"]
        )
        # move theme to group
        app.add_url_rule(
            "/themes/move_theme_to_group/<string:tid>/<string:old_gid>/<string:gid>/",
            "move_theme_to_group", self.move_theme_to_group, methods=["GET"]
        )

        self.app = app
        self.handler = handler
        self.themesconfig = themesconfig
        self.template_dir = "plugins/themes/templates"

        config_handler = handler()
        db_engine = config_handler.db_engine()
        self.config_models = ConfigModels(db_engine, config_handler.conn_str())
        self.resources = self.config_models.model('resources')

    def index(self):
        """Show theme list."""
        self.themesconfig = ThemeUtils.load_themesconfig(self.app, self.handler)
        themes = OrderedDict()
        themes["items"] = []
        themes["groups"] = []

        for item in self.themesconfig["themes"].get("items", []):
            themes["items"].append({
                "name": item["title"] if "title" in item else item["url"],
                "url": item["url"]
            })

        # TODO: nested groups
        for group in self.themesconfig["themes"].get("groups", []):
            groupEntry = {
                "title": group["title"],
                "items": []
            }
            for item in group["items"]:
                groupEntry["items"].append({
                    "name": item["title"] if "title" in item else item["url"],
                    "url": item["url"]
                })
            themes["groups"].append(groupEntry)

        return render_template(
            "%s/themes.html" % self.template_dir, themes=themes,
            endpoint_suffix="theme", title="Theme configuration"
        )

    def new_theme(self, gid=None):
        """Show new theme form."""
        form = self.create_form()
        template = "%s/theme.html" % self.template_dir
        title = "Create theme"
        action = url_for("create_theme", gid=gid)

        return render_template(
            template, title=title, form=form, action=action, gid=gid,
            method="POST"
        )

    def create_theme(self, gid=None):
        """Create new theme."""
        form = self.create_form()
        if form.validate_on_submit():
            try:
                self.create_or_update_theme(None, form, gid=gid)
                flash("Theme {0} created.".format(form.title.data),
                      "success")
                return redirect(url_for("themes"))
            except ValidationError:
                flash("Could not create theme {0}.".format(
                    form.title.data), "warning")
        else:
            flash("Could not create theme {0}.".format(form.title.data),
                  "warning")

        # show validation errors
        template = "%s/theme.html" % self.template_dir
        title = "Theme configuration"
        action = url_for("create_theme", gid=gid)

        return render_template(
            template, title=title, form=form, action=action, gid=gid,
            method="POST"
        )

    def edit_theme(self, tid, gid=None):
        """Show edit theme form.

        :param int id: Theme ID
        """
        # find theme
        theme = self.find_theme(tid, gid)

        if theme is not None:
            template = "%s/theme.html" % self.template_dir
            form = self.create_form(theme)
            title = "Edit theme"
            action = url_for("update_theme", tid=tid, gid=gid)

            return render_template(
                template, title=title, form=form, action=action, theme=theme,
                tid=tid, gid=gid, method="POST"
            )
        else:
            # theme not found
            abort(404)

    def update_theme(self, tid, gid=None):
        """Update existing theme.

        :param int id: Theme ID
        """
        # find theme
        theme = self.find_theme(tid, gid)

        if theme is not None:
            form = self.create_form()

            if form.validate_on_submit():
                try:
                    # update theme
                    self.create_or_update_theme(theme, form, tid=tid, gid=gid)
                    flash("Theme {0} was updated.".format(
                        form.title.data), "success")
                    return redirect(url_for("themes"))
                except ValidationError:
                    flash("Could not update theme {0}.".format(
                        form.title.data), "warning")
            else:
                flash("Could not update theme {0}.".format(
                      form.title.data), "warning")

            # show validation errors
            template = "%s/theme.html" % self.template_dir
            title = "Update theme"
            action = url_for("update_theme", tid=tid, gid=gid)

            return render_template(
                template, title=title, form=form, action=action, tid=tid,
                gid=gid, method="POST"
            )

        else:
            # theme not found
            abort(404)

    def delete_theme(self, tid, gid=None):
        if gid is None:
            name = self.themesconfig["themes"]["items"][tid]["url"]
            name = name.split("/")[-1]
            self.themesconfig["themes"]["items"].pop(tid)
        else:
            name = self.themesconfig["themes"]["groups"][gid]["items"][tid]["url"]
            name = name.split("/")[-1]
            self.themesconfig["themes"]["groups"][gid]["items"].pop(tid)

        session = self.config_models.session()
        resource = session.query(self.resources).filter_by(
            type="map", name=name
        ).first()

        if resource:
            try:
                session.delete(resource)
                session.commit()
            except InternalError as e:
                flash("InternalError: %s" % e.orig, "error")
            except IntegrityError as e:
                flash("Could not delete resource for map '{0}'!".format(
                    resource.name), "warning")

        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme(self, direction, tid, gid=None):
        if gid is None:
            items = self.themesconfig["themes"]["items"]

            if direction == "up" and tid > 0:
                items[tid-1], items[tid] = items[tid], items[tid-1]

            elif direction == "down" and len(items)-1 > tid:
                items[tid], items[tid+1] = items[tid+1], items[tid]

            self.themesconfig["themes"]["items"] = items

        else:
            items = self.themesconfig["themes"]["groups"][gid]["items"]

            if direction == "up" and tid > 0:
                items[tid-1], items[tid] = items[tid], items[tid-1]

            elif direction == "down" and len(items)-1 > tid:
                items[tid], items[tid+1] = items[tid+1], items[tid]

            self.themesconfig["themes"]["groups"][gid]["items"] = items

        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme_to_group(self, tid, old_gid, gid):
        if old_gid == gid : 
            return redirect(url_for("themes"))
        if old_gid == 'undefined':
            items = self.themesconfig["themes"]["items"]
            self.themesconfig["themes"]["groups"][int(gid)]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["items"].pop(int(tid))
        elif gid == 'undefined':
            items = self.themesconfig["themes"]["groups"][int(old_gid)]["items"]
            self.themesconfig["themes"]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["groups"][int(old_gid)]["items"].pop(int(tid))
        else:
            items = self.themesconfig["themes"]["groups"][int(old_gid)]["items"]
            self.themesconfig["themes"]["groups"][int(gid)]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["groups"][int(old_gid)]["items"].pop(int(tid))
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def add_theme_group(self):
        self.themesconfig["themes"]["groups"] = self.themesconfig["themes"].get("groups", [])
        self.themesconfig["themes"]["groups"].append({
            "title": "new theme group",
            "items": []
        })
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def delete_theme_group(self, gid):
        self.themesconfig["themes"]["groups"].pop(gid)
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def update_theme_group(self, gid):
        self.themesconfig["themes"]["groups"][gid]["title"] = request.form[
            "group_title"]
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme_group(self, gid, direction):
        groups = self.themesconfig["themes"]["groups"]

        if direction == "up" and gid > 1:
            groups[gid-1], groups[gid] = groups[gid], groups[gid-1]

        elif direction == "down" and len(groups) > gid:
            groups[gid], groups[gid-1] = groups[gid-1], groups[gid]

        self.themesconfig["themes"]["groups"] = groups
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def save_themesconfig(self):
        if ThemeUtils.save_themesconfig(self.themesconfig, self.app, self.handler):
            flash("Theme configuration was saved.", "success")
        else:
            flash("Could not save theme configuration.",
                  "error")

        return redirect(url_for("themes"))

    def reset_themesconfig(self):
        self.themesconfig = ThemeUtils.load_themesconfig(self.app, self.handler)
        flash("Theme configuration reloaded from disk.", "warning")
        return redirect(url_for("themes"))

    def find_theme(self, tid, gid=None):
        """Find theme by ID.

        :param int id: Theme ID
        """
        if gid is None:
            for i, item in enumerate(self.themesconfig["themes"]["items"]):
                if i == tid:
                    return item
        else:
            for i, group in enumerate(self.themesconfig["themes"]["groups"]):
                if i == gid:
                    for j, item in enumerate(group["items"]):
                        if j == tid:
                            return item

        return None

    def create_form(self, theme=None):
        """Return form with fields loaded from themesConfig.json.

        :param object theme: Optional theme object
        """
        form = ThemeForm()
        if theme:
            form = ThemeForm(url=theme["url"])

        crslist = ThemeUtils.get_crs(self.app, self.handler)
        defaultSearchProvidersList = ThemeUtils.get_default_search_providers(self.app, self.handler)

        form.url.choices = [("", "---")] + ThemeUtils.get_projects(self.app, self.handler)
        form.thumbnail.choices = ThemeUtils.get_mapthumbs(self.app, self.handler)
        form.format.choices = ThemeUtils.get_format()
        form.mapCrs.choices = crslist
        form.additionalMouseCrs.choices = crslist
        form.searchProviders.choices = defaultSearchProvidersList
        form.backgroundLayersList = self.get_backgroundlayers()

        if form.backgroundLayers.data:
            for i in range(len(form.backgroundLayers.data)):
                form.backgroundLayers[i].layerName.choices = self.get_backgroundlayers()

        if theme is None:
            return form
        else:
            current_handler = self.handler()
            ogc_service_url = current_handler.config().get("ogc_service_url")
            ows_prefix = current_handler.config().get("ows_prefix", urlparse(ogc_service_url).path)
            if "url" in theme:
                if theme["url"].startswith(ows_prefix):
                    form.url.data = theme["url"]
                else:
                    form.url.data = ows_prefix.rstrip("/") + "/" + theme["url"]
            else:
                form.url.data = None
            if "title" in theme:
                form.title.data = theme["title"]
            if "default" in theme:
                form.default.data = theme["default"]
            if "tiled" in theme:
                form.tiled.data = theme["tiled"]
            if "mapTips" in theme:
                form.mapTips.data = theme["mapTips"]
            if "thumbnail" in theme:
                form.thumbnail.data = theme["thumbnail"]
            if "attribution" in theme:
                form.attribution.data = theme["attribution"]
            # TODO: FORM attributionUrl
            # if "attributionUrl" in theme:
            #    form.attribution.data = theme["attributionUrl"]
            if "format" in theme:
                form.format.data = theme["format"]
            if "mapCrs" in theme:
                form.mapCrs.data = theme["mapCrs"]
            if "additionalMouseCrs" in theme:
                form.additionalMouseCrs.data = theme["additionalMouseCrs"]
            if "searchProviders" in theme:
                form.searchProviders.data = theme["searchProviders"]
            if "scales" in theme:
                form.scales.data = ", ".join(map(str, theme["scales"]))
            if "printScales" in theme:
                form.printScales.data = ", ".join(map(str, theme[
                    "printScales"]))
            if "printResolutions" in theme:
                form.printResolutions.data = ", ".join(map(str, theme[
                    "printResolutions"]))
            if "printLabelBlacklist" in theme:
                form.printLabelBlacklist.data = ", ".join(map(str, theme[
                    "printLabelBlacklist"]))
            if "skipEmptyFeatureAttributes" in theme:
                form.skipEmptyFeatureAttributes.data = theme["skipEmptyFeatureAttributes"]
            if "collapseLayerGroupsBelowLevel" in theme:
                form.collapseLayerGroupsBelowLevel.data = theme["collapseLayerGroupsBelowLevel"]

            if "backgroundLayers" in theme:
                for i, layer in enumerate(theme["backgroundLayers"]):
                    data = {
                        "layerName": ("", ""),
                        "printLayer": "",
                        "visibility": False
                    }

                    for l in self.get_backgroundlayers():
                        if layer["name"] == l[0]:
                            data["layerName"] = l

                    if "printLayer" in layer:
                        data["printLayer"] = layer["printLayer"]

                    if "visibility" in layer:
                        data["visibility"] = layer["visibility"]

                    form.backgroundLayers.append_entry(data)
                    form.backgroundLayers[i].layerName.choices = self.get_backgroundlayers()
                    form.backgroundLayers[i].layerName.data = layer["name"]
            qgis_search = [provider for provider in theme["searchProviders"] if "provider" in provider and provider["provider"] == "qgis"]
            if qgis_search :
                for provider in qgis_search:
                    data = {
                        "title": "",
                        "featureCount": "",
                        "resultTitle": "",
                        "searchDescription" : "",
                        "defaultSearch" : False,
                        "group" : "",
                        "expression":"",
                        "fields": ""
                    }
                    if "title" in provider["params"]:
                        data["title"] = provider["params"]["title"]
                    if "featureCount" in provider["params"]:
                        data["featureCount"] = provider["params"]["featureCount"]
                    if "resultTitle" in provider["params"]:
                        data["resultTitle"] = provider["params"]["resultTitle"]
                    if "description"in provider["params"]:
                        data["searchDescription"] = provider["params"]["description"]
                    if "default" in provider["params"]:
                        data["defaultSearch"] = provider["params"]["default"]
                    if "group" in provider["params"]:
                        data["group"] = provider["params"]["group"]
                    if "expression" in provider["params"]:
                        data["expression"] = provider["params"]["expression"]
                    if "fields" in provider["params"]:
                        data["fields"] = provider["params"]["fields"]
                    form.qgisSearchProvider.append_entry(data)

            return form

    def create_or_update_theme(self, theme, form, tid=None, gid=None):
        """Create or update theme records in Themesconfig.

        :param object theme: Optional theme object
                                (None for create)
        :param FlaskForm form: Form for theme
        """
        item = OrderedDict()
        item["url"] = form.url.data

        if form.title.data:
            item["title"] = form.title.data
        else:
            if "title" in item: del item["title"]

        item["default"] = False
        if form.default.data:
            item["default"] = True

        item["tiled"] = False
        if form.tiled.data:
            item["tiled"] = True

        item["mapTips"] = False
        if form.mapTips.data:
            item["mapTips"] = True

        if form.thumbnail.data:
            item["thumbnail"] = form.thumbnail.data

        item["attribution"] = ""
        if form.attribution.data:
            item["attribution"] = form.attribution.data

        # TODO: FORM attributionUrl
        item["attributionUrl"] = ""

        if form.format.data:
            item["format"] = form.format.data
        else:
            if "format" in item: del item["format"]

        if form.mapCrs.data:
            item["mapCrs"] = form.mapCrs.data
        else:
            if item in "mapCrs": del item["mapCrs"]

        if form.additionalMouseCrs.data:
            item["additionalMouseCrs"] = form.additionalMouseCrs.data
        else:
            if "additionalMouseCrs" in item: del item["additionalMouseCrs"]

        item["searchProviders"] = []
        if form.searchProviders.data:
            item["searchProviders"] = form.searchProviders.data
        if form.qgisSearchProvider.data:
            for search in form.qgisSearchProvider.data:
                item["searchProviders"].append({
                    "provider": "qgis",
                    "params": {
                    "title": search["title"],
                    "featureCount": search["featureCount"],
                    "resultTitle": search["resultTitle"],
                    "description": search["searchDescription"],
                    "default": search["defaultSearch"],
                    "group": search["group"],
                    "expression": search["expression"],
                    "fields": search["fields"]
                    }
                })
        if not form.qgisSearchProvider.data and not form.searchProviders.data:
            if "searchProviders" in item: del item["searchProviders"]

        if form.scales.data:
            item["scales"] = list(map(int, form.scales.data.replace(
                " ", "").split(",")))
        else:
            if "scales" in item: del item["scales"]

        if form.printScales.data:
            item["printScales"] = list(map(int, form.printScales.data.replace(
                " ", "").split(",")))
        else:
            if "printScales" in item: del item["printScales"]

        if form.printResolutions.data:
            item["printResolutions"] = list(map(
                int, form.printResolutions.data.replace(" ", "").split(",")))
        else:
            if "printResolutions" in item: del item["printResolutions"]

        if form.printLabelBlacklist.data:
            item["printLabelBlacklist"] = list(map(
                str, form.printLabelBlacklist.data.replace(" ", "").split(",")
            ))
        else:
            if "printLabelBlacklist" in item: del item["printLabelBlacklist"]

        item["skipEmptyFeatureAttributes"] = False
        if form.skipEmptyFeatureAttributes.data:
            item["skipEmptyFeatureAttributes"] = True

        if form.collapseLayerGroupsBelowLevel.data:
            item["collapseLayerGroupsBelowLevel"] = form.collapseLayerGroupsBelowLevel.data
        else:
            if "collapseLayerGroupsBelowLevel" in item: del item["collapseLayerGroupsBelowLevel"]

        item["backgroundLayers"] = []
        if form.backgroundLayers.data:
            for layer in form.backgroundLayers.data:
                item["backgroundLayers"].append({
                    "name": layer["layerName"],
                    "printLayer": layer["printLayer"],
                    "visibility": layer["visibility"]
                })

        new_name = form.url.data.split("/")[-1]
        session = self.config_models.session()

        # edit theme
        if theme:
            if gid is None:
                name = self.themesconfig["themes"]["items"][tid]["url"]
                self.themesconfig["themes"]["items"][tid] = item
            else:
                name = self.themesconfig["themes"]["groups"][gid]["items"][tid]["url"]
                self.themesconfig["themes"]["groups"][gid]["items"][tid] = item

            name = name.split("/")[-1]
            resource = session.query(self.resources).filter_by(name=name).first()
            if resource:
                resource.name = new_name
                try:
                    session.commit()
                except InternalError as e:
                    flash("InternalError: {0}".format(e.orig), "error")
                except IntegrityError as e:
                    flash("Resource for map '{0}' could not be edited!".format(
                        resource.name), "warning")

        # new theme
        else:
            resource = self.resources()
            resource.type = "map"
            resource.name = new_name
            try:
                session.add(resource)
                session.commit()
            except InternalError as e:
                flash("InternalError: {0}".format(e.orig), "error")
            except IntegrityError as e:
                flash("Resource for map '{0}' already exists!".format(
                    resource.name), "warning")

            if gid is None:
                self.themesconfig["themes"]["items"].append(item)
            else:
                self.themesconfig["themes"]["groups"][gid]["items"].append(
                    item)

        self.save_themesconfig()

    def get_backgroundlayers(self):
        layers = []
        for layer in self.themesconfig["themes"]["backgroundLayers"]:
            layers.append((layer["name"], layer["name"]))
        return layers
