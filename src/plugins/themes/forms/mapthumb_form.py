from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField
from utils import i18n


class MapthumbForm(FlaskForm):
    """Subform for backgroundlayers"""

    upload = FileField(i18n('plugins.themes.mapthumbs.form_file'), validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], i18n('plugins.themes.mapthumbs.form_allowed'))
    ])
    submit = SubmitField(i18n('plugins.themes.common.form_submit'))
