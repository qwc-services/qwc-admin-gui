import configparser
import os

from flask import flash, redirect, render_template, url_for
from sqlalchemy.exc import IntegrityError, InternalError
from sqlalchemy.ext.automap import automap_base
from qwc_services_core.config_models import ConfigModels

from plugins.alkis.forms import ALKISForm


class ALKISController():
    """Controller for theme model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        """
        app.add_url_rule(
            "/alkis", "alkis", self.index, methods=["GET"]
        )
        app.add_url_rule(
            "/alkis/new", "new_alkis", self.new, methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/alkis/create", "create_alkis", self.create,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/alkis/edit/<int:index>", "edit_alkis", self.edit,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/alkis/update", "update_alkis", self.update,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/alkis/update/<int:index>", "update_alkis", self.update,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            "/alkis/delete/<int:index>", "delete_alkis", self.delete,
            methods=["GET", "POST"]
        )
        self.app = app
        self.handler = handler
        config_handler = handler()
        db_engine = config_handler.db_engine()
        self.config_models = ConfigModels(db_engine, config_handler.conn_str(), ["alkis"])
        self.resources = self.config_models.model('resources')
        self.alkis = self.config_models.model('alkis')

        self.plugindir = "plugins/alkis/templates"

    def index(self):
        """Show alkis configs."""
        session = self.config_models.session()
        resources = session.query(self.alkis).order_by(self.alkis.name)
        session.close()
        return render_template(
            "%s/index.html" % self.plugindir, resources=resources, title="ALKIS"
        )

    def new(self):
        """Show empty alkis form."""
        form = ALKISForm()
        form.pgservice.choices = self.get_pgservices()
        form.header_template.choices = self.get_templates()
        return render_template(
            "%s/form.html" % self.plugindir, title="neue ALKIS Konfiguration",
            action=url_for("create_alkis"), form=form
        )

    def create(self):
        """Create alkis config."""
        form = ALKISForm()
        form.pgservice.choices = self.get_pgservices()
        form.header_template.choices = self.get_templates()
        session = self.config_models.session()
        if form.validate_on_submit():
            alkis = self.alkis()
            alkis.name = form.name.data
            alkis.pgservice = ','.join(form.pgservice.data)
            alkis.enable_alkis = form.enable_alkis.data
            alkis.enable_owner = form.enable_owner.data
            alkis.header_template = form.header_template.data
            resource = self.resources()
            resource.type = "alkis"
            resource.name = alkis.name
            try:
                session.add(alkis)
                session.add(resource)
                session.commit()
                flash("ALKIS Konfiguration hinzugefügt.")
                return redirect(url_for("alkis"))
            except InternalError as e:
                flash("InternalError: %s" % e.orig, "error")
            except IntegrityError as e:
                flash("Name existiert bereits! Bitte einen anderen Namen \
                      verwenden.", "error")

        else:
            flash("ALKIS Konfuration konnte nicht erzeugt werden.", "error")

        session.close()
        return render_template(
            "%s/form.html" % self.plugindir, title="neue ALKIS Konfiguration",
            action=url_for("create_alkis"), form=form
        )

    def edit(self, index=None):
        """Edit alkis config."""
        session = self.config_models.session()
        alkis = session.query(self.alkis).filter_by(id=index).first()
        form = ALKISForm(
            pgservice=[alkis.pgservice],
            name=alkis.name,
            enable_alkis=alkis.enable_alkis,
            enable_owner=alkis.enable_owner,
            header_template=alkis.header_template
        )
        form.pgservice.choices = self.get_pgservices()
        form.header_template.choices = self.get_templates()
        session.close()
        return render_template(
            "%s/form.html" % self.plugindir, title="ALKIS Konfiguration bearbeiten",
            action=url_for("update_alkis") + "/" + str(index), form=form
        )

    def update(self, index=None):
        """Update alkis config."""
        form = ALKISForm()
        form.pgservice.choices = self.get_pgservices()
        form.header_template.choices = self.get_templates()
        session = self.config_models.session()
        if form.validate_on_submit():
            alkis = session.query(self.alkis).filter_by(id=index).first()
            resource = session.query(self.resources).filter_by(
                type="alkis", name=alkis.name
            ).first()
            alkis.name = form.name.data
            alkis.pgservice = ','.join(form.pgservice.data)
            alkis.enable_alkis = form.enable_alkis.data
            alkis.enable_owner = form.enable_owner.data
            alkis.header_template = form.header_template.data
            resource.type = "alkis"
            resource.name = alkis.name
            try:
                session.commit()
                flash("ALKIS Konfiguration aktualisiert.")
                return redirect(url_for("alkis"))
            except InternalError as e:
                flash('InternalError: %s' % e.orig, 'error')
            except IntegrityError as e:
                flash('IntegrityError: %s' % e.orig, 'error')

        else:
            flash("ALKIS Konfuration konnte nicht erzeugt werden.", "error")

        session.close()
        return render_template(
            "%s/form.html" % self.plugindir, title="ALKIS Konfiguration bearbeiten",
            action=url_for("update_alkis") + "/" + str(index), form=form
        )

    def delete(self, index=None):
        """Delete alkis config."""
        session = self.config_models.session()
        alkis = session.query(self.alkis).filter_by(id=index).first()
        resource = session.query(self.resources).filter_by(
            type="alkis", name=alkis.name
        ).first()
        try:
            # delete and commit
            session.delete(alkis)
            session.delete(resource)
            session.commit()
            flash("ALKIS Konfiguration wurde gelöscht.", "success")
        except InternalError as e:
            flash("InternalError: %s" % e.orig, "error")
        except IntegrityError as e:
            flash("IntegrityError: %s" % e.orig, "error")

        session.close()
        return redirect(url_for("alkis"))

    def get_pgservices(self):
        """ Returns alkis pgservices."""

        candidates = []
        PGSERVICEFILE = os.environ.get('PGSERVICEFILE')
        if PGSERVICEFILE:
            candidates = [PGSERVICEFILE]

        candidates.append(os.path.expanduser("~/.pg_service.conf"))

        PGSYSCONFDIR = os.environ.get('PGSYSCONFDIR')
        if PGSYSCONFDIR:
            candidates.append(os.path.join(PGSYSCONFDIR, 'pg_service.conf'))

        candidates.append(os.path.join("/etc", 'pg_service.conf'))
        candidates.append(os.path.join("/etc/postgresql-common", 'pg_service.conf'))
        candidates.append(os.path.join("/etc/sysconfig/pgsql", 'pg_service.conf'))

        config = configparser.ConfigParser()
        for candidate in candidates:
            if os.path.exists(candidate):
                config.read(candidate)
                break

        services = []
        for section in config.sections():
            if section.startswith("alkis") or section.endswith("alkis"):
                services.append((section, section))
        return services

    def get_templates(self):
        """ Returns header templates. """
        current_handler = self.handler()
        qwc2_path = current_handler.config().get("qwc2_path")
        template_path = qwc2_path + "assets/templates/alkis"
        templates = []
        for tmpl in os.listdir(template_path):
            if tmpl.startswith("header"):
                templates.append((tmpl, tmpl))
        return sorted(templates)
