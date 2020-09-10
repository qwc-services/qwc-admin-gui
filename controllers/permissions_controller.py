from collections import OrderedDict
import math

from flask import render_template, request
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import PermissionForm


class PermissionsController(Controller):
    """Controller for permission model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        super(PermissionsController, self).__init__(
            "Permission", 'permissions', 'permission', 'permissions', app,
            handler
        )

    def resources_for_index_query(self, search_text, role, resource_type,
                                  resource_id, session):
        """Return query for permissions list filtered by role or resource type.

        :param str search_text: Search string for filtering
        :param str role: Optional role filter
        :param str resource_type: Optional resource type filter
        :param int resource_id: Optional resource ID filter
        :param Session session: DB session
        """
        query = session.query(self.Permission). \
            join(self.Permission.role).join(self.Permission.resource). \
            order_by(self.Role.name, self.Resource.type, self.Resource.name)

        if search_text:
            query = query.filter(
                self.Resource.name.ilike("%%%s%%" % search_text)
            )

        if role is not None:
            # filter by role name
            query = query.filter(self.Role.name == role)

        if resource_type is not None:
            # filter by resource type
            query = query.filter(self.Resource.type == resource_type)

        if resource_id is not None:
            # filter by resource ID
            query = query.filter(self.Permission.resource_id == resource_id)

        # eager load relations
        query = query.options(
            joinedload(self.Permission.role),
            joinedload(self.Permission.resource)
        )

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': [self.Permission.id],
            'role': [self.Role.name, self.Resource.type, self.Resource.name],
            'type': [self.Resource.type, self.Role.name, self.Resource.name],
            'resource': [
                self.Resource.name, self.Role.name, self.Resource.type
            ],
            'priority': [
                self.Permission.priority, self.Role.name, self.Resource.type,
                self.Resource.name
            ],
            'write': [
                self.Permission.write, self.Role.name, self.Resource.type,
                self.Resource.name
            ]
        }

        order_by = sortable_columns.get(sort)
        if order_by is not None:
            if not sort_asc:
                # sort in descending order
                order_by[0] = order_by[0].desc()
            # convert multiple columns to tuple
            order_by = tuple(order_by)

        return order_by

    def index(self):
        """Show permissions list."""
        self.setup_models()

        session = self.session()

        # get resources filtered by resource type
        search_text = self.search_text_arg()
        role = request.args.get('role')
        active_resource_type = request.args.get('type')
        resource_id = request.args.get('resource_id')
        query = self.resources_for_index_query(
            search_text, role, active_resource_type, resource_id, session
        )

        # order by sort args
        sort, sort_asc = self.sort_args()
        sort_param = None
        if sort is not None:
            order_by = self.order_by_criterion(sort, sort_asc)
            if order_by is not None:
                if type(order_by) is tuple:
                    # order by multiple sort columns
                    query = query.order_by(None).order_by(*order_by)
                else:
                    # order by single sort column
                    query = query.order_by(None).order_by(order_by)

                sort_param = sort
                if not sort_asc:
                    # append sort direction suffix
                    sort_param = "%s-" % sort

        # paginate
        page, per_page = self.pagination_args()
        num_pages = math.ceil(query.count() / per_page)
        resources = query.limit(per_page).offset((page - 1) * per_page).all()

        pagination = {
            'page': page,
            'num_pages': num_pages,
            'per_page': per_page,
            'per_page_options': self.PER_PAGE_OPTIONS,
            'per_page_default': self.DEFAULT_PER_PAGE,
            'params': {
                'search': search_text,
                'role': role,
                'type': active_resource_type,
                'sort': sort_param
            }
        }

        # query roles
        roles = session.query(self.Role).order_by(self.Role.name).all()

        # query resource types
        resource_types = OrderedDict()
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name)
        for resource_type in query.all():
            resource_types[resource_type.name] = resource_type.description

        # Create dict with all defined parents from resource objects
        parents_dict = {}
        for res in resources:
            if res.resource.parent is not None and \
                    res.resource.parent.id not in parents_dict.keys():
                parents_dict[res.resource.parent.id] = res.resource.parent.name

        session.close()

        return render_template(
            '%s/index.html' % self.templates_dir, resources=resources,
            parents_dict=parents_dict, endpoint_suffix=self.endpoint_suffix,
            pkey=self.resource_pkey(), search_text=search_text,
            pagination=pagination, sort=sort, sort_asc=sort_asc,
            base_route=self.base_route, roles=roles, active_role=role,
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

        # This small code is needed to make sure that the parent object
        # of all resources is called at least once before closing the session.
        # Doing this allows us to call the parent object even after the session
        # was closed.
        for res in resources:
            if res.parent is not None:
                res.parent.name

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
            group['options'].append((r.id, r.name, r.parent))

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
