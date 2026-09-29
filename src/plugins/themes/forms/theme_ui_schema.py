from utils import i18n


# Theme settings edited as JSON text, besides the objects without any property
# definition which the form always edits as JSON
JSON_FIELD = {"ui:field": "json"}


def theme_ui_schema():
    """Return the layout of the theme form (RJSF uiSchema).

    Theme settings listed in no section are shown above the sections.
    """
    return {
        # the page has its own submit button, below the other settings
        "ui:submitButtonOptions": {"norender": True},
        "ui:order": ["url", "title", "description", "thumbnail", "default", "disabled", "*"],
        "ui:options": {"sections": [
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
        "ArrayItemTitle": i18n('plugins.themes.theme.rjsf_item'),
        "EmptyArray": i18n('plugins.themes.theme.rjsf_empty_array'),
        "YesLabel": i18n('plugins.themes.theme.rjsf_yes'),
        "NoLabel": i18n('plugins.themes.theme.rjsf_no'),
        "ErrorsLabel": i18n('plugins.themes.theme.rjsf_errors'),
        "NewStringDefault": i18n('plugins.themes.theme.rjsf_new_value'),
        "AddButton": i18n('plugins.themes.theme.rjsf_add'),
        "AddItemButton": i18n('plugins.themes.theme.rjsf_add_item'),
        "CopyButton": i18n('plugins.themes.theme.rjsf_copy'),
        "MoveDownButton": i18n('plugins.themes.theme.rjsf_move_down'),
        "MoveUpButton": i18n('plugins.themes.theme.rjsf_move_up'),
        "RemoveButton": i18n('plugins.themes.theme.rjsf_remove'),
        "OptionalObjectAdd": i18n('plugins.themes.theme.rjsf_optional_add'),
        "OptionalObjectRemove": i18n('plugins.themes.theme.rjsf_optional_remove'),
        "OptionalObjectEmptyMsg": i18n('plugins.themes.theme.rjsf_optional_empty'),
        "Type": i18n('plugins.themes.theme.rjsf_type'),
        "Value": i18n('plugins.themes.theme.rjsf_value'),
        "OptionPrefix": i18n('plugins.themes.theme.rjsf_option'),
        "TitleOptionPrefix": i18n('plugins.themes.theme.rjsf_title_option'),
        "KeyLabel": i18n('plugins.themes.theme.rjsf_key'),
        "DeprecatedLabel": i18n('plugins.themes.theme.rjsf_deprecated'),
        # not an RJSF string, used by the JSON field of the theme form
        "InvalidJson": i18n('plugins.themes.theme.rjsf_invalid_json')
    }
    # i18n returns the key of missing strings, RJSF then uses English
    return {
        name: text for name, text in translations.items()
        if not text.startswith('plugins.')
    }
