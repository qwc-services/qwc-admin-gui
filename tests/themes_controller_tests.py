import unittest
from collections import OrderedDict

from plugins.themes.utils import ThemeUtils


class MergeThemeItemTestCase(unittest.TestCase):
    """Test merging theme form output onto the existing theme item"""

    def test_keeps_keys_not_edited_by_form(self):
        existing = OrderedDict([
            ("id", "qwc_demo"),
            ("url", "/ows/qwc_demo"),
            ("title", "Demo"),
            ("predefinedFilters", [{"id": "timefilter", "title": "Time"}]),
            ("featureReport", {"countries": "Country"}),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("title", "Demo renamed"),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [])

        self.assertEqual(merged, OrderedDict([
            ("id", "qwc_demo"),
            ("url", "/ows/qwc_demo"),
            ("title", "Demo renamed"),
            ("predefinedFilters", [{"id": "timefilter", "title": "Time"}]),
            ("featureReport", {"countries": "Country"}),
        ]))

    def test_removes_keys_cleared_in_form(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("thumbnail", "qwc_demo.png"),
            ("tileSize", [512, 512]),
            ("predefinedFilters", []),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [])

        self.assertEqual(merged, OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("predefinedFilters", []),
        ]))

    def test_keeps_search_providers_not_selectable_in_form(self):
        fulltext = {"provider": "fulltext", "params": {"default": ["countries"]}}
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", ["coordinates", "nominatim", fulltext]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", ["coordinates"]),
        ])

        merged = ThemeUtils.merge_theme_item(
            existing, form_item, ["coordinates"], [])

        self.assertEqual(
            merged["searchProviders"], ["coordinates", "nominatim", fulltext])

    def test_keeps_qgis_search_params_not_edited_by_form(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [{
                "provider": "qgis",
                "params": {
                    "title": "Countries",
                    "titlemsgid": "search.countries",
                    "resultTitle": "{name}",
                    "expression": {"countries": "\"name\" ILIKE '%$TEXT$%'"},
                    "featuresearch": False
                }
            }]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [{
                "provider": "qgis",
                "params": {
                    "title": "Countries",
                    "featureCount": 10,
                    "description": "",
                    "default": False,
                    "group": "",
                    "expression": {"countries": "\"iso\" = '$TEXT$'"},
                    "fields": None
                }
            }]),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [0])

        self.assertEqual(merged["searchProviders"], [{
            "provider": "qgis",
            "params": {
                "title": "Countries",
                "titlemsgid": "search.countries",
                "resultTitle": "{name}",
                "expression": {"countries": "\"iso\" = '$TEXT$'"},
                "featuresearch": False,
                "featureCount": 10,
                "description": "",
                "default": False,
                "group": "",
                "fields": None
            }
        }])

    def test_keeps_qgis_search_params_when_search_is_renamed(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [{
                "provider": "qgis",
                "params": {"titlemsgid": "search.countries", "featuresearch": False}
            }]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [{
                "provider": "qgis", "params": {"title": "Countries"}
            }]),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [0])

        self.assertEqual(merged["searchProviders"], [{
            "provider": "qgis",
            "params": {
                "titlemsgid": "search.countries",
                "featuresearch": False,
                "title": "Countries"
            }
        }])

    def test_pairs_qgis_searches_with_their_form_row(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [
                {"provider": "qgis", "params": {"title": "Search", "group": "a"}},
                {"provider": "qgis", "params": {"title": "Search", "group": "b"}},
            ]),
        ])
        # first row removed, second row kept, new row added
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [
                {"provider": "qgis", "params": {"title": "Search"}},
                {"provider": "qgis", "params": {"title": "New"}},
            ]),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [1, 2])

        self.assertEqual(merged["searchProviders"], [
            {"provider": "qgis", "params": {"title": "Search", "group": "b"}},
            {"provider": "qgis", "params": {"title": "New"}},
        ])

    def test_keeps_default_search_provider_objects(self):
        fulltext = {"provider": "fulltext", "params": {}}
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", ["coordinates", fulltext]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", ["coordinates"]),
        ])

        merged = ThemeUtils.merge_theme_item(
            existing, form_item, ["coordinates", fulltext], [])

        self.assertEqual(merged["searchProviders"], ["coordinates", fulltext])

    def test_keeps_search_provider_order(self):
        countries = {"provider": "qgis", "params": {"title": "Countries"}}
        fulltext = {"provider": "fulltext", "params": {}}
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [
                "coordinates", "nominatim", countries, fulltext, "places"
            ]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", ["coordinates", "places", countries]),
        ])

        merged = ThemeUtils.merge_theme_item(
            existing, form_item, ["coordinates", "places"], [0])

        self.assertEqual(merged["searchProviders"], [
            "coordinates", "nominatim", countries, fulltext, "places"
        ])

    def test_keeps_background_layer_keys_not_edited_by_form(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("backgroundLayers", [
                {"name": "bluemarble", "printLayer": "bluemarble_bg",
                 "visibility": True, "overview": True},
                {"name": "mapnik", "printLayer": "osm_bg"},
            ]),
        ])
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("backgroundLayers", [
                {"name": "bluemarble", "printLayer": "bluemarble_bg",
                 "visibility": False},
                {"name": "mapnik", "printLayer": "osm_bg", "visibility": False},
            ]),
        ])

        merged = ThemeUtils.merge_theme_item(existing, form_item, [], [])

        self.assertEqual(merged["backgroundLayers"], [
            {"name": "bluemarble", "printLayer": "bluemarble_bg",
             "visibility": False, "overview": True},
            {"name": "mapnik", "printLayer": "osm_bg", "visibility": False},
        ])
