[![](https://github.com/qwc-services/qwc-admin-gui/workflows/build/badge.svg)](https://github.com/qwc-services/qwc-admin-gui/actions)
[![](https://img.shields.io/docker/pulls/sourcepole/qwc-admin-gui)](https://hub.docker.com/r/sourcepole/qwc-admin-gui)

QWC Admin GUI
=============

GUI for administration of QWC Services.

* manage users, groups and roles
* define QWC resources and assign [permissions](https://github.com/qwc-services/qwc-services-core#resources-and-permissions)
* define registrable groups and manage [group registration requests](https://github.com/qwc-services/qwc-services-core#group_registration)

**Note:** requires a QWC ConfigDB


Configuration
-------------

The static config files are stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### Admin Gui Service config

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

To connect with the demo database, the following `~/.pg_service.conf` entry is expected:

```
[qwc_configdb]
host=localhost
port=5439
dbname=qwc_demo
user=qwc_admin
password=qwc_admin
sslmode=disable
```

Set the `GROUP_REGISTRATION_ENABLED` environment variable to `False` to disable registrable groups and group registration requests, if not using the [Registration GUI](https://github.com/qwc-services/qwc-registration-gui) (default: `True`).

To automatically logout from the admin gui after a period of inactivity, set the `IDLE_TIMEOUT` environment variable to the desired period, in seconds (default: `0`, i.e. disabled).

Set `totp_enabled` to `true` to show the TOTP fields in the user form, if two factor authentication is enabled in the [DB-Auth service](https://github.com/qwc-services/qwc-db-auth) (default: `false`).

### Additional user fields

Additional user fields are saved in the table `qwc_config.user_infos` with a a one-to-one relation to `qwc_config.users` via the `user_id` foreign key.
To add custom user fields, add new columns to your `qwc_config.user_infos` table and set your `user_info_fields` to a JSON with the following structure:

```json
[
  {
    "title": "<field title>",
    "name": "<column name>",
    "type": "<field type (text|textarea|integer, default: text)>",
    "required" "<whether field is required (true|false, default: false)>"
  }
]
```

These fields are then added to the user form.

Example:

```sql
-- add custom columns
ALTER TABLE qwc_config.user_infos ADD COLUMN surname character varying NOT NULL;
ALTER TABLE qwc_config.user_infos ADD COLUMN first_name character varying NOT NULL;
```

```bash
# set user info fields config
"user_info_fields": [{"title": "Surname", "name": "surname", "type": "text", "required": true}, {"title": "First name", "name": "first_name", "type": "text", "required": true}]
```

### Mailer

[Flask-Mail](https://pythonhosted.org/Flask-Mail/) is used for sending mails like user notifications. These are the available options:
* `MAIL_SERVER`: default ‘localhost’
* `MAIL_PORT`: default 25
* `MAIL_USE_TLS`: default False
* `MAIL_USE_SSL`: default False
* `MAIL_DEBUG`: default app.debug
* `MAIL_USERNAME`: default None
* `MAIL_PASSWORD`: default None
* `MAIL_DEFAULT_SENDER`: default None
* `MAIL_MAX_EMAILS`: default None
* `MAIL_SUPPRESS_SEND`: default app.testing
* `MAIL_ASCII_ATTACHMENTS`: default False

In addition the standard Flask `TESTING` configuration option is used by Flask-Mail in unit tests.

### Proxy to internal services

The route `/proxy?url=http://example.com/path?a=1` serves as a proxy for calling whitelisted internal services. This can be used e.g. to call other internal services from custom pages in the Admin GUI, without having to expose those services externally.

Set `proxy_url_whitelist` to a list of RegExes for whitelisted URLs (default: `[]`), e.g.
```json
    ["<RegEx pattern for full URL from proxy request>", "^http://example.com/path\\?.*$"]
```

Set `proxy_timeout` to the timeout in seconds for proxy requests (default: `60`s).

### Translations

Translation strings are stored in a JSON file for each locale in `translations/<locale>.json` (e.g. `en.json`). Add any new languages as new JSON files.

Set the `DEFAULT_LOCALE` environment variable to choose the locale for the user notification mails (default: `en`).

### Plugins

The admin gui is extendable through plugins, which reside in the `plugins` folder. To enable them, list them in `plugins` in the admin gui configuration. See the JSON schema for details, and for configuration parameters which may be required by plugins shipped by default with `qwc-admin-gui`.

Usage
-----

Base URL:

    http://localhost:5031/

### Default login

username: admin
password: admin


Docker usage
------------

To run this docker image you will need a configuration database. For testing purposes you can use the demo DB.

The following steps explain how to download the demo DB docker image and how to run the `qwc-admin-gui` service with `docker-compose`.

**Step 1: Clone qwc-docker**

    git clone https://github.com/qwc-services/qwc-docker
    cd qwc-docker

**Step 2: Create docker-compose.yml file**

    cp docker-compose-example.yml docker-compose.yml

**Step 3: Set flask debug mode to true**

For the QWC Admin GUI to work without login you will have to add the following `env` variable:

    FLASK_DEBUG=1

**Step 4: Start docker containers**

    docker-compose up qwc-admin-gui

For more information please visit: https://github.com/qwc-services/qwc-docker

Development
-----------

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt

Set the `CONFIG_PATH` environment variable to the path containing the service config and permission files when starting this service (default: `config`).

    export CONFIG_PATH=../qwc-docker/demo-config

Configure environment:

    echo FLASK_ENV=development >.flaskenv

Start local service:

     python server.py
