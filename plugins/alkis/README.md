ALKIS Plugin
============

This plugin allows managing some settings in the qwc_config.alkis table, which can then be used by a QGIS project to selectively activate preconfigured DB service connections (in pg_service.conf).

![image](https://github.com/qwc-services/qwc-admin-gui/assets/8257055/fc41a58f-b777-46c6-8eec-55efd83193ab)

New table qwc_conf.alkis needs to be created:

```
CREATE TABLE qwc_config.alkis (
	name varchar NULL,
	pgservice varchar NULL,
	enable_alkis bool NULL,
	enable_owner bool NULL,
	header_template varchar NULL,
	id serial4 NOT NULL,
	CONSTRAINT alkis_pk PRIMARY KEY (id)
);
```

A new type with name "alkis" needs to be created in table qwc_config.resource_types.
![image](https://github.com/w0pr/qwc-admin-gui/assets/8257055/dcede457-99e4-4c07-934d-9027781c0561)


Usage
=====

Enable this plugin by setting the following options in `config` block of the `adminGui` section of the `tenantConfig.json`:

    "plugins": ["alkis"],
    "qwc2_path": "<path to the qwc2 prod build>",
   
