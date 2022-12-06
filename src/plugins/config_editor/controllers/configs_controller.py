from collections import OrderedDict
import datetime
import os
from shutil import copyfile

from flask import flash, json, redirect, render_template, request, url_for
from markupsafe import Markup
from json.decoder import JSONDecodeError

from utils import i18n


class ConfigsController():
    """Controller for config editors"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param TenantConfigHandler handler: Tenant config handler
        """
        app.add_url_rule(
            "/config_editor", "config_editor", self.index, methods=["GET"]
        )
        app.add_url_rule(
            "/config_editor/tenantConfig", "config_editor_edit_tenant_config",
            self.edit_tenant_config, methods=["GET"]
        )
        app.add_url_rule(
            "/config_editor/tenantConfig", "config_editor_update_tenant_config",
            self.update_tenant_config, methods=["POST"]
        )
        app.add_url_rule(
            "/config_editor/config", "config_editor_edit_qwc2_config",
            self.edit_qwc2_config, methods=["GET"]
        )
        app.add_url_rule(
            "/config_editor/config", "config_editor_update_qwc2_config",
            self.update_qwc2_config, methods=["POST"]
        )

        self.templates_dir = "plugins/config_editor/templates"
        self.logger = app.logger
        self.handler = handler

    def index(self):
        """Show entry page."""
        return render_template(
            "%s/index.html" % self.templates_dir, title=i18n('plugins.config_editor.title'), i18n=i18n
        )

    def edit_tenant_config(self):
        """Show editor for tenantConfig.json."""
        return self.edit_json_config(
            'tenantConfig.json', url_for('config_editor_update_tenant_config')
        )

    def update_tenant_config(self):
        """Update tenantConfig.json."""
        return self.update_json_config(
            'tenantConfig.json', url_for('config_editor_update_tenant_config')
        )

    def edit_qwc2_config(self):
        """Show editor for config.json."""
        return self.edit_json_config(
            'config.json', url_for('config_editor_update_qwc2_config')
        )

    def update_qwc2_config(self):
        """Update config.json."""
        return self.update_json_config(
            'config.json', url_for('config_editor_update_qwc2_config')
        )

    def edit_json_config(self, file_name, action_url):
        """Show editor for a JSON config file.

        :param str file_name: Config file name
        :param str action_url: URL for form submit
        """
        try:
            config_data = self.load_config_file(file_name)
        except Exception as e:
            flash(
                Markup(
                    "%s <b>%s</b>:"
                    "<br><br>"
                    "<pre>%s</pre>" %
                    (i18n('plugins.config_editor.edit_message_error'), file_name, e)
                ),
                'error'
            )
            return redirect(url_for('config_editor'))

        title = "%s %s" % (i18n('interface.common.edit'), file_name)

        return render_template(
            "%s/editor.html" % self.templates_dir, title=title,
            action=action_url, config_data=config_data, i18n=i18n
        )

    def update_json_config(self, file_name, action_url):
        """Update a JSON config file.

        :param str file_name: Config file name
        :param str action_url: URL for form submit
        """
        try:
            # update config file
            config_data = request.values.get('config_data')
            self.save_json_config_file(config_data, file_name)
            flash("%s %s." % (i18n('plugins.config_editor.update_message_success'), file_name), 'success')

            return redirect(url_for('config_editor'))
        except JSONDecodeError as e:
            flash("%s: %s" % (i18n('plugins.config_editor.json_message_error'), e), 'error')
        except Exception as e:
            flash(
                Markup(
                    "%s <b>%s</b>:"
                    "<br><br>"
                    "<pre>%s</pre>" %
                    (i18n('plugins.config_editor.save_message_error'), file_name, e)
                ),
                'error'
            )

        # return to editor and show errors
        title = "%s %s" % (i18n('interface.common.edit'), file_name)

        return render_template(
            "%s/editor.html" % self.templates_dir, title=title,
            action=action_url, config_data=config_data, i18n=i18n
        )

    def input_config_path(self):
        """Get input_config_path from config or raise exception if not set."""
        current_handler = self.handler()
        input_config_path = current_handler.config().get('input_config_path')
        if input_config_path is None:
            raise RuntimeError(
                "Required config option 'input_config_path' is not set"
            )

        return input_config_path

    def load_config_file(self, file_name):
        """Get contents of input config file as JSON string.

        :param str file_name: Config file name
        """
        config_data = None

        # read config file
        config_file_path = ""
        try:
            config_file_path = os.path.join(
                self.input_config_path(), self.handler().tenant, file_name
            )
            self.logger.info("Reading config file %s" % config_file_path)
            with open(config_file_path, encoding='utf-8') as f:
                config_data = f.read()
        except Exception as e:
            self.logger.error(
                "Could not read config file %s:\n%s" % (config_file_path, e)
            )
            raise e

        return config_data

    def save_json_config_file(self, config_data, file_name):
        """Save contents to input config file.

        :param str config_data: Config contents as JSON string
        :param str file_name: Config file name
        """
        config_file_path = ""
        try:
            # validate JSON
            config = json.loads(config_data, object_pairs_hook=OrderedDict)

            # get target path
            config_path = os.path.join(
                self.input_config_path(), self.handler().tenant
            )
            config_file_path = os.path.join(config_path, file_name)

            # save backup of current config file
            # as '<file_name>-YYYYmmdd-HHMMSS.bak'
            timestamp = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d-%H%M%S")
            backup_file_name = "%s-%s.bak" % (file_name, timestamp)
            backup_file_path = os.path.join(config_path, backup_file_name)
            self.logger.info(
                "Saving backup of config file to %s" % backup_file_path
            )
            copyfile(config_file_path, backup_file_path)

            # update config file
            self.logger.info("Updating config file %s" % config_file_path)
            with open(config_file_path, 'wb') as f:
                # NOTE: do not reformat JSON string
                f.write(config_data.encode('utf8'))
        except JSONDecodeError as e:
            raise e
        except Exception as e:
            self.logger.error(
                "Could not save config file %s:\n%s" % (config_file_path, e)
            )
            raise e
