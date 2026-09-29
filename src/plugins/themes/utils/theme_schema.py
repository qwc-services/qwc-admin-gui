import json
import os
import requests

from urllib.parse import urljoin

from json_schemas import SCHEMA_VERSIONS_PATH, schema_file_name, schema_urls


class ThemeSchema():
    """JSON schema of a theme item, from the qwc2 themesConfig schemas listed in
    schema-versions.json"""

    ROOT = "theme.json"

    def __init__(self, logger):
        """Constructor

        :param Logger logger: Application logger
        """
        self.logger = logger
        self.json_schemas_path = os.environ.get('JSON_SCHEMAS_PATH', '/tmp/')
        self.documents = None

        try:
            self.schema_urls = schema_urls()
        except Exception as e:
            self.logger.warning(
                "Could not load JSON schema versions from %s:\n%s" %
                (SCHEMA_VERSIONS_PATH, e)
            )
            self.schema_urls = []

    def load_documents(self):
        """Return the schema documents by file name, read from
        JSON_SCHEMAS_PATH or downloaded if missing there.

        Raises an exception if a schema cannot be loaded.
        """
        if self.documents is None:
            documents = {}
            for schema_url in self.schema_urls:
                file_name = schema_file_name(schema_url)
                documents[file_name] = self.load_document(
                    schema_url, os.path.join(self.json_schemas_path, file_name)
                )
            self.documents = documents
        return self.documents

    def load_document(self, schema_url, file_path):
        """Return a schema document read from a local file, or downloaded
        from its URL if the file is missing.

        :param str schema_url: JSON schema URL
        :param str file_path: Local JSON schema file
        """
        try:
            with open(file_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.warning(
                "Could not load JSON schema from %s:\n%s" % (file_path, e)
            )

        self.logger.info("Downloading JSON schema from %s" % schema_url)
        response = requests.get(schema_url, timeout=30)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def bundle(documents):
        """Return the root schema as a single schema: every document is added
        to its definitions, keyed by file name without extension, and every
        $ref is rewritten to point there.

        :param dict documents: Schema documents by file name
        """
        root = ThemeSchema.ROOT
        names = {
            document["$id"]: os.path.splitext(file_name)[0]
            for file_name, document in documents.items()
        }
        definitions = {
            names[document["$id"]]: ThemeSchema.local_refs(
                document, document["$id"], names
            )
            for document in documents.values()
        }
        schema = dict(definitions[names[documents[root]["$id"]]])
        schema["$schema"] = documents[root]["$schema"]
        schema["definitions"] = definitions
        return schema

    @staticmethod
    def local_refs(node, base_uri, names):
        """Return a copy of a schema node with its $refs pointing to the
        bundled documents, and without the $id and $schema keys.

        :param obj node: Schema node
        :param str base_uri: $id of the document of the node
        :param dict names: Bundled document names by $id
        """
        if isinstance(node, list):
            return [
                ThemeSchema.local_refs(item, base_uri, names) for item in node
            ]
        if not isinstance(node, dict):
            return node

        result = {}
        for key, value in node.items():
            if key == "$ref":
                uri, _, fragment = urljoin(base_uri, value).partition("#")
                if uri not in names:
                    raise ValueError("Unknown $ref %s" % value)
                result[key] = "#/definitions/%s%s" % (names[uri], fragment)
            elif key not in ("$id", "$schema"):
                result[key] = ThemeSchema.local_refs(value, base_uri, names)
        return result
