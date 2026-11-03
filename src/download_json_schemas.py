import os

from json_schemas import (
    SCHEMA_VERSIONS_PATH, download_json_schema, json_schemas_path,
    schema_file_name, schema_urls
)
from plugins.themes.utils import ThemeSchema


# get target path
target_path = json_schemas_path()

print(
    "Downloading JSON schemas for the theme form to %s" % target_path
)

# load schema-versions.json
try:
    urls = schema_urls()
except Exception as e:
    print(
        "Error: Could not load JSON schema versions from %s:\n%s" %
        (SCHEMA_VERSIONS_PATH, e)
    )
    exit(1)

# download and save JSON schemas
errors = False
documents = {}
for schema_url in urls:
    try:
        file_name = schema_file_name(schema_url)
        file_path = os.path.join(target_path, file_name)

        # download JSON schema, rejecting a response which is not JSON
        response = download_json_schema(schema_url)
        documents[file_name] = response.json()

        # save to file
        with open(file_path, 'wb') as f:
            f.write(response.content)
            print("Downloaded %s" % file_name)
    except Exception as e:
        print(
            "Error: Could not download JSON schema from %s\n%s" %
            (schema_url, e)
        )
        errors = True

if errors:
    exit(1)

# check that schema-versions.json lists every schema the theme schema
# references, so that a new schema in qwc2 fails the build rather than the
# theme form
try:
    ThemeSchema.bundle(documents)
except Exception as e:
    print(
        "Error: The theme schema references a schema missing from %s:\n%s" %
        (SCHEMA_VERSIONS_PATH, e)
    )
    exit(1)
