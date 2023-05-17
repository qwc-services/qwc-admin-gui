from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField

class LayerForm(FlaskForm):
    """Main form for Geospatial layer GUI"""

    upload = FileField('Geospatial Layer (.geojson, .kml, .gpkg, .shp, .zip)', validators=[
        FileRequired(),
        FileAllowed(['geojson', 'kml', 'gpkg', 'shp', 'dbf', 'shx', 'cpg', 'prj', 'zip'],
        'Please only use geospatial files (geojson, kml, gpkg, shp, zip) !')
    ])
    submit = SubmitField("Upload")

class ProjectForm(FlaskForm):
    """Main form for QGS Project GUI"""

    upload = FileField('QGIS Project (.qgs)', validators=[
        FileRequired(),
        FileAllowed(['qgs'], 'Please only use QGS projects !')
    ])
    submit = SubmitField("Upload")
    
class TemplateForm(FlaskForm):
    """Main form for QGS Project GUI"""

    upload = FileField('HTML template (.html)', validators=[
        FileRequired(),
        FileAllowed(['html'], 'Please only HTML files')
    ])
    submit = SubmitField("Upload")

