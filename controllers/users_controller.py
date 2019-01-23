import os

from flask import json

from .controller import Controller
from forms import UserForm


class UsersController(Controller):
    """Controller for user model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(UsersController, self).__init__(
            "User", 'users', 'user', 'users', app, config_models
        )
        self.User = self.config_models.model('users')
        self.UserInfo = self.config_models.model('user_infos')
        self.Group = self.config_models.model('groups')
        self.Role = self.config_models.model('roles')

        # get custom user info fields
        try:
            user_info_fields = json.loads(
                os.environ.get('USER_INFO_FIELDS', '[]')
            )
        except Exception as e:
            app.logger.error("Could not load USER_INFO_FIELDS:\n%s" % e)
            user_info_fields = []

        UserForm.add_custom_fields(user_info_fields)

    def resources_for_index(self, session):
        """Return users list.

        :param Session session: DB session
        """
        return session.query(self.User).order_by(self.User.name).all()

    def find_resource(self, id, session):
        """Find user by ID.

        :param int id: User ID
        :param Session session: DB session
        """
        return session.query(self.User).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional user object
        :param bool edit_form: Set if edit form
        """
        form = UserForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_collection(
            resource, edit_form, form.groups, self.Group, 'sorted_groups',
            'id', 'name', session
        )
        self.update_form_collection(
            resource, edit_form, form.roles, self.Role, 'sorted_roles', 'id',
            'name', session
        )
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update user records in DB.

        :param object resource: Optional user object
                                (None for create)
        :param FlaskForm form: Form for user
        :param Session session: DB session
        """
        if resource is None:
            # create new user
            user = self.User()
            session.add(user)
        else:
            # update existing user
            user = resource

        # update user
        user.name = form.name.data
        user.description = form.description.data
        user.email = form.email.data
        if form.password.data:
            user.set_password(form.password.data)
        user.failed_sign_in_count = form.failed_sign_in_count.data or 0

        # update user info
        if form.user_info.data:
            # ignore crsf_token of subform
            user_info_data = form.user_info.data
            user_info_data.pop('csrf_token', None)

            if user_info_data:
                user_info = user.user_info
                if user_info is None:
                    # create new user_info
                    user_info = self.UserInfo()
                    # assign to user
                    user_info.user = user

                # update user info fields
                for field, value in user_info_data.items():
                    setattr(user_info, field, value)

        # update groups
        self.update_collection(
            user.groups_collection, form.groups, self.Group, 'id', session
        )
        # update roles
        self.update_collection(
            user.roles_collection, form.roles, self.Role, 'id', session
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
