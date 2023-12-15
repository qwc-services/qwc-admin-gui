import os
from zipfile import ZipFile

from flask import flash, redirect, render_template, url_for
from werkzeug.utils import secure_filename

from plugins.themes.forms import LayerForm, ProjectForm, TemplateForm
from plugins.themes.utils import ThemeUtils
from utils import i18n


class FilesController:
    """Controller for theme model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        """

        # index
        app.add_url_rule(
            "/files", "files", self.index, methods=["GET"]
        )
        # Projects
        # upload
        app.add_url_rule(
            '/files/projects/upload', 'upload_project', self.upload_project,
            methods=["GET", "POST"]
        )
        # delete
        app.add_url_rule(
            "/files/projects/delete/<string:projectname>", "delete_project",
            self.delete_project, methods=["GET"]
        )
        # Geospatial layers
        # upload
        app.add_url_rule(
            '/files/layers/upload', 'upload_layer', self.upload_layer,
            methods=["GET", "POST"]
        )
        # delete
        app.add_url_rule(
            "/files/layers/delete/<string:layername>", "delete_layer",
            self.delete_layer, methods=["GET"]
        )
        # Custom templates
        # upload 
        app.add_url_rule(
            '/files/templates/upload', 'upload_template', self.upload_template,
            methods=["GET", "POST"]
        )
        # delete
        app.add_url_rule(
            "/files/templates/delete/<string:templatename>", "delete_template",
            self.delete_template, methods=["GET"]
        )

        self.app = app
        self.handler = handler
        self.template_dir = "plugins/themes/templates"

        config_handler = handler()
        self.resources_path = config_handler.config().get("qgs_resources_path")
        self.info_templates_path = config_handler.config().get("info_templates_path")
          
    def index(self):
        """Show project list."""
        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)

        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates= templates,
            form_project=form_project, form_layer=form_layer, form_template = form_template,
            title=i18n('plugins.themes.files.title'), i18n=i18n
        )

    def upload_project(self):
        """Upload QGIS project."""
        form = ProjectForm()
        if form.validate_on_submit():
            f = form.upload.data
            filename = secure_filename(f.filename)
            try:
                f.save(os.path.join(self.resources_path, filename))
                flash("{0}: '{1}'.".format(
                    i18n('plugins.themes.files.project_upload_message_success'), filename),
                      'success')
                return redirect(url_for('files'))
            except IOError as e:
                self.app.logger.error("Error writing project to {}: {}".format(
                    self.resources_path, e.strerror))
                flash(i18n('plugins.themes.files.project_save_message_error'), 'error')
        else:
            # TODO: validation error
            self.app.logger.error("Error uploading project: \
                                  {}".format(form.errors))
            flash("{0}: {1}.".format(
                    i18n('plugins.themes.files.project_upload_message_error'), form.upload.errors[0]), 'error')
        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates=templates,
            form_project=form_project, form_layer=form_layer, form_template=form_template,
            title=i18n('plugins.themes.files.title'), i18n=i18n
        )

    def delete_project(self, projectname):
        """Delete QGIS project."""
        try:
            os.remove(os.path.join(self.resources_path, projectname + '.qgs'))
            return redirect(url_for('files'))
        except IOError as e:
            self.app.logger.error("Error deleting project: \
                                  {}".format(e.strerror))
            flash(i18n('plugins.themes.files.project_delete_message_error'), 'error')

        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates=templates,
            form_project=form_project, form_layer=form_layer, form_template=form_template,
            title=i18n('plugins.themes.files.title'), i18n=i18n
        )

    def upload_layer(self):
        """Upload layer file."""
        form = LayerForm()
        if form.validate_on_submit():
            f = form.upload.data
            filename = secure_filename(f.filename)
            try:
                f.save(os.path.join(self.resources_path, filename))
                is_zip_file = os.path.splitext(filename)[1] == '.zip'
                if (is_zip_file):
                    self.app.logger.info(f"Extracting files from file {filename}...")
                    extensions = ('shp', 'shx', 'dbf', 'prj', 'cpg', 'geojson', 'kml', 'gpkg')
                    with ZipFile(os.path.join(self.resources_path, filename), 'r') as zip:
                        for file in zip.namelist():
                            if file.endswith(extensions):
                                self.app.logger.info(f"Extracting {file} from {filename}")
                                zip.extract(file, os.path.join(self.resources_path))
                    os.remove(os.path.join(self.resources_path, filename))
                flash("{0} {2}: {1}".format(
                    i18n('plugins.themes.files.file_upload_message_success'), filename, 
                    i18n('plugins.themes.files.file_extract_message_success') if is_zip_file else ""),
                      'success')
                return redirect(url_for('files'))
            except IOError as e:
                self.app.logger.error("Error writing file: \
                                      {}".format(e.strerror))
                flash(i18n('plugins.themes.files.file_save_message_error'), 'error')
        else:
            # TODO: validation error
            self.app.logger.error("Error uploading file: \
                                  {}".format(form.errors))
            flash("{0}: {1}".format(
                    i18n('plugins.themes.files.file_upload_message_error'), form.upload.errors[0]), 'error')
        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates=templates,
            form_project=form_project, form_layer=form_layer, form_template=form_template,
            title=i18n('plugins.themes.files.title'), i18n=i18n
        )

    def delete_layer(self, layername):
        """Delete layer file."""
        try:
            is_shp_file = os.path.splitext(layername)[1] == '.shp'
            if is_shp_file:
                # Also remove all extensions that could be with SHP layer
                extensions = ['.shx', '.dbf', '.prj', '.cpg']
                name = os.path.splitext(layername)[0]
                [os.remove(os.path.join(self.resources_path, name + ext)) for ext in extensions if os.path.exists(os.path.join(self.resources_path, name + ext))]
            os.remove(os.path.join(self.resources_path, layername))
            return redirect(url_for('files'))
        except IOError as e:
            self.app.logger.error("Error deleting file: \
                                  {}".format(e.strerror))
            flash(i18n('plugins.themes.files.file_delete_message_error'), 'error')

        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates=templates,
            form_project=form_project, form_layer=form_layer, form_template=form_template,
            title=i18n('plugins.themes.files.title'), i18n=i18n
        )

    def upload_template(self):
        """Upload HTML template."""
        form = TemplateForm()
        if form.validate_on_submit():
            f = form.upload.data
            filename = secure_filename(f.filename)
            try:
                f.save(os.path.join(self.info_templates_path, filename))
                flash("{1}: '{0}'".format(filename, i18n('plugins.themes.files.template_upload_message_success')),
                      'success')
                return redirect(url_for('files'))
            except IOError as e:
                self.app.logger.error("Error writing template to {}: {}".format(
                    self.info_templates_path, e.strerror))
                flash(i18n('plugins.themes.files.template_save_message_error'), 'error')
        else:
            # TODO: validation error
            self.app.logger.error("Error uploading template: \
                                  {}".format(form.errors))
            flash("{1}: \
                  {0}".format(form.upload.errors[0], i18n('plugins.themes.files.template_upload_message_error')), 'error')
        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates=templates,
            form_project=form_project, form_layer=form_layer, form_template = form_template,
            title=i18n('plugins.themes.files.template_upload_title')
        )
  
    def delete_template(self, templatename):
        """Delete template file."""
        try:
            os.remove(os.path.join(self.info_templates_path, templatename))
            return redirect(url_for('files'))
        except IOError as e:
            self.app.logger.error("Error deleting file: \
                                  {}".format(e.strerror))
            flash(i18n('plugins.themes.files.template_delete_message_error'), 'error')

        form_project = ProjectForm()
        form_layer = LayerForm()
        form_template = TemplateForm()
        projects = ThemeUtils.get_projects(self.app, self.handler)
        layers = ThemeUtils.get_layers(self.app, self.handler)
        templates = ThemeUtils.get_info_templates(self.app, self.handler)
        return render_template(
            "%s/files.html" % self.template_dir,
            projects=projects, layers=layers, templates = templates,
            form_project=form_project, form_layer=form_layer, form_template=form_template,
            title=i18n('plugins.themes.files.template_delete_title')
        )
