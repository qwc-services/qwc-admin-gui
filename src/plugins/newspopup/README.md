NewsPopup Plugin
================

This plugin adds an editor for editing the contents of the `NewsPopup` displayed in QWC2.

Usage
=====

Make sure the `NewsPopup` plugin is enabled in your QWC2 `config.json`. Then, enable this plugin by setting the following options in the `config` block of the `adminGui` section of the `tenantConfig.json`:

```json
"plugins": ["newspopup"],
"news_file": "<path_to_news.html>",
"viewer_config_file": "<path_to_config.json>"
```

For example
```json
"news_file": "/qwc2/assets/news.html",
"viewer_config_file": "/qwc2/config.json"
```

The plugin requires write access to the files specified by `news_file` and `viewer_config_file` (i.e. the files need to be mounted read-write into the container).

The plugin will display an editor to modify the contents of `news_file` and update the `NewsPopup` plugin configuration in `viewer_config_file`.
