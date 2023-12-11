import json

from collections import OrderedDict

from flask import flash, redirect, render_template, url_for
from wtforms import ValidationError

from plugins.themes.forms import WMSLayerForm, WMTSLayerForm, XYZLayerForm
from plugins.themes.utils import ThemeUtils


class BackgroundLayersController():
    """Controller for theme model"""

    def __init__(self, app, handler, themesconfig):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        :param themesconfig: Themes config
        """

        self.themesconfig = themesconfig
        self.app = app
        self.handler = handler
        self.template_dir = "plugins/themes/templates"

        app.add_url_rule(
            "/themes/backgroundlayers", "backgroundlayers", self.index,
            methods=["GET"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/new/<string:type>",
            "new_backgroundlayer", self.new, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/create/<string:type>",
            "create_backgroundlayer", self.create, methods=["POST"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/edit/<int:index>",
            "edit_backgroundlayer", self.edit, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/update/<int:index>",
            "update_backgroundlayer", self.update, methods=["POST"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/delete/<int:index>",
            "delete_backgroundlayer", self.delete, methods=["GET", "POST"]
        )

    def index(self):
        """Show backgroundlayers."""
        self.themesconfig = ThemeUtils.load_themesconfig(self.app, self.handler)
        layers = []
        for layer in self.themesconfig["themes"]["backgroundLayers"]:
            layers.append(layer)

        return render_template(
            "%s/backgroundlayers.html" % self.template_dir, backgroundlayers=layers,
            title="Background layers"
        )

    def new(self, type="wms"):
        """Show empty backgroundlayer form."""

        form = self.create_form(type, None)
        if type == "wms":
            template = "%s/wmslayer.html" % self.template_dir
        elif type == "wmts":
            template = "%s/wmtslayer.html" % self.template_dir
        elif type == "xyz":
            form.crs.choices = ThemeUtils.get_crs(self.app, self.handler)
            template = "%s/xyzlayer.html" % self.template_dir
        action = url_for("create_backgroundlayer", type=type)

        form.thumbnail.choices = list(map(lambda x: (x, x), ThemeUtils.get_mapthumbs(self.app, self.handler)))
        return render_template(
            template, title="Add background layer", action=action, type=type, form=form
        )

    def create(self, type="wms"):
        """Add backgroundlayer."""

        form = self.create_form(type, None)

        form.thumbnail.choices = ThemeUtils.get_mapthumbs(self.app, self.handler)
        if type == "xyz":
            form.crs.choices = ThemeUtils.get_crs(self.app, self.handler)

        if form.validate_on_submit():
            try:
                self.create_or_update_backgroundlayer(type, form)
                return redirect(url_for("backgroundlayers"))
            except ValidationError:
                flash("Could not create background layer {0}.".format(
                    form.title.data), "warning")
        else:
            # TODO: form.errors
            flash("Could not create background layer {0}. {1}".format(form.title.data, form.errors),
                  "error")
            self.app.logger.error("Error adding backgroundlayer: \
                                  {}".format(form.errors))

        # show validation errors
        if type == "wms":
            template = "%s/wmslayer.html" % self.template_dir
        elif type == "wmts":
            template = "%s/wmtslayer.html" % self.template_dir
        elif type == "xyz":
            template = "%s/xyzlayer.html" % self.template_dir
        action = url_for("create_backgroundlayer", type=type)

        return render_template(
            template, title="Add background layer", action=action, type=type, form=form,
            method="POST"
        )

    def edit(self, index=None):
        """Show edit backgroundlayer form.

        :param int index: Backgroundlayer ID
        """
        # find background layer
        backgroundlayer = self.find_backgroundlayer(index)

        if backgroundlayer is not None:
            # show validation errors
            if backgroundlayer["type"] == "wms":
                template = "%s/wmslayer.html" % self.template_dir
            elif backgroundlayer["type"] == "wmts":
                template = "%s/wmtslayer.html" % self.template_dir
            elif backgroundlayer["type"] == "xyz":
                template = "%s/xyzlayer.html" % self.template_dir
            form = self.create_form(type=backgroundlayer["type"], backgroundlayer=backgroundlayer)
            title = "Edit background layer"
            action = url_for("update_backgroundlayer", index=index)

            return render_template(
                template, title=title, type=backgroundlayer["type"], form=form, action=action,
                index=index, method="POST"
            )
        else:
            # theme not found
            abort(404)

    def update(self, index=None):
        """Update existing background layer.

        :param int index: Backgroundlayer ID
        """
        # find backgroundlayer
        backgroundlayer = self.find_backgroundlayer(index)

        if backgroundlayer is not None:
            form = self.create_form(type=backgroundlayer["type"], backgroundlayer=None)

            if form.validate_on_submit():
                try:
                    # update background layer
                    self.create_or_update_backgroundlayer(backgroundlayer["type"], form, index=index)
                    return redirect(url_for("backgroundlayers"))
                except ValidationError:
                    flash("Could not update background layer {0}.".format(
                        form.title.data), "warning")
            else:
                flash("Could not update background layer {0}. {1}".format(
                      form.title.data, form.errors), "warning")
            
            # show validation errors
            if backgroundlayer["type"] == "wms":
                template = "%s/wmslayer.html" % self.template_dir
            elif backgroundlayer["type"] == "wmts":
                template = "%s/wmtslayer.html" % self.template_dir
            elif backgroundlayer["type"] == "xyz":
                template = "%s/xyzlayer.html" % self.template_dir
            title = "Edit background layer"
            action = url_for("update_backgroundlayer", index=index)

            return render_template(
                template, title=title, type=backgroundlayer["type"], form=form, action=action,
                method="POST"
            )
        else:
            # backgroundlayer not found
            abort(404)

    def delete(self, index=None):
        """Delete backgroundlayer."""
        count = len(self.themesconfig["themes"]["backgroundLayers"])
        if index is None or index > count - 1:
            self.app.logger.error("Error saving backgroundLayer: index not defined \
                    or out of range. index={0} count={1}".format(index, count))
            flash("Could not delete background layer.", "error")
        else:
            self.themesconfig["themes"]["backgroundLayers"].pop(index)
            if ThemeUtils.save_themesconfig(self.themesconfig, self.app, self.handler):
                flash("Background layer deleted.", "success")
            else:
                flash("Could not delete background layer.", "error")
        return redirect(url_for("backgroundlayers"))

    def find_backgroundlayer(self, index=None):
        """Find backgroundlayer by ID.

        :param int index: Backgroundlayer ID
        """
        for i, item in enumerate(self.themesconfig["themes"]["backgroundLayers"]):
            if i == index:
                return item

        return None

    def create_form(self, type="wms", backgroundlayer=None):
        """Return form with fields loaded from themesConfig.json.

        :param object backgroundlayer: Optional backgroundlayer object
        """
        if type == "wms":
            form = WMSLayerForm()
            # template = "%s/wmslayer.html" % self.template_dir
        elif type == "wmts":
            form = WMTSLayerForm()
            # template = "%s/wmtslayer.html" % self.template_dir
        elif type == "xyz" : 
            form = XYZLayerForm()
            form.crs.choices = ThemeUtils.get_crs(self.app, self.handler)
        else:
            flash("Type {0} is not supported.".format(type), 'warning')
            return redirect(url_for('backgroundlayers'))

        form.thumbnail.choices = ThemeUtils.get_mapthumbs(self.app, self.handler)

        if backgroundlayer is None:
            return form
        else:
            if "url" in backgroundlayer:
                form.url.data = backgroundlayer["url"]

            if "title" in backgroundlayer:
                form.title.data = backgroundlayer["title"]

            if "name" in backgroundlayer:
                form.name.data = backgroundlayer["name"]

            if "attribution" in backgroundlayer:
                form.attribution.data = backgroundlayer["attribution"]

            if "thumbnail" in backgroundlayer:
                form.thumbnail.data = backgroundlayer["thumbnail"]

            if "crs" in backgroundlayer:
                form.crs.data = backgroundlayer["crs"]

            if type == "wms":
                if "format" in backgroundlayer:
                    form.format.data = backgroundlayer["format"]
                if "srs" in backgroundlayer:
                    form.srs.data = backgroundlayer["srs"]
                if "tiled" in backgroundlayer:
                    form.tiled.data = backgroundlayer["tiled"]
                if "boundingBox" in backgroundlayer:
                    bbox = ",".join([str(x) for x in backgroundlayer["boundingBox"]["bounds"]])
                    form.bbox.data = bbox
            elif type == "wmts":
                # if form.style.data:
                #     item["url"] = item["url"].replace(
                #         "{Style}", form.style.data)
                # TODO: tileMatrixPrefix ?
                # item["tileMatrixPrefix"] = ""
                if "tileMatrixSet" in backgroundlayer:
                    form.tileMatrixSet.data = backgroundlayer["tileMatrixSet"]
                if "projection" in backgroundlayer:
                    form.projection.data = backgroundlayer["projection"]
                if "originX" in backgroundlayer:
                    form.originX.data = str(backgroundlayer["originX"])
                if "originY" in backgroundlayer:
                    form.originY.data = str(backgroundlayer["originY"])
                if "resolutions" in backgroundlayer:
                    resolutions = ",".join([str(x) for x in backgroundlayer["resolutions"]])
                    form.resolutions.data = resolutions
                if "tileSize" in backgroundlayer:
                    tileSize = ",".join([str(x) for x in backgroundlayer["tileSize"]])                    
                    form.tileSize.data = tileSize
                if "capabilities" in backgroundlayer:
                    form.with_capabilities.data = json.dumps(backgroundlayer["capabilities"])

        return form

    def create_or_update_backgroundlayer(self, type, form, index=None):
        """Create or update backgroundlayer records in Themesconfig.

        :param object backgroundlayer: Optional backgroundlayer object
                                (None for create)
        :param str type: Optional backgroundlayer object
                                (None for create)
        :param FlaskForm form: Form for backgroundlayer
        """
        item = OrderedDict()
        item["type"] = type
        item["url"] = form.url.data

        if form.title.data:
            item["title"] = form.title.data
        else:
            if "title" in item: del item["title"]

        if form.name.data:
            item["name"] = form.name.data
        else:
            if "name" in item: del item["name"]

        item["attribution"] = ""
        if form.attribution.data:
            item["attribution"] = form.attribution.data

        if form.thumbnail.data:
            item["thumbnail"] = form.thumbnail.data

        if type == "wms":
            if form.format.data:
                item["format"] = form.format.data
            if form.srs.data:
                item["srs"] = form.srs.data
            if form.tiled.data:
                item["tiled"] = form.tiled.data
            if form.bbox.data:
                bbox = [float(x) for x in form.bbox.data.split(",")]
                item["boundingBox"] = {
                    "crs": form.srs.data,
                    "bounds": bbox
                }
        elif type == "wmts":
            if form.style.data:
                item["url"] = item["url"].replace(
                    "{Style}", form.style.data)
            # TODO: tileMatrixPrefix ?
            item["tileMatrixPrefix"] = ""
            if form.tileMatrixSet.data:
                item["tileMatrixSet"] = form.tileMatrixSet.data
            if form.projection.data:
                item["projection"] = form.projection.data
            if form.format.data:
                item["format"] = form.format.data
            if form.requestEncoding.data:
                item["requestEncoding"] = form.requestEncoding.data
            if form.style.data:
                item["style"] = form.style.data
            if form.originX.data:
                item["originX"] = float(form.originX.data)
            if form.originY.data:
                item["originY"] = float(form.originY.data)
            if form.resolutions.data:
                resolutions = [
                    float(x) for x in form.resolutions.data.split(",")
                ]
                item["resolutions"] = resolutions
            if form.tileSize.data:
                tilesize = [
                    int(x) for x in form.tileSize.data.split(",")
                ]
                item["tileSize"] = tilesize
            if form.with_capabilities.data:
                item["capabilities"] = json.loads(
                    form.capabilities.data)
        elif type == "xyz":
            if form.crs.data:
                item["crs"] = form.crs.data

        # edit background layer
        if index:
            action_name = "updated"
            self.themesconfig["themes"]["backgroundLayers"][index] = item
        # new background layer
        else:
            action_name = "created"
            self.themesconfig["themes"]["backgroundLayers"].append(
                item)

        if ThemeUtils.save_themesconfig(self.themesconfig, self.app, self.handler):
            message = "Background layer '{0}' {1}.\
                    ".format(item.get("title", ""), action_name)
            flash(message, "success")
        else:
            message = "Could not save background layer '{0}'.\
                    ".format(item["title"])
            flash(message, "error")
