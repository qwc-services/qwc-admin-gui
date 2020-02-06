QWC Admin GUI
=============

GUI for administration of QWC Services.

* manage users, groups and roles
* define QWC resources and assign [permissions](https://github.com/qwc-services/qwc-services-core#resources-and-permissions)
* define registrable groups and manage [group registration requests](https://github.com/qwc-services/qwc-services-core#group_registration)

**Note:** requires a QWC ConfigDB

Docker usage
------------

### Run docker image

    docker run -v /PATH/TO/pg_service.conf:/var/www/.pg_service.conf:ro -p 5031:9090 --env FLASK_DEBUG=1 sourcepole/qwc-admin-gui

A configuration database is required to run the Admin GUI. For testing purposes you can use the demo DB:

    docker run -p 5439:5432 sourcepole/qwc-demo-db


| docker parameters | Description |
|----------------------|-------------|
| `-v /PATH/TO/pg_service.conf:/var/www/.pg_service.conf:ro` | Mount your pg_service.conf file to `/var/www/` with read only mode|
| `-p 5031:9090` | This binds port 9090 of the container to port 5031 on 127.0.0.1 of the host machine. |
| `--env FLASK_DEBUG=1` | Set debug mode to true, so the login is deactivated |

### Build docker image locally:

    docker build .

Setup
-----

Uses PostgreSQL connection service `qwc_configdb` (ConfigDB).

Setup PostgreSQL connection service file `~/.pg_service.conf`:

```
[qwc_configdb]
host=localhost
port=5439
dbname=qwc_demo
user=qwc_admin
password=qwc_admin
sslmode=disable
```


Configuration
-------------

Additional user fields are saved in the table `qwc_config.user_infos` with a a one-to-one relation to `qwc_config.users` via the `user_id` foreign key.
To add custom user fields, add new columns to your `qwc_config.user_infos` table and set your `USER_INFO_FIELDS` to a JSON with the following structure:

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
USER_INFO_FIELDS='[{"title": "Surname", "name": "surname", "type": "text", "required": true}, {"title": "First name", "name": "first_name", "type": "text", "required": true}]'
```

Set the `TOTP_ENABLED` environment variable to `True` to show the TOTP fields in the user form, if two factor authentication is enabled in the [DB-Auth service](https://github.com/qwc-services/qwc-db-auth) (default: `False`).

Set the `GROUP_REGISTRATION_ENABLED` environment variable to `False` to disable registrable groups and group registration requests, if not using the [Registration GUI](https://github.com/qwc-services/qwc-registration-gui) (default: `True`).


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


### Translations

Translation strings are stored in a JSON file for each locale in `translations/<locale>.json` (e.g. `en.json`). Add any new languages as new JSON files.

Set the `DEFAULT_LOCALE` environment variable to choose the locale for the user notification mails (default: `en`).


### Proxy to internal services

The route `/proxy?url=http://example.com/path?a=1` serves as a proxy for calling whitelisted internal services. This can be used e.g. to call other internal services from custom pages in the Admin GUI, without having to expose those services externally.

Set the `PROXY_URL_WHITELIST` environment variable to a JSON with a list of RegExes for whitelisted URLs (default: `[]`), e.g.
```json
    ["<RegEx pattern for full URL from proxy request>", "^http://example.com/path\\?.*$"]
```

Set the `PROXY_TIMEOUT` environment variable to the timeout in seconds for proxy requests (default: `60`s).


Usage
-----

Set the `USER_INFO_FIELDS` environment variable to your custom user info fields JSON (default: `[]`.

Base URL:

    http://localhost:5031/

### Default login

username: admin
password: admin


Development
-----------

Install Python module for PostgreSQL:

    apt-get install python3-psycopg2

Create a virtual environment:

    virtualenv --python=/usr/bin/python3 --system-site-packages .venv

Without system packages:

    virtualenv --python=/usr/bin/python3 .venv

Activate virtual environment:

    source .venv/bin/activate

Install requirements:

    pip install -r requirements.txt

Start local service:

    MAIL_SUPPRESS_SEND=True MAIL_DEFAULT_SENDER=from@example.com python server.py
