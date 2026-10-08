import json
import os

from urllib.parse import urlparse


# schema-versions.json lists the URLs of the JSON schemas used by the admin gui
SCHEMA_VERSIONS_PATH = os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'schema-versions.json'
)


def schema_urls():
    """Return the JSON schema URLs listed in schema-versions.json.

    Raises an exception if schema-versions.json cannot be read.
    """
    with open(SCHEMA_VERSIONS_PATH, encoding='utf-8') as f:
        schema_versions = json.load(f)
    return [
        schema.get('schema_url', '')
        for schema in schema_versions.get('schemas', [])
    ]


def schema_file_name(schema_url):
    """Return the local file name of a JSON schema.

    :param str schema_url: JSON schema URL
    """
    return os.path.basename(urlparse(schema_url).path)
