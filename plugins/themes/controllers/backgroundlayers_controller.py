import json

from collections import OrderedDict

from flask import flash, redirect, render_template, url_for

from plugins.themes.forms import WMSLayerForm, WMTSLayerForm
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
            "new_backgroundlayer", self.new, methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/create/<string:type>",
            "create_backgroundlayer", self.create, methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/themes/backgroundlayers/delete/<int:index>",
            "delete_backgroundlayer", self.delete, methods=["GET", "POST"]
        )

    def index(self):
        """Show backgroundlayers."""
        layers = []
        for layer in self.themesconfig["themes"]["backgroundLayers"]:
            layers.append(layer)

        return render_template(
            "%s/backgroundlayers.html" % self.template_dir, backgroundlayers=layers,
            title="Background layers"
        )

    def new(self, type="wms"):
        """Show empty backgroundlayer form."""

        if type == "wms":
            form = WMSLayerForm()
            template = "%s/wmslayer.html" % self.template_dir
        elif type == "wmts":
            form = WMTSLayerForm()
            template = "%s/wmtslayer.html" % self.template_dir
        else:
            flash("Type {0} is not supported.".format(type), "warning")
            return redirect(url_for("backgroundlayers"))

        form.thumbnail.choices = list(map(lambda x: (x, x), ThemeUtils.get_mapthumbs(self.app, self.handler)))
        return render_template(
            template, title="Add background layer", type=type, form=form
        )

    def create(self, type="wms"):
        """Add backgroundlayer."""

        if type == "wms":
            form = WMSLayerForm()
            template = "%s/wmslayer.html" % self.template_dir
        elif type == "wmts":
            form = WMTSLayerForm()
            template = "%s/wmtslayer.html" % self.template_dir
        else:
            flash("Type {0} is not supported.".format(type), 'warning')
            return redirect(url_for('backgroundlayers'))

        form.thumbnail.choices = ThemeUtils.get_mapthumbs(self.app, self.handler)

        if form.validate_on_submit():
            backgroundlayer = OrderedDict()
            backgroundlayer["type"] = type
            backgroundlayer["url"] = form.url.data
            backgroundlayer["name"] = form.name.data
            backgroundlayer["title"] = form.title.data
            backgroundlayer["attribution"] = form.attribution.data
            backgroundlayer["thumbnail"] = form.thumbnail.data

            if type == "wms":
                backgroundlayer["format"] = form.format.data
                backgroundlayer["srs"] = form.srs.data
                backgroundlayer["tiled"] = form.tiled.data
                bbox = [float(x) for x in form.bbox.data.split(",")]
                backgroundlayer["boundingBox"] = {
                    "crs": form.srs.data,
                    "bounds": bbox
                }
            elif type == "wmts":
                backgroundlayer["url"] = backgroundlayer["url"].replace(
                    "{Style}", form.style.data)
                # TODO: tileMatrixPrefix ?
                backgroundlayer["tileMatrixPrefix"] = ""
                backgroundlayer["tileMatrixSet"] = form.tileMatrixSet.data
                backgroundlayer["projection"] = form.projection.data
                backgroundlayer["originX"] = float(form.originX.data)
                backgroundlayer["originY"] = float(form.originY.data)
                resolutions = [
                    float(x) for x in form.resolutions.data.split(",")
                ]
                backgroundlayer["resolutions"] = resolutions
                tilesize = [
                    int(x) for x in form.tileSize.data.split(",")
                ]
                backgroundlayer["tileSize"] = tilesize

                if form.with_capabilities.data:
                    backgroundlayer["capabilities"] = json.loads(
                        form.capabilities.data)

            self.themesconfig["themes"]["backgroundLayers"].append(
                backgroundlayer)

            if ThemeUtils.save_themesconfig(self.themesconfig, self.app, self.handler):
                message = "Background layer '{0}' was created.\
                        ".format(backgroundlayer["title"])
                flash(message, "success")
            else:
                message = "Could not save background layer '{0}'.\
                        ".format(backgroundlayer["title"])
                flash(message, "error")

            return redirect(url_for("backgroundlayers"))

        else:
            # TODO: form.errors
            self.app.logger.error("Error adding backroundlayer: \
                                  {}".format(form.errors))
            flash("Background layer could not be created: \
                  {}".format(form.errors), "error")

        return render_template(
            template, title="Add background layer", type=type, form=form
        )

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
