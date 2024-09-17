import json
import os
from flask import flash, json, redirect, render_template, request, url_for
from utils import i18n

class NewsPopupController():
    """Controller for config editors"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param TenantConfigHandler handler: Tenant config handler
        """
        app.add_url_rule(
            "/newspopup", "newspopup", self.index, methods=["GET"]
        )
        app.add_url_rule(
            "/newspopup", "newspopup_update", self.update_news, methods=["POST"]
        )

        self.templates_dir = "plugins/newspopup/templates"
        self.logger = app.logger
        self.handler = handler

    def index(self):
        current_handler = self.handler()
        news_file = current_handler.config().get('news_file')
        viewer_config_file = current_handler.config().get('viewer_config_file')

        # Read news file contents
        news_contents = ""
        try:
            with open(news_file, 'r') as fh:
                news_contents = fh.read()
        except Exception as e:
            self.logger.warn("Unable to read %s: %s" % (news_file, str(e)))

        # Read news version
        news_version = ""
        try:
            with open(viewer_config_file) as fh:
                data = json.load(fh)
                news_plugin_conf = next((e for e in data["plugins"]["common"] if e["name"] == "NewsPopup"), None)
                if news_plugin_conf:
                    news_version = news_plugin_conf["cfg"]["newsRev"]
                else:
                    news_plugin_conf = next((e for e in data["plugins"]["desktop"] if e["name"] == "NewsPopup"), None)
                    if news_plugin_conf:
                        news_version = news_plugin_conf["cfg"]["newsRev"]
                    else:
                        news_plugin_conf = next((e for e in data["plugins"]["mobile"] if e["name"] == "NewsPopup"), None)
                        if news_plugin_conf:
                            news_version = news_plugin_conf["cfg"]["newsRev"]
                if news_version is None:
                    news_version = ""
        except Exception as e:
            self.logger.warn("Unable to read news version: %s" % (str(e)))

        return render_template(
            "%s/index.html" % self.templates_dir, title="News Popup", i18n=i18n,
            news_contents=news_contents, news_version=news_version
        )

    def update_news(self):
        current_handler = self.handler()
        news_file = current_handler.config().get('news_file')
        viewer_config_file = current_handler.config().get('viewer_config_file')

        success = True

        # Update news file
        try:
            with open(news_file, 'w') as fh:
                fh.write(request.values.get('news_contents'))
        except Exception as e:
            self.logger.warn("Unable to write %s: %s" % (news_file, str(e)))
            success = False

        # Write news version
        try:
            with open(viewer_config_file, 'r+') as fh:
                data = json.load(fh)
                news_version = request.values.get('news_version', '')

                news_plugin_conf = next((e for e in data["plugins"]["common"] if e["name"] == "NewsPopup"), None)
                if news_plugin_conf:
                    news_plugin_conf["cfg"]["newsRev"] = news_version
                news_plugin_conf = next((e for e in data["plugins"]["desktop"] if e["name"] == "NewsPopup"), None)
                if news_plugin_conf:
                    news_plugin_conf["cfg"]["newsRev"] = news_version
                news_plugin_conf = next((e for e in data["plugins"]["mobile"] if e["name"] == "NewsPopup"), None)
                if news_plugin_conf:
                    news_plugin_conf["cfg"]["newsRev"] = news_version

                fh.seek(0)
                json.dump(data, fh, indent=2)
                fh.truncate()
        except Exception as e:
            self.logger.warn("Unable to write news version: %s" % (str(e)))

        if success:
            flash("Values updated successfully", 'success')
        else:
            flash("Not all values were updated", 'error')

        return redirect(url_for('newspopup'))
