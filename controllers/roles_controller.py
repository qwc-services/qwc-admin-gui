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

    def resources_for_index_query(self, search_text, session):
        """Return query for roles list.

        :param str search_text: Search string for filtering
        :param Session session: DB session
        """
        query = session.query(self.Role).order_by(self.Role.name)
        if search_text:
            query = query.filter(self.Role.name.ilike("%%%s%%" % search_text))

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': self.Role.id,
            'name': self.Role.name
        }

        order_by = sortable_columns.get(sort)
        if order_by is not None:
            if not sort_asc:
                # sort in descending order
                order_by = order_by.desc()

        return order_by

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
            resource, edit_form, form.groups, self.Group, 'sorted_groups',
            'id', 'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.users, self.User, 'sorted_users', 'id',
            'name', session
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
            role.groups_collection, form.groups, self.Group, 'id', session
        )
        # update users
        self.update_collection(
            role.users_collection, form.users, self.User, 'id', session
        )
