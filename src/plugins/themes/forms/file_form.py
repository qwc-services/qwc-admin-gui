from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField
from utils import i18n


class LayerForm(FlaskForm):
    """Main form for Geospatial layer GUI"""

    upload = FileField('{0} (.geojson, .kml, .gpkg, .shp, .zip)'.format(
        i18n('plugins.themes.files.form_layer_file')
    ), validators=[
        FileRequired(),
        FileAllowed(['geojson', 'kml', 'gpkg', 'shp', 'dbf', 'shx', 'cpg', 'prj', 'zip'],
        '{0} (geojson, kml, gpkg, shp, zip) !'.format(i18n('plugins.themes.files.form_layer_allowed')))
    ])
    submit = SubmitField(i18n('plugins.themes.files.form_submit'))

class ProjectForm(FlaskForm):
    """Main form for QGS Project GUI"""

    upload = FileField('{0} (.qgs)'.format(i18n('plugins.themes.files.form_project_file')), validators=[
        FileRequired(),
        FileAllowed(['qgs'], i18n('plugins.themes.files.form_project_allowed'))
    ])
    submit = SubmitField(i18n('plugins.themes.files.form_submit'))
    
class TemplateForm(FlaskForm):
    """Main form for QGS Project GUI"""

    upload = FileField('{0} (.html)'.format(i18n('plugins.themes.files.form_template_file')), validators=[
        FileRequired(),
        FileAllowed(['html'], i18n('plugins.themes.files.form_project_allowed'))
    ])
    submit = SubmitField(i18n('plugins.themes.files.form_submit'))

