from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired
from utils import i18n

class InfoTemplateForm(FlaskForm):
    """HTML template form"""

    url = SelectField(i18n('plugins.themes.info_templates.project'), validators=[DataRequired()])
    template = SelectField(i18n('plugins.themes.info_templates.template'), validators=[DataRequired()])
    layer = StringField(i18n('plugins.themes.common.layer'), validators=[DataRequired()])
    submit = SubmitField(i18n('plugins.themes.common.form_submit'))