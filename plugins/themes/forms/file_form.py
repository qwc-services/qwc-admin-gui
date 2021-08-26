from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField

class LayerForm(FlaskForm):
    """Main form for Geospatial layer GUI"""

    upload = FileField('Geospatial Layer', validators=[
        FileRequired(),
        FileAllowed(['geojson', 'kml', 'gpkg', 'shp', 'dbf', 'shx', 'cpg', 'prj'],
        'Please only use geospatial files (geojson, kml, gpkg, shp) !')
    ])
    submit = SubmitField("Upload")

class ProjectForm(FlaskForm):
    """Main form for QGS Project GUI"""

    upload = FileField('QGIS Project', validators=[
        FileRequired(),
        FileAllowed(['qgs'], 'Please only use QGS projects !')
    ])
    submit = SubmitField("Upload")
