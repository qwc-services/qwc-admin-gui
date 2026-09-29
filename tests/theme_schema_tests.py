import json
import logging
import os
import tempfile
import unittest
from collections import OrderedDict
from unittest.mock import patch

from plugins.themes.utils import ThemeSchema


BASE_URL = "https://example.com/schemas/"

# small schema documents with the same kinds of $refs as the qwc2 schemas
DOCUMENTS = {
    "theme.json": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": BASE_URL + "theme.json",
        "definitions": {
            "bbox": {"type": "array", "items": {"type": "number"}}
        },
        "type": "object",
        "properties": {
            "extent": {
                "description": "Initial extent.",
                "allOf": [{"$ref": "#/definitions/bbox"}]
            },
            "backgroundLayers": {
                "type": "array",
                "items": {"$ref": "layer.json"}
            }
        }
    },
    "layer.json": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": BASE_URL + "layer.json",
        "definitions": {
            "name": {"type": "string"}
        },
        "type": "object",
        "properties": {
            "name": {"$ref": "#/definitions/name"},
            "extent": {"$ref": "theme.json#/definitions/bbox"}
        }
    }
}


class ThemeSchemaBundleTestCase(unittest.TestCase):
    """Test bundling the theme schema documents into one schema"""

    def test_bundles_documents_with_local_refs(self):
        schema = ThemeSchema.bundle(DOCUMENTS)

        bbox_ref = {"$ref": "#/definitions/theme/definitions/bbox"}
        theme = {
            "definitions": {
                "bbox": {"type": "array", "items": {"type": "number"}}
            },
            "type": "object",
            "properties": {
                "extent": {"description": "Initial extent.", "allOf": [bbox_ref]},
                "backgroundLayers": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/layer"}
                }
            }
        }
        layer = {
            "definitions": {
                "name": {"type": "string"}
            },
            "type": "object",
            "properties": {
                "name": {"$ref": "#/definitions/layer/definitions/name"},
                "extent": bbox_ref
            }
        }
        self.assertEqual(schema, {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": theme["properties"],
            "definitions": {"theme": theme, "layer": layer}
        })

    def test_keeps_recursive_refs(self):
        documents = {
            "theme.json": {
                **DOCUMENTS["theme.json"],
                "definitions": {"group": {
                    "type": "object",
                    "properties": {"items": {"$ref": "#/definitions/group"}}
                }},
                "properties": {"group": {"$ref": "#/definitions/group"}}
            }
        }

        schema = ThemeSchema.bundle(documents)

        self.assertEqual(
            schema["definitions"]["theme"]["definitions"]["group"]["properties"],
            {"items": {"$ref": "#/definitions/theme/definitions/group"}}
        )

    def test_leaves_out_unreferenced_documents(self):
        documents = {**DOCUMENTS, "other.json": {
            "$id": BASE_URL + "other.json", "type": "object"
        }}

        schema = ThemeSchema.bundle(documents)

        self.assertEqual(list(schema["definitions"]), ["theme", "layer"])

    def test_rejects_refs_to_other_documents(self):
        documents = {
            "theme.json": {
                **DOCUMENTS["theme.json"],
                "properties": {"layer": {"$ref": "other.json"}}
            }
        }

        with self.assertRaises(ValueError):
            ThemeSchema.bundle(documents)


class ThemeSchemaLoadTestCase(unittest.TestCase):
    """Test loading the schema documents listed in schema-versions.json"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        patcher = patch.dict(os.environ, {"JSON_SCHEMAS_PATH": self.tmpdir.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)
        self.theme_schema = ThemeSchema(logging.getLogger(__name__))
        self.theme_schema.schema_urls = [
            BASE_URL + "theme.json", BASE_URL + "layer.json"
        ]

    def test_lists_qwc2_schemas(self):
        schema_urls = ThemeSchema(logging.getLogger(__name__)).schema_urls

        self.assertIn(
            "https://github.com/qgis/qwc2/raw/master/schemas/theme.json",
            schema_urls
        )

    def test_reads_local_files(self):
        for file_name, document in DOCUMENTS.items():
            with open(os.path.join(self.tmpdir.name, file_name), "w") as f:
                json.dump(document, f)

        with patch("plugins.themes.utils.theme_schema.requests.get") as get:
            documents = self.theme_schema.load_documents()

        get.assert_not_called()
        self.assertEqual(documents, DOCUMENTS)

    def test_downloads_missing_files(self):
        with open(os.path.join(self.tmpdir.name, "theme.json"), "w") as f:
            json.dump(DOCUMENTS["theme.json"], f)

        with patch("plugins.themes.utils.theme_schema.requests.get") as get:
            get.return_value.json.return_value = DOCUMENTS["layer.json"]
            documents = self.theme_schema.load_documents()

        get.assert_called_once_with(BASE_URL + "layer.json", timeout=30)
        self.assertEqual(documents, DOCUMENTS)


class ThemeSchemaTranslateTestCase(unittest.TestCase):
    """Test translating the schema titles and descriptions"""

    def test_lists_titles_and_descriptions_of_referenced_documents(self):
        documents = {**DOCUMENTS, "other.json": {
            "$id": BASE_URL + "other.json", "title": "Other"
        }}

        strings = ThemeSchema.translatable_strings(documents)

        prefix = "plugins.themes.schema."
        self.assertEqual(strings, {
            prefix + "theme.properties.extent.title": None,
            prefix + "theme.properties.extent.description": "Initial extent.",
            prefix + "theme.properties.backgroundLayers.title": None,
            prefix + "layer.properties.name.title": None,
            prefix + "layer.properties.extent.title": None,
        })

    def test_translates_titles_and_descriptions(self):
        prefix = "plugins.themes.schema."
        translations = {
            prefix + "theme.properties.extent.title": "Emprise",
            prefix + "theme.properties.extent.description":
                "Emprise initiale, avec {placeholder}.",
            prefix + "layer.properties.name.title": "Nom"
        }

        documents = ThemeSchema.translate(DOCUMENTS, translations.get)

        self.assertEqual(documents["theme.json"]["properties"]["extent"], {
            "title": "Emprise",
            "description": "Emprise initiale, avec {placeholder}.",
            "allOf": [{"$ref": "#/definitions/bbox"}]
        })
        self.assertEqual(
            documents["layer.json"]["properties"]["name"],
            {"title": "Nom", "$ref": "#/definitions/name"}
        )
        self.assertNotIn("title", DOCUMENTS["layer.json"]["properties"]["name"])

    def test_keeps_english_for_missing_translations(self):
        # updateTranslations.py fills missing strings with the last key part
        prefix = "plugins.themes.schema.theme.properties.extent."
        translations = {
            prefix + "title": "title", prefix + "description": "description"
        }

        documents = ThemeSchema.translate(DOCUMENTS, translations.get)

        self.assertEqual(
            documents["theme.json"]["properties"]["extent"],
            DOCUMENTS["theme.json"]["properties"]["extent"]
        )


class ThemeSchemaDefaultsTestCase(unittest.TestCase):
    """Test moving the schema default values to the descriptions"""

    def test_moves_defaults_to_descriptions(self):
        schema = {"type": "object", "definitions": {"format": {
            "type": "string", "description": "Image format.",
            "default": "image/png"
        }}, "properties": {
            "tiled": {"type": "boolean", "default": False},
            "format": {"$ref": "#/definitions/format"}
        }}

        ThemeSchema.describe_defaults(schema, "Default:")

        self.assertEqual(schema["definitions"]["format"], {
            "type": "string", "description": "Image format. Default: image/png"
        })
        self.assertEqual(schema["properties"]["tiled"], {
            "type": "boolean", "description": "Default: false"
        })


class ThemeSchemaChoicesTestCase(unittest.TestCase):
    """Test restricting schema values to lists of choices"""

    def test_sets_choices_behind_refs(self):
        schema = ThemeSchema.bundle(DOCUMENTS)

        ThemeSchema.set_choices(
            schema, ("properties", "backgroundLayers", "items", "properties", "name"),
            [("osm", "OpenStreetMap"), ("ortho", "Orthophoto")], ["osm"]
        )

        self.assertEqual(schema["definitions"]["layer"]["definitions"]["name"], {
            "type": "string",
            "oneOf": [
                {"const": "osm", "title": "OpenStreetMap"},
                {"const": "ortho", "title": "Orthophoto"}
            ]
        })

    def test_keeps_current_values_missing_from_choices(self):
        schema = {"type": "object", "properties": {"mapCrs": {"type": "string"}}}

        ThemeSchema.set_choices(
            schema, ("properties", "mapCrs"), [("EPSG:3857", "EPSG:3857")],
            ["EPSG:2056", None, "EPSG:3857", "EPSG:2056"]
        )

        self.assertEqual(schema["properties"]["mapCrs"]["oneOf"], [
            {"const": "EPSG:3857", "title": "EPSG:3857"},
            {"const": "EPSG:2056", "title": "EPSG:2056"}
        ])


    def test_leaves_schema_unchanged_without_values(self):
        schema = {"type": "object", "properties": {"thumbnail": {"type": "string"}}}

        ThemeSchema.set_choices(schema, ("properties", "thumbnail"), [], [None])

        self.assertEqual(schema["properties"]["thumbnail"], {"type": "string"})


    def test_keeps_values_missing_from_enums(self):
        schema = {"type": "object", "properties": {
            "startupView": {"type": "string", "enum": ["2d", "3d"]},
            "format": {"type": "string"}
        }}

        ThemeSchema.keep_enum_values(schema, {
            "startupView": "4d", "format": "image/png", "custom": 1
        })

        self.assertEqual(schema["properties"], {
            "startupView": {"type": "string", "enum": ["2d", "3d", "4d"]},
            "format": {"type": "string"}
        })

    def test_marks_constant_properties_read_only(self):
        schema = {"type": "object", "definitions": {"qgis": {"properties": {
            "provider": {"const": "qgis"}
        }}}, "properties": {
            "mapCrs": {"oneOf": [{"const": "EPSG:3857", "title": "EPSG:3857"}]}
        }}

        ThemeSchema.mark_constants_read_only(schema)

        self.assertEqual(
            schema["definitions"]["qgis"]["properties"]["provider"],
            {"const": "qgis", "readOnly": True}
        )
        self.assertNotIn("readOnly", schema["properties"]["mapCrs"]["oneOf"][0])


class ThemeSchemaSplitTestCase(unittest.TestCase):
    """Test splitting a theme in settings defined by the schema and others"""

    def test_splits_theme_keeping_key_order(self):
        schema = ThemeSchema.bundle(DOCUMENTS)
        theme = OrderedDict([
            ("custom", 1), ("extent", [0, 0, 1, 1]), ("other", {"a": 2}),
            ("backgroundLayers", [])
        ])

        defined, others = ThemeSchema.split_theme(schema, theme)

        self.assertEqual(list(defined.items()), [
            ("extent", [0, 0, 1, 1]), ("backgroundLayers", [])
        ])
        self.assertEqual(list(others.items()), [
            ("custom", 1), ("other", {"a": 2})
        ])
