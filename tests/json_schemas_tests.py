import json
import logging
import os
import tempfile
import unittest
from unittest.mock import patch

from json_schemas import load_json_schemas, schema_urls


BASE_URL = "https://example.com/schemas/"

DOCUMENTS = {
    "theme.json": {"$id": BASE_URL + "theme.json", "type": "object"},
    "layer.json": {"$id": BASE_URL + "layer.json", "type": "object"}
}


class LoadJsonSchemasTestCase(unittest.TestCase):
    """Test loading the JSON schemas listed in schema-versions.json"""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        patcher = patch.dict(os.environ, {"JSON_SCHEMAS_PATH": self.tmpdir.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmpdir.cleanup)
        patcher = patch("json_schemas.schema_urls", return_value=[
            BASE_URL + "theme.json", BASE_URL + "layer.json"
        ])
        patcher.start()
        self.addCleanup(patcher.stop)
        self.logger = logging.getLogger(__name__)

    def test_lists_qwc2_schemas(self):
        # schema_urls is imported before it is patched
        self.assertIn(
            "https://github.com/qgis/qwc2/raw/master/schemas/theme.json",
            schema_urls()
        )

    def test_reads_local_files(self):
        for file_name, document in DOCUMENTS.items():
            with open(os.path.join(self.tmpdir.name, file_name), "w") as f:
                json.dump(document, f)

        with patch("json_schemas.requests.get") as get:
            documents = load_json_schemas(self.logger)

        get.assert_not_called()
        self.assertEqual(documents, DOCUMENTS)

    def test_downloads_missing_files(self):
        with open(os.path.join(self.tmpdir.name, "theme.json"), "w") as f:
            json.dump(DOCUMENTS["theme.json"], f)

        with patch("json_schemas.requests.get") as get:
            get.return_value.json.return_value = DOCUMENTS["layer.json"]
            get.return_value.content = json.dumps(DOCUMENTS["layer.json"]).encode()
            documents = load_json_schemas(self.logger)

        get.assert_called_once_with(BASE_URL + "layer.json", timeout=30)
        self.assertEqual(documents, DOCUMENTS)

        # the downloaded file is saved for the next loads
        with patch("json_schemas.requests.get") as get:
            documents = load_json_schemas(self.logger)

        get.assert_not_called()
        self.assertEqual(documents, DOCUMENTS)
