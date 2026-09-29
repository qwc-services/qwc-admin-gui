import json
import os
import requests

from collections import OrderedDict
from copy import deepcopy
from urllib.parse import urljoin

from json_schemas import SCHEMA_VERSIONS_PATH, schema_file_name, schema_urls


class ThemeSchema():
    """JSON schema of a theme item, from the qwc2 themesConfig schemas listed in
    schema-versions.json"""

    ROOT = "theme.json"

    # Translation keys of the schema titles and descriptions start with this
    # prefix, followed by the document name and the JSON pointer of the
    # schema in the document, e.g.
    # plugins.themes.schema.theme.properties.mapCrs.title
    TRANSLATION_PREFIX = "plugins.themes.schema"

    # Keywords whose values are schemas, or lists or mappings of schemas
    SUBSCHEMA_KEYWORDS = ("items", "additionalProperties", "not")
    SUBSCHEMA_LIST_KEYWORDS = ("allOf", "anyOf", "oneOf")
    SUBSCHEMA_MAPPING_KEYWORDS = ("properties", "definitions")

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
    def referenced_documents(documents):
        """Return the root schema document and the documents it references,
        directly or not.

        :param dict documents: Schema documents by file name
        """
        file_names = {
            document["$id"]: file_name
            for file_name, document in documents.items()
        }
        referenced = {}
        pending = [ThemeSchema.ROOT]
        while pending:
            file_name = pending.pop()
            if file_name in referenced:
                continue
            document = documents[file_name]
            referenced[file_name] = document
            for _, _, node in ThemeSchema.schema_nodes(document):
                if "$ref" in node:
                    uri = urljoin(document["$id"], node["$ref"]).partition("#")[0]
                    if uri not in file_names:
                        raise ValueError("Unknown $ref %s" % node["$ref"])
                    pending.append(file_names[uri])
        return referenced

    @staticmethod
    def bundle(documents):
        """Return the root schema as a single schema: every document it
        references is added to its definitions, keyed by file name without
        extension, and every $ref is rewritten to point there.

        :param dict documents: Schema documents by file name
        """
        documents = ThemeSchema.referenced_documents(documents)
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

    @staticmethod
    def schema_nodes(node, path=()):
        """Yield the JSON pointer path, whether it is a property schema, and
        the schema itself for a schema and all its subschemas.

        :param dict node: Schema
        :param tuple path: JSON pointer path of the schema
        """
        is_property = len(path) >= 2 and path[-2] == "properties"
        yield path, is_property, node
        for key, value in node.items():
            if key in ThemeSchema.SUBSCHEMA_KEYWORDS and isinstance(value, dict):
                yield from ThemeSchema.schema_nodes(value, path + (key,))
            elif key in ThemeSchema.SUBSCHEMA_LIST_KEYWORDS:
                for idx, item in enumerate(value):
                    yield from ThemeSchema.schema_nodes(
                        item, path + (key, str(idx))
                    )
            elif key in ThemeSchema.SUBSCHEMA_MAPPING_KEYWORDS:
                for name, item in value.items():
                    yield from ThemeSchema.schema_nodes(
                        item, path + (key, name)
                    )

    @staticmethod
    def translatable_fields(documents):
        """Yield the translation key, the schema and the field name of the
        titles and descriptions of the schema documents: the title of every
        property, and every existing title and description.

        :param dict documents: Schema documents by file name
        """
        for file_name, document in documents.items():
            name = os.path.splitext(file_name)[0]
            for path, is_property, node in ThemeSchema.schema_nodes(document):
                key = ".".join((ThemeSchema.TRANSLATION_PREFIX, name) + path)
                if is_property or "title" in node:
                    yield key + ".title", node, "title"
                if "description" in node:
                    yield key + ".description", node, "description"

    @staticmethod
    def translatable_strings(documents):
        """Return the translation keys of the schema titles and descriptions
        with their English text. The English text of property titles not
        defined in the schema is None.

        :param dict documents: Schema documents by file name
        """
        return {
            key: node.get(field) for key, node, field in
            ThemeSchema.translatable_fields(
                ThemeSchema.referenced_documents(documents)
            )
        }

    @staticmethod
    def translate(documents, lookup):
        """Return copies of the schema documents with their titles and
        descriptions translated, the schema English is kept for missing
        translations.

        Missing strings are filled with the last key part in en.json by
        updateTranslations.py, they count as missing.

        :param dict documents: Schema documents by file name
        :param callable lookup: Return the translation of a message id, or
                                None if it is missing
        """
        documents = deepcopy(documents)
        for key, node, field in ThemeSchema.translatable_fields(documents):
            text = lookup(key)
            if text not in (None, "", key.rsplit(".", 1)[-1]):
                node[field] = text
        return documents

    @staticmethod
    def describe_defaults(schema, label):
        """Move the default values of a schema and its subschemas to their
        descriptions, so that forms show them without filling them in.

        :param dict schema: Schema, modified in place
        :param str label: Text written before the default value
        """
        for _, _, node in ThemeSchema.schema_nodes(schema):
            if "default" not in node:
                continue
            value = node.pop("default")
            if not isinstance(value, str):
                value = json.dumps(value, ensure_ascii=False)
            text = "%s %s" % (label, value)
            if node.get("description"):
                text = "%s %s" % (node["description"], text)
            node["description"] = text

    @staticmethod
    def subschema(schema, path):
        """Return the subschema at a path of a bundled schema, following
        local $refs.

        :param dict schema: Bundled schema
        :param tuple path: Path of keys and list indexes below the schema
        """
        def follow_refs(node):
            while "$ref" in node:
                node = ThemeSchema.subschema(schema, tuple(
                    int(part) if part.isdigit() else part
                    for part in node["$ref"].removeprefix("#/").split("/")
                ))
            return node

        node = schema
        for key in path:
            node = follow_refs(node)[key]
        return follow_refs(node)

    @staticmethod
    def set_choices(schema, path, choices, current_values):
        """Restrict a string subschema of a bundled schema to a list of
        choices, completed with the current values missing from the list.
        The subschema is left unchanged if there is no value at all.

        :param dict schema: Bundled schema, modified in place
        :param tuple path: Path of the string subschema
        :param list choices: (value, label) pairs
        :param list current_values: Values of the edited theme
        """
        options = [
            {"const": value, "title": label} for value, label in choices
        ]
        values = [value for value, _ in choices]
        for value in current_values:
            if isinstance(value, str) and value not in values:
                options.append({"const": value, "title": value})
                values.append(value)
        if options:
            ThemeSchema.subschema(schema, path)["oneOf"] = options

    @staticmethod
    def keep_enum_values(schema, theme):
        """Add the values of a theme missing from the enums of the schema
        properties to these enums, so that they are kept.

        Only the enums of the top-level properties are completed, the qwc2
        theme schemas have no other enum. A value missing from a nested enum
        would fail the form validation, and the theme could not be saved
        until it is changed, but it would not be lost.

        :param dict schema: Bundled schema, modified in place
        :param dict theme: Theme item
        """
        properties = schema.get("properties", {})
        for key, value in theme.items():
            if key not in properties:
                continue
            node = ThemeSchema.subschema(schema, ("properties", key))
            if "enum" in node and value not in node["enum"]:
                node["enum"] = node["enum"] + [value]

    @staticmethod
    def mark_constants_read_only(schema):
        """Mark the properties with a constant value as read-only, so that
        forms do not offer to edit them.

        :param dict schema: Schema, modified in place
        """
        for _, is_property, node in ThemeSchema.schema_nodes(schema):
            if is_property and "const" in node:
                node["readOnly"] = True

    @staticmethod
    def split_theme(schema, theme):
        """Return the theme settings defined by the schema, and the others.

        :param dict schema: Bundled schema
        :param dict theme: Theme item
        """
        properties = schema.get("properties", {})
        defined = OrderedDict(
            (key, value) for key, value in theme.items() if key in properties
        )
        others = OrderedDict(
            (key, value) for key, value in theme.items()
            if key not in properties
        )
        return defined, others
