from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, HiddenField, \
        SubmitField
from wtforms.validators import DataRequired, URL


class WMSLayerForm(FlaskForm):
    """Subform for WMS Layer"""

    url = HiddenField(validators=[DataRequired()])
    name = HiddenField(validators=[DataRequired()])
    format = HiddenField()
    srs = HiddenField()
    bbox = HiddenField()
    title = StringField("Title")
    attribution = StringField("Attribution")
    thumbnail = SelectField("Thumbnail", coerce=str, choices=[("", "")])
    tiled = BooleanField("tiled")
    submit = SubmitField("Save")


class WMTSLayerForm(FlaskForm):
    """Subform for WMS Layer"""

    url = HiddenField(validators=[DataRequired(), URL()])
    name = HiddenField(validators=[DataRequired()])
    style = HiddenField(validators=[DataRequired()])
    title = StringField("Title")
    # tileMatrixPrefix = StringField("TileMatrixPrefix")
    tileMatrixSet = HiddenField(validators=[DataRequired()])
    projection = HiddenField(validators=[DataRequired()])
    originX = HiddenField(validators=[DataRequired()])
    originY = HiddenField(validators=[DataRequired()])
    resolutions = HiddenField(validators=[DataRequired()])
    tileSize = HiddenField(validators=[DataRequired()])
    capabilities = HiddenField(validators=[DataRequired()])
    with_capabilities = BooleanField("Save capabilities? \
        (Only needed for QGIS Server WMTS!)"
    )
    attribution = StringField("Attribution")
    thumbnail = SelectField("Thumbnail", coerce=str, choices=[("", "")])
    submit = SubmitField("Save")
