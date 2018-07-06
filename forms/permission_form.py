from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, \
    SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class PermissionForm(FlaskForm):
    """Main form for Permission GUI"""
    role_id = SelectField(
        'Role', coerce=int, validators=[DataRequired()]
    )
    resource_id = SelectField(
        'Resource', coerce=int, validators=[DataRequired()]
    )
    priority = IntegerField(
        'Priority',
        validators=[
            Optional(),
            NumberRange(min=0, message="Priority must be greater or equal 0")
        ]
    )
    write = BooleanField('Write')

    submit = SubmitField('Save')
