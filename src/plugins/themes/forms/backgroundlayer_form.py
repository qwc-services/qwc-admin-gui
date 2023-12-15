from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, HiddenField, \
        SubmitField
from wtforms.validators import DataRequired, URL
from utils import i18n


class WMSLayerForm(FlaskForm):
    """Subform for WMS Layer"""

    url = HiddenField(validators=[DataRequired()])
    name = HiddenField(validators=[DataRequired()])
    format = HiddenField()
    srs = HiddenField()
    bbox = HiddenField()
    title = StringField(i18n('interface.common.title'), validators=[DataRequired()])
    attribution = StringField(i18n('plugins.themes.common.form_attribution'))
    thumbnail = SelectField(i18n('plugins.themes.common.form_thumbnail'), coerce=str, choices=[("", "")])
    tiled = BooleanField(i18n('plugins.themes.wmslayer.form_tiled'))
    submit = SubmitField(i18n('plugins.themes.common.form_submit'))


class WMTSLayerForm(FlaskForm):
    """Subform for WMS Layer"""

    url = HiddenField(validators=[DataRequired(), URL()])
    name = HiddenField(validators=[DataRequired()])
    style = HiddenField(validators=[DataRequired()])
    format = HiddenField(validators=[DataRequired()])
    title = StringField(i18n('interface.common.title'))
    # tileMatrixPrefix = StringField("TileMatrixPrefix")
    tileMatrixSet = HiddenField(validators=[DataRequired()])
    projection = HiddenField(validators=[DataRequired()])
    originX = HiddenField(validators=[DataRequired()])
    originY = HiddenField(validators=[DataRequired()])
    resolutions = HiddenField(validators=[DataRequired()])
    tileSize = HiddenField(validators=[DataRequired()])
    capabilities = HiddenField(validators=[DataRequired()])
    requestEncoding = HiddenField(validators=[DataRequired()])
    with_capabilities = BooleanField(i18n('plugins.themes.wmtslayer.form_with_capabilities'))
    attribution = StringField(i18n('plugins.themes.common.form_attribution'))
    thumbnail = SelectField(i18n('plugins.themes.common.form_thumbnail'), coerce=str, choices=[("", "")])
    submit = SubmitField(i18n('plugins.themes.common.form_submit'))

class XYZLayerForm(FlaskForm):
    url = StringField(i18n('interface.common.url'), validators=[DataRequired(), URL()])
    name = StringField(i18n('interface.common.name'), validators=[DataRequired()])
    title = StringField(i18n('interface.common.title'), validators=[DataRequired()])
    thumbnail = SelectField(i18n('plugins.themes.common.form_thumbnail'), coerce=str, choices=[("", "")])
    attribution = StringField(i18n('plugins.themes.common.form_attribution'))
    submit = SubmitField(i18n('plugins.themes.common.form_submit'))
    crs = SelectField(i18n('plugins.themes.common.crs'), default=("EPSG:3857"))
