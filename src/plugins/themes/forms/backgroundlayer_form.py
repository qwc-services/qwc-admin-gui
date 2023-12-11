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
    title = StringField("Title", validators=[DataRequired()])
    attribution = StringField("Attribution")
    thumbnail = SelectField("Thumbnail", coerce=str, choices=[("", "")])
    tiled = BooleanField("Tiled")
    submit = SubmitField("Save")


class WMTSLayerForm(FlaskForm):
    """Subform for WMS Layer"""

    url = HiddenField(validators=[DataRequired(), URL()])
    name = HiddenField(validators=[DataRequired()])
    style = HiddenField(validators=[DataRequired()])
    format = HiddenField(validators=[DataRequired()])
    title = StringField("Title")
    # tileMatrixPrefix = StringField("TileMatrixPrefix")
    tileMatrixSet = HiddenField(validators=[DataRequired()])
    projection = HiddenField(validators=[DataRequired()])
    originX = HiddenField(validators=[DataRequired()])
    originY = HiddenField(validators=[DataRequired()])
    resolutions = HiddenField(validators=[DataRequired()])
    tileSize = HiddenField(validators=[DataRequired()])
    capabilities = HiddenField(validators=[DataRequired()])
    requestEncoding = HiddenField(validators=[DataRequired()])
    with_capabilities = BooleanField("Save capabilities? \
        (Only needed for QGIS Server WMTS!)"
    )
    attribution = StringField("Attribution")
    thumbnail = SelectField("Thumbnail", coerce=str, choices=[("", "")])
    submit = SubmitField("Save")

class XYZLayerForm(FlaskForm):
    url = StringField(validators=[DataRequired(), URL()])
    name = StringField(validators=[DataRequired()])
    title = StringField("Title", validators=[DataRequired()])
    thumbnail = SelectField("Thumbnail", coerce=str, choices=[("", "")])
    attribution = StringField("Attribution")
    submit = SubmitField("Save")
    crs = SelectField("CRS", default=("EPSG:3857"))
