import unittest
from collections import OrderedDict
from unittest.mock import patch

from plugins.themes.controllers import ThemesController
from plugins.themes.utils import ThemeUtils


SCHEMA = {
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "title": {"type": "string"},
        "mapCrs": {"type": "string"},
        "extent": {"type": "array", "items": {"type": "number"}, "minItems": 4, "maxItems": 4}
    },
    "required": ["url"]
}


class ThemeItemFromFormTestCase(unittest.TestCase):
    """Test building a theme item from the submitted theme form"""

    def test_combines_form_data_and_other_settings_in_original_order(self):
        existing = OrderedDict([
            ("url", "/ows/demo"), ("custom", 1), ("title", "Demo"), ("mapCrs", "EPSG:3857")
        ])

        item, errors = ThemesController.theme_item_from_form(
            existing, {"title": "Demo 2", "extent": [-1, -2, 3, 4], "url": "/ows/demo"},
            {"custom": 2}, SCHEMA
        )

        self.assertEqual(errors, [])
        self.assertEqual(list(item.items()), [
            ("url", "/ows/demo"), ("custom", 2), ("title", "Demo 2"),
            ("extent", [-1, -2, 3, 4])
        ])

    def test_removes_settings_missing_from_the_form(self):
        existing = {"url": "/ows/demo", "mapCrs": "EPSG:3857", "custom": 1}

        item, errors = ThemesController.theme_item_from_form(
            existing, {"url": "/ows/demo"}, {}, SCHEMA
        )

        self.assertEqual(errors, [])
        self.assertEqual(item, {"url": "/ows/demo"})

    def test_removes_empty_values_left_by_the_form(self):
        existing = {"url": "/ows/demo", "mapCrs": "", "extent": [0, 0, 1, 1]}

        item, errors = ThemesController.theme_item_from_form(
            existing, {"url": "/ows/demo", "mapCrs": "", "extent": [], "title": ""},
            {}, SCHEMA
        )

        self.assertEqual(errors, [])
        self.assertEqual(item, {"url": "/ows/demo", "mapCrs": ""})

    def test_rejects_schema_settings_in_other_settings(self):
        item, errors = ThemesController.theme_item_from_form(
            {}, {"url": "/ows/demo"}, {"title": "Demo"}, SCHEMA
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("title", errors[0])
        self.assertNotIn("title", item)

    def test_rejects_other_settings_in_form_data(self):
        item, errors = ThemesController.theme_item_from_form(
            {}, {"url": "/ows/demo", "custom": 1}, {}, SCHEMA
        )

        self.assertEqual(len(errors), 1)
        self.assertIn("custom", errors[0])
        self.assertNotIn("custom", item)

    def test_reports_schema_errors(self):
        item, errors = ThemesController.theme_item_from_form(
            {}, {"extent": [1, 2, 3]}, {}, SCHEMA
        )

        self.assertEqual(errors, [
            "'url' is a required property",
            "extent: [1, 2, 3] is too short"
        ])


class RestoreKeyOrderTestCase(unittest.TestCase):
    """Test restoring the key order of a theme item edited in a form"""

    def test_restores_nested_key_order_new_keys_last(self):
        original = OrderedDict([
            ("url", "/ows/demo"), ("title", "Demo"),
            ("map3d", OrderedDict([("dtm", OrderedDict([("url", "/dtm.tif"), ("nodata", -500)]))])),
            ("backgroundLayers", [OrderedDict([("name", "osm"), ("visibility", True)])])
        ])
        value = {
            "backgroundLayers": [{"visibility": False, "name": "osm"}, {"name": "ortho"}],
            "map3d": {"dtm": {"nodata": -500, "url": "/dtm.tif"}},
            "mapCrs": "EPSG:2056",
            "url": "/ows/demo"
        }

        result = ThemeUtils.restore_key_order(original, value)

        self.assertEqual(list(result), ["url", "map3d", "backgroundLayers", "mapCrs"])
        self.assertEqual(list(result["map3d"]["dtm"]), ["url", "nodata"])
        self.assertEqual(
            [list(layer) for layer in result["backgroundLayers"]],
            [["name", "visibility"], ["name"]]
        )
        self.assertEqual(result, value)


class PruneEmptyTestCase(unittest.TestCase):
    """Test removing the empty values left by a form"""

    def test_removes_nested_empty_values_not_in_the_original(self):
        original = {"map3d": {"dtm": {"url": "/dtm.tif"}}, "flags": [], "printLayer": [{"maxScale": None}]}
        value = {
            "map3d": {"dtm": {"url": ""}, "objects": []},
            "flags": [],
            "printLayer": [{"maxScale": None, "name": "bg"}],
            "searchProviders": [{"provider": "qgis", "params": {"title": "a", "group": ""}}]
        }

        result = ThemeUtils.prune_empty(original, value)

        self.assertEqual(result, {
            "flags": [],
            "printLayer": [{"maxScale": None, "name": "bg"}],
            "searchProviders": [{"provider": "qgis", "params": {"title": "a"}}]
        })

    def test_keeps_empty_values_of_moved_items(self):
        original = [{"name": "osm", "thumbnail": ""}, {"name": "ortho"}]
        value = [{"name": "ortho"}, {"name": "osm", "thumbnail": ""}]

        result = ThemeUtils.prune_empty(original, value)

        self.assertEqual(result, value)


class OriginalItemsTestCase(unittest.TestCase):
    """Test matching edited list items with the original items"""

    def test_matches_moved_edited_and_new_items(self):
        original = [{"name": "osm", "visibility": True}, {"name": "ortho"}, "coordinates"]
        items = [{"name": "ortho"}, {"name": "osm", "visibility": False}, "nominatim", "coordinates"]

        result = ThemeUtils.original_items(original, items)

        self.assertEqual(result, [
            {"name": "ortho"}, {"name": "osm", "visibility": True}, None,
            "coordinates"
        ])


class FormSchemaTestCase(unittest.TestCase):
    """Test injecting the choices of the theme settings in the form schema"""

    BASE_SCHEMA = {
        "type": "object",
        "definitions": {
            "layer": {"type": "object", "properties": {"name": {"type": "string"}}},
            "provider": {"oneOf": [
                {"type": "object", "properties": {"provider": {"const": "qgis"}}},
                {"type": "string"}
            ]}
        },
        "properties": {
            "url": {"type": "string"},
            "thumbnail": {"type": "string"},
            "format": {"type": "string"},
            "mapCrs": {"type": "string"},
            "defaultDisplayCrs": {"type": "string"},
            "additionalMouseCrs": {"type": "array", "items": {"type": "string"}},
            "backgroundLayers": {"type": "array", "items": {"$ref": "#/definitions/layer"}},
            "searchProviders": {"type": "array", "items": {"$ref": "#/definitions/provider"}},
            "startupView": {"type": "string", "enum": ["2d", "3d"]}
        }
    }

    def form_schema(self, theme):
        controller = ThemesController.__new__(ThemesController)
        controller.app = controller.handler = None
        controller.themesconfig = {
            "themes": {"backgroundLayers": [{"name": "osm"}]},
            "defaultSearchProviders": ["coordinates", {"provider": "fulltext"}]
        }
        with patch.object(ThemeUtils, "get_projects", return_value=[("/ows/demo", "demo")]), \
                patch.object(ThemeUtils, "get_mapthumbs", return_value=["", "demo.png"]), \
                patch.object(ThemeUtils, "get_crs", return_value=(["EPSG:3857", "EPSG:3857"],)):
            return controller.form_schema(self.BASE_SCHEMA, theme)

    def options(self, node):
        return [(option["const"], option["title"]) for option in node["oneOf"]]

    def test_injects_choices_completed_with_theme_values(self):
        schema = self.form_schema({
            "url": "/ows/other", "thumbnail": "other.png", "mapCrs": "EPSG:2056",
            "additionalMouseCrs": ["EPSG:3948"], "startupView": "oblique",
            "backgroundLayers": [{"name": "ortho"}], "map3d": {"basemaps": [{"name": "dtm_bg"}]},
            "searchProviders": ["nominatim", {"provider": "qgis"}]
        })

        properties = schema["properties"]
        definitions = schema["definitions"]
        self.assertEqual(self.options(properties["url"]), [("/ows/demo", "demo"), ("/ows/other", "/ows/other")])
        self.assertEqual(self.options(properties["thumbnail"]), [("demo.png", "demo.png"), ("other.png", "other.png")])
        self.assertEqual(self.options(properties["mapCrs"]), [("EPSG:3857", "EPSG:3857"), ("EPSG:2056", "EPSG:2056")])
        self.assertEqual(self.options(properties["defaultDisplayCrs"]), [("EPSG:3857", "EPSG:3857")])
        self.assertEqual(self.options(properties["additionalMouseCrs"]["items"]), [("EPSG:3857", "EPSG:3857"), ("EPSG:3948", "EPSG:3948")])
        self.assertIn(("image/png", "image/png"), self.options(properties["format"]))
        self.assertEqual(self.options(definitions["layer"]["properties"]["name"]), [("osm", "osm"), ("ortho", "ortho"), ("dtm_bg", "dtm_bg")])
        self.assertEqual(self.options(definitions["provider"]["oneOf"][1]), [("coordinates", "coordinates"), ("nominatim", "nominatim")])
        self.assertNotIn("oneOf", definitions["provider"]["oneOf"][0])
        self.assertEqual(properties["startupView"]["enum"], ["2d", "3d", "oblique"])

    def test_leaves_base_schema_unchanged(self):
        self.form_schema({"mapCrs": "EPSG:2056"})

        self.assertNotIn("oneOf", self.BASE_SCHEMA["properties"]["mapCrs"])
