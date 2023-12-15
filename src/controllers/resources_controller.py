from collections import OrderedDict
import math
import requests
import json
from urllib.parse import urljoin
from operator import itemgetter

from flask import abort, flash, redirect, render_template, request, url_for, session as flask_session
from sqlalchemy.exc import IntegrityError, InternalError
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.declarative import DeclarativeMeta

from .controller import Controller
from forms import ImportResourceForm, ResourceForm
from utils import i18n


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
        # delete cascaded
        app.add_url_rule(
            '/%s/<int:id>/cascaded' % base_route,
            'destroy_cascaded_%s' % suffix,
            self.destroy_cascaded, methods=['DELETE', 'POST']
        )
        # delete selected
        app.add_url_rule(
            '/%s/delete_multiple' % base_route,
            'destroy_multiple_%s' % suffix,
            self.destroy_multiple, methods=['DELETE', 'POST']
        )
        # resource hierarchy
        app.add_url_rule(
            '/%s/<int:id>/hierarchy' % base_route, 'hierarchy_%s' % suffix,
            self.hierarchy, methods=['GET']
        )
        # import maps
        app.add_url_rule(
            '/%s/import_maps' % base_route, 'import_maps_%s' % suffix,
            self.import_maps, methods=['POST']
        )
        # import resource children
        app.add_url_rule(
            '/%s/<int:id>/import_children' % base_route,
            'import_children_%s' % suffix,
            self.import_children, methods=['POST']
        )
        # import resources from parent map
        app.add_url_rule(
            '/%s/<int:id>/import' % base_route,
            'import_%s' % suffix,
            self.import_resources, methods=['GET', 'POST']
        )
        app.add_url_rule(
            '/%s/<int:id>/import_from_parent_map' % base_route,
            'import_%s_from_parent_map' % suffix,
            self.import_resources_from_parent_map, methods=['GET', 'POST']
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

        # A flask session works like a normal cookie, but it is encrypted via the JWT token
        # Only create resources dict if it doesn't exist in the current flask session
        if "resources" not in flask_session.keys():
            flask_session["resources"] = {
                "params": {}
            }

        session = self.session()

        # get resources filtered by resource type
        search_text = request.args.get('search')
        # First check wether user deleted the filter
        # "" implies that the user actively deleted the filter and not just changed to a different page
        # (which would not set the filter in the requests params when switching back)
        if search_text == "":
            flask_session["resources"]['params'].pop("search", None)
        elif search_text is not None:
            flask_session["resources"]['params']["search"] = search_text
        active_search_text = flask_session["resources"]['params'].get("search", None)

        resource_type = request.args.get('type')
        if resource_type == "all":
            flask_session["resources"]['params'].pop("type", None)
        elif resource_type is not None:
            flask_session["resources"]['params']["type"] = resource_type
        active_resource_type = flask_session["resources"]['params'].get("type", None)

        query = self.resources_for_index_query(
            active_search_text, active_resource_type, session
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
                flask_session["resources"]['params']["sort"] = sort_param

        # paginate
        page, per_page = self.pagination_args(flask_session["resources"]['params'])
        num_pages = math.ceil(query.count() / per_page)
        resources = query.limit(per_page).offset((page - 1) * per_page).all()
        flask_session["resources"]['params']['per_page'] = per_page

        check_unused = request.args.get('check_unused')
        if check_unused == "True":
            flask_session["resources"]['params']['check_unused'] = check_unused
            self._check_unused_resources(resources)
        else:
            flask_session["resources"]['params'].pop('check_unused', None)
        active_check_unused = flask_session["resources"]['params'].get('check_unused', None)

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
            'params': flask_session["resources"]["params"]
        }

        # query resource types
        resource_types = OrderedDict()
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name)
        for resource_type in query.all():
            resource_types[resource_type.name] = resource_type.description

        session.close()

        have_config_generator = True if self.handler().config().get(
            "config_generator_service_url",
            "http://qwc-config-service:9090"
        ) else False

        return render_template(
            '%s/index.html' % self.templates_dir, resources=resources,
            endpoint_suffix=self.endpoint_suffix, pkey=self.resource_pkey(),
            search_text=active_search_text, pagination=pagination,
            sort=sort, sort_asc=sort_asc, check_unused=active_check_unused,
            base_route=self.base_route, resource_types=resource_types,
            active_resource_type=active_resource_type,
            have_config_generator=have_config_generator, i18n=i18n
        )

    def find_resource(self, id, session):
        """Find resource by ID.

        :param int id: Resource ID
        :param Session session: DB session
        """
        return session.query(self.Resource).filter_by(id=id).first()

    def destroy_cascaded(self, id):
        """Delete existing resource and its children.

        :param int id: Resource ID
        """
        # workaround for missing DELETE methods in HTML forms
        #   using hidden form parameter '_method'
        method = request.form.get('_method', request.method).upper()
        if method != 'DELETE':
            abort(405)

        self.setup_models()

        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            parent_id = resource.parent_id

            try:
                # delete and commit resource and its children
                self.destroy_resource_cascaded(resource, session)
                session.commit()
                self.update_config_timestamp(session)
                flash(
                    'Resource and its children have been deleted.', 'success'
                )
            except InternalError as e:
                flash('InternalError: %s' % e.orig, 'error')
            except IntegrityError as e:
                flash('IntegrityError: %s' % e.orig, 'error')

            session.close()

            if parent_id:
                # redirect to hierarchy view of parent resource
                return redirect(url_for(
                    'hierarchy_%s' % self.endpoint_suffix, id=parent_id
                ))
            else:
                # redirect to resources list
                return redirect(url_for(self.base_route))
        else:
            # resource not found
            session.close()
            abort(404)

    def destroy_resource_cascaded(self, resource, session):
        """Recursively delete existing resource and its children in DB.

        :param object resource: Resource object
        :param Session session: DB session
        """
        # recursively delete child resources (depth first)
        for child in resource.children:
            self.destroy_resource_cascaded(child, session)

        # delete resource
        session.delete(resource)

    def destroy_multiple(self):
        """Delete selected resources.
        """
        # workaround for missing DELETE methods in HTML forms
        #   using hidden form parameter '_method'
        method = request.form.get('_method', request.method).upper()
        if method != 'DELETE':
            abort(405)

        self.setup_models()

        selected_id_resources = request.form.getlist("resource_checkbox")

        session = self.session()
        for id in selected_id_resources:
            # find resource
            resource = self.find_resource(id, session)

            if resource is not None:
                try:
                    # delete and commit resource and its children
                    self.destroy_resource(resource, session)
                    session.commit()
                    self.update_config_timestamp(session)
                    flash(
                        f"{self.resource_name} '{resource.name}' has been deleted.", 'success'
                    )
                except InternalError as e:
                    flash('InternalError: %s' % e.orig, 'error')
                except IntegrityError as e:
                    flash('IntegrityError: %s' % e.orig, 'error')

            else:
                # resource not found
                session.close()
                abort(404)
        session.close()
        # redirect to resources list
        return redirect(url_for(self.base_route))

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

    def create_import_form(self):
        """Return form with fields loaded from DB.

        :param object resource: Optional resource object
        :param bool edit_form: Set if edit form
        """
        form = ImportResourceForm()

        session = self.session()

        # query resource types
        query = session.query(self.ResourceType) \
            .order_by(self.ResourceType.list_order, self.ResourceType.name) \
            .filter(self.ResourceType.name.in_(('layer', 'data', 'data_create', 'data_read', 'data_update', 'data_delete')))
        resource_types_to_import_from_map = query.all()

        # query permission roles
        roles = session.query(self.Role).order_by(self.Role.name).all()

        session.close()

        # set choices for import_type select field
        form.import_type.choices = [
            (t.name, t.description) for t in resource_types_to_import_from_map
        ]
        # set choices for permission_role_id select field
        form.role_id.choices = [(0, "")] + [
            (r.id, r.name) for r in roles
        ]

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
        self.setup_models()

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
                pkey=self.resource_pkey(), resource_types=resource_types, i18n=i18n
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
        # query resource permissions
        query = session.query(self.Permission) \
            .filter(self.Permission.resource_id == resource.id)
        has_permissions = query.count() > 0

        permissions = []
        for permission in query.all():
            permissions.append({
                "role": permission.role.name,
                "write": permission.write
            })

        # add resource
        items.append({
            'depth': depth,
            'resource': resource,
            'has_permissions': has_permissions,
            'permissions': permissions
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

    def import_maps(self):
        """Import map resources."""
        # get config generator URL
        config_generator_service_url = self.handler().config().get(
            "config_generator_service_url",
            "http://qwc-config-service:9090"
        )

        session = None
        try:
            # get maps for tenant from config generator service
            url = urljoin(config_generator_service_url, 'maps')
            tenant = self.handler().tenant
            response = requests.get(url, params={'tenant': tenant})
            if response.status_code != requests.codes.ok:
                self.logger.error(
                    "Could not get maps from %s:\n%s" %
                    (response.url, response.content)
                )
                flash(
                    '%s Status %s' %(
                    i18n('interface.resources.import_maps_message_error'), response.status_code), 
                    'error'
                )
                return redirect(url_for(self.base_route))

            maps_from_config = response.json()

            self.setup_models()
            session = self.session()

            # get maps from ConfigDB
            query = session.query(self.Resource) \
                .filter(self.Resource.type == 'map')
            maps = [
                resource.name for resource in query.all()
            ]

            # add additional maps to ConfigDB
            new_maps = sorted(list(set(maps_from_config) - set(maps)))
            if new_maps:
                for map_name in new_maps:
                    # create new map resource
                    resource = self.Resource()
                    resource.type = 'map'
                    resource.name = map_name
                    session.add(resource)

                # commit resources
                session.commit()
                self.update_config_timestamp(session)

                flash(
                    '%d %s' % (
                    len(new_maps), i18n('interface.resources.add_maps_message_success')), 
                    'success'
                )
            else:
                flash(i18n('interface.resources.add_maps_message_error'), 'info')

            session.close()

            return redirect(url_for(self.base_route, type='map'))
        except Exception as e:
            if session:
                session.close()
            msg = "%s %s" % (i18n('interface.resources.import_maps_message_error'), e)
            self.logger.error(msg)
            flash(msg, 'error')
            return redirect(url_for(self.base_route))

    def _check_unused_resources(self, resources):
        """Check for unreferenced resources."""
        # get config generator URL
        config_generator_service_url = self.handler().config().get(
            "config_generator_service_url",
            "http://qwc-config-service:9090"
        )
        url = urljoin(config_generator_service_url, "resources")
        tenant = self.handler().tenant
        response = requests.get(url, params={'tenant': tenant})
        if response.status_code != requests.codes.ok:
            self.logger.error(
                "Could not get all resources from %s:\n%s" %
                (response.url, response.content)
            )
            resources_from_config = []
        else:
            # List of resources that are referenced somewhere in the config of
            # a service
            resources_from_config = response.json()

        self.logger.debug("resources_from_config: %s" % resources_from_config)
        maps_from_config = list(map(itemgetter('map'), resources_from_config))

        # Iterate over all registered resources and
        # check whether they are referenced in a service config or not

        # resources_from_config is a dict with all maps and their
        # layers(and attributes) that the ConfigGenerator sees.

        for res in resources:
            if res.type == "map":
                if res.name not in maps_from_config:
                    res.not_referenced = True

                continue
            elif res.type in ["layer", "attribute", "data"]:
                # Check if parent exists --> If not, then resource is not referenced
                if res.parent is None:
                    res.not_referenced = True
                else:
                    # Iterate over all resources found in the config
                    res.not_referenced = True
                    for resource in resources_from_config:
                        # data and layer types are handled the same

                        # When iterating over the `resources_from_config` list,
                        # the existance of the `res` resource will be checked in all maps.
                        # This means that when have found the resource in a map, this loop should end.
                        if res.not_referenced == False:
                            break

                        # Check whether the resource parent is referenced
                        if "*" in res.name and res.parent.name in maps_from_config:
                            res.not_referenced = False
                            continue
                        elif (res.type == "data" or res.type == "layer") and \
                            res.parent.name in maps_from_config and \
                                resource["map"] == res.parent.name:

                            # Here we use generator comprehension to boost the
                            # performance
                            res.not_referenced = next(
                                (False for layer in resource[
                                    "layers"] if res.name in layer.keys()),
                                True)
                            # Stop here, because we iterated over
                            # the maps(parent) resources and didn't find
                            # any reference
                            continue

                        elif res.type == "attribute":
                            # Here we use generator comprehension to boost the
                            # performance
                            # What we do here is we iterate over the layers list and check the following
                            # - Is the resources parent (which is a layer) in the layers list?
                            # - Does the corresponding layer attribute list contain the resource name?
                            res.not_referenced = next(
                                (False for layer in resource["layers"] if res.parent.name in layer.keys() \
                                    and res.name in list(layer.values())[0]), True)
                            # Stop here, because we iterated over
                            # the maps(parent) resources and didn't find
                            # any reference
                            continue
            else:
                # Resources are marked as referenced per default, if we don't check them
                res.not_referenced = False

            if res.not_referenced:
                self.logger.info("Unreferenced resource: %s" % json.dumps(
                    res, cls=AlchemyEncoder))

    def import_children(self, id):
        """Import child resources for a resource:

        * Import layers for a map

        :param int id: Resource ID
        """
        self.setup_models()

        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            # get config generator URL
            config_generator_service_url = self.handler().config().get(
                "config_generator_service_url",
                "http://qwc-config-service:9090"
            )
            if resource.type == 'map':
                self.import_layers(
                    resource, config_generator_service_url, session
                )
            else:
                flash(i18n('interface.resources.import_children_message_error'),
                      'warning')

            session.close()

            return redirect(
                url_for('hierarchy_%s' % self.endpoint_suffix, id=id)
            )
        else:
            # resource not found
            session.close()
            abort(404)

    def import_layers(self, map_resource, config_generator_service_url,
                      session):
        """Import layers for a map.

        :param object map_resource: Map resource
        :param str config_generator_service_url: ConfigGenerator service URL
        :param Session session: DB session
        """
        try:
            # get map details from config generator service
            url = urljoin(
                config_generator_service_url, 'maps/%s' % map_resource.name
            )
            tenant = self.handler().tenant
            response = requests.get(url, params={'tenant': tenant})
            if response.status_code != requests.codes.ok:
                self.logger.error(
                    "Could not get map details from %s:\n%s" %
                    (response.url, response.content)
                )
                flash(
                    '%s Status %s' %(
                    i18n('interface.resources.import_layers_message_error'), response.status_code), 'error'
                )
                return redirect(url_for(self.base_route))

            layers_from_config = response.json().get('layers', [])

            if layers_from_config:
                # get map layers from ConfigDB
                query = session.query(self.Resource) \
                    .filter(self.Resource.type == 'layer') \
                    .filter(self.Resource.parent_id == map_resource.id)
                layers = [
                    resource.name for resource in query.all()
                ]

                # add additional layers to ConfigDB
                new_layers = sorted(
                    list(set(layers_from_config) - set(layers))
                )
                if new_layers:
                    for layer in new_layers:
                        # create new layer resource
                        resource = self.Resource()
                        resource.type = 'layer'
                        resource.name = layer
                        resource.parent_id = map_resource.id
                        session.add(resource)

                    # commit resources
                    session.commit()
                    self.update_config_timestamp(session)

                    flash(
                        '%d %s' %(
                        len(new_layers), i18n('interface.resources.add_layers_message_success')), 'success'
                    )
                else:
                    flash(i18n('interface.resources.add_map_message_error'), 'info')
            else:
                # map not found or no layers
                flash(i18n('interface.resources.add_layers_map_message_error'), 'warning')
        except Exception as e:
            msg = "%s %s" % (i18n('interface.resources.import_layers_message_error'), e)
            self.logger.error(msg)
            flash(msg, 'error')

    def import_resources(self, id):
        """Import child resources for a map:

        * Import resources for a map

        :param int id: Resource ID
        """
        self.setup_models()
        template = '%s/import_form.html' % self.templates_dir
        form = self.create_import_form()
        title = "%s %s" % (i18n('interface.resources.import_resources_title'), self.resource_name)
        action = url_for('import_%s_from_parent_map' % self.endpoint_suffix, id=id)

        return render_template(
            template, title=title, form=form, action=action, method='POST', i18n=i18n
        )

    def import_resources_from_parent_map(self, id):
        """Import layers for a map.

        :param int id: Resource ID
        """
        self.setup_models()
        form = self.create_import_form()
        if form.validate_on_submit():
            try:
                # find resource
                session = self.session()
                parent_resource = self.find_resource(id, session)
                if parent_resource is not None:
                    # get config generator URL
                    config_generator_service_url = self.handler().config().get(
                        "config_generator_service_url",
                        "http://qwc-config-service:9090"
                    )
                    type = form.import_type.data
                    if parent_resource.type == 'map':

                        # get map details from config generator service
                        url = urljoin(
                            config_generator_service_url, 'maps/%s' % parent_resource.name
                        )
                        tenant = self.handler().tenant
                        response = requests.get(url, params={'tenant': tenant})
                        if response.status_code != requests.codes.ok:
                            self.logger.error(
                                "Could not get map details from %s:\n%s" %
                                (response.url, response.content)
                            )
                            flash(
                                '%s Status %s' % (
                                i18n('interface.resources.import_resources_message_error'), response.status_code), 'error'
                            )
                            return redirect(url_for(self.base_route))

                        layers_from_config = response.json().get('layers', [])

                        if layers_from_config:
                            new_resources = []
                            new_permissions = []
                            for layer in layers_from_config:
                                # first query to know if resource already exists
                                query = session.query(self.Resource) \
                                    .filter(self.Resource.name == layer) \
                                    .filter(self.Resource.type == type) \
                                    .filter(self.Resource.parent_id == parent_resource.id)
                                resources = query.all()

                                if not resources:
                                    # resource does not exist in database so create new resource
                                    resource = self.Resource()
                                    resource.type = type
                                    resource.name = layer
                                    resource.parent_id = parent_resource.id
                                    new_resources.append(resource)
                                    session.add(resource)

                                    # new query to get id of new resource
                                    query = session.query(self.Resource) \
                                        .filter(self.Resource.name == layer) \
                                        .filter(self.Resource.type == type) \
                                        .filter(self.Resource.parent_id == parent_resource.id)
                                    resources = query.all()

                                # handle permission for existing or new resource if role has been chosen
                                role = form.role_id.data
                                if role > 0:
                                    for resource in resources:
                                        resource_id = resource.__dict__.get('id')
                                        # query resource permissions
                                        query = session.query(self.Permission) \
                                            .filter(self.Permission.resource_id == resource_id) \
                                            .filter(self.Permission.role_id == role)

                                        permissions = []
                                        for permission in query.all():
                                            permissions.append({
                                                "role": permission.role.name,
                                                "write": permission.write
                                            })
                                        if not permissions:
                                            # create new permission for resource
                                            permission = self.Permission()
                                            session.add(permission)

                                            # update permission
                                            permission.priority = form.priority.data
                                            permission.write = form.write.data

                                            permission.role_id = role

                                            permission.resource_id = resource_id
                                            new_permissions.append(permission)                                

                            # commit resources
                            session.commit()
                            self.update_config_timestamp(session)

                            if new_resources:
                                flash(
                                    '%d %s' % (
                                    len(new_resources), i18n('interface.resources.add_resources_message_success')), 
                                    'success'
                                )
                            else:
                                flash(i18n('interface.resources.add_resources_message_error'), 'info')

                            if new_permissions:
                                flash(
                                    '%d %s' % (
                                    len(new_permissions), i18n('interface.resources.add_permissions_message_success')), 'success'
                                )
                            else:
                                flash(i18n('interface.resources.add_permissions_message_error'), 'info')
                        else:
                            # map not found or no layers
                            flash(i18n('interface.resources.add_layers_map_message_error'), 'warning')

                    else:
                        flash(i18n('interface.resources.import_children_message_error'),
                            'warning')

                else:
                    # resource not found
                    session.close()
                    abort(404)

                session.close()

                return redirect(
                    url_for('hierarchy_%s' % self.endpoint_suffix, id=id)
                )                
            except Exception as e:
                if session:
                    session.close()
                msg = "%s %s" % (i18n('interface.resources.import_resources_message_error'), e)
                self.logger.error(msg)
                flash(msg, 'error')
                return redirect(
                    url_for(self.base_route)
                )
        else:
            flash('%s %s.' % (i18n('interface.resources.import_ressources_parent_message_error'), parent_resource),
                  'warning')

class AlchemyEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj.__class__, DeclarativeMeta):
            # an SQLAlchemy class
            fields = {}
            for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata']:
                data = obj.__getattribute__(field)
                try:
                    json.dumps(data)
                    fields[field] = data
                except TypeError:
                    fields[field] = None
            # a json-encodable dict
            return fields

        return json.JSONEncoder.default(self, obj)
