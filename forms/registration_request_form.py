from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional


class RequestForm(FlaskForm):
    """Subform for a single registration request"""
    request_id = HiddenField('ID', validators=[DataRequired()])
    action = SelectField(
        'Action',
        choices=[
            ('skip', "Skip"),
            ('accept', "Accept"),
            ('reject', "Reject")
        ],
        default='skip'
    )

    # data fields for display
    title = HiddenField('Title', validators=[Optional()])
    unsubscribe = HiddenField('Unsubscribe', validators=[Optional()])
    created_at = HiddenField('Created at', validators=[Optional()])
    group = HiddenField('Group', validators=[Optional()])
    member = HiddenField('Member', validators=[Optional()])


class RegistrationRequestForm(FlaskForm):
    """Main form for RegistrationRequest GUI"""
    # user name and email
    username = None
    user_email = None
    # pending registration requests of user
    registration_requests = FieldList(FormField(RequestForm))

    submit = SubmitField("Update group memberships")
