from flask_wtf import FlaskForm
from wtforms import FormField, IntegerField, SelectMultipleField, \
    StringField, SubmitField, TextAreaField, ValidationError, PasswordField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, \
    Length, NumberRange
from wtforms.widgets.html5 import NumberInput


class UserInfoForm(FlaskForm):
    """Subform for custom user info fields"""
    pass


class UserForm(FlaskForm):
    """Main form for User GUI"""
    name = StringField('User name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    email = StringField('Email', validators=[Optional(), Email()])

    # custom user fields
    user_info = FormField(UserInfoForm, "User info", _meta={'csrf': False})

    password = PasswordField('Password')
    password2 = PasswordField(
        'Repeat Password', validators=[EqualTo('password')])
    totp_enabled = False
    totp_secret = StringField(
        'TOTP secret', validators=[Optional(), Length(max=16)]
    )
    last_sign_in_at = StringField('Last sign in', validators=[Optional()])
    failed_sign_in_count = IntegerField(
        'Failed login attempts',
        widget=NumberInput(min=0),
        validators=[
            Optional(),
            NumberRange(min=0, message="Number must be greater or equal 0")
        ]
    )

    groups = SelectMultipleField(
        'Assigned groups',
        coerce=int, validators=[Optional()]
    )
    roles = SelectMultipleField(
        'Assigned roles',
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Save')

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
            raise ValidationError('Name has already been taken.')

    def validate_email(self, email):
        session = self.config_models.session()
        query = session.query(self.User).filter_by(email=email.data)
        if self.obj:
            # ignore current user
            query = query.filter(self.User.id != self.obj.id)
        user = query.first()
        session.close()
        if user is not None:
            raise ValidationError('Please use a different email address.')
