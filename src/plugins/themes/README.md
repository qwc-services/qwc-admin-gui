Theme Manager Plugin
====================

This plugin allows managing the `themesConfig` section of the `tenantConfig.json` graphically in the admin GUI.

Some configuration options available when configuring the themes by hand may not be available in the GUI.

Usage
=====

Enable this plugin by setting the following options in `config` block of the `adminGui` section of the `tenantConfig.json`:

    "plugins": ["themes"],
    "input_config_path": "<path to the input configs>",
    "qwc2_path": "<path to the qwc2 prod build>",
    "qgs_resources_path": "<path to the qgs resources>",
    "info_templates_path": "<path to the html info templates>",
    "ows_prefix": "<ows service prefix, i.e. /ows>",
    "default_qgis_server_url": "<qgis server url>"
