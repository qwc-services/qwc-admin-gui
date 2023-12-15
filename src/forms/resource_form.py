from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from utils import i18n


class ResourceForm(FlaskForm):
    """Main form for Resource GUI"""
    type = SelectField(i18n('interface.common.title'), coerce=str)
    name = StringField(i18n('interface.common.name'), validators=[DataRequired()])
    parent_id = SelectField(
        i18n('interface.resources.parent_resource'), coerce=int, validators=[Optional()]
    )
    """ list of parent choices grouped by resource type

        parent_choices = [
            {
                'resource_type': '<resource type>',
                'group_label': '<resource type description>',
                'options': [
                    (<resource ID>, '<resource name>')
                ]
            }
        ]
    """
    parent_choices = []

    submit = SubmitField(i18n('interface.common.form_submit'))

class ImportResourceForm(FlaskForm):
    """Form for Import Resource from Map"""
    import_type = SelectField(i18n('interface.resources.form_import_type'), coerce=str)
    role_id = SelectField(i18n('interface.resources.form_role'), coerce=int)
    priority = IntegerField(
        i18n('interface.common.form_priority'),
        validators=[
            Optional(),
            NumberRange(min=0, message=i18n('interface.common.form_priority_message'))
        ]
    )
    write = BooleanField(i18n('interface.resources.form_write'))
