import tempfile
from datetime import date
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from .config import get_config, load_config

VALID_CONFIG = """\
week_start: monday
timezone: Europe/London
anchor_date: 2026-09-01
url_token: test-token
people:
  - Alex
  - Sam
  - Jo
chores:
  - name: kitchen
    period: weekly
    offset: 0
  - name: fridge
    period: monthly
    offset: 1
"""


class LoadConfigTests(SimpleTestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def write_config(self, text):
        path = Path(self.tmpdir.name) / "config.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def load(self, text):
        return load_config(self.write_config(text))

    def test_valid_config_loads(self):
        config = self.load(VALID_CONFIG)
        self.assertEqual(config.week_start, "monday")
        self.assertEqual(config.timezone, "Europe/London")
        self.assertEqual(config.anchor_date, date(2026, 9, 1))
        self.assertEqual(config.url_token, "test-token")
        self.assertEqual(config.people, ("Alex", "Sam", "Jo"))
        self.assertEqual([c.name for c in config.chores], ["kitchen", "fridge"])
        self.assertEqual(config.chores[0].period, "weekly")
        self.assertEqual(config.chores[1].offset, 1)

    def test_daily_period_accepted(self):
        config = self.load(VALID_CONFIG.replace("period: weekly", "period: daily"))
        self.assertEqual(config.chores[0].period, "daily")

    def test_anchor_date_as_quoted_string_accepted(self):
        config = self.load(VALID_CONFIG.replace("2026-09-01", '"2026-09-01"'))
        self.assertEqual(config.anchor_date, date(2026, 9, 1))

    def test_unknown_period_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("period: weekly", "period: yearly"))

    def test_duplicate_people_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("  - Jo\n", "  - Sam\n"))

    def test_duplicate_chore_names_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("name: fridge", "name: kitchen"))

    def test_missing_offset_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("    offset: 0\n", ""))

    def test_non_integer_offset_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("offset: 0", "offset: first"))

    def test_missing_top_level_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("url_token: test-token\n", ""))

    def test_unknown_top_level_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG + "anchr_date: 2026-09-01\n")

    def test_unknown_chore_key_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("offset: 0", "offest: 0"))

    def test_invalid_timezone_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("Europe/London", "Europe/Narnia"))

    def test_non_monday_week_start_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("week_start: monday", "week_start: sunday"))

    def test_anchor_date_with_time_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("2026-09-01", "2026-09-01T12:00:00"))

    def test_empty_people_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            self.load(VALID_CONFIG.replace("  - Alex\n  - Sam\n  - Jo\n", "  []\n"))

    def test_missing_file_rejected(self):
        with self.assertRaises(ImproperlyConfigured):
            load_config(Path(self.tmpdir.name) / "does-not-exist.yaml")

    def test_get_config_uses_settings_path(self):
        path = self.write_config(VALID_CONFIG)
        get_config.cache_clear()
        self.addCleanup(get_config.cache_clear)
        with override_settings(CHORES_CONFIG_PATH=path):
            config = get_config()
        self.assertEqual(config.people, ("Alex", "Sam", "Jo"))
