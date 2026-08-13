from flask import flash, g
from markupsafe import Markup
from wtforms import ValidationError

from admin_sections import ADMIN_SECTION_RESOURCE_TYPE, SECTION_LABELS, \
    ensure_admin_panel_resources
from .controller import Controller
from forms import RoleForm


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
            "Role", 'roles', 'role', 'roles', app, handler
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

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional role object
        :param bool edit_form: Set if edit form
        """
        form = RoleForm(self.config_models, obj=resource)

        form.is_admin_role = (
            resource is not None and resource.name == self.ADMIN_ROLE_NAME
        )
        form.can_edit_admin_sections = g.get('full_admin_access', False)

        with self.session() as session:
            self.update_form_collection(
                resource, edit_form, form.groups, self.Group, 'sorted_groups',
                'id', 'name', session
            )
            self.update_form_collection(
                resource, edit_form, form.users, self.User, 'sorted_users', 'id',
                'name', session
            )

            form.admin_sections.choices = sorted(
                SECTION_LABELS.items(), key=lambda item: item[1]
            )
            if edit_form:
                if form.is_admin_role:
                    form.admin_sections.data = list(SECTION_LABELS.keys())
                else:
                    query = session.query(self.Resource.name) \
                        .join(
                            self.Permission,
                            self.Permission.resource_id == self.Resource.id
                        ) \
                        .filter(self.Permission.role_id == resource.id) \
                        .filter(
                            self.Resource.type == ADMIN_SECTION_RESOURCE_TYPE
                        )
                    form.admin_sections.data = [
                        name for (name, ) in query.all()
                    ]

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

        # only a full admin may change the admin role's own group/user
        if role.name != self.ADMIN_ROLE_NAME or g.get('full_admin_access', False):
            self.update_collection(
                role.groups_collection, form.groups, self.Group, 'id',
                session
            )
            self.update_collection(
                role.users_collection, form.users, self.User, 'id', session
            )

        # skip for the admin role (avoids wiping its permission rows via a
        # disabled, non-submitting checkbox) and for non-full-admins
        if role.name != self.ADMIN_ROLE_NAME and g.get('full_admin_access', False):
            self.update_admin_section_permissions(
                role, form.admin_sections, session
            )

    def update_admin_section_permissions(self, role, admin_sections_field,
                                          session):
        """Diff selected admin panel sections against a role's existing
        admin_panel_section Permission rows, creating/deleting rows to
        match.

        :param object role: Role object
        :param SelectMultipleField admin_sections_field: form.admin_sections
        :param Session session: DB session
        """
        ensure_admin_panel_resources(self.config_models, session)
        # flush so role.id is populated for a not-yet-persisted new role
        # before it's used in the filter/assignments below
        session.flush()

        selected_sections = set(admin_sections_field.data or [])

        existing_permissions = session.query(self.Permission) \
            .join(
                self.Resource, self.Permission.resource_id == self.Resource.id
            ) \
            .filter(self.Permission.role_id == role.id) \
            .filter(self.Resource.type == ADMIN_SECTION_RESOURCE_TYPE) \
            .all()
        existing_sections = {p.resource.name: p for p in existing_permissions}

        # remove sections that were unchecked
        for section, permission in existing_sections.items():
            if section not in selected_sections:
                session.delete(permission)

        # add sections that were newly checked
        resources_by_section = {
            resource.name: resource for resource in
            session.query(self.Resource)
            .filter_by(type=ADMIN_SECTION_RESOURCE_TYPE).all()
        }
        for section in selected_sections - existing_sections.keys():
            resource = resources_by_section.get(section)
            if resource is not None:
                permission = self.Permission()
                permission.role_id = role.id
                permission.resource_id = resource.id
                permission.write = False
                session.add(permission)

    def destroy_resource(self, resource, session):
        """Delete existing resource in DB.

        :param object resource: Resource object
        :param Session session: DB session
        """

        if resource.name == self.ADMIN_ROLE_NAME:
            raise ValidationError('The <code>admin</code> role cannot be deleted.')

        Controller.destroy_resource(self, resource, session)
