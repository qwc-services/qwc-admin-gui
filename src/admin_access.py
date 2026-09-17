"""Capability-based authorization for admin GUI actions.

Capabilities are ordinary ConfigDB resources/permissions

    admin_capabilities      resource name = capability, e.g. 'manage_users'
                            a permission on it grants the capability unscoped
    admin_capability_scope  child of an admin_capabilities resource,
                            resource name = the role the grant is limited to
"""

import functools

from flask import abort, g
from sqlalchemy import and_


CAPABILITY_TYPE = 'admin_capabilities'
SCOPE_TYPE = 'admin_capability_scope'

MANAGE_USERS = 'manage_users'
MANAGE_GROUPS = 'manage_groups'
MANAGE_ROLES = 'manage_roles'
ASSIGN_ROLE_MEMBERSHIP = 'assign_role_membership'
MANAGE_RESOURCES = 'manage_resources'
MANAGE_PERMISSIONS = 'manage_permissions'
MANAGE_REGISTRATIONS = 'manage_registrations'
SYSTEM_TOOLS = 'system_tools'

CAPABILITIES = [
    MANAGE_USERS, MANAGE_GROUPS, MANAGE_ROLES, ASSIGN_ROLE_MEMBERSHIP,
    MANAGE_RESOURCES, MANAGE_PERMISSIONS, MANAGE_REGISTRATIONS, SYSTEM_TOOLS
]

# capabilities that can be limited to a set of roles
# the rest are all-or-nothing
SCOPED_CAPABILITIES = {
    MANAGE_USERS, MANAGE_GROUPS, MANAGE_ROLES, ASSIGN_ROLE_MEMBERSHIP
}

# whoever can edit permissions can grant themselves anything,
# which would make every other restriction cosmetic
ADMIN_ONLY_CAPABILITIES = {MANAGE_PERMISSIONS}

ADMIN_ROLE_NAME = 'admin'


def permits(grants, capability, subject_roles=None):
    """Return whether grants allow `capability` on a subject.

    :param dict grants: capability -> None (unscoped) or set of role names
    :param str capability: One of CAPABILITIES
    :param subject_roles: Names of the roles held by the subject acted on, or
                          None for actions without a role-scopable subject
    """
    if capability not in grants:
        return False

    scope = grants[capability]
    if scope is None:
        # unscoped grant
        return True
    if subject_roles is None:
        # scoped grant, but this action has no subject to scope by
        return False

    return set(subject_roles) <= scope


def permits_any(grants, capability):
    """Return whether grants allow `capability` at all, scoped or not.

    For page-level access (listings, forms); the actual rows shown and the
    mutations performed are still checked per subject with `permits()`.

    :param dict grants: capability -> None (unscoped) or set of role names
    :param str capability: One of CAPABILITIES
    """
    return capability in grants


def user_role_names(user):
    """Return names of all roles a user holds, directly and via their groups.

    :param object user: User model object
    """
    names = {role.name for role in user.roles_collection}
    for group in user.groups_collection:
        names.update(role.name for role in group.roles_collection)
    return names


def group_role_names(group):
    """Return names of all roles a group holds.

    :param object group: Group model object
    """
    return {role.name for role in group.roles_collection}


def user_in_scope(User, Group, Role, scope):
    """Return filter criteria for users whose every role is within scope.

    :param User: Users model
    :param Group: Groups model
    :param Role: Roles model
    :param set scope: Role names the capability is limited to
    """
    return and_(
        ~User.roles_collection.any(Role.name.notin_(scope)),
        ~User.groups_collection.any(
            Group.roles_collection.any(Role.name.notin_(scope))
        )
    )


def group_in_scope(Group, Role, scope):
    """Return filter criteria for groups whose every role is within scope.

    :param Group: Groups model
    :param Role: Roles model
    :param set scope: Role names the capability is limited to
    """
    return ~Group.roles_collection.any(Role.name.notin_(scope))


def grants():
    """Return the capability grants of the current request's identity."""
    return getattr(g, 'admin_grants', {})


def require(capability):
    """Route decorator: abort with 403 unless `capability` is granted.

    For routes without a role-scopable subject (e.g. the system tools).

    :param str capability: One of CAPABILITIES
    """
    def decorator(view):
        @functools.wraps(view)
        def wrapper(*args, **kwargs):
            if not permits(grants(), capability):
                abort(403)
            return view(*args, **kwargs)
        return wrapper
    return decorator


class AdminAccessControl:
    """Reads capability grants of an identity from the ConfigDB."""

    def __init__(self, access_control):
        """Constructor

        :param AccessControl access_control: Role lookup for identities
        """
        self.access_control = access_control

    def grants(self, identity):
        """Return capability grants of an identity.

        Full admins get every capability, unscoped.

        :param dict|str identity: User identity
        """
        roles = self.access_control.role_names(identity)
        if ADMIN_ROLE_NAME in roles:
            return {capability: None for capability in CAPABILITIES}
        if not roles:
            return {}

        config_models = self.access_control.config_models
        Permission = config_models.model('permissions')
        Resource = config_models.model('resources')
        Role = config_models.model('roles')

        grants = {}
        with config_models.session() as session:
            granted = session.query(Resource) \
                .join(Permission, Permission.resource_id == Resource.id) \
                .join(Role, Permission.role_id == Role.id) \
                .filter(Role.name.in_(roles)) \
                .filter(Resource.type.in_([CAPABILITY_TYPE, SCOPE_TYPE])) \
                .all()

            # resolve scope rows to (capability, role name) via their parent
            capability_resources = session.query(Resource).filter(
                Resource.type == CAPABILITY_TYPE
            ).all()
            capability_names = {
                resource.id: resource.name
                for resource in capability_resources
            }

        for resource in granted:
            if resource.type == CAPABILITY_TYPE:
                capability = resource.name
                scope = None
            else:
                capability = capability_names.get(resource.parent_id)
                scope = resource.name
                if scope == ADMIN_ROLE_NAME:
                    # the admin role is excluded from every scope
                    continue
            if capability not in CAPABILITIES:
                self.access_control.logger.warning(
                    "Ignoring unknown admin capability '%s'" % capability
                )
                continue
            if capability in ADMIN_ONLY_CAPABILITIES:
                continue
            if scope is None:
                grants[capability] = None
            elif capability in SCOPED_CAPABILITIES:
                if grants.get(capability, set()) is None:
                    # already granted unscoped
                    continue
                grants.setdefault(capability, set()).add(scope)

        return grants
