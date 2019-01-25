from collections import OrderedDict
import math

from flask import render_template, request
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import PermissionForm


class PermissionsController(Controller):
    """Controller for permission model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(PermissionsController, self).__init__(
            "Permission", 'permissions', 'permission', 'permissions', app,
            config_models
        )
        self.Permission = self.config_models.model('permissions')
        self.Role = self.config_models.model('roles')
        self.Resource = self.config_models.model('resources')
        self.ResourceType = self.config_models.model('resource_types')

    def resources_for_index_query(self, session, role, resource_type):
        """Return query for permissions list filtered by role or resource type.

        :param Session session: DB session
        :param str role: Optional role filter
        :param str resource_type: Optional resource type filter
        """
        query = session.query(self.Permission). \
            join(self.Permission.role).join(self.Permission.resource). \
            order_by(self.Role.name, self.Resource.type, self.Resource.name)

        if role is not None:
            # filter by role name
            query = query.filter(self.Role.name == role)

        if resource_type is not None:
            # filter by resource type
            query = query.filter(self.Resource.type == resource_type)

        # eager load relations
        query = query.options(
            joinedload(self.Permission.role),
            joinedload(self.Permission.resource)
        )

        return query

    def index(self):
        """Show permissions list."""

        session = self.session()

        # get resources filtered by resource type
        active_resource_type = request.args.get('type')
        role = request.args.get('role')
        query = self.resources_for_index_query(
            session, role, active_resource_type
        )

        # paginate
        page, per_page = self.pagination_args()
        num_pages = math.ceil(query.count() / per_page)
        resources = query.limit(per_page).offset((page - 1) * per_page).all()

        pagination = {
            'page': page,
            'num_pages': num_pages,
            'per_page': per_page,
            'params': {
                'type': active_resource_type,
                'role': role
            }
        }
        if per_page == self.DEFAULT_PER_PAGE:
            # clear default per_page value
            pagination['per_page'] = None

        # query roles
        roles = session.query(self.Role).order_by(self.Role.name).all()

        # query resource types
        resource_types = OrderedDict()
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name)
        for resource_type in query.all():
            resource_types[resource_type.name] = resource_type.description

        session.close()

        return render_template(
            '%s/index.html' % self.templates_dir, resources=resources,
            endpoint_suffix=self.endpoint_suffix, pkey=self.resource_pkey(),
            pagination=pagination, base_route=self.base_route,
            roles=roles, active_role=role,
            resource_types=resource_types,
            active_resource_type=active_resource_type
        )

    def find_resource(self, id, session):
        """Find permission by ID.

        :param int id: Permission ID
        :param Session session: DB session
        """
        return session.query(self.Permission).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional permission object
        :param bool edit_form: Set if edit form
        """
        form = PermissionForm(obj=resource)

        # load related resources from DB
        session = self.session()

        # query roles
        query = session.query(self.Role).order_by(self.Role.name)
        roles = query.all()

        # query resource types
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name)
        resource_types = query.all()

        # query resources
        query = session.query(self.Resource) \
            .join(self.Resource.resource_type) \
            .order_by(self.ResourceType.list_order, self.Resource.type,
                      self.Resource.name)
        # eager load relations
        query = query.options(
            joinedload(self.Resource.resource_type)
        )
        resources = query.all()

        session.close()

        # set choices for role select field
        form.role_id.choices = [(0, "")] + [
            (r.id, r.name) for r in roles
        ]

        # set choices for resource type filter
        form.resource_types = [
            (r.name, r.description) for r in resource_types
        ]

        # set choices for resource select field
        form.resource_id.choices = [(0, "")] + [
            (r.id, "%s: %s" % (r.type, r.name)) for r in resources
        ]

        # set choices for resource select field, grouped by resource type
        current_type = None
        group = {}
        form.resource_choices = []
        for r in resources:
            if r.type != current_type:
                # add new group
                current_type = r.type
                group = {
                    'resource_type': r.type,
                    'group_label': r.resource_type.description,
                    'options': []
                }

                form.resource_choices.append(group)

            # add resource to group
            group['options'].append((r.id, r.name))

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update resource records in DB.

        :param object resource: Optional permission object
                                (None for create)
        :param FlaskForm form: Form for permission
        :param Session session: DB session
        """
        if resource is None:
            # create new permission
            permission = self.Permission()
            session.add(permission)
        else:
            # update existing permission
            permission = resource

        # update permission
        permission.priority = form.priority.data
        permission.write = form.write.data

        if form.role_id.data > 0:
            permission.role_id = form.role_id.data
        else:
            permission.role_id = None

        if form.resource_id.data > 0:
            permission.resource_id = form.resource_id.data
        else:
            permission.resource_id = None
