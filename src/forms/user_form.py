from flask_wtf import FlaskForm
from wtforms import FormField, IntegerField, SelectMultipleField, \
    StringField, SubmitField, TextAreaField, ValidationError, PasswordField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, \
    Length, NumberRange
from wtforms.widgets import NumberInput

from utils import i18n


class UserForm(FlaskForm):
    """Main form for User GUI"""
    name = StringField(i18n('interface.users.form_name'), validators=[DataRequired()])
    description = TextAreaField(i18n('interface.common.description'), validators=[Optional()])
    email = StringField(i18n('interface.users.form_email'), validators=[Optional(), Email()])

    # custom user fields
    # NOTE: actual subform added in add_custom_fields()
    user_info = FormField(FlaskForm, i18n('interface.users.user_info'), _meta={'csrf': False})

    password = PasswordField(i18n('interface.users.form_password'))
    password2 = PasswordField(
        i18n('interface.users.form_password_repeat'), validators=[EqualTo('password')])
    totp_enabled = False
    totp_secret = StringField(
        i18n('interface.users.form_totp'), validators=[Optional(), Length(max=128)]
    )
    last_sign_in_at = StringField(i18n('interface.users.form_last_sign_in'), validators=[Optional()])
    failed_sign_in_count = IntegerField(
        i18n('interface.users.form_failed_login'),
        widget=NumberInput(min=0),
        validators=[
            Optional(),
            NumberRange(min=0, message=i18n('interface.users.form_failed_login_message'))
        ]
    )

    groups = SelectMultipleField(
        i18n('interface.common.assigned_groups'),
        coerce=int, validators=[Optional()]
    )
    roles = SelectMultipleField(
        i18n('interface.common.assigned_roles'),
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField(i18n('interface.common.form_submit'))

    def __init__(self, config_models, user_info_fields, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.User = self.config_models.model('users')

        # store any provided user object
        self.obj = kwargs.get('obj')

        self.add_custom_fields(user_info_fields)

        super(UserForm, self).__init__(**kwargs)

    def add_custom_fields(self, user_info_fields):
        """Add custom user_info fields.

        :param list(obj) user_info_fields: Custom user info fields
        """
        # NOTE: use a new UserInfoForm class for every UserForm instance,
        #       so custom fields are only set for the current tenant
        #       and not globally
        class UserInfoForm(FlaskForm):
            """Subform for custom user info fields"""
            pass

        # override form_class in user_info FormField
        self.user_info.args = (UserInfoForm, i18n('interface.users.user_info'))

        # add custom fields
        for field in user_info_fields:
            field_class = StringField
            widget = None
            if field.get('type') == 'string':
                field_class = StringField
            if field.get('type') == 'textarea':
                field_class = TextAreaField
            elif field.get('type') == 'integer':
                field_class = IntegerField
                widget = NumberInput()

            validators = [Optional()]
            if field.get('required', False):
                validators = [DataRequired()]

            form_field = field_class(
                field['title'],
                widget=widget,
                validators=validators
            )
            # add custom field to UserInfoForm
            setattr(UserInfoForm, field['name'], form_field)

    def validate_name(self, field):
        # check if user name exists
        session = self.config_models.session()
        query = session.query(self.User).filter_by(name=field.data)
        if self.obj:
            # ignore current user
            query = query.filter(self.User.id != self.obj.id)
        user = query.first()
        session.close()
        if user is not None:
            raise ValidationError(i18n('interface.common.form_name_error'))

    def validate_email(self, email):
        session = self.config_models.session()
        query = session.query(self.User).filter_by(email=email.data)
        if self.obj:
            # ignore current user
            query = query.filter(self.User.id != self.obj.id)
        user = query.first()
        session.close()
        if user is not None:
            raise ValidationError(i18n('interface.users.form_email_error'))
