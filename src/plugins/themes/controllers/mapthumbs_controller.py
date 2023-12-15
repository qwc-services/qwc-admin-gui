import os

from flask import flash, redirect, render_template, url_for, send_from_directory
from werkzeug.utils import secure_filename
from plugins.themes.forms import MapthumbForm
from plugins.themes.utils import ThemeUtils
from utils import i18n


class MapthumbsController():
    """Controller for theme model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        current_handler = handler()
        qwc2_path = current_handler.config().get("qwc2_path")
        self.mapthumb_path = os.path.join(qwc2_path, "assets/img/mapthumbs/")

        app.add_url_rule(
            '/themes/mapthumbs', 'mapthumbs', self.mapthumbs,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            '/themes/mapthumbs/upload', 'upload_mapthumb', self.upload,
            methods=["GET", "POST"]
        )
        app.add_url_rule(
            '/themes/mapthumbs/delete/<string:image>', 'delete_mapthumb',
            self.delete, methods=["GET", "POST"]
        )
        app.add_url_rule(
            '/themes/mapthumbs/<string:image>', 'load_mapthumb',
            self.load_mapthumb, methods=["GET"]
        )
        self.app = app
        self.handler = handler
        self.template_dir = "plugins/themes/templates"

    def mapthumbs(self):
        """Show mapthumbs."""
        form = MapthumbForm()
        mapthumbs = ThemeUtils.get_mapthumbs(self.app, self.handler)

        return render_template(
            '%s/mapthumbs.html' % self.template_dir, mapthumbs=mapthumbs, title=i18n('plugins.themes.mapthumbs.title'),
            form=form, i18n=i18n
        )

    def upload(self):
        """Upload mapthumb."""
        form = MapthumbForm()
        if form.validate_on_submit():
            f = form.upload.data
            filename = secure_filename(f.filename)
            try:
                f.save(os.path.join(self.mapthumb_path, filename))
                flash(": '{1}'".format(
                    i18n('plugins.themes.mapthumbs.upload_message_success'), filename),
                    'success')
                return redirect(url_for('mapthumbs'))
            except IOError as e:
                self.app.logger.error("Error writing mapthumb: \
                                      {}".format(e.strerror))
                flash(i18n('plugins.themes.mapthumbs.save_message_error'), 'error')
        else:
            # TODO: validation error
            self.app.logger.error("Error uploading mapthumb: \
                                  {}".format(form.errors))
            flash("{0}: {1}".format(
                    i18n('plugins.themes.mapthumbs.upload_message_error'), form.upload.errors[0]), 
                    'error')

        mapthumbs = ThemeUtils.get_mapthumbs(self.app, self.handler)
        return render_template(
            '%s/mapthumbs.html' % self.template_dir, mapthumbs=mapthumbs, title=i18n('plugins.themes.mapthumbs.title'),
            form=form, i18n=i18n
        )

    def delete(self, image=None):
        """Delete mapthumb."""
        try:
            os.remove(os.path.join(self.mapthumb_path, image))
            return redirect(url_for('mapthumbs'))
        except IOError as e:
            self.app.logger.error("Error deleting mapthumb: \
                                  {}".format(e.strerror))
            flash(i18n('plugins.themes.mapthumbs.delete_message_error'), 'error')

        form = MapthumbForm()
        mapthumbs = ThemeUtils.get_mapthumbs(self.app, self.handler)
        return render_template(
            '%s/mapthumbs.html' % self.template_dir, mapthumbs=mapthumbs, title=i18n('plugins.themes.mapthumbs.title'),
            form=form, i18n=i18n
        )

    def load_mapthumb(self, image=None):
        """Load mapthumb from qwc2 assets path."""
        return send_from_directory(self.mapthumb_path, image)
