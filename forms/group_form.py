from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class GroupForm(FlaskForm):
    """Main form for Group GUI"""
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    users = SelectMultipleField(
        'Assigned users',
        coerce=int, validators=[Optional()]
    )
    roles = SelectMultipleField(
        'Assigned roles',
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Save')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Group = self.config_models.model('groups')

        # store any provided group object
        self.obj = kwargs.get('obj')

        super(GroupForm, self).__init__(**kwargs)

    def validate_name(self, field):
        # check if group name exists
        session = self.config_models.session()
        query = session.query(self.Group).filter_by(name=field.data)
        if self.obj:
            # ignore current group
            query = query.filter(self.Group.id != self.obj.id)
        group = query.first()
        session.close()
        if group is not None:
            raise ValidationError('Name has already been taken.')
