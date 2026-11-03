import json
import os
import requests

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


def json_schemas_path():
    """Return the directory of the local JSON schema files."""
    return os.environ.get('JSON_SCHEMAS_PATH', '/tmp/')


def download_json_schema(schema_url):
    """Return the response of a JSON schema download.

    Raises an exception if the download fails.

    :param str schema_url: JSON schema URL
    """
    response = requests.get(schema_url, timeout=30)
    response.raise_for_status()
    return response


def load_json_schemas(logger):
    """Return the JSON schemas listed in schema-versions.json by file name,
    read from JSON_SCHEMAS_PATH or downloaded if missing there.

    Raises an exception if a schema cannot be loaded.

    :param Logger logger: Application logger
    """
    documents = {}
    for schema_url in schema_urls():
        file_name = schema_file_name(schema_url)
        documents[file_name] = load_json_schema(
            schema_url, os.path.join(json_schemas_path(), file_name), logger
        )
    return documents


def load_json_schema(schema_url, file_path, logger):
    """Return a JSON schema read from a local file, or downloaded from its
    URL and saved to the file if the file is missing.

    :param str schema_url: JSON schema URL
    :param str file_path: Local JSON schema file
    :param Logger logger: Application logger
    """
    try:
        with open(file_path, encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(
            "Could not load JSON schema from %s:\n%s" % (file_path, e)
        )

    logger.info("Downloading JSON schema from %s" % schema_url)
    response = download_json_schema(schema_url)
    document = response.json()
    try:
        with open(file_path, 'wb') as f:
            f.write(response.content)
    except Exception as e:
        logger.warning(
            "Could not save JSON schema to %s:\n%s" % (file_path, e)
        )
    return document
