from .controller import Controller
from forms import GroupForm


class GroupsController(Controller):
    """Controller for group model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        super(GroupsController, self).__init__(
            "Group", 'groups', 'group', 'groups', app, handler
        )

    def resources_for_index_query(self, search_text, session):
        """Return query for groups list.

        :param str search_text: Search string for filtering
        :param Session session: DB session
        """
        query = session.query(self.Group).order_by(self.Group.name)
        if search_text:
            query = query.filter(self.Group.name.ilike("%%%s%%" % search_text))

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': self.Group.id,
            'name': self.Group.name
        }

        order_by = sortable_columns.get(sort)
        if order_by is not None:
            if not sort_asc:
                # sort in descending order
                order_by = order_by.desc()

        return order_by

    def find_resource(self, id, session):
        """Find group by ID.

        :param int id: Group ID
        :param Session session: DB session
        """
        return session.query(self.Group).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional group object
        :param bool edit_form: Set if edit form
        """
        form = GroupForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_collection(
            resource, edit_form, form.users, self.User, 'sorted_users', 'id',
            'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.roles, self.Role, 'sorted_roles', 'id',
            'name', session
        )
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update group records in DB.

        :param object resource: Optional group object
                                (None for create)
        :param FlaskForm form: Form for group
        :param Session session: DB session
        """
        if resource is None:
            # create new group
            group = self.Group()
            session.add(group)
        else:
            # update existing group
            group = resource

        # update group
        group.name = form.name.data
        group.description = form.description.data

        # update users
        self.update_collection(
            group.users_collection, form.users, self.User, 'id', session
        )
        # update roles
        self.update_collection(
            group.roles_collection, form.roles, self.Role, 'id', session
        )
