import os

from flask import flash, render_template, redirect, url_for, abort
from wtforms import ValidationError
from collections import OrderedDict
from plugins.themes.forms import InfoTemplateForm
from plugins.themes.utils import ThemeUtils
from qwc_services_core.config_models import ConfigModels
from sqlalchemy.exc import IntegrityError, InternalError

class InfoTemplatesController():
    """Controller for HTML template model"""

    def __init__(self, app, handler, featureInfoconfig):
        """Constructor
        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        current_handler = handler()
        qwc2_path = current_handler.config().get("qwc2_path")
        self.mapthumb_path = os.path.join(qwc2_path, "assets/img/mapthumbs/")
        self.featureInfoconfig = featureInfoconfig
        self.info_templates_path = current_handler.config().get("info_templates_path")
        self.ogc_service_url = current_handler.config().get("ogc_service_url")
        self.default_qgis_server_url = current_handler.config().get("default_qgis_server_url")
        db_engine = current_handler.db_engine()
        self.config_models = ConfigModels(db_engine, current_handler.conn_str())
        self.resources = self.config_models.model('resources')

        app.add_url_rule(
            '/themes/info_templates', 'info_templates', self.info_templates,
            methods=["GET"]
        )
        app.add_url_rule(
            '/themes/info_template', 'info_template', self.info_template,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            '/themes/info_template/edit/<int:gid>/<int:tid>', 'edit_info_template', self.edit_info_template,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            '/themes/info_template/delete/<int:gid>/<int:tid>', 'delete_info_template', self.delete_info_template,
            methods=["GET", "POST"]
        )

        self.app = app
        self.handler = handler
        self.template_dir = "plugins/themes/templates"

    def info_template(self):
        """Create info_template."""
        form = InfoTemplateForm()
        form.url.choices = [("", "---")] + ThemeUtils.get_projects(self.app, self.handler)
        form.template.choices = [("---")] + ThemeUtils.get_info_templates(self.app, self.handler)
        if form.validate_on_submit():
            try:
                self.create_or_update_info_templates(form)
            except ValidationError:
                flash("Could not create template.", "warning")
            return redirect(url_for("info_templates"))

        return render_template(
            '%s/info_template.html' % self.template_dir, title='Add template',
            form=form
        )

    def info_templates(self):
        """Show info_templates."""
        items = []
        for item in self.featureInfoconfig["wms_services"]:
            items.append(item)

        return render_template(
            '%s/info_templates.html' % self.template_dir, title='HTML templates', items=items
        )

    def create_or_update_info_templates(self, info_template, tid=None, gid=None):
        """Create or update HTML templates records in Tenantconfig."""
        ogc_service_url = self.ogc_service_url.rstrip("/") + "/"
        info_templates_path = self.info_templates_path.rstrip("/") + "/"
        default_qgis_server_url = self.default_qgis_server_url.rstrip("/") + "/"
        project_name = info_template.url.data.replace((ogc_service_url), '')
        new_layer = OrderedDict({
            "name": info_template.layer.data,
            "info_template": OrderedDict({
                "type": "wms",
                "wms_url": f"{default_qgis_server_url}{project_name}",
                "template_path": f"{info_templates_path}{info_template.template.data}"
            })
        })
        existing_item = next((item for item in self.featureInfoconfig["wms_services"] if item["name"] == project_name), None)
        if existing_item :
            layers = existing_item["root_layer"]["layers"]
            existing_layer = next((layer for layer in layers if layer["name"] == new_layer["name"]), None)
            if existing_layer and tid != None:
                self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"][tid]["info_template"]= new_layer["info_template"]
            elif existing_layer and tid == None: 
                    flash("A template already exist for this layer", "warning")
                    return redirect(url_for("info_templates"))
            else:
                layers.append(new_layer)
                resource = self.resources()
                resource.type = "feature_info_layer"
                resource.name = new_layer["name"]
                session = self.config_models.session()
                parent_ressource = session.query(self.resources).filter_by(
                    type="feature_info_service", name=project_name
                ).first()
                resource.parent_id = parent_ressource.id
                try:
                    session.add(resource)
                    session.commit()
                except InternalError as e:
                    flash("InternalError: {0}".format(e.orig), "error")
                except IntegrityError as e:
                    flash("Resource for featureInfoLayer '{0}' already exists!".format(
                        resource.name), "warning")
        else:
            item = OrderedDict()
            item["name"] = project_name
            item["root_layer"] = OrderedDict()
            item["root_layer"]["name"] = project_name
            item["root_layer"]["layers"] = [new_layer]
            self.featureInfoconfig["wms_services"].append(item)
            session = self.config_models.session()
            resource = self.resources()
            resource.type = "feature_info_service"
            resource.name = project_name
            try:
                session.add(resource)
                session.commit()
            except InternalError as e:
                flash("InternalError: {0}".format(e.orig), "error")
            except IntegrityError as e:
                flash("Resource for featureInfoService '{0}' already exists!".format(
                    resource.name), "warning")
            resource = self.resources()
            resource.type = "feature_info_layer"
            resource.name = new_layer["name"]
            session = self.config_models.session()
            parent_ressource = session.query(self.resources).filter_by(
                type="feature_info_service", name=project_name
            ).first()
            resource.parent_id = parent_ressource.id
            try:
                session.add(resource)
                session.commit()
            except InternalError as e:
                flash("InternalError: {0}".format(e.orig), "error")
            except IntegrityError as e:
                flash("Resource for featureInfoLayer '{0}' already exists!".format(
                    resource.name), "warning")

        self.save_featureinfo_config()

    def edit_info_template(self, gid, tid):
        """Edit info_template."""
        form = InfoTemplateForm()
        form.url.choices = [("", "---")] + ThemeUtils.get_projects(self.app, self.handler)
        form.template.choices = [("---")] + ThemeUtils.get_info_templates(self.app, self.handler)
        try: 
            form.url.data = self.ogc_service_url.rstrip("/") + "/" + self.featureInfoconfig["wms_services"][gid]["name"]
            form.layer.data = self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"][tid]["name"]
            if form.validate_on_submit():
                try:
                    self.create_or_update_info_templates(form, tid, gid)
                except ValidationError:
                    flash("Could not update template.", "warning")
                return redirect(url_for("info_templates"))
            form.template.data = self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"][tid]["info_template"]["template_path"].split("/")[-1]
            
            return render_template(
                '%s/info_template.html' % self.template_dir, title='Edit template', is_disabled = True,
                form=form
            )
        except Exception : 
            abort(404)

    def delete_info_template(self, gid, tid):
        """Delete info_template."""
        session = self.config_models.session()
        resource = session.query(self.resources).filter_by(
            type="feature_info_layer", name=self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"][tid]["name"]
        ).first()
        if resource:
            try:
                session.delete(resource)
                session.commit()
            except InternalError as e:
                flash("InternalError: %s" % e.orig, "error")
            except IntegrityError as e:
                flash("Could not delete resource for template '{0}'!".format(
                    resource.name), "warning")
        self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"].pop(tid)
        if not self.featureInfoconfig["wms_services"][gid]["root_layer"]["layers"] :
            session = self.config_models.session()
            resource = session.query(self.resources).filter_by(
                type="feature_info_service", name=self.featureInfoconfig["wms_services"][gid]["name"]
            ).first()
            if resource:
                try:
                    session.delete(resource)
                    session.commit()
                except InternalError as e:
                    flash("InternalError: %s" % e.orig, "error")
                except IntegrityError as e:
                    flash("Could not delete resource for template '{0}'!".format(
                        resource.name), "warning")
            self.featureInfoconfig["wms_services"].pop(gid)
        self.save_featureinfo_config()

        return redirect(url_for("info_templates"))

    def save_featureinfo_config(self):
        if ThemeUtils.save_featureinfo_config(self.featureInfoconfig, self.app, self.handler):
            flash("Template configuration was saved.", "success")
        else:
            flash("Could not save template configuration.",
                  "error")