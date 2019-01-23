from .controller import Controller
from forms import GroupForm


class GroupsController(Controller):
    """Controller for group model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(GroupsController, self).__init__(
            "Group", 'groups', 'group', 'groups', app, config_models
        )
        self.Group = self.config_models.model('groups')
        self.User = self.config_models.model('users')
        self.Role = self.config_models.model('roles')

    def resources_for_index(self, session):
        """Return groups list.

        :param Session session: DB session
        """
        return session.query(self.Group).order_by(self.Group.name).all()

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

    def update_form_collection(
        self, resource, edit_form, multi_select, relation_model,
        collection_attr, id_attr, name_attr, session
    ):
        """Helper to update collection multi-select field for resource.

        :param object resource: Optional resource object for edit (e.g. group)
        :param bool edit_form: Set if edit form
        :param SelectMultipleField multi_select: MultiSelect for relations
                                                 (e.g. form.users)
        :param object relation_model: ConfigModel for relation (e.g. User)
        :param str collection_attr: Collection attribute for resource
                                    (e.g. 'users_collection')
        :param str id_attr: ID attribute of relation model (e.g. 'id')
        :param str name_attr: Name attribute of relation model (e.g. 'name')
        :param Session session: DB session
        """
        if edit_form:
            # add collection items for resource on edit
            items = getattr(resource, collection_attr)
            multi_select.data = [
                getattr(i, id_attr) for i in items
            ]

        # load related resources from DB
        query = session.query(relation_model). \
            order_by(getattr(relation_model, name_attr))
        items = query.all()

        # set choices for collection select field
        multi_select.choices = [
            (getattr(i, id_attr), getattr(i, name_attr)) for i in items
        ]

    def update_collection(self, collection, multi_select, relation_model,
                          id_attr, session):
        """Helper to add or remove relations from a resource collection.

        :param object collection: Collection of resource relations
                                  (e.g. Group.user_collection)
        :param SelectMultipleField multi_select: MultiSelect for relations
                                                 (e.g. form.users)
        :param object relation_model: ConfigModel for relation (e.g. User)
        :param str id_attr: ID attribute of relation model (e.g. 'id')
        :param Session session: DB session
        """
        # lookup for relation of resource
        resource_relations = {}
        for relation in collection:
            resource_relations[relation.id] = relation

        # update relations
        relation_ids = []
        for relation_id in multi_select.data:
            # get relation from ConfigDB
            filter = {id_attr: relation_id}
            query = session.query(relation_model).filter_by(**filter)
            relation = query.first()

            if relation is not None:
                relation_ids.append(relation_id)
                if relation_id not in resource_relations:
                    # add relation to resource
                    collection.append(relation)

        # remove removed relations
        for relation in resource_relations.values():
            if relation.id not in relation_ids:
                # remove relation from resource
                collection.remove(relation)
