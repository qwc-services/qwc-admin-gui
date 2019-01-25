from collections import OrderedDict
import math

from flask import render_template, request
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import ResourceForm


class ResourcesController(Controller):
    """Controller for resource model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(ResourcesController, self).__init__(
            "Resource", 'resources', 'resource', 'resources', app,
            config_models
        )
        self.Resource = self.config_models.model('resources')
        self.ResourceType = self.config_models.model('resource_types')

    def resources_for_index_query(self, session, resource_type):
        """Return query for resources list filtered by resource type.

        :param Session session: DB session
        :param str resource_type: Optional resource type filter
        """
        query = session.query(self.Resource) \
            .join(self.Resource.resource_types) \
            .order_by(self.ResourceType.list_order, self.Resource.type,
                      self.Resource.name)

        if resource_type is not None:
            # filter by resource type
            query = query.filter(self.Resource.type == resource_type)

        # eager load relations
        query = query.options(joinedload(self.Resource.parent))

        return query

    def index(self):
        """Show resources list."""

        session = self.session()

        # get resources filtered by resource type
        active_resource_type = request.args.get('type')
        query = self.resources_for_index_query(session, active_resource_type)

        # paginate
        page, per_page = self.pagination_args()
        num_pages = math.ceil(query.count() / per_page)
        resources = query.limit(per_page).offset((page - 1) * per_page).all()

        pagination = {
            'page': page,
            'num_pages': num_pages,
            'per_page': per_page,
            'params': {
                'type': active_resource_type
            }
        }
        if per_page == self.DEFAULT_PER_PAGE:
            # clear default per_page value
            pagination['per_page'] = None

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
            resource_types=resource_types,
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
