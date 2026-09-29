import json
import logging
import os
import tempfile
import unittest
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
