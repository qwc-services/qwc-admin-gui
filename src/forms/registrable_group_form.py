from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional
from utils import i18n

class RegistrableGroupForm(FlaskForm):
    """Main form for RegistrableGroup GUI"""
    group_id = SelectField(i18n('interface.common.group'), coerce=int, validators=[DataRequired()])
    title = StringField(i18n('interface.common.title'), validators=[DataRequired()])
    description = TextAreaField(i18n('interface.common.description'), validators=[Optional()])

    submit = SubmitField(i18n('interface.common.form_submit'))
