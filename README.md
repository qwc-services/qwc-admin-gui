QWC Admin GUI
=============

GUI for administration of QWC Services.

* manage users, groups and roles
* define QWC resources and assign [permissions](https://github.com/qwc-services/qwc-services-core#resources-and-permissions)
* define registrable groups and manage group registration requests

**Note:** requires a QWC ConfigDB


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

Set the `TOTP_ENABLED` environment variable to `True` to show the TOTP fields in the user form, if two factor authentication is enabled in the DB-Auth service (default: `False`).


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


Usage
-----

Set the `USER_INFO_FIELDS` environment variable to your custom user info fields JSON (default: `[]`.

Base URL:

    http://localhost:5031/


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
