Config Editor Plugin
====================

This plugin adds editors for the input configs `tenantConfig.json` and `config.json` to the Admin GUI.

Uses Ace v1.4.14 code editor from https://ace.c9.io


Usage
=====

Enable this plugin by setting the following options in the `config` block of the `adminGui` section of the `tenantConfig.json`:

```json
"plugins": ["config_editor"],
"input_config_path": "<path to the input configs>"
```

The Admin GUI requires write access to the `input_config_path`.
