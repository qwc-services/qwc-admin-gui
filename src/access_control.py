from sqlalchemy import distinct
from sqlalchemy.sql import text as sql_text, exists

from qwc_services_core.config_models import ConfigModels

from admin_sections import ADMIN_SECTION_RESOURCE_TYPE, SECTION_LABELS, \
    ensure_admin_panel_resources


class AccessControl:

    # name of admin iam.role
    ADMIN_ROLE_NAME = 'admin'

    def __init__(self, handler, logger):
        """Constructor

        :param ConfigModels handler: Helper for ORM models
        :param Logger logger: Application logger
        """
        self.handler = handler
        self.logger = logger

    def is_admin(self, identity):
        db_engine = self.handler().db_engine()
        self.config_models = ConfigModels(
            db_engine, self.handler().conn_str(),
            qwc_config_schema=self.handler().qwc_config_schema()
        )

        # Extract user infos from identity
        if isinstance(identity, dict):
            username = identity.get('username')
            groups = identity.get('groups', [])
        else:
            username = identity
            groups = []
        with self.config_models.session() as session:
            admin_role = self.admin_role_query(username, groups, session)

        return admin_role

    def get_accessible_sections(self, identity, full_access):
        """Return the admin panel section keys accessible to identity.

        Must be called after is_admin(identity) in the same request

        :param identity: JWT identity
        :param bool full_access: Set if identity should see every known
                                  section without querying per-role grants
        :rtype: set(str)
        """
        if full_access:
            return set(SECTION_LABELS.keys())

        with self.config_models.session() as session:
            return self.accessible_sections(identity, session)

    def admin_role_query(self, username, groups, session):
        """Create base query for all permissions of a user and group.

        Combine permissions from roles of user and user groups, group roles and
        public role.

        :param str username: User name
        :param list(str) groups: List of groups name
        :param Session session: DB session
        """
        Role = self.config_models.model('roles')
        Group = self.config_models.model('groups')
        User = self.config_models.model('users')

        # create query
        query = session.query(Role)

        # query permissions from roles in user groups
        groups_roles_query = query.join(Role.groups_collection) \
            .join(Group.users_collection) \
            .filter(User.name == username)

        # query permissions from direct user roles
        user_roles_query = query.join(Role.users_collection) \
            .filter(User.name == username)

        # query permissions from group roles
        group_roles_query = query.join(Role.groups_collection) \
            .filter(Group.name.in_(groups))

        # combine queries
        query = groups_roles_query.union(user_roles_query) \
            .union(group_roles_query) \
            .filter(Role.name == self.ADMIN_ROLE_NAME)

        (admin_role, ), = session.query(query.exists())

        return admin_role

    def ensure_admin_panel_resources(self, session):
        """Wrapper around admin_sections.ensure_admin_panel_resources for
        callers that already hold an AccessControl instance.

        :param Session session: DB session
        """
        ensure_admin_panel_resources(self.config_models, session)

    def has_section_access(self, identity, section, session):
        """Return whether identity has permission for an admin panel
        section. Mirrors admin_role_query's join pattern

        :param identity: JWT identity (dict with 'username'/'groups', or a
                          plain username string)
        :param str section: Admin panel section key
        :param Session session: DB session
        """
        if isinstance(identity, dict):
            username = identity.get('username')
            groups = identity.get('groups', [])
        else:
            username = identity
            groups = []

        Role = self.config_models.model('roles')
        Group = self.config_models.model('groups')
        User = self.config_models.model('users')
        Resource = self.config_models.model('resources')
        Permission = self.config_models.model('permissions')

        # create query
        query = session.query(Role) \
            .join(Permission, Permission.role_id == Role.id) \
            .join(Permission.resource) \
            .filter(Resource.type == ADMIN_SECTION_RESOURCE_TYPE) \
            .filter(Resource.name == section)

        # query permissions from roles in user groups
        groups_roles_query = query.join(Role.groups_collection) \
            .join(Group.users_collection) \
            .filter(User.name == username)

        # query permissions from direct user roles
        user_roles_query = query.join(Role.users_collection) \
            .filter(User.name == username)

        # query permissions from group roles
        group_roles_query = query.join(Role.groups_collection) \
            .filter(Group.name.in_(groups))

        # combine queries
        query = groups_roles_query.union(user_roles_query) \
            .union(group_roles_query)

        (has_access, ), = session.query(query.exists())

        return has_access

    def accessible_sections(self, identity, session):
        """Return the full set of admin panel section keys granted to
        identity, in a single query.

        :param identity: JWT identity (dict with 'username'/'groups', or a
                          plain username string)
        :param Session session: DB session
        :rtype: set(str)
        """
        if isinstance(identity, dict):
            username = identity.get('username')
            groups = identity.get('groups', [])
        else:
            username = identity
            groups = []

        Role = self.config_models.model('roles')
        Group = self.config_models.model('groups')
        User = self.config_models.model('users')
        Resource = self.config_models.model('resources')
        Permission = self.config_models.model('permissions')

        # create query
        query = session.query(Resource.name) \
            .join(Permission, Permission.resource_id == Resource.id) \
            .join(Permission.role) \
            .filter(Resource.type == ADMIN_SECTION_RESOURCE_TYPE)

        # query permissions from roles in user groups
        groups_roles_query = query.join(Role.groups_collection) \
            .join(Group.users_collection) \
            .filter(User.name == username)

        # query permissions from direct user roles
        user_roles_query = query.join(Role.users_collection) \
            .filter(User.name == username)

        # query permissions from group roles
        group_roles_query = query.join(Role.groups_collection) \
            .filter(Group.name.in_(groups))

        # combine queries (UNION de-duplicates section names)
        query = groups_roles_query.union(user_roles_query) \
            .union(group_roles_query)

        return {name for (name, ) in query.all()}
