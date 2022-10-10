from flask_wtf import FlaskForm
from wtforms import BooleanField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional


class ResourceForm(FlaskForm):
    """Main form for Resource GUI"""
    type = SelectField('Type', coerce=str)
    name = StringField('Name', validators=[DataRequired()])
    parent_id = SelectField(
        'Parent resource', coerce=int, validators=[Optional()]
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

    submit = SubmitField('Save')

class ImportResourceForm(FlaskForm):
    """Form for Import Resource from Map"""
    import_type = SelectField('Type of resources to import from map', coerce=str)
    role_id = SelectField('Role permission of resources to import from map', coerce=int)
    priority = IntegerField(
        'Priority',
        validators=[
            Optional(),
            NumberRange(min=0, message="Priority must be greater or equal 0")
        ]
    )
    write = BooleanField('Write')
