from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, \
    SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from utils import i18n


class PermissionForm(FlaskForm):
    """Main form for Permission GUI"""
    role_id = SelectField(
        i18n('interface.common.role'), coerce=int, validators=[DataRequired()]
    )
    # list of resource types with (name, description)
    resource_types = []
    resource_id = SelectField(
        i18n('interface.common.resource'), coerce=int, validators=[DataRequired()]
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
        i18n('interface.common.form_priority'),
        validators=[
            Optional(),
            NumberRange(min=0, message=i18n('interface.common.form_priority_message'))
        ]
    )
    write = BooleanField(i18n('interface.permissions.write'))

    submit = SubmitField(i18n('interface.common.form_submit'))
