from collections import OrderedDict
import math

from flask import abort, render_template, request
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import ResourceForm


class ResourcesController(Controller):
    """Controller for resource model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        super(ResourcesController, self).__init__(
            "Resource", 'resources', 'resource', 'resources', app,
            handler
        )

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # resource hierarchy
        app.add_url_rule(
            '/%s/<int:id>/hierarchy' % base_route, 'hierarchy_%s' % suffix,
            self.hierarchy, methods=['GET']
        )

    def resources_for_index_query(self, search_text, resource_type, session):
        """Return query for resources list filtered by resource type.

        :param str search_text: Search string for filtering
        :param str resource_type: Optional resource type filter
        :param Session session: DB session
        """
        query = session.query(self.Resource) \
            .join(self.Resource.resource_types) \
            .order_by(self.ResourceType.list_order, self.Resource.type,
                      self.Resource.name, self.Resource.id)

        if search_text:
            query = query.filter(
                self.Resource.name.ilike("%%%s%%" % search_text)
            )

        if resource_type is not None:
            # filter by resource type
            query = query.filter(self.Resource.type == resource_type)

        # eager load relations
        query = query.options(joinedload(self.Resource.parent))

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': [self.Resource.id],
            'type': [
                self.ResourceType.name, self.Resource.name, self.Resource.id
            ],
            'name': [
                self.Resource.name, self.ResourceType.list_order,
                self.Resource.type, self.Resource.id
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
        """Show resources list."""
        self.setup_models()

        session = self.session()

        # get resources filtered by resource type
        search_text = self.search_text_arg()
        active_resource_type = request.args.get('type')
        query = self.resources_for_index_query(
            search_text, active_resource_type, session
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
                'type': active_resource_type,
                'sort': sort_param
            }
        }

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
            search_text=search_text, pagination=pagination,
            sort=sort, sort_asc=sort_asc,
            base_route=self.base_route, resource_types=resource_types,
            active_resource_type=active_resource_type
        )

    def find_resource(self, id, session):
        """Find resource by ID.

        :param int id: Resource ID
        :param Session session: DB session
        """
        return session.query(self.Resource).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional resource object
        :param bool edit_form: Set if edit form
        """
        form = ResourceForm(obj=resource)

        session = self.session()

        # query resource types
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name)
        resource_types = query.all()

        # query resources
        query = session.query(self.Resource) \
            .join(self.Resource.resource_types) \
            .order_by(self.ResourceType.list_order, self.Resource.type,
                      self.Resource.name)
        # eager load relations
        query = query.options(
            joinedload(self.Resource.resource_type)
        )
        resources = query.all()

        session.close()

        # set choices for type select field
        form.type.choices = [
            (t.name, t.description) for t in resource_types
        ]

        resource_type = request.args.get('type')
        if resource_type is not None:
            form.type.data = resource_type

        # set choices for parent select field
        form.parent_id.choices = [(0, "")] + [
            (r.id, "%s: %s" % (r.type, r.name)) for r in resources
        ]

        # set choices for parent select field, grouped by resource type
        current_type = None
        group = {}
        form.parent_choices = []
        for r in resources:
            if r.type != current_type:
                # add new group
                current_type = r.type
                group = {
                    'resource_type': r.type,
                    'group_label': r.resource_type.description,
                    'options': []
                }

                form.parent_choices.append(group)

            # add resource to group
            group['options'].append((r.id, r.name))

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update resource records in DB.

        :param object resource: Optional resource object
                                (None for create)
        :param FlaskForm form: Form for resource
        :param Session session: DB session
        """
        if resource is None:
            # create new resource
            resource = self.Resource()
            session.add(resource)
        else:
            # update existing resource
            resource = resource

        # update resource
        resource.type = form.type.data
        resource.name = form.name.data

        if form.parent_id.data is not None and form.parent_id.data > 0:
            resource.parent_id = form.parent_id.data
        else:
            resource.parent_id = None

    def hierarchy(self, id):
        """Show resource hierarchy.

        :param int id: Resource ID
        """
        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            # get root resource
            root = resource
            parent = root.parent
            while parent is not None:
                root = parent
                parent = root.parent

            # recursively collect hierarchy
            items = []
            self.collect_resources(root, 0, items, session)

            # query resource types
            resource_types = OrderedDict()
            query = session.query(self.ResourceType) \
                .order_by(self.ResourceType.list_order, self.ResourceType.name)
            for resource_type in query.all():
                resource_types[resource_type.name] = resource_type.description

            session.close()

            return render_template(
                '%s/hierarchy.html' % self.templates_dir, items=items,
                selected_item_id=resource.id,
                endpoint_suffix=self.endpoint_suffix,
                pkey=self.resource_pkey(), resource_types=resource_types
            )
        else:
            # resource not found
            session.close()
            abort(404)

    def collect_resources(self, resource, depth, items, session):
        """Recursively collect resource hierarchy from DB.

        :param object resource: Resource object
        :param int depth: Hierarchy depth
        :param list[object] choices: List of collected resources
        :param Session session: DB session
        """
        # add resource
        items.append({
            'depth': depth,
            'resource': resource
        })

        # get sorted children
        query = session.query(self.Resource) \
            .join(self.Resource.resource_types) \
            .order_by(self.ResourceType.list_order, self.Resource.type,
                      self.Resource.name, self.Resource.id) \
            .filter(self.Resource.parent_id == resource.id)

        # recursively collect children
        for child in query.all():
            self.collect_resources(child, depth + 1, items, session)
