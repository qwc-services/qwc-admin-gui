from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class UserForm(FlaskForm):
    """Subform for users"""
    user_id = HiddenField(validators=[DataRequired()])
    user_name = HiddenField(validators=[Optional()])


class RoleForm(FlaskForm):
    """Subform for roles"""
    role_id = HiddenField(validators=[DataRequired()])
    role_name = HiddenField(validators=[Optional()])


class GroupForm(FlaskForm):
    """Main form for Group GUI"""
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional()])
    users = FieldList(FormField(UserForm))
    user = SelectField(
        coerce=int, validators=[Optional()]
    )
    roles = FieldList(FormField(RoleForm))
    role = SelectField(
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Save')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Group = self.config_models.model('groups')

        # store any provided role object
        self.obj = kwargs.get('obj')

        super(GroupForm, self).__init__(**kwargs)

    def validate_name(self, field):
        # check if role name exists
        session = self.config_models.session()
        query = session.query(self.Group).filter_by(name=field.data)
        if self.obj:
            # ignore current role
            query = query.filter(self.Group.id != self.obj.id)
        group = query.first()
        session.close()
        if group is not None:
            raise ValidationError('Name has already been taken.')
