from flask_wtf import FlaskForm
import json
from wtforms import FieldList, FormField, SelectField, BooleanField, \
        SelectMultipleField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional, Regexp


class BackgroundLayerForm(FlaskForm):
    """Subform for backgroundlayers"""

    layerName = SelectField(coerce=str, validators=[DataRequired()])
    printLayer = StringField(validators=[Optional()])
    visibility = BooleanField(validators=[Optional()])

class JSONField(StringField):
    def _value(self):
        return json.dumps(self.data) if self.data else ''

    def process_formdata(self, valuelist):
        if valuelist:
            try:
                self.data = json.loads(valuelist[0])
            except ValueError:
                raise ValueError('This field contains invalid JSON')
            else:
                self.data = None

    def pre_validate(self, form):
        super().pre_validate(form)
        if self.data:
            try:
                json.dumps(self.data)
            except TypeError:
                raise ValueError('This field contains invalid JSON')

class ThemeForm(FlaskForm):
    """Main form for Theme GUI"""

    url = SelectField("Project", validators=[DataRequired()])
    title = StringField(
        "Title",
        description="Customized theme title.",
        validators=[Optional()]
    )
    attribution = StringField(
        "Atrribution",
        description=("Theme attribution, is displayed in the bottom right corner of the map."),
        validators=[Optional()]
    )
    thumbnail = SelectField(
        "Thumbnail",
        description=("Filename of the theme thumbnail. "
                     "By default, autogenerated via WMS GetMap."),
        validators=[Optional()]
    )
    format = SelectField(
        "Format",
        description=("Image format requested from the WMS Service. Default is 'image/png'."),
        validators=[Optional()]
    )
    mapCrs = SelectField(
        "CRS",
        description="The map projection.",
        default=("EPSG:3857"),
        validators=[Optional()]
    )
    additionalMouseCrs = SelectMultipleField(
        "Add. CRS",
        description=("Additional CRS for the mouse coordinate display."),
        validators=[Optional()]
    )
    searchProviders = SelectMultipleField(
        "Search providers",
        description="List of available search providers.",
        validators=[Optional()],
        default=("coordinates")
    )
    qgisSearchProvider = JSONField(
        "Qgis search",
        description="""Qgis search configuration, see
                    <a target="_blank"
                    href='https://qwc-services.github.io/topics/Search/#configuring-the-qgis-feature-search'>
                    documentation</a>""",
        validators=[Optional()]
    )
    scales = StringField(
        "Scales",
        description="List of available map scales.",
        default=(""),
        validators=[Optional(), Regexp(r'^(\d+)(,\s*\d+)*$',
                    message="Please enter a comma separted list of numbers.")]
    )
    printScales = StringField(
        "Print scales",
        description="List of available print scales.",
        default=(""),
        validators=[Optional(), Regexp(r'^(\d+)(,\s*\d+)*$',
                    message="Please enter a comma separted list of numbers.")]
    )
    printResolutions = StringField(
        "Print resolutions",
        description="List of available print resolutions.",
        default=(""),
        validators=[Optional(), Regexp(r'^(\d+)(,\s*\d+)*$',
                    message="Please enter a comma separted list of numbers.")]
    )
    printLabelBlacklist = StringField(
        "Print label blacklist",
        description="Optional, list of composer label ids to not expose in the print dialog.",
        validators=[Optional(), Regexp(r'^(\w+)(,\s*\w+)*$',
                    message="Please enter a comma separted list of names.")]
    )
    collapseLayerGroupsBelowLevel = IntegerField(
        "collapse layer groups below level",
        description="Optional, layer tree level below which to initially collapse groups. By default the tree is completely expanded.",
        validators=[Optional()]
    )
    default = BooleanField(
        "Default",
        description="Whether to use this theme as initial theme.",
        validators=[Optional()]
    )
    tiled = BooleanField(
        "Tiled",
        description="Tiling the layers",
        validators=[Optional()]
    )
    mapTips = BooleanField(
        "Enable tooltip by default",
        description="Enable the theme tooltip by default",
        validators=[Optional()]
    )
    skipEmptyFeatureAttributes = BooleanField(
        "Skip empty feature attributes",
        description="Optional, whether to skip empty attributes in the identify results. Default is false.",
        validators=[Optional()]
    )

    backgroundLayers = FieldList(FormField(BackgroundLayerForm))

    submit = SubmitField("Save")
