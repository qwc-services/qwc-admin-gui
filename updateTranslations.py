#!/usr/bin/python3

import copy
import importlib.util
import json
import logging
import re
import sys
from pathlib import Path

DEFAULT_LANG = 'en' # Default language, the admin gui shows it for the strings missing in a language

def read_json(absolute_path):
    try:
        with open(absolute_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def merge(base, addon):
    for key in base:
        if key in addon:
            if isinstance(base[key], dict):
                # Base structure is the good one. Translation files could be with out-to-date structure 
                if isinstance(addon[key], dict): 
                    merge(base[key], addon[key])
            elif not isinstance(addon[key], dict) and base[key] != addon[key]:
                base[key] = addon[key]
    return base

def remove_untranslated(lang):
    # the admin gui shows the strings missing in a language in the default language
    for key, value in list(lang.items()):
        if key == value:  # not translated string
            del lang[key]
        elif isinstance(value, dict):
            remove_untranslated(value)
            if not value:
                del lang[key]
    return lang

def create_skel(strings):
    skel = {'locale': ''}
    for string in strings:
        path = string.split('.')
        cur = skel
        for leef in path[:-1]:
            cur[leef] = cur.get(leef, {})
            cur = cur[leef]
        cur[path[-1]] = path[-1]
    return skel

def create_lang(skel, lang):
    # Adding language at the beginning of the file.
    lang_skel = merge(copy.deepcopy(skel), {'locale': lang})

    # Merge with skeleton to get missing strings
    lang_data = merge(lang_skel, read_json(current_dir / f'translations/{lang}.json'))

    if lang != DEFAULT_LANG:
        lang_data = remove_untranslated(lang_data)

    return lang_data

def list_dir(directory): 
    results = []
    extensions = ['.html', '.py', '.txt']
    for file in directory.rglob("*"):
        if file.suffix in extensions:
            results.append(file)
    return results

def update_ts_config(topdir, tsconfig, extra_msg_ids):
    files = list_dir(topdir)
    tr_regex = re.compile(r"i18n\('([A-Za-z0-9\._]+)'") 
    msg_ids = set()
    for file in files:
        with open(file, 'r') as file_content:
            data = file_content.read()
            for match in tr_regex.finditer(data):
                if not match.group(1).endswith("."):
                    msg_ids.add(match.group(1))

    msg_ids.update(extra_msg_ids)

    msg_id_list = sorted(list(msg_ids))
    json_data = read_json(tsconfig)
    json_data['strings'] = msg_id_list
    with open(tsconfig, 'w') as tsconfig_file:
        json.dump(json_data, tsconfig_file, indent=2, ensure_ascii=False)
    return msg_ids

def load_theme_schema_strings():
    # Titles and descriptions of the theme form schema, read from JSON_SCHEMAS_PATH or downloaded
    # theme_schema.py is loaded from its file to skip the flask controllers imported by the themes plugin package, and imports json_schemas.py from src
    sys.path.insert(0, str(current_dir))
    module_path = current_dir / 'plugins/themes/utils/theme_schema.py'
    spec = importlib.util.spec_from_file_location('theme_schema', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    theme_schema = module.ThemeSchema(logging.getLogger(__name__))
    return module.ThemeSchema.translatable_strings(theme_schema.load_documents())

def set_schema_english(lang_data, schema_strings):
    # The English of the texts defined in the schema is refreshed on each run, property titles are written in en.json
    for msg_id, text in schema_strings.items():
        if text is None:
            continue
        path = msg_id.split('.')
        cur = lang_data
        for part in path[:-1]:
            cur = cur[part]
        cur[path[-1]] = text


# Generate application translations
current_dir = Path(__file__).parent.absolute() / 'src'
tsconfig = current_dir / 'translations/tsconfig.json'
theme_schema_strings = load_theme_schema_strings()
update_ts_config(current_dir, tsconfig, theme_schema_strings)
config = read_json(tsconfig)
strings = config.get('strings', []) + config.get('extra_strings', [])
skel = create_skel(strings)
for lang in config.get('languages', []):
    lang_data = create_lang(skel, lang)
    if lang == DEFAULT_LANG:
        set_schema_english(lang_data, theme_schema_strings)

    # Write output
    try:
        with open(current_dir / f'translations/{lang}.json', 'w') as lang_file:
            json.dump(lang_data, lang_file, indent=2, ensure_ascii=False)
        print(f'Wrote translations/{lang}.json')
    except Exception as e:
        print(f'Failed to write translations/{lang}.json: {e}')
