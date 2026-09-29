import json
import logging
import os
import pathlib

# Load translation strings, English is used for the strings missing in the
# locale
DEFAULT_LOCALE = os.environ.get('DEFAULT_LOCALE', 'en')
FALLBACK_LOCALE = 'en'
translations = {}
for locale in dict.fromkeys([DEFAULT_LOCALE, FALLBACK_LOCALE]):
    try:
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

def lookup_translation(value, locale = DEFAULT_LOCALE):
    """Return the translation string of a message id in a locale, or in the
    fallback locale if it is missing there, or None if it is missing in both.

    :param str value: Message id
    :param str locale: Locale
    """
    # traverse translations dict for locale, then for the fallback locale
    parts = value.split('.')
    for lookup_locale in (locale, FALLBACK_LOCALE):
        lookup = translations.get(lookup_locale, {})
        for part in parts:
            if isinstance(lookup, dict):
                # get next lookup level
                lookup = lookup.get(part)
            else:
                # lookup level too deep
                lookup = None
            if lookup is None:
                break
        if isinstance(lookup, str):
            return lookup
    return None

def i18n(value, args = [],locale = DEFAULT_LOCALE) : 
    text = lookup_translation(value, locale)
    # return input value if not found
    return (value if text is None else text).format(*args)
