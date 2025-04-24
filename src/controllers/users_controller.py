import os
import secrets

from flask import json, flash, redirect, render_template, url_for
from flask_mail import Message

from .controller import Controller
from forms import UserForm

from utils import i18n

class UsersController(Controller):
    """Controller for user model"""

    def __init__(self, app, handler, mail):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        :param flask_mail.Mail mail: Application mailer
        """
        super(UsersController, self).__init__(
            "User", 'users', 'user', 'users', app, handler
        )

        self.mail = mail

        # send mail
        app.add_url_rule(
            '/%s/<int:id>/sendmail' % self.base_route, 'sendmail_%s' % self.endpoint_suffix, self.sendmail,
            methods=['GET']
        )

    def resources_for_index_query(self, search_text, session):
        """Return query for users list.

        :param str search_text: Search string for filtering
        :param Session session: DB session
        """
        query = session.query(self.User).order_by(self.User.name)
        if search_text:
            query = query.filter(self.User.name.ilike("%%%s%%" % search_text))

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': self.User.id,
            'name': self.User.name
        }

        order_by = sortable_columns.get(sort)
        if order_by is not None:
            if not sort_asc:
                # sort in descending order
                order_by = order_by.desc()

        return order_by

    def find_resource(self, id, session):
        """Find user by ID.

        :param int id: User ID
        :param Session session: DB session
        """
        return session.query(self.User).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional user object
        :param bool edit_form: Set if edit form
        """

        # get custom user info fields
        # get custom user info fields
        user_info_fields = self.handler().config().get(
            "user_info_fields", [])
        # make sure that all python strings
        # are in double quotes and not single quotes
        user_info_fields = json.loads(
            json.dumps(user_info_fields)
        )

        form = UserForm(self.config_models, user_info_fields, obj=resource)

        # show TOTP fields?
        form.totp_enabled = self.handler().config().get(
            "totp_enabled", False)

        with self.session() as session:
            self.update_form_collection(
                resource, edit_form, form.groups, self.Group, 'sorted_groups',
                'id', 'name', session
            )
            self.update_form_collection(
                resource, edit_form, form.roles, self.Role, 'sorted_roles', 'id',
                'name', session
            )

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update user records in DB.

        :param object resource: Optional user object
                                (None for create)
        :param FlaskForm form: Form for user
        :param Session session: DB session
        """
        if resource is None:
            # create new user
            user = self.User()
            session.add(user)
        else:
            # update existing user
            user = resource

        # update user
        user.name = form.name.data
        user.description = form.description.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        user.force_password_change = form.force_password_change.data
        user.failed_sign_in_count = form.failed_sign_in_count.data or 0

        totp_enabled = self.handler().config().get(
            "totp_enabled", False)

        if totp_enabled:
            if form.totp_secret.data:
                user.totp_secret = form.totp_secret.data
            else:
                user.totp_secret = None

        # update user info
        if form.user_info.data:
            # ignore crsf_token of subform
            user_info_data = form.user_info.data
            user_info_data.pop('csrf_token', None)

            if user_info_data:
                user_info = user.user_info
                if user_info is None:
                    # create new user_info
                    user_info = self.UserInfo()
                    # assign to user
                    user_info.user = user
                    session.add(user_info)

                # update user info fields
                for field, value in user_info_data.items():
                    if value == '':
                        value = None
                    setattr(user_info, field, value)

        # update groups
        self.update_collection(
            user.groups_collection, form.groups, self.Group, 'id', session
        )
        # update roles
        self.update_collection(
            user.roles_collection, form.roles, self.Role, 'id', session
        )

    def sendmail(self, id):
        """Send mail with access link.

        :param int id: User ID
        """
        if not self.app.config.get("MAIL_USERNAME", None):
            flash(
                i18n('interface.users.no_mail_config'),
                'error'
            )
            return redirect(url_for(self.base_route))

        self.setup_models()
        # find user
        with self.session() as session, session.begin():
            user = self.find_resource(id, session)

            if not user or not user.email:
                flash(
                    i18n('interface.users.no_user_email'),
                    'error'
                )
                return redirect(url_for(self.base_route))

            password = secrets.token_urlsafe(8).replace('-','0')
            user.set_password(password)
            user.force_password_change = True

            app_name = self.handler().config().get("application_name", "QWC")
            app_url = self.handler().config().get("application_url",
                os.path.dirname(url_for('home', _external=True).rstrip("/")) + "/"
            )

            locale = os.environ.get('DEFAULT_LOCALE', 'en')
            try:
                body = render_template(
                    '%s/invite_email_body.%s.txt' % (self.templates_dir, locale),
                    user=user, password=password, app_name=app_name
                )
            except:
                body = render_template(
                    '%s/invite_email_body.en.txt' % (self.templates_dir),
                    user=user, password=password, app_name=app_name, app_url=app_url
                )

            try:
                msg = Message(
                    i18n('interface.users.mail_subject', [app_name]),
                    recipients=[user.email]
                )
                # set message body from template
                msg.body = body

                # send message
                self.logger.debug(msg)
                self.mail.send(msg)
                flash(
                    i18n('interface.users.send_mail_success'),
                    'success'
                )
            except Exception as e:
                self.logger.error(
                    "Could not send mail to user '%s':\n%s" %
                    (user.email, e)
                )
                flash(
                    i18n('interface.users.send_mail_failure'),
                    'error'
                )

            return redirect(url_for(self.base_route))
