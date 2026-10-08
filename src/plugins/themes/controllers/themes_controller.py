import json
from collections import OrderedDict
from copy import deepcopy
from flask import abort, flash, redirect, render_template, request, url_for
from jinja2.utils import htmlsafe_json_dumps
from sqlalchemy.exc import IntegrityError, InternalError
from qwc_services_core.config_models import ConfigModels

from plugins.themes.forms.theme_ui_schema import rjsf_translations, theme_ui_schema
from plugins.themes.utils import ThemeSchema, ThemeUtils
from utils import DEFAULT_LOCALE, i18n, lookup_translation


class ThemesConfigSaveError(Exception):
    """Saving the themes configuration failed"""


class ThemesController:
    """Controller for theme model"""

    def __init__(self, app, handler, themesconfig):
        """Constructor

        :param Flask app: Flask application
        """

        # index
        app.add_url_rule(
            "/themes", "themes", self.index, methods=["GET"]
        )
        # new
        app.add_url_rule(
            "/themes/new", "new_theme", self.new_theme,
            methods=["GET"]
        )
        app.add_url_rule(
            "/themes/new/<int:gid>", "new_theme", self.new_theme,
            methods=["GET"]
        )
        # create
        app.add_url_rule(
            "/themes/create", "create_theme", self.create_theme,
            methods=["POST"]
        )
        app.add_url_rule(
            "/themes/create/<int:gid>", "create_theme", self.create_theme,
            methods=["POST"]
        )
        # edit
        app.add_url_rule(
            "/themes/edit/<int:tid>", "edit_theme", self.edit_theme,
            methods=["GET"]
        )
        app.add_url_rule(
            "/themes/edit/<int:tid>/<int:gid>", "edit_theme", self.edit_theme,
            methods=["GET"]
        )
        # update
        app.add_url_rule(
            "/themes/update/<int:tid>", "update_theme",
            self.update_theme, methods=["POST"]
        )
        app.add_url_rule(
            "/themes/update/<int:tid>/<int:gid>", "update_theme",
            self.update_theme, methods=["POST"]
        )
        # delete
        app.add_url_rule(
            "/themes/delete/<int:tid>", "delete_theme",
            self.delete_theme, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/delete/<int:tid>/<int:gid>", "delete_theme",
            self.delete_theme, methods=["GET"]
        )
        # move
        app.add_url_rule(
            "/themes/move/<string:direction>/<int:tid>",
            "move_theme", self.move_theme, methods=["GET"]
        )
        app.add_url_rule(
            "/themes/move/<string:direction>/<int:tid>/<int:gid>",
            "move_theme", self.move_theme, methods=["GET"]
        )

        # add group
        app.add_url_rule(
            "/themes/add_theme_group", "add_theme_group", self.add_theme_group,
            methods=["GET"]
        )
        # delete group
        app.add_url_rule(
            "/themes/delete_theme_group/<int:gid>", "delete_theme_group",
            self.delete_theme_group, methods=["GET"]
        )
        # update group
        app.add_url_rule(
            "/themes/update_theme_group/<int:gid>", "update_theme_group",
            self.update_theme_group, methods=["POST"]
        )
        # move group
        app.add_url_rule(
            "/themes/move_theme_group/<string:direction>/<int:gid>",
            "move_theme_group", self.move_theme_group, methods=["GET"]
        )

        # save themesconfig
        app.add_url_rule(
            "/themes/save_themesconfig", "save_themesconfig",
            self.save_themesconfig, methods=["GET"]
        )
        # reset themesconfig
        app.add_url_rule(
            "/themes/reset_themesconfig", "reset_themesconfig",
            self.reset_themesconfig, methods=["GET"]
        )
        # move theme to group
        app.add_url_rule(
            "/themes/move_theme_to_group/<string:tid>/<string:old_gid>/<string:gid>/",
            "move_theme_to_group", self.move_theme_to_group, methods=["GET"]
        )

        self.app = app
        self.handler = handler
        self.themesconfig = themesconfig
        self.template_dir = "plugins/themes/templates"

        config_handler = handler()
        current_handler = handler()
        db_engine = config_handler.db_engine()
        self.config_models = ConfigModels(
            db_engine, config_handler.conn_str(),
            qwc_config_schema=current_handler.qwc_config_schema()
        )
        self.resources = self.config_models.model('resources')
        self.theme_schema = ThemeSchema(app.logger)
        self.base_form_schema = None

    def index(self):
        """Show theme list."""
        self.themesconfig = ThemeUtils.load_themesconfig(self.app, self.handler)
        themes = OrderedDict()
        themes["items"] = []
        themes["groups"] = []

        for item in self.themesconfig["themes"].get("items", []):
            themes["items"].append({
                "name": item["title"] if "title" in item else item["url"],
                "url": item["url"],
                "disabled": item.get("disabled", False)
            })

        # TODO: nested groups
        for group in self.themesconfig["themes"].get("groups", []):
            groupEntry = {
                "title": group["title"],
                "items": []
            }
            for item in group["items"]:
                groupEntry["items"].append({
                    "name": item["title"] if "title" in item else item["url"],
                    "url": item["url"],
                    "disabled": item.get("disabled", False)
                })
            themes["groups"].append(groupEntry)

        return render_template(
            "%s/themes.html" % self.template_dir, themes=themes,
            endpoint_suffix="theme", title=i18n('plugins.themes.themes.title'), i18n=i18n
        )

    def new_theme(self, gid=None):
        """Show new theme form."""
        return self.render_theme_form(
            {}, i18n('plugins.themes.themes.create_theme_title'),
            url_for("create_theme", gid=gid)
        )

    def create_theme(self, gid=None):
        """Create new theme."""
        return self.save_theme_form(
            None, i18n('plugins.themes.themes.create_theme_title'),
            url_for("create_theme", gid=gid), gid=gid
        )

    def edit_theme(self, tid, gid=None):
        """Show edit theme form.

        :param int id: Theme ID
        """
        # find theme
        theme = self.find_theme(tid, gid)

        if theme is not None:
            return self.render_theme_form(
                theme, i18n('plugins.themes.themes.edit_theme_title'),
                url_for("update_theme", tid=tid, gid=gid)
            )
        else:
            # theme not found
            abort(404)

    def update_theme(self, tid, gid=None):
        """Update existing theme.

        :param int id: Theme ID
        """
        # find theme
        theme = self.find_theme(tid, gid)

        if theme is not None:
            return self.save_theme_form(
                theme, i18n('plugins.themes.themes.update_theme_title'),
                url_for("update_theme", tid=tid, gid=gid), tid=tid, gid=gid
            )
        else:
            # theme not found
            abort(404)

    def save_theme_form(self, theme, title, action, tid=None, gid=None):
        """Save the submitted theme form, or show it again with the errors.

        :param dict theme: Edited theme item, None for a new theme
        :param str title: Page title
        :param str action: Form submit URL
        :param int tid: Theme ID, None for a new theme
        :param int gid: Theme group ID, None for a theme outside the groups
        """
        try:
            form_data = json.loads(request.form.get("theme", ""))
            other_settings = json.loads(request.form.get("other_settings", "{}"))
        except ValueError:
            form_data = other_settings = None
        if not isinstance(form_data, dict) or not isinstance(other_settings, dict):
            abort(400)

        base_schema = self.load_base_form_schema()
        if base_schema is None:
            return redirect(url_for("themes"))
        schema = self.form_schema(base_schema, theme or {})

        item, errors = self.theme_item_from_form(
            theme or {}, form_data, other_settings, schema
        )
        name = item.get("title") or item.get("url", "")
        if theme is None:
            success = i18n('plugins.themes.themes.create_theme_message_success')
            failure = i18n('plugins.themes.themes.create_theme_message_error')
        else:
            success = i18n('plugins.themes.themes.update_theme_message_success')
            failure = i18n('plugins.themes.themes.update_theme_message_error')

        if not errors:
            try:
                self.create_or_update_theme(theme, item, tid=tid, gid=gid)
                flash("{0}: {1}.".format(success, name), "success")
                return redirect(url_for("themes"))
            except ThemesConfigSaveError:
                pass

        flash("{0} {1}.".format(failure, name), "warning")
        for error in errors:
            flash(error, "warning")
        return self.render_theme_form(
            theme or {}, title, action, form_data=form_data,
            other_settings=other_settings
        )

    @staticmethod
    def theme_item_from_form(existing, form_data, other_settings, schema):
        """Return the theme item built from the theme form and the errors
        found in it.

        :param dict existing: Edited theme item, empty for a new theme
        :param dict form_data: Theme settings edited in the form
        :param dict other_settings: Theme settings not defined by the schema
        :param dict schema: Theme form schema
        """
        defined, _ = ThemeSchema.split_theme(schema, form_data)
        _, others = ThemeSchema.split_theme(schema, other_settings)
        errors = [
            i18n('plugins.themes.theme.other_settings_defined_key', [key])
            for key in other_settings if key not in others
        ]
        errors += [
            i18n('plugins.themes.theme.form_undefined_key', [key])
            for key in form_data if key not in defined
        ]
        # a form leaves empty values, e.g. a list whose items were all removed
        defined = ThemeUtils.prune_empty(existing, defined)
        item = ThemeUtils.restore_key_order(existing, {**defined, **others})
        errors += ThemeSchema.validation_errors(schema, item)
        return item, errors

    def delete_theme(self, tid, gid=None):
        if gid is None:
            name = self.themesconfig["themes"]["items"][tid]["url"]
            name = name.split("/")[-1]
            self.themesconfig["themes"]["items"].pop(tid)
        else:
            name = self.themesconfig["themes"]["groups"][gid]["items"][tid]["url"]
            name = name.split("/")[-1]
            self.themesconfig["themes"]["groups"][gid]["items"].pop(tid)

        with self.config_models.session() as session, session.begin():
            resource = session.query(self.resources).filter_by(
                type="map", name=name
            ).first()

            if resource:
                try:
                    session.delete(resource)
                except InternalError as e:
                    flash("InternalError: %s" % e.orig, "error")
                except IntegrityError as e:
                    flash("{0} '{1}'!".format(
                        i18n('plugins.themes.themes.delete_theme_message_error'), resource.name), 
                        "warning")

        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme(self, direction, tid, gid=None):
        if gid is None:
            items = self.themesconfig["themes"]["items"]

            if direction == "up" and tid > 0:
                items[tid-1], items[tid] = items[tid], items[tid-1]

            elif direction == "down" and len(items)-1 > tid:
                items[tid], items[tid+1] = items[tid+1], items[tid]

            self.themesconfig["themes"]["items"] = items

        else:
            items = self.themesconfig["themes"]["groups"][gid]["items"]

            if direction == "up" and tid > 0:
                items[tid-1], items[tid] = items[tid], items[tid-1]

            elif direction == "down" and len(items)-1 > tid:
                items[tid], items[tid+1] = items[tid+1], items[tid]

            self.themesconfig["themes"]["groups"][gid]["items"] = items

        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme_to_group(self, tid, old_gid, gid):
        if old_gid == gid : 
            return redirect(url_for("themes"))
        if old_gid == 'undefined':
            items = self.themesconfig["themes"]["items"]
            self.themesconfig["themes"]["groups"][int(gid)]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["items"].pop(int(tid))
        elif gid == 'undefined':
            items = self.themesconfig["themes"]["groups"][int(old_gid)]["items"]
            self.themesconfig["themes"]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["groups"][int(old_gid)]["items"].pop(int(tid))
        else:
            items = self.themesconfig["themes"]["groups"][int(old_gid)]["items"]
            self.themesconfig["themes"]["groups"][int(gid)]["items"].append(items[int(tid)])
            self.themesconfig["themes"]["groups"][int(old_gid)]["items"].pop(int(tid))
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def add_theme_group(self):
        self.themesconfig["themes"]["groups"] = self.themesconfig["themes"].get("groups", [])
        self.themesconfig["themes"]["groups"].append({
            "title": i18n('plugins.themes.themes.new_group'),
            "items": []
        })
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def delete_theme_group(self, gid):
        self.themesconfig["themes"]["groups"].pop(gid)
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def update_theme_group(self, gid):
        self.themesconfig["themes"]["groups"][gid]["title"] = request.form[
            "group_title"]
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def move_theme_group(self, gid, direction):
        groups = self.themesconfig["themes"]["groups"]

        if direction == "up" and gid > 1:
            groups[gid-1], groups[gid] = groups[gid], groups[gid-1]

        elif direction == "down" and len(groups) > gid:
            groups[gid], groups[gid-1] = groups[gid-1], groups[gid]

        self.themesconfig["themes"]["groups"] = groups
        self.save_themesconfig()
        return redirect(url_for("themes"))

    def save_themesconfig(self):
        self.write_themesconfig(self.themesconfig)
        return redirect(url_for("themes"))

    def write_themesconfig(self, themesconfig):
        """Save themesconfig and flash the result, return whether it was saved.

        :param dict themesconfig: Themes configuration
        """
        if ThemeUtils.save_themesconfig(themesconfig, self.app, self.handler):
            flash(i18n('plugins.themes.themes.save_theme_message_success'), "success")
            return True
        else:
            flash(i18n('plugins.themes.themes.save_theme_message_error'),
                  "error")
            return False

    def reset_themesconfig(self):
        self.themesconfig = ThemeUtils.load_themesconfig(self.app, self.handler)
        flash(i18n('plugins.themes.themes.reload_theme_message'), "warning")
        return redirect(url_for("themes"))

    def find_theme(self, tid, gid=None):
        """Find theme by ID.

        :param int id: Theme ID
        """
        if gid is None:
            for i, item in enumerate(self.themesconfig["themes"]["items"]):
                if i == tid:
                    return item
        else:
            for i, group in enumerate(self.themesconfig["themes"]["groups"]):
                if i == gid:
                    for j, item in enumerate(group["items"]):
                        if j == tid:
                            return item

        return None

    def render_theme_form(self, theme, title, action, form_data=None,
                          other_settings=None):
        """Render the theme form.

        :param dict theme: Theme item, empty for a new theme
        :param str title: Page title
        :param str action: Form submit URL
        :param dict form_data: Submitted form data, shown instead of the theme
        :param dict other_settings: Submitted other settings
        """
        base_schema = self.load_base_form_schema()
        if base_schema is None:
            return redirect(url_for("themes"))
        schema = self.form_schema(base_schema, theme)
        if form_data is None:
            form_data, other_settings = ThemeSchema.split_theme(schema, theme)
        form_options = {
            "schema": schema,
            "uiSchema": theme_ui_schema(),
            "formData": form_data,
            "locale": DEFAULT_LOCALE,
            "translations": rjsf_translations()
        }
        # json.dumps keeps the key order, unlike the tojson filter
        return render_template(
            "%s/theme.html" % self.template_dir, title=title, action=action,
            form_options=htmlsafe_json_dumps(form_options, dumps=json.dumps),
            other_settings=htmlsafe_json_dumps(other_settings, dumps=json.dumps),
            i18n=i18n
        )

    def load_base_form_schema(self):
        """Return the theme form schema without the choices of the edited
        theme, loaded once. Return None and show an error if the schema
        cannot be loaded.
        """
        if self.base_form_schema is None:
            try:
                documents = ThemeSchema.translate(
                    self.theme_schema.load_documents(), lookup_translation
                )
                schema = ThemeSchema.bundle(documents)
            except Exception:
                self.app.logger.exception("Could not load the theme schema")
                flash(i18n('plugins.themes.theme.schema_load_error'), "error")
                return None
            ThemeSchema.describe_defaults(
                schema, i18n('plugins.themes.theme.schema_default')
            )
            ThemeSchema.mark_constants_read_only(schema)
            self.base_form_schema = schema
        return self.base_form_schema

    def form_schema(self, base_schema, theme):
        """Return the theme form schema, with the choices of the settings
        selected from lists completed with the values of the theme.

        :param dict base_schema: Theme form schema without choices
        :param dict theme: Theme item, empty for a new theme
        """
        schema = deepcopy(base_schema)

        def as_list(value):
            return value if isinstance(value, list) else []

        crs_choices = [
            tuple(crs) for crs in ThemeUtils.get_crs(self.app, self.handler)
        ]
        map3d = theme.get("map3d")
        background_layers = as_list(theme.get("backgroundLayers")) + (
            as_list(map3d.get("basemaps")) if isinstance(map3d, dict) else []
        )
        search_providers = as_list(
            self.themesconfig.get("defaultSearchProviders")
        )
        choices = [
            (("url",), ThemeUtils.get_projects(self.app, self.handler),
             [theme.get("url")]),
            (("thumbnail",), [
                (thumbnail, thumbnail)
                for thumbnail in ThemeUtils.get_mapthumbs(self.app, self.handler)
                if thumbnail
            ], [theme.get("thumbnail")]),
            (("format",), [
                tuple(image_format) for image_format in ThemeUtils.get_format()
                if image_format[0]
            ], [theme.get("format")]),
            (("mapCrs",), crs_choices, [theme.get("mapCrs")]),
            (("defaultDisplayCrs",), crs_choices, [theme.get("defaultDisplayCrs")]),
            (("additionalMouseCrs", "items"), crs_choices,
             as_list(theme.get("additionalMouseCrs"))),
            (("backgroundLayers", "items", "properties", "name"),
             self.get_backgroundlayers(),
             [layer.get("name") for layer in background_layers
              if isinstance(layer, dict)]),
        ]
        # search providers given by their key
        provider_variants = ThemeSchema.subschema(
            schema, ("properties", "searchProviders", "items")
        ).get("oneOf", [])
        key_variant = next((
            idx for idx, variant in enumerate(provider_variants)
            if variant.get("type") == "string"
        ), None)
        if key_variant is not None:
            choices.append((
                ("searchProviders", "items", "oneOf", key_variant), [
                    (provider, provider) for provider in search_providers
                    if isinstance(provider, str)
                ], as_list(theme.get("searchProviders"))
            ))
        for path, values, current_values in choices:
            ThemeSchema.set_choices(
                schema, ("properties",) + path, values, current_values
            )
        ThemeSchema.keep_enum_values(schema, theme)
        return schema

    def create_or_update_theme(self, theme, item, tid=None, gid=None):
        """Create or update theme records in Themesconfig.

        :param object theme: Optional theme object
                                (None for create)
        :param dict item: Theme item to save
        """
        # edit a copy, kept only once saved
        themesconfig = deepcopy(self.themesconfig)
        new_name = item["url"].split("/")[-1]
        with self.config_models.session() as session, session.begin():
            # edit theme
            if theme:
                if gid is None:
                    name = themesconfig["themes"]["items"][tid]["url"]
                    themesconfig["themes"]["items"][tid] = item
                else:
                    name = themesconfig["themes"]["groups"][gid]["items"][tid]["url"]
                    themesconfig["themes"]["groups"][gid]["items"][tid] = item

                name = name.split("/")[-1]
                resource = session.query(self.resources).filter_by(name=name).first()
                if resource:
                    resource.name = new_name

            # new theme
            else:
                resource = self.resources()
                resource.type = "map"
                resource.name = new_name
                try:
                    session.add(resource)
                except InternalError as e:
                    flash("InternalError: {0}".format(e.orig), "error")
                except IntegrityError as e:
                    flash("{0}: '{1}'!".format(
                        i18n('plugins.themes.themes.create_theme_message_integrity_error'), resource.name), 
                        "warning")

                if gid is None:
                    themesconfig["themes"]["items"].append(item)
                else:
                    themesconfig["themes"]["groups"][gid]["items"].append(
                        item)

            # save themes configuration before commit, so that the resource
            # change is rolled back if saving fails (if the commit fails, the
            # saved file is ahead of the ConfigDB)
            session.flush()
            if not self.write_themesconfig(themesconfig):
                # rolls back the resource change, callers show the form again
                raise ThemesConfigSaveError()

        self.themesconfig = themesconfig

    def get_backgroundlayers(self):
        layers = []
        for layer in self.themesconfig["themes"]["backgroundLayers"]:
            layers.append((layer["name"], layer["name"]))
        return layers
