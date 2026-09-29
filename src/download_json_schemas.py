import os
import requests

from json_schemas import SCHEMA_VERSIONS_PATH, schema_file_name, schema_urls


# get target path
json_schemas_path = os.environ.get('JSON_SCHEMAS_PATH', '/tmp/')

print(
    "Downloading JSON schemas for the theme form to %s" % json_schemas_path
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
for schema_url in urls:
    try:
        file_name = schema_file_name(schema_url)
        file_path = os.path.join(json_schemas_path, file_name)

        # download JSON schema
        response = requests.get(schema_url, timeout=30)
        if response.status_code != requests.codes.ok:
            raise Exception(
                "Download error: Status %s\n%s..." %
                (response.status_code, response.text[0:150])
            )

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
