from sqlalchemy import distinct
from sqlalchemy.sql import text as sql_text, exists

from qwc_services_core.config_models import ConfigModels


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
        self.config_models = ConfigModels(db_engine, self.handler().conn_str())

        # Extract user infos from identity
        if isinstance(identity, dict):
            username = identity.get('username')
            group = identity.get('group')
        else:
            username = identity
            group = None
        session = self.config_models.session()
        admin_role = self.admin_role_query(username, group, session)
        session.close()

        return admin_role

    def admin_role_query(self, username, group, session):
        """Create base query for all permissions of a user and group.

        Combine permissions from roles of user and user groups, group roles and
        public role.

        :param str username: User name
        :param str group: Group name
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
            .filter(Group.name == group)

        # combine queries
        query = groups_roles_query.union(user_roles_query) \
            .union(group_roles_query) \
            .filter(Role.name == self.ADMIN_ROLE_NAME)

        (admin_role, ), = session.query(query.exists())

        return admin_role
