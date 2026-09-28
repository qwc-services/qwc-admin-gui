import unittest
from collections import OrderedDict

from flask import Flask

from plugins.themes.controllers import ThemesController
from plugins.themes.forms import ThemeForm


app = Flask(__name__)
app.config.update(SECRET_KEY="test", WTF_CSRF_ENABLED=False)


class ThemeItemFromFormTestCase(unittest.TestCase):
    """Test building a theme item from submitted theme form data"""

    def submit(self, data):
        """Return the theme item built from the submitted form data."""
        with app.test_request_context(method="POST", data=data):
            return ThemesController.theme_item_from_form(ThemeForm())

    def test_saves_scale_dependent_print_layer_as_list(self):
        item = self.submit({
            "url": "/ows/qwc_demo",
            "backgroundLayers-0-layerName": "mapnik",
            "backgroundLayers-0-printLayer":
                '[{"maxScale": 10000, "name": "osm_detail"},'
                ' {"maxScale": null, "name": "osm_bg"}]',
            "backgroundLayers-0-visibility": "y",
        })

        self.assertEqual(item["backgroundLayers"], [{
            "name": "mapnik",
            "printLayer": [
                {"maxScale": 10000, "name": "osm_detail"},
                {"maxScale": None, "name": "osm_bg"}
            ],
            "visibility": True
        }])

    def test_rejects_invalid_scale_dependent_print_layer(self):
        data = {
            "url": "/ows/qwc_demo",
            "backgroundLayers-0-layerName": "mapnik",
            "backgroundLayers-0-printLayer":
                '[{"maxScale": 10000, "name": "osm_detail"}',
        }
        with app.test_request_context(method="POST", data=data):
            layer_form = ThemeForm().backgroundLayers[0].form
            self.assertFalse(layer_form.printLayer.validate(layer_form))

    def test_accepts_print_layer_name_in_brackets(self):
        data = {
            "url": "/ows/qwc_demo",
            "backgroundLayers-0-layerName": "mapnik",
            "backgroundLayers-0-printLayer": "[OSM] background",
        }
        with app.test_request_context(method="POST", data=data):
            form = ThemeForm()
            layer_form = form.backgroundLayers[0].form
            self.assertTrue(layer_form.printLayer.validate(layer_form))
            item = ThemesController.theme_item_from_form(form)

        self.assertEqual(
            item["backgroundLayers"][0]["printLayer"], "[OSM] background")

    def test_saves_indented_scale_dependent_print_layer_as_list(self):
        item = self.submit({
            "url": "/ows/qwc_demo",
            "backgroundLayers-0-layerName": "mapnik",
            "backgroundLayers-0-printLayer":
                '\n [{"maxScale": null, "name": "osm_bg"}]',
        })

        self.assertEqual(
            item["backgroundLayers"][0]["printLayer"],
            [{"maxScale": None, "name": "osm_bg"}])

    def test_accepts_negative_extent(self):
        data = {
            "url": "/ows/qwc_demo",
            "extent": "-1000000, 4000000, 3000000, 8000000.5",
        }
        with app.test_request_context(method="POST", data=data):
            form = ThemeForm()
            self.assertTrue(form.extent.validate(form), form.extent.errors)
            item = ThemesController.theme_item_from_form(form)

        self.assertEqual(item["extent"], [-1000000, 4000000, 3000000, 8000000.5])

    def test_reads_qgis_search_source_index(self):
        data = {
            "url": "/ows/qwc_demo",
            "qgisSearchProvider-0-sourceIndex": "2",
            "qgisSearchProvider-0-title": "Countries",
            "qgisSearchProvider-3-title": "New",
        }
        with app.test_request_context(method="POST", data=data):
            form = ThemeForm()
            sources = [
                entry.sourceIndex.data for entry in form.qgisSearchProvider
            ]
            self.assertTrue(all(
                entry.sourceIndex.validate(entry.form)
                for entry in form.qgisSearchProvider
            ))

        self.assertEqual(sources, [2, None])


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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [])

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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [])

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

        merged = ThemesController.merge_theme_item(
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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [0])

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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [0])

        self.assertEqual(merged["searchProviders"], [{
            "provider": "qgis",
            "params": {
                "titlemsgid": "search.countries",
                "featuresearch": False,
                "title": "Countries"
            }
        }])

    def test_pairs_qgis_searches_with_the_search_they_were_loaded_from(self):
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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [1, None])

        self.assertEqual(merged["searchProviders"], [
            {"provider": "qgis", "params": {"title": "Search", "group": "b"}},
            {"provider": "qgis", "params": {"title": "New"}},
        ])

    def test_does_not_pair_new_qgis_searches_with_removed_ones(self):
        existing = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [
                {"provider": "qgis", "params": {"title": "A", "group": "a"}},
                {"provider": "qgis", "params": {"title": "B", "group": "b"}},
                {"provider": "qgis", "params": {"title": "C", "group": "c"}},
            ]),
        ])
        # last two rows removed, new row added
        form_item = OrderedDict([
            ("url", "/ows/qwc_demo"),
            ("searchProviders", [
                {"provider": "qgis", "params": {"title": "A"}},
                {"provider": "qgis", "params": {"title": "New"}},
            ]),
        ])

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [0, None])

        self.assertEqual(merged["searchProviders"], [
            {"provider": "qgis", "params": {"title": "A", "group": "a"}},
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

        merged = ThemesController.merge_theme_item(
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

        merged = ThemesController.merge_theme_item(
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

        merged = ThemesController.merge_theme_item(
            existing, form_item, [], [])

        self.assertEqual(merged["backgroundLayers"], [
            {"name": "bluemarble", "printLayer": "bluemarble_bg",
             "visibility": False, "overview": True},
            {"name": "mapnik", "printLayer": "osm_bg", "visibility": False},
        ])
