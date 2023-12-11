from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired

class InfoTemplateForm(FlaskForm):
    """HTML template form"""

    url = SelectField("Project", validators=[DataRequired()])
    template = SelectField("Template", validators=[DataRequired()])
    layer = StringField("Layer", validators=[DataRequired()])
    submit = SubmitField("Save")