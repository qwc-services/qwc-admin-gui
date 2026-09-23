from admin_access import MANAGE_GROUPS, group_in_scope, group_role_names
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
            "Group", 'groups', 'group', 'groups', app, handler,
            MANAGE_GROUPS
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

    # authorization

    def scope_filter(self, query):
        """Restrict a groups query to groups whose every role is within scope.

        :param Query query: Query for groups
        """
        scope = self.scope()
        if scope is None:
            return query

        return query.filter(group_in_scope(self.Group, self.Role, scope))

    def subject_roles(self, resource=None, form=None):
        """Return the roles the group holds, plus any the form would add.

        :param object resource: Optional group object (None for create)
        :param FlaskForm form: Optional form for group
        """
        roles = set()
        if resource is not None:
            roles |= group_role_names(resource)
        if form is not None:
            with self.session() as session:
                roles |= self.role_names_for_ids(form.roles.data, session)
                # adding a user to this group reaches into every role that
                # user already holds
                roles |= self.roles_of_users(
                    self.changed_member_ids(resource, form), session
                )

        return roles

    def changed_member_ids(self, resource=None, form=None):
        """Return the IDs of the users this change adds to or removes from
        the group.

        :param object resource: Optional group object (None for create)
        :param FlaskForm form: Optional form for group
        """
        current = set()
        if resource is not None:
            current = {user.id for user in resource.users_collection}

        return current ^ set(form.users.data or [])

    def membership_roles(self, resource=None, form=None):
        """Return the roles this group is added to or removed from.

        :param object resource: Optional group object (None for create)
        :param FlaskForm form: Optional form for group
        """
        if form is None:
            return set()

        current = set()
        if resource is not None:
            current = group_role_names(resource)
        with self.session() as session:
            submitted = self.role_names_for_ids(form.roles.data, session)

        return current ^ submitted

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional group object
        :param bool edit_form: Set if edit form
        """
        form = GroupForm(self.config_models, obj=resource)

        with self.session() as session:
            self.update_form_collection(
                resource, edit_form, form.users, self.User, 'sorted_users', 'id',
                'name', session
            )
            self.update_form_collection(
                resource, edit_form, form.roles, self.Role, 'sorted_roles', 'id',
                'name', session
            )
            self.restrict_choices(form)

        return form

    def restrict_choices(self, form):
        """Drop roles outside the scope of the identity's grant from the form
        choices.

        A group within scope only holds roles within scope, so this never
        drops one of its own roles.

        :param FlaskForm form: Form for group
        """
        scope = self.scope()
        if scope is None:
            return

        form.roles.choices = [
            choice for choice in form.roles.choices if choice[1] in scope
        ]

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
