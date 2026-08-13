ADMIN_ROLE_NAME = 'admin'

ADMIN_SECTION_RESOURCE_TYPE = 'admin_panel_section'

RESERVED_RESOURCE_TYPES = {ADMIN_SECTION_RESOURCE_TYPE}

# Flask endpoint name -> admin section key
ENDPOINT_SECTIONS = {}

# admin section key -> display label
SECTION_LABELS = {}


def tag_new_routes(app, section, fn):
    """Call fn() and tag every route it registers with `section`."""
    before = set(app.url_map.iter_rules())
    fn()
    for rule in set(app.url_map.iter_rules()) - before:
        ENDPOINT_SECTIONS[rule.endpoint] = section


def ensure_admin_panel_resources(config_models, session):
    """Get or create the admin_panel_section resource type and one
    resources row per known admin gui section.

    :param ConfigModels config_models: Helper for ORM models
    :param Session session: DB session
    """
    ResourceType = config_models.model('resource_types')
    Resource = config_models.model('resources')

    resource_type = session.query(ResourceType) \
        .filter_by(name=ADMIN_SECTION_RESOURCE_TYPE).first()
    if resource_type is None:
        resource_type = ResourceType()
        resource_type.name = ADMIN_SECTION_RESOURCE_TYPE
        resource_type.description = "Admin GUI section"
        resource_type.list_order = 0
        resource_type.parent_is_default_allow = False
        resource_type.parents = []
        session.add(resource_type)

    existing_sections = {
        resource.name for resource in
        session.query(Resource)
        .filter_by(type=ADMIN_SECTION_RESOURCE_TYPE).all()
    }
    for section in set(ENDPOINT_SECTIONS.values()) - existing_sections:
        resource = Resource()
        resource.type = ADMIN_SECTION_RESOURCE_TYPE
        resource.name = section
        session.add(resource)
