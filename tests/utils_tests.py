import unittest
from unittest.mock import patch

import utils


TRANSLATIONS = {
    "fr": {"common": {"save": "Enregistrer", "count": "{} éléments"}},
    "en": {"common": {"save": "Save", "cancel": "Cancel", "count": "{} items"}}
}


@patch.object(utils, "FALLBACK_LOCALE", "en")
@patch.dict(utils.translations, TRANSLATIONS, clear=True)
class I18nTestCase(unittest.TestCase):
    """Test looking up translation strings"""

    def test_returns_string_of_the_locale(self):
        self.assertEqual(utils.i18n("common.save", locale="fr"), "Enregistrer")
        self.assertEqual(utils.i18n("common.count", [3], locale="fr"), "3 éléments")

    def test_falls_back_to_english(self):
        self.assertEqual(utils.i18n("common.cancel", locale="fr"), "Cancel")

    def test_returns_the_key_of_missing_strings(self):
        self.assertEqual(utils.i18n("common.missing", locale="fr"), "common.missing")
        self.assertEqual(utils.i18n("common.save.deeper", locale="fr"), "common.save.deeper")

    def test_looks_up_strings_without_formatting(self):
        self.assertEqual(utils.lookup_translation("common.count", "fr"), "{} éléments")
        self.assertEqual(utils.lookup_translation("common.cancel", "fr"), "Cancel")
        self.assertIsNone(utils.lookup_translation("common.missing", "fr"))
