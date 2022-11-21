from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional
from utils import i18n


class RoleForm(FlaskForm):
    """Main form for Role GUI"""
    name = StringField(i18n('interface.common.name'), validators=[DataRequired()])
    description = TextAreaField(i18n('interface.common.description'), validators=[Optional()])
    groups = SelectMultipleField(
        i18n('interface.common.assigned_groups'),
        coerce=int, validators=[Optional()]
    )
    users = SelectMultipleField(
        i18n('interface.common.assigned_users'),
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField(i18n('interface.common.form_submit'))

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Role = self.config_models.model('roles')

        # store any provided role object
        self.obj = kwargs.get('obj')

        super(RoleForm, self).__init__(**kwargs)

    def validate_name(self, field):
        # check if role name exists
        session = self.config_models.session()
        query = session.query(self.Role).filter_by(name=field.data)
        if self.obj:
            # ignore current role
            query = query.filter(self.Role.id != self.obj.id)
        role = query.first()
        session.close()
        if role is not None:
            raise ValidationError(i18n('interface.common.form_name_error'))
