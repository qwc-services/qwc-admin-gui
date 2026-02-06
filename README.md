[![](https://github.com/qwc-services/qwc-admin-gui/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-admin-gui/actions)
[![docker](https://img.shields.io/docker/v/sourcepole/qwc-admin-gui?label=Docker%20image&sort=semver)](https://hub.docker.com/r/sourcepole/qwc-admin-gui)

QWC Admin GUI
=============

Web backend for administration of QWC Services.

* Manage users, groups and roles
* Define resources and assign permissions
* Define registrable groups and manage group registration requests

See also [Managing Users, Resources and Permissions](https://qwc-services.github.io/master/configuration/ResourcesPermissions/).

Configuration
-------------

The static config files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### JSON config

* [JSON schema](schemas/qwc-admin-gui.json)
* File location: `$CONFIG_PATH/<tenant>/adminGuiConfig.json`

Example:
```json
{
  "$schema": "https://raw.githubusercontent.com/qwc-services/qwc-admin-gui/master/schemas/qwc-admin-gui.json",
  "service": "admin-gui",
  "config": {
    "db_url": "postgresql:///?service=qwc_configdb",
    "config_generator_service_url": "http://qwc-config-service:9090",
    "totp_enabled": false,
    "user_info_fields": [],
    "proxy_url_whitelist": [],
    "proxy_timeout": 60
  }
}
```

See the [schema definition](schemas/qwc-admin-gui.json) for the full set of supported config variables.

### Environment variables

Config options in the config file can be overridden by equivalent uppercase environment variables.

In addition, the following environment variables are supported:

| Name                         | Default       | Description                                                                               |
|------------------------------|---------------|-------------------------------------------------------------------------------------------|
| `GROUP_REGISTRATION_ENABLED` | `True`        | Whether to allow registrable groups and group registration requests via [Registration GUI](https://github.com/qwc-services/qwc-registration-gui). |
| `IDLE_TIMEOUT`               | `0`           | Idle timeout after which to automatically log out (`0` disables automatic logout).        |
| `SKIP_LOGIN`                 | `False`       | Whether to skip redirect to the `auth_service_url` is user is not authenticated (for development). |
| `DEFAULT_LOCALE`             | `en`          | Admin GUI language (see [src/translations](src/translations) for available languages).    |
| `MAIL_SERVER`                | `localhost`   | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_PORT`                  | `25`          | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_USE_TLS`               | `False`       | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_USE_SSL`               | `False`       | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_DEBUG`                 | `app.debug`   | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_USERNAME`              | `None`        | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_PASSWORD`              | `None`        | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_DEFAULT_SENDER`        | `None`        | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_MAX_EMAILS`            | `None`        | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_SUPPRESS_SEND`         | `app.testing` | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |
| `MAIL_ASCII_ATTACHMENTS`     | `False`       | Mailer setup, see [Flask-Mail](https://flask-mail.readthedocs.io/en/latest/#configuring). |


### Two-factor authentication

If two factor authentication is enabled in the [DB-Auth service](https://github.com/qwc-services/qwc-db-auth), set `totp_enabled` to `true` to show the TOTP fields in the user form.

### Additional user fields

Additional user fields are saved in the table `qwc_config.user_infos` with a a one-to-one relation to `qwc_config.users` via the `user_id` foreign key.
To add custom user fields, add new columns to your `qwc_config.user_infos` table and set your `user_info_fields` to a JSON with the following structure:

```json
[
  {
    "title": "<field title>",
    "name": "<column name>",
    "type": "<field type (text|textarea|integer|list, default: text)>",
    "values": "<field values in dropdown list ([(value1, label1), (value2, label2), ...]|[value1, value2, ...])>",
    "required" "<whether field is required (true|false, default: false)>"
  }
]
```

These fields are then added to the user form.

Example:

```sql
ALTER TABLE qwc_config.user_infos ADD COLUMN surname character varying NOT NULL;
ALTER TABLE qwc_config.user_infos ADD COLUMN first_name character varying NOT NULL;
```

```json
"user_info_fields": [{"title": "Surname", "name": "surname", "type": "text", "required": true}, {"title": "First name", "name": "first_name", "type": "text", "required": true}]
```

### Invitations

You can send invitation mails to users from the `Users` page. You will need to configure the mailer using the `MAIL_*` environment variables documented above. You can customize the invitation mail by setting the `application_name` and `application_url` JSON config variables, or provide a fully custom template by replacing the [`invite_email_body.<lang>.txt`](src/templates/users) files. If you are running `qwc-admin-gui` in Docker, you can mount your custom templates to `/srv/qwc_service/templates/users/`.

### Translations

Translation strings are stored in a JSON file for each locale in `translations/<locale>.json` (e.g. `en.json`). Add any new languages as new JSON files. You can use the [updateTranslations.py](updateTranslations.py) helper script to update the translation files with all message ids from the source files.

Set the `DEFAULT_LOCALE` environment variable to choose the locale for the user notification mails (default: `en`).

### Solr search index update

If using a Solr search service, the Solr search index of a tenant may be updated via a button on the main page. This can be activated by adding the following configuration options to the Admin GUI service config:
```json
{
  "config": {
    "solr_service_url": "http://qwc-solr:8983/solr/gdi/",
    "solr_tenant_dih": "dih_geodata",
    "solr_tenant_dih_config_file": "/solr/config-in/dih_geodata_config.xml",
    "solr_config_path": "/solr/config-out",
    "solr_update_check_wait": 5,
    "solr_update_check_max_retries": 10
  }
}
```

* `solr_service_url`: Solr Service base URL for collection
* `solr_tenant_dih`: Solr DataImportHandler for the tenant
* `solr_tenant_dih_config_file` (optional): Path to source DataImportHandler config file for the tenant
* `solr_config_path` (optional): Path to Solr configs (**Note:** requires write permissions for DataImportHandler config files)
* `solr_update_check_wait` (optional): Wait time in seconds for checks during Solr index update (default: `5`s)
* `solr_update_check_max_retries` (optional): Max number of retries for checks during Solr index update (default: `10`)

If both `solr_tenant_dih_config_file` and `solr_config_path` are set, the tenant config file is first copied to the Solr configs dir before updating the Solr search index.

Example volumes for `qwc-docker` environment and above service config:
```yaml
services:
  qwc-admin-gui:
    # ...
    volumes:
      # ...
      # Solr configs
      - ./volumes/solr/configsets/gdi/conf:/solr/config-in:ro
      - ./volumes/solr/data/gdi/conf:/solr/config-out
```

### Plugins

The admin gui is extendable through plugins, which reside in the `plugins` folder. To enable them, list them in `plugins` in the admin gui configuration. See the JSON schema for details, and for configuration parameters which may be required by plugins shipped by default with `qwc-admin-gui`.

### Proxy to internal services

The route `/proxy?url=<url>` serves as a proxy for calling whitelisted internal services. This can be used e.g. to call other internal services from custom pages in the Admin GUI, without having to expose those services externally.

Set `proxy_url_whitelist` to a list of RegExes for whitelisted URLs (default: `[]`), e.g.
```json
    ["<RegEx pattern for full URL from proxy request>", "^http://example.com/path\\?.*$"]
```

Set `proxy_timeout` to the timeout in seconds for proxy requests (default: `60`s).

Run locally
-----------

Install dependencies and run:

    export CONFIG_PATH=<CONFIG_PATH>
    uv run src/server.py

To use configs from a `qwc-docker` setup, set `CONFIG_PATH=<...>/qwc-docker/volumes/config`.

Set `FLASK_DEBUG=1` for additional debug output.

Set `SKIP_LOGIN=1` if running without an authentication service (i.e. for development).

Set `FLASK_RUN_PORT=<port>` to change the default port (default: `5000`).
    
Docker usage
------------

The Docker image is published on [Dockerhub](https://hub.docker.com/r/sourcepole/qwc-admin-gui).

See sample [docker-compose.yml](https://github.com/qwc-services/qwc-docker/blob/master/docker-compose-example.yml) of [qwc-docker](https://github.com/qwc-services/qwc-docker).
