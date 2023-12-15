from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional
from utils import i18n


class GroupForm(FlaskForm):
    """Main form for Group GUI"""
    name = StringField(i18n('interface.common.name'), validators=[DataRequired()])
    description = TextAreaField(i18n('interface.common.description'), validators=[Optional()])
    users = SelectMultipleField(
        i18n('interface.common.assigned_users'),
        coerce=int, validators=[Optional()]
    )
    roles = SelectMultipleField(
        i18n('interface.common.assigned_roles'),
        coerce=int, validators=[Optional()]
    )

    submit = SubmitField(i18n('interface.common.form_submit'))

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
            raise ValidationError(i18n('interface.common.form_name_error'))
