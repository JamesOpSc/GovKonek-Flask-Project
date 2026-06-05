"""
Unit tests for the GovKonek configuration module.

Tests OOP principles:
  - ENCAPSULATION: @property accessors prevent direct attribute modification
  - DEPENDENCY INJECTION: Config instances are injectable for testing
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DATABASE_NAME, SECRET_KEY, LOGIN_VIEW, get_config


class TestConfigEncapsulation(unittest.TestCase):
    """
    Tests for Config class encapsulation.

    From the Encapsulation lecture:
      'Make your data private and access it through public methods.'
      'Getters: methods used to access private attributes from a class.'
    """

    def setUp(self):
        self.config = Config(
            db_name='test.db',
            secret_key='my-secret',
            login_view='my-login',
            openweather_api_key='weather-key-123'
        )

    def tearDown(self):
        del self.config

    # -- Property access (read) ------------------------------------------

    def test_db_name_property(self):
        """@property db_name should return the constructor value."""
        self.assertEqual(self.config.db_name, 'test.db')

    def test_secret_key_property(self):
        """@property secret_key should return the constructor value."""
        self.assertEqual(self.config.secret_key, 'my-secret')

    def test_login_view_property(self):
        """@property login_view should return the constructor value."""
        self.assertEqual(self.config.login_view, 'my-login')

    def test_openweather_api_key_property(self):
        """@property openweather_api_key should return the constructor value."""
        self.assertEqual(self.config.openweather_api_key, 'weather-key-123')

    # -- ENCAPSULATION: Properties are read-only -------------------------

    def test_db_name_is_read_only(self):
        """
        ENCAPSULATION: @property without @setter means read-only.
        Attempting to set should raise AttributeError.
        """
        with self.assertRaises(AttributeError):
            self.config.db_name = 'hacked.db'

    def test_secret_key_is_read_only(self):
        """ENCAPSULATION: secret_key cannot be modified at runtime."""
        with self.assertRaises(AttributeError):
            self.config.secret_key = 'leaked-key'

    def test_login_view_is_read_only(self):
        """ENCAPSULATION: login_view cannot be modified at runtime."""
        with self.assertRaises(AttributeError):
            self.config.login_view = 'fake-login'

    def test_openweather_api_key_is_read_only(self):
        """ENCAPSULATION: openweather_api_key cannot be modified at runtime."""
        with self.assertRaises(AttributeError):
            self.config.openweather_api_key = 'stolen-key'

    # -- Default values --------------------------------------------------

    def test_default_db_name(self):
        """Default db_name should be 'govkonek.db'."""
        c = Config()
        self.assertEqual(c.db_name, 'govkonek.db')

    def test_default_login_view(self):
        """Default login_view should be 'login'."""
        c = Config()
        self.assertEqual(c.login_view, 'login')

    # -- as_dict and repr ------------------------------------------------

    def test_as_dict_masks_secrets(self):
        """as_dict() should mask the secret_key."""
        d = self.config.as_dict()
        self.assertEqual(d['db_name'], 'test.db')
        self.assertEqual(d['secret_key'], '***masked***')
        self.assertEqual(d['openweather_api_key'], '***masked***')

    def test_repr_masks_secrets(self):
        """__repr__ should mask the secret_key."""
        r = repr(self.config)
        self.assertNotIn('my-secret', r)
        self.assertIn('***', r)


class TestModuleLevelAliases(unittest.TestCase):
    """Tests for backward-compatible module-level constants."""

    def test_database_name_is_string(self):
        """DATABASE_NAME should be a non-empty string."""
        self.assertIsInstance(DATABASE_NAME, str)
        self.assertTrue(len(DATABASE_NAME) > 0)

    def test_secret_key_is_string(self):
        """SECRET_KEY should be a non-empty string."""
        self.assertIsInstance(SECRET_KEY, str)
        self.assertTrue(len(SECRET_KEY) > 0)

    def test_login_view_is_string(self):
        """LOGIN_VIEW should be a non-empty string."""
        self.assertIsInstance(LOGIN_VIEW, str)
        self.assertTrue(len(LOGIN_VIEW) > 0)

    def test_get_config_returns_config_instance(self):
        """get_config() should return a Config instance."""
        c = get_config()
        self.assertIsInstance(c, Config)


if __name__ == '__main__':
    unittest.main(verbosity=2)
