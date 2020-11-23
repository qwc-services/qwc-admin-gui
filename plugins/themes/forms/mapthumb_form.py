from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import SubmitField


class MapthumbForm(FlaskForm):
    """Subform for backgroundlayers"""

    upload = FileField('Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Please only use jpg or png!')
    ])
    submit = SubmitField("Upload")
