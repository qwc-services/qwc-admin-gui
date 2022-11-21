from flask import flash, render_template
from flask_mail import Message
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import RegistrationRequestForm

from utils import i18n


class RegistrationRequestsController(Controller):
    """Controller for registration request model"""

    def __init__(self, app, handler, mail):
        """Constructor

        :param Flask app: Flask application
        :param handler: Tenant config handler
        :param flask_mail.Mail mail: Application mailer
        """
        super(RegistrationRequestsController, self).__init__(
            "Registration request", 'registration_requests',
            'registration_request', 'registration_requests', app, handler
        )

        self.mail = mail

    def resources_for_index_query(self, search_text, session):
        """Return query for registration requests list.

        :param str search_text: Search string for filtering
        :param Session session: DB session
        """
        query = session.query(self.RegistrationRequest) \
            .join(self.RegistrationRequest.user) \
            .join(self.RegistrationRequest.registrable_group) \
            .filter(self.RegistrationRequest.pending.is_(True)) \
            .order_by(
                self.User.name, self.RegistrationRequest.created_at.desc(),
                self.RegistrableGroup.title
            )
        if search_text:
            # filter by user name or group name
            query = query.join(self.RegistrationRequest.registrable_group) \
                .join(self.RegistrableGroup.group) \
                .filter(or_(
                    self.User.name.ilike("%%%s%%" % search_text),
                    self.RegistrableGroup.title.ilike("%%%s%%" % search_text),
                    self.Group.name.ilike("%%%s%%" % search_text)
                ))

        # eager load relations
        query = query.options(
            joinedload(self.RegistrationRequest.user),
            joinedload(self.RegistrationRequest.registrable_group)
        )

        return query

    def order_by_criterion(self, sort, sort_asc):
        """Return order_by criterion for sorted resources list as tuple.

        :param str sort: Column name for sorting
        :param bool sort_asc: Set to sort in ascending order
        """
        sortable_columns = {
            'id': [self.RegistrationRequest.id],
            'user': [
                self.User.name, self.RegistrationRequest.created_at.desc(),
                self.RegistrableGroup.title
            ],
            'group': [
                self.RegistrableGroup.title, self.User.name,
                self.RegistrationRequest.created_at.desc()
            ],
            'created': [
                self.RegistrationRequest.created_at, self.User.name,
                self.RegistrableGroup.title
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

    def find_resource(self, id, session):
        """Find registration request by ID.

        :param int id: Registration request ID
        :param Session session: DB session
        """
        return session.query(self.RegistrationRequest).filter_by(id=id).first()

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional registration request object
        :param bool edit_form: Set if edit form
        """
        # create form
        form = RegistrationRequestForm(obj=resource)

        if edit_form:
            session = self.session()

            # find user for registration request
            query = session.query(self.User).filter_by(id=resource.user_id)
            user = query.first()

            # query all pending registration requests of same user
            pending_requests = self.pending_requests(user.id, session)

            # query group memberships
            user_groups = user.sorted_groups
            user_group_ids = [g.id for g in user_groups]

            session.close()

            # user details
            form.username = user.name
            form.user_email = user.email or '-'

            # add registration_requests
            for registration_request in pending_requests:
                registrable_group = registration_request.registrable_group
                form.registration_requests.append_entry({
                    'request_id': registration_request.id,
                    'title': registrable_group.title,
                    'unsubscribe': registration_request.unsubscribe,
                    'created_at': registration_request.created_at,
                    'group': registrable_group.group.name,
                    'member': registrable_group.group_id in user_group_ids
                })

        return form

    def create_or_update_resources(self, resource, form, session):
        """Update registration request records in DB.

        :param object resource: Registration request object
        :param FlaskForm form: Form for registration request
        :param Session session: DB session
        """
        if resource is None:
            # registration requests can only be created in Registration service
            abort(405)

        # find user for registration request
        user = session.query(self.User).filter_by(id=resource.user_id).first()

        # query all pending registration requests of same user
        pending_requests = self.pending_requests(user.id, session)

        # query group memberships
        user_groups = user.sorted_groups
        user_group_ids = [g.id for g in user_groups]

        # lookup for subform data
        request_forms = {}
        for req in form.registration_requests:
            request_forms[int(req.data['request_id'])] = req.data['action']

        # update registration requests
        groups_joined = []
        groups_left = []
        rejected_requests = []
        for registration_request in pending_requests:
            registrable_group = registration_request.registrable_group
            group = registrable_group.group

            action = request_forms.get(registration_request.id)
            if action == 'skip':
                # skip registration request
                pass

            elif action == 'accept':
                # accept request
                if registration_request.unsubscribe:
                    # remove from group
                    self.logger.info(
                        "Remove user from group '%s'" % group.name
                    )
                    user.groups_collection.remove(group)
                    groups_left.append(registrable_group.title)
                elif group.id not in user_group_ids:
                    # add to group
                    self.logger.info("Add user to group '%s'" % group.name)
                    user.groups_collection.append(group)
                    groups_joined.append(registrable_group.title)
                else:
                    # already a group member
                    self.logger.info(
                        "User is already a member of group '%s'" % group.name
                    )
                    groups_joined.append(registrable_group.title)
                registration_request.pending = False
                registration_request.accepted = True

            elif action == 'reject':
                # reject request
                self.logger.info(
                    "Rejected request for group '%s'" % group.name
                )
                registration_request.pending = False
                registration_request.accepted = False
                rejected_requests.append(registrable_group.title)

            else:
                if group.id in user_group_ids:
                    # close request for existing membership
                    self.logger.info(
                        "User is already a member of group '%s'" % group.name
                    )
                    registration_request.pending = False
                    groups_joined.append(registrable_group.title)

        if user.email:
            self.send_user_notification(
                user, groups_joined, groups_left, rejected_requests, session
            )

    def pending_requests(self, user_id, session):
        """Return all pending registration requests of a user.

        :paran int user_id: User ID
        :param Session session: DB session
        """
        query = session.query(self.RegistrationRequest) \
            .join(self.RegistrationRequest.registrable_group) \
            .filter(self.RegistrationRequest.user_id == user_id) \
            .filter(self.RegistrationRequest.pending.is_(True)) \
            .order_by(
                self.RegistrationRequest.created_at.desc(),
                self.RegistrableGroup.title
            )
        # eager load relations
        query = query.options(
            joinedload(self.RegistrationRequest.registrable_group)
            .joinedload(self.RegistrableGroup.group)
        )
        return query.all()

    def send_user_notification(self, user, groups_joined, groups_left,
                               rejected_requests, session):
        """Send mail with any registration request updates to user.

        :param User user: User instance
        :param list[str] groups_joined: List of groups joined
        :param list[str] groups_left: List of groups left
        :param list[str] rejected_requests: List of rejected requests
        :param Session session: DB session
        """
        if not groups_joined and not groups_left and not rejected_requests:
            # no changes in registration requests
            return

        # successfully commit changes before sending user notification
        try:
            session.commit()
        except Exception as e:
            raise(e)

        # send notification to user
        try:
            msg = Message(
                i18n('registration_requests.user_notification.subject'),
                recipients=[user.email]
            )
            # set message body from template
            msg.body = render_template(
                '%s/user_notification.txt' % self.templates_dir, user=user,
                groups_joined=groups_joined, groups_left=groups_left,
                rejected_requests=rejected_requests, i18n=i18n
            )

            # send message
            self.logger.debug(msg)
            self.mail.send(msg)
            flash(
                i18n('interface.registration_requests.send_message_success'),
                'success'
            )
        except Exception as e:
            self.logger.error(
                "Could not send notification to user '%s':\n%s" %
                (user.email, e)
            )
            flash(
                "%s\n%s" % (i18n('interface.registration_requests.send_message_error'), e), 
                'error'
            )
