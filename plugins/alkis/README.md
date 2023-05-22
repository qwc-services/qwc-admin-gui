ALKIS Plugin
============

This plugin allows managing some settings in the qwc_configdb."alkis" table, which can then be used by a QGIS project to selectively activate preconfigured DB service connections (in pg_service.conf).

![image](https://github.com/qwc-services/qwc-admin-gui/assets/8257055/fc41a58f-b777-46c6-8eec-55efd83193ab)

Some configuration options available when configuring the themes by hand may not be available in the GUI.

Usage
=====

Enable this plugin by setting the following options in `config` block of the `adminGui` section of the `tenantConfig.json`:

    "plugins": ["alkis"],
    "input_config_path": "<path to the input configs>",
    "qwc2_path": "<path to the qwc2 prod build>",
    "qgs_resources_path": "<path to the qgs resources>",
    "ogc_service_url": "<ows service url>"
