from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import RegistrableGroupForm


class RegistrableGroupsController(Controller):
    """Controller for registrable group model"""

    def __init__(self, app, handler):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        """
        super(RegistrableGroupsController, self).__init__(
            "Registrable Group", 'registrable_groups', 'registrable_group',
            'registrable_groups', app, handler
        )

    def resources_for_index_query(self, search_text, session):
        """Return query for registrable groups list.

        :param str search_text: Search string for filtering
        :param Session session: DB session
        """
        query = session.query(self.RegistrableGroup) \
            .join(self.RegistrableGroup.group) \
            .order_by(self.RegistrableGroup.title)
        if search_text:
            # filter by registrable group title or group name
            query = query.join(self.RegistrableGroup.group) \
                .filter(or_(
                    self.RegistrableGroup.title.ilike("%%%s%%" % search_text),
                    self.Group.name.ilike("%%%s%%" % search_text)
                ))

        # eager load relations
        query = query.options(joinedload(self.RegistrableGroup.group))

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': self.RegistrableGroup.id,
            'title': self.RegistrableGroup.title,
            'description': self.RegistrableGroup.description,
            'group': self.Group.name
        }

        order_by = sortable_columns.get(sort)
        if order_by is not None:
            if not sort_asc:
                # sort in descending order
                order_by = order_by.desc()

        return order_by

    def find_resource(self, id, session):
        """Find registrable group by ID.

        :param int id: Registrable group ID
        :param Session session: DB session
        """
        return session.query(self.RegistrableGroup).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional registrable group object
        :param bool edit_form: Set if edit form
        """
        form = RegistrableGroupForm(obj=resource)

        session = self.session()

        # query groups
        query = session.query(self.Group).order_by(self.Group.name)
        groups = query.all()

        session.close()

        # set choices for group select field
        form.group_id.choices = [(0, "")] + [
            (t.id, t.name) for t in groups
        ]

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update registrable group records in DB.

        :param object resource: Optional registrable group object
                                (None for create)
        :param FlaskForm form: Form for registrable group
        :param Session session: DB session
        """
        if resource is None:
            # create new registrable group
            registrable_group = self.RegistrableGroup()
            session.add(registrable_group)
        else:
            # update existing registrable group
            registrable_group = resource

        # update registrable group
        registrable_group.title = form.title.data
        registrable_group.description = form.description.data

        if form.group_id.data is not None and form.group_id.data > 0:
            registrable_group.group_id = form.group_id.data
        else:
            registrable_group.group_id = None
