from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional


class RegistrableGroupForm(FlaskForm):
    """Main form for RegistrableGroup GUI"""
    group_id = SelectField('Group', coerce=int, validators=[DataRequired()])
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])

    submit = SubmitField('Save')
