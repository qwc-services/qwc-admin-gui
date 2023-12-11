from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, \
    SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class PermissionForm(FlaskForm):
    """Main form for Permission GUI"""
    role_id = SelectField(
        'Role', coerce=int, validators=[DataRequired()]
    )
    # list of resource types with (name, description)
    resource_types = []
    resource_id = SelectField(
        'Resource', coerce=int, validators=[DataRequired()]
    )
    """ list of resource choices grouped by resource type

        resource_choices = [
            {
                'resource_type': '<resource type>',
                'group_label': '<resource type description>',
                'options': [
                    (<resource ID>, '<resource name>')
                ]
            }
        ]
    """
    resource_choices = []
    priority = IntegerField(
        'Priority',
        validators=[
            Optional(),
            NumberRange(min=0, message="Priority must be greater or equal 0")
        ]
    )
    write = BooleanField('Write')

    submit = SubmitField('Save')
