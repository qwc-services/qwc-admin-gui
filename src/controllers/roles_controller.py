from admin_access import MANAGE_ROLES
from .controller import Controller
from forms import RoleForm
from flask import flash
from markupsafe import Markup
from wtforms import ValidationError


class RolesController(Controller):
    """Controller for role model"""


    # name of admin iam.role
    ADMIN_ROLE_NAME = 'admin'

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        super(RolesController, self).__init__(
            "Role", 'roles', 'role', 'roles', app, handler, MANAGE_ROLES
        )

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

    # authorization

    def scope_filter(self, query):
        """Restrict a roles query to the roles within scope.

        :param Query query: Query for roles
        """
        scope = self.scope()
        if scope is None:
            return query

        return query.filter(self.Role.name.in_(scope))

    def subject_roles(self, resource=None, form=None):
        """Return the role being changed, plus every role held by the members
        this change adds or removes - adding a user to this role reaches into
        every other role that user already holds.

        :param object resource: Optional role object (None for create)
        :param FlaskForm form: Optional form for role
        """
        roles = set()
        if resource is not None:
            roles.add(resource.name)
        elif form is not None:
            roles.add(form.name.data)
        if form is not None:
            roles |= self.changed_member_roles(resource, form)

        return roles

    def membership_roles(self, resource=None, form=None):
        """Return this role if the change adds or removes members.

        :param object resource: Optional role object (None for create)
        :param FlaskForm form: Optional form for role
        """
        if form is None:
            return set()

        user_ids, group_ids = self.changed_member_ids(resource, form)
        if not user_ids and not group_ids:
            return set()

        return {resource.name if resource is not None else form.name.data}

    def changed_member_ids(self, resource=None, form=None):
        """Return the IDs of the users and groups this change adds to or
        removes from the role, as (user_ids, group_ids).

        :param object resource: Optional role object (None for create)
        :param FlaskForm form: Optional form for role
        """
        current_users = set()
        current_groups = set()
        if resource is not None:
            current_users = {user.id for user in resource.users_collection}
            current_groups = {group.id for group in resource.groups_collection}

        return (
            current_users ^ set(form.users.data or []),
            current_groups ^ set(form.groups.data or [])
        )

    def changed_member_roles(self, resource=None, form=None):
        """Return the names of all roles held by the users and groups this
        change adds to or removes from the role.

        :param object resource: Optional role object (None for create)
        :param FlaskForm form: Optional form for role
        """
        user_ids, group_ids = self.changed_member_ids(resource, form)
        if not user_ids and not group_ids:
            return set()

        with self.session() as session:
            return self.roles_of_users(user_ids, session) \
                | self.roles_of_groups(group_ids, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional role object
        :param bool edit_form: Set if edit form
        """
        form = RoleForm(self.config_models, obj=resource)

        with self.session() as session:
            self.update_form_collection(
                resource, edit_form, form.groups, self.Group, 'sorted_groups',
                'id', 'name', session
            )
            self.update_form_collection(
                resource, edit_form, form.users, self.User, 'sorted_users', 'id',
                'name', session
            )

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
        if role.name != self.ADMIN_ROLE_NAME:
            role.name = form.name.data
        elif form.name.data != "admin":
            flash(Markup("The <code>admin</code> role cannot be renamed."), 'error')
        role.description = form.description.data

        # update groups
        self.update_collection(
            role.groups_collection, form.groups, self.Group, 'id', session
        )
        # update users
        self.update_collection(
            role.users_collection, form.users, self.User, 'id', session
        )

    def destroy_resource(self, resource, session):
        """Delete existing resource in DB.

        :param object resource: Resource object
        :param Session session: DB session
        """

        if resource.name == self.ADMIN_ROLE_NAME:
            raise ValidationError('The <code>admin</code> role cannot be deleted.')

        Controller.destroy_resource(self, resource, session)
