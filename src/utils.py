import json
import logging
import os
import pathlib

# Load translation strings
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'en')
translations = {}
try:
    locale = DEFAULT_LOCALE
    # Get the directory of utils.py
    script_directory = pathlib.Path(__file__).resolve().parent
    # Adjust the path based on the script directory
    path = script_directory / 'translations/{}.json'.format(locale)
    with open(path, 'r') as f:
        translations[locale] = json.load(f)
except Exception as e:
    logging.error( 
        "Failed to load translation strings for locale '%s' from %s\n%s"
        % (locale, path, e)
    )

def i18n(value, args = [],locale = DEFAULT_LOCALE) : 
    # traverse translations dict for locale
    parts = value.split('.')
    lookup = translations.get(locale, {})
    for part in parts:
        if isinstance(lookup, dict):
            # get next lookup level
            lookup = lookup.get(part)
        else:
            # lookup level too deep
            lookup = None
        if lookup is None:
            # return input value if not found
            lookup = value
            break
    return lookup.format(*args)
