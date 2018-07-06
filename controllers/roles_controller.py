from .controller import Controller
from forms import RoleForm


class RolesController(Controller):
    """Controller for role model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(RolesController, self).__init__(
            "Role", 'roles', 'role', 'roles', app, config_models
        )
        self.Role = self.config_models.model('roles')
        self.User = self.config_models.model('users')
        self.Group = self.config_models.model('groups')

    def resources_for_index(self, session):
        """Return roles list.

        :param Session session: DB session
        """
        return session.query(self.Role).order_by(self.Role.name).all()

    def find_resource(self, id, session):
        """Find role by ID.

        :param int id: Role ID
        :param Session session: DB session
        """
        return session.query(self.Role).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional role object
        :param bool edit_form: Set if edit form
        """
        form = RoleForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_collection(
            resource, edit_form, form.groups, form.group, self.Group,
            'sorted_groups', 'group_id', 'id', 'group_name', 'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.users, form.user, self.User,
            'sorted_users', 'user_id', 'id', 'user_name', 'name', session
        )
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update role records in DB.

        :param object resource: Optional role object
                                (None for create)
        :param FlaskForm form: Form for role
        :param Session session: DB session
        """
        if resource is None:
            # create new role
            role = self.Role()
            session.add(role)
        else:
            # update existing role
            role = resource

        # update role
        role.name = form.name.data
        role.description = form.description.data

        # update groups
        self.update_collection(
            role.groups_collection, form.groups, 'group_id', self.Group, 'id',
            session
        )
        # update users
        self.update_collection(
            role.users_collection, form.users, 'user_id', self.User, 'id',
            session
        )
