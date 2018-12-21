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
    # list of parent choices with (value, label, resource type)
    parent_choices = []

    submit = SubmitField('Save')
