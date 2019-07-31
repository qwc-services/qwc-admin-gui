import os

from flask import json

from .controller import Controller
from forms import UserForm


class UsersController(Controller):
    """Controller for user model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(UsersController, self).__init__(
            "User", 'users', 'user', 'users', app, config_models
        )
        self.User = self.config_models.model('users')
        self.UserInfo = self.config_models.model('user_infos')
        self.Group = self.config_models.model('groups')
        self.Role = self.config_models.model('roles')

        # get custom user info fields
        try:
            user_info_fields = json.loads(
                os.environ.get('USER_INFO_FIELDS', '[]')
            )
        except Exception as e:
            app.logger.error("Could not load USER_INFO_FIELDS:\n%s" % e)
            user_info_fields = []

        # show TOTP fields?
        self.totp_enabled = os.environ.get('TOTP_ENABLED', 'False') == 'True'

        UserForm.add_custom_fields(user_info_fields)

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
        form = UserForm(self.config_models, obj=resource)

        form.totp_enabled = self.totp_enabled

        session = self.session()
        self.update_form_collection(
            resource, edit_form, form.groups, self.Group, 'sorted_groups',
            'id', 'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.roles, self.Role, 'sorted_roles', 'id',
            'name', session
        )
        session.close()

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
        user.failed_sign_in_count = form.failed_sign_in_count.data or 0

        if self.totp_enabled:
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

                # update user info fields
                for field, value in user_info_data.items():
                    setattr(user_info, field, value)

        # update groups
        self.update_collection(
            user.groups_collection, form.groups, self.Group, 'id', session
        )
        # update roles
        self.update_collection(
            user.roles_collection, form.roles, self.Role, 'id', session
        )
