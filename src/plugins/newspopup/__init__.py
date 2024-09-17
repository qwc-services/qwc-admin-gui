import os

from plugins.newspopup.controllers import NewsPopupController

name = "News Popup"


def load_plugin(app, handler):
    # check required config
    config = handler().config()
    errors = []

    news_file = config.get('news_file')
    if news_file is None or not os.path.isfile(news_file):
        errors.append("Required config option 'news_file' is not set or invalid")

    viewer_config_file = config.get('viewer_config_file')
    if viewer_config_file is None or not os.path.isfile(viewer_config_file):
        errors.append("Required config option 'viewer_config_file' is not set or invalid")

    if errors:
        app.logger.error(
            "NewsPopup plugin:\n" + "\n".join(errors)
        )
        raise RuntimeError("NewsPopup plugin:\n" + "\n".join(errors))

    # create controller (including routes)
    NewsPopupController(app, handler)
