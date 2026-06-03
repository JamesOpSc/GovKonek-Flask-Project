"""
GovKonek Flask Configuration Module

Uses a Config class (not module-level globals) so configuration can be
injected for testing. The default instance provides production-ready values.
"""

import os


class Config:
    """
    Injectable configuration class.

    Design principle: Dependency Injection for testability.
    Instead of importing module-level globals (hard to mock in tests),
    create a Config instance and pass it where needed.

    Usage:
        # Production
        config = Config()

        # Testing
        config = Config(db_name=':memory:', secret_key='test-key')
    """

    def __init__(self,
                 db_name=None,
                 secret_key=None,
                 login_view=None):
        """
        @param db_name: SQLite database filename (default: 'govkonek.db')
        @param secret_key: Flask session signing key (default: from env or hardcoded)
        @param login_view: Flask-Login redirect endpoint (default: 'login')
        """
        self.db_name = db_name or os.environ.get('GOVKONEK_DB', 'govkonek.db')
        self.secret_key = secret_key or os.environ.get(
            'GOVKONEK_SECRET_KEY', 'govkonek_super_secret_key'
        )
        self.login_view = login_view or 'login'


# Singleton default config for backward compatibility and simple usage
_default = Config()

# Module-level aliases so existing code doesn't break during transition
DATABASE_NAME = _default.db_name
SECRET_KEY = _default.secret_key
LOGIN_VIEW = _default.login_view


def get_config():
    """Return the default Config instance (useful for simple scripts)."""
    return _default
