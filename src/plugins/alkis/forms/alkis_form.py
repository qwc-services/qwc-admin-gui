from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField, \
        SelectMultipleField, SubmitField
from wtforms.validators import DataRequired


class ALKISForm(FlaskForm):
    """Subform for ALKIS Resource"""

    pgservice = SelectMultipleField("PGSERVICE", coerce=str,
                                    validators=[DataRequired()],
                                    default=("alkis"))
    name = StringField("Name", validators=[DataRequired()])
    enable_alkis = BooleanField("ALKIS aktivieren", default=True)
    enable_owner = BooleanField("Eigentümer abfragen", default=True)
    header_template = SelectField("Header Template", default=("header.html"))
    submit = SubmitField("Speichern")
