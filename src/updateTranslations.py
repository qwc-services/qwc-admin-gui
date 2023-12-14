import json
import re
from pathlib import Path

DEFAULT_LANG = 'en' # Default language used to complete file when translation is missing (to avoid blank string in interface)

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

def merge_with_ref(lang, ref):
    for key,value in lang.items():
        if key == value:  # not translated string
            lang[key] = ref[key]
        else:
            if isinstance(value, dict):
                merge_with_ref(lang[key], ref[key])
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

def create_lang(skel, lang, ref=None):
    # Adding language at the beginning of the file.
    lang_skel = merge(skel, {'locale': lang})

    # Merge with skeleton to get missing strings
    lang_data = merge(lang_skel, read_json(current_dir / f'translations/{lang}.json'))

    if ref : 
        # If ref language is defined, merge with ref to get not translated string in ref language
        lang_data = merge_with_ref(lang_data, ref)

    return lang_data

def list_dir(directory): 
    results = []
    extensions = ['.html', '.py', '.txt']
    for file in directory.rglob("*"):
        if file.suffix in extensions:
            results.append(file)
    return results

def update_ts_config(topdir, tsconfig):
    files = list_dir(topdir)
    tr_regex = re.compile(r"i18n\('([A-Za-z0-9\._]+)'") 
    msg_ids = set()
    for file in files:
        with open(file, 'r') as file_content:
            data = file_content.read()
            for match in tr_regex.finditer(data):
                if not match.group(1).endswith("."):
                    msg_ids.add(match.group(1))

    msg_id_list = sorted(list(msg_ids))
    json_data = read_json(tsconfig)
    json_data['strings'] = msg_id_list
    with open(tsconfig, 'w') as tsconfig_file:
        json.dump(json_data, tsconfig_file, indent=2, ensure_ascii=False)
    return msg_ids


# Generate application translations
current_dir = Path(__file__).parent.absolute()
tsconfig = current_dir / 'translations/tsconfig.json'
update_ts_config(current_dir, tsconfig)
config = read_json(tsconfig)
strings = config.get('strings', []) + config.get('extra_strings', [])
skel = create_skel(strings)
ref = create_lang(skel, DEFAULT_LANG)
for lang in config.get('languages', []):
    lang_data = create_lang(skel, lang, ref)

    # Write output
    try:
        with open(current_dir / f'translations/{lang}.json', 'w') as lang_file:
            json.dump(lang_data, lang_file, indent=2, ensure_ascii=False)
        print(f'Wrote translations/{lang}.json')
    except Exception as e:
        print(f'Failed to write translations/{lang}.json: {e}')
