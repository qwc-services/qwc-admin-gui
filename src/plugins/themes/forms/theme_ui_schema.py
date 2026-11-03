from utils import i18n, lookup_translation


# Theme settings edited as JSON text, besides the objects without any property
# definition which the form always edits as JSON
JSON_FIELD = {"ui:field": "json"}


def theme_ui_schema(schema):
    """Return the layout of the theme form (RJSF uiSchema), listing only the
    theme settings defined by the schema, since RJSF rejects an order with
    other names.

    Theme settings listed in no section are shown above the sections.

    :param dict schema: Theme form schema
    """
    properties = schema.get("properties", {})
    order = ["url", "title", "description", "thumbnail", "default", "disabled"]
    sections = [
        {"title": i18n('plugins.themes.theme.section_map'), "expanded": True, "fields": [
            "mapCrs", "defaultDisplayCrs", "additionalMouseCrs", "extent",
            "mapExtent", "scales", "startupView", "attribution", "attributionUrl"
        ]},
        {"title": i18n('plugins.themes.theme.section_wms'), "fields": [
            "format", "tiled", "tileSize", "version", "externalLayers"
        ]},
        {"title": i18n('plugins.themes.theme.section_background_layers'), "fields": [
            "backgroundLayers"
        ]},
        {"title": i18n('plugins.themes.theme.options_search'), "fields": [
            "searchProviders", "minSearchScaleDenom"
        ]},
        {"title": i18n('plugins.themes.theme.options_interface'), "fields": [
            "mapTips", "skipEmptyFeatureAttributes", "collapseLayerGroupsBelowLevel",
            "layerTreeHiddenSublayers", "lockedVisibilityPreset",
            "visibilityPresetsBlacklist", "flags", "themeInfoLinks", "featureReport",
            "snapping", "labelProfiles"
        ]},
        {"title": i18n('plugins.themes.theme.options_print'), "fields": [
            "printScales", "printResolutions", "printGrid", "defaultPrintLayout",
            "extraPrintTemplates", "printTemplateBlacklist", "printLabelBlacklist",
            "printLabelConfig", "printLabelForAttribution", "printLabelForSearchResult",
            "extraPrintLayers", "extraPrintParameters", "extraLegendParameters",
            "watermark"
        ]},
        {"title": i18n('plugins.themes.theme.section_filters'), "fields": [
            "predefinedFilters", "filter"
        ]},
        {"title": i18n('plugins.themes.theme.section_3d'), "fields": [
            "map3d", "obliqueDatasets"
        ]},
        {"title": i18n('plugins.themes.theme.section_advanced'), "fields": [
            "id", "wmsOnly", "hidden_in_ows_landing_page", "wmsBasicAuth",
            "printUrl", "legendUrl", "featureInfoUrl", "editConfig", "pluginData",
            "config"
        ]}
    ]
    for section in sections:
        section["fields"] = [name for name in section["fields"] if name in properties]
    return {
        # the page has its own submit button, below the other settings
        "ui:submitButtonOptions": {"norender": True},
        "ui:order": [name for name in order if name in properties] + ["*"],
        "ui:options": {"sections": [
            section for section in sections if section["fields"]
        ]},
        "description": {"ui:widget": "textarea"},
        "searchProviders": {"items": {"params": {
            "expression": JSON_FIELD, "fields": JSON_FIELD
        }}},
        "predefinedFilters": {"items": {
            "filter": JSON_FIELD
        }},
        "featureReport": JSON_FIELD,
        "labelProfiles": JSON_FIELD,
        "printLabelConfig": JSON_FIELD,
        "editConfig": JSON_FIELD,
        "pluginData": JSON_FIELD
    }


def rjsf_translations():
    """Return the translated interface strings of the theme form, keyed by
    RJSF TranslatableString name."""
    translations = {
        "ArrayItemTitle": lookup_translation('plugins.themes.theme.rjsf_item'),
        "EmptyArray": lookup_translation('plugins.themes.theme.rjsf_empty_array'),
        "YesLabel": lookup_translation('plugins.themes.theme.rjsf_yes'),
        "NoLabel": lookup_translation('plugins.themes.theme.rjsf_no'),
        "ErrorsLabel": lookup_translation('plugins.themes.theme.rjsf_errors'),
        "NewStringDefault": lookup_translation('plugins.themes.theme.rjsf_new_value'),
        "AddButton": lookup_translation('plugins.themes.theme.rjsf_add'),
        "AddItemButton": lookup_translation('plugins.themes.theme.rjsf_add_item'),
        "CopyButton": lookup_translation('plugins.themes.theme.rjsf_copy'),
        "MoveDownButton": lookup_translation('plugins.themes.theme.rjsf_move_down'),
        "MoveUpButton": lookup_translation('plugins.themes.theme.rjsf_move_up'),
        "RemoveButton": lookup_translation('plugins.themes.theme.rjsf_remove'),
        "OptionalObjectAdd": lookup_translation('plugins.themes.theme.rjsf_optional_add'),
        "OptionalObjectRemove": lookup_translation('plugins.themes.theme.rjsf_optional_remove'),
        "OptionalObjectEmptyMsg": lookup_translation('plugins.themes.theme.rjsf_optional_empty'),
        "Type": lookup_translation('plugins.themes.theme.rjsf_type'),
        "Value": lookup_translation('plugins.themes.theme.rjsf_value'),
        "OptionPrefix": lookup_translation('plugins.themes.theme.rjsf_option'),
        "TitleOptionPrefix": lookup_translation('plugins.themes.theme.rjsf_title_option'),
        "KeyLabel": lookup_translation('plugins.themes.theme.rjsf_key'),
        "DeprecatedLabel": lookup_translation('plugins.themes.theme.rjsf_deprecated'),
        # not an RJSF string, used by the JSON field of the theme form
        "InvalidJson": lookup_translation('plugins.themes.theme.rjsf_invalid_json')
    }
    # RJSF uses English for the strings missing in the translations
    return {
        name: text for name, text in translations.items() if text is not None
    }
