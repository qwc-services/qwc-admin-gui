from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional


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
