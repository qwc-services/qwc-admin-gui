from collections import OrderedDict
import math

from flask import flash, render_template, request, session as flask_session
from markupsafe import Markup
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import PermissionForm
from utils import i18n


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

        # A flask session works like a normal cookie, but it is encrypted via the JWT token
        # Only create resources dict if it doesn't exist in the current flask session
        if "permissions" not in flask_session.keys():
            flask_session["permissions"] = {
                "params": {}
            }

        session = self.session()
        # get resources filtered by resource type
        search_text = request.args.get('search')
        # First check wether user deleted the filter
        # "" implies that the user actively deleted the filter and not just changed to a different page
        # (which would not set the filter in the requests params when switching back)
        if search_text == "":
            flask_session["permissions"]['params'].pop("search", None)
        elif search_text is not None:
            flask_session["permissions"]['params']["search"] = search_text
        active_search_text = flask_session["permissions"]['params'].get("search", None)

        role = request.args.get('role')
        if role == "all":
            flask_session["permissions"]['params'].pop("role", None)
        elif role is not None:
            flask_session["permissions"]['params']["role"] = role
        active_role = flask_session["permissions"]['params'].get("role", None)

        resource_type = request.args.get('type')
        if resource_type == "all":
            flask_session["permissions"]['params'].pop("type", None)
        elif resource_type is not None:
            flask_session["permissions"]['params']["type"] = resource_type
        active_resource_type = flask_session["permissions"]['params'].get("type", None)

        resource_id = request.args.get('resource_id')
        query = self.resources_for_index_query(
            active_search_text, active_role, active_resource_type, resource_id, session
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
                flask_session["permissions"]['params']["sort"] = sort_param

        # paginate
        page, per_page = self.pagination_args(flask_session["permissions"]['params'])
        num_pages = math.ceil(query.count() / per_page)
        resources = query.limit(per_page).offset((page - 1) * per_page).all()
        flask_session["permissions"]['params']['per_page'] = per_page

        # Set modified property to True so that the flask_session object
        # updates our cookie
        # Without this, the presistence of data stored in the cookie is not reliable
        # (Sometimes the data is not saved, this fixes the issue)
        # See https://stackoverflow.com/questions/39261260/flask-session-variable-not-persisting-between-requests/39261335#39261335
        flask_session.modified = True

        pagination = {
            'page': page,
            'num_pages': num_pages,
            'per_page_options': self.PER_PAGE_OPTIONS,
            'per_page_default': self.DEFAULT_PER_PAGE,
            'params': flask_session["permissions"]["params"]
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
        all_resources = self.resources_for_index_query(
            None, None, None, resource_id, session
        ).all()
        parents_dict = {}
        for res in all_resources:
            if res.resource.parent is not None and \
                    res.resource.parent.id not in parents_dict.keys():
                parents_dict[res.resource.parent.id] = res.resource.parent.name

        # Warn if role does not have permission on resource parent
        resource_roles = {}
        for res in all_resources:
            resource_roles[res.resource.type + ":" + res.resource.name] = \
                resource_roles.get(res.resource.type + ":" + res.resource.name, []) + [res.role.name]

        public_default_allow_resources = ['attribute', 'layer', 'feature_info_layer', 'print_template']

        role_warnings = []
        for res in all_resources:
            parent = res.resource.parent
            default_parent_roles = ['public'] if parent is not None and res.resource.type in public_default_allow_resources else []
            if parent is not None and \
                    'public' not in resource_roles.get(parent.type + ":" + parent.name, default_parent_roles) and \
                    res.role.name not in resource_roles.get(parent.type + ":" + parent.name, default_parent_roles):
                role_warnings.append(
                    (
                        "The permission for role <b>%s</b> on the <b>%s</b> resource <b>%s</b> " +
                        "has no effect because <b>%s</b> has no permission on the " +
                        "parent resource <b>%s</b>."
                     ) % (res.role.name, res.resource.type, res.resource.name, res.role.name, parent.name)
                )
        if role_warnings:
            flash(Markup("<br />".join(role_warnings)), 'warning')

        session.close()

        return render_template(
            '%s/index.html' % self.templates_dir, resources=resources,
            parents_dict=parents_dict, endpoint_suffix=self.endpoint_suffix,
            pkey=self.resource_pkey(), search_text=active_search_text,
            pagination=pagination, sort=sort, sort_asc=sort_asc,
            base_route=self.base_route, roles=roles, active_role=active_role,
            resource_types=resource_types,
            active_resource_type=active_resource_type, i18n = i18n
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

        resource_id = request.args.get('resource_id')
        if resource_id is not None and resource_id.isdigit():
            form.resource_id.data = int(resource_id)

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
