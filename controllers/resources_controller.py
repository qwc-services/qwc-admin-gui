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

    def resources_for_index(self, session):
        """Return resources list.

        :param Session session: DB session
        """
        query = session.query(self.Resource). \
            order_by(self.Resource.type, self.Resource.name)
        # eager load relations
        query = query.options(joinedload(self.Resource.parent))

        return query.all()

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
        query = session.query(self.Resource) \
            .order_by(self.Resource.type, self.Resource.name) \
            .filter(self.Resource.type != 'attribute')
        resources = query.all()
        session.close()

        # set choices for parent select field
        form.parent_id.choices = [(0, "")] + [
            (r.id, "%s: %s" % (r.type, r.name)) for r in resources
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

        if form.parent_id.data > 0:
            resource.parent_id = form.parent_id.data
        else:
            resource.parent_id = None
