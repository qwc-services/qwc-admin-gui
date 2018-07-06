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
        self.Group = self.config_models.model('groups')
        self.Role = self.config_models.model('roles')

    def resources_for_index(self, session):
        """Return users list.

        :param Session session: DB session
        """
        return session.query(self.User).order_by(self.User.name).all()

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

        session = self.session()
        self.update_form_collection(
            resource, edit_form, form.groups, form.group, self.Group,
            'sorted_groups', 'group_id', 'id', 'group_name', 'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.roles, form.role, self.Role,
            'sorted_roles', 'role_id', 'id', 'role_name', 'name', session
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

        # update groups
        self.update_collection(
            user.groups_collection, form.groups, 'group_id', self.Group, 'id',
            session
        )
        # update roles
        self.update_collection(
            user.roles_collection, form.roles, 'role_id', self.Role, 'id',
            session
        )
