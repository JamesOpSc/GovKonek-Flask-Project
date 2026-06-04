"""
GovKonek Flask Configuration Module

Uses a Config class (not module-level globals) so configuration can be
injected for testing. The default instance provides production-ready values.

OOP PRINCIPLES DEMONSTRATED:
    - ENCAPSULATION: Private attributes (_db_name, _secret_key, etc.) with
      @property accessors prevent accidental modification at runtime.
    - DEPENDENCY INJECTION: Config instances are passed to create_app(),
      not imported as module globals.
"""

import os


class Config:
    """
    Injectable configuration class with encapsulated attributes.

    ENCAPSULATION (from lecture):
      - Private attributes (prefixed with _) prevent direct access.
      - @property provides read-only access.
      - Values are set ONLY at construction time.
      - This prevents a bug where one module accidentally changes the
        database path or secret key at runtime.

    Usage:
        # Production
        config = Config()

        # Testing
        config = Config(db_name=':memory:', secret_key='test-key')
    """

    def __init__(self,
                 db_name=None,
                 secret_key=None,
                 login_view=None,
                 openweather_api_key=None,
                 upload_folder=None):
        """
        @param db_name: SQLite database filename (default: from GOVKONEK_DB env or 'govkonek.db')
        @param secret_key: Flask session signing key (default: from GOVKONEK_SECRET_KEY env)
        @param login_view: Flask-Login redirect endpoint (default: 'login')
        @param openweather_api_key: OpenWeatherMap API key (default: from OPENWEATHER_API_KEY env)
        @param upload_folder: Directory for uploaded transparency documents (default: 'static/uploads')
        """
        # Private attributes — cannot be modified after construction
        self._db_name = db_name or os.environ.get('GOVKONEK_DB', 'govkonek.db')
        self._secret_key = secret_key or os.environ.get(
            'GOVKONEK_SECRET_KEY', 'govkonek_super_secret_key'
        )
        self._login_view = login_view or 'login'
        self._openweather_api_key = openweather_api_key or os.environ.get('OPENWEATHER_API_KEY', '')
        self._upload_folder = upload_folder or os.environ.get(
            'GOVKONEK_UPLOAD_FOLDER',
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
        )
        self._allowed_extensions = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'txt', 'csv'}

    # ===================================================================
    # ENCAPSULATION: @property accessors (read-only)
    # ===================================================================
    # Per the Encapsulation lecture:
    #   "Make your data private and access it through public methods."
    #   "Getters: methods used to access private attributes from a class."
    #   "Setters: methods used to set values to private attributes."
    #
    # Here we use Python's @property decorator (as shown in
    # 03_encapsulation_property_class.py) instead of explicit get_/set_
    # methods, which is the more Pythonic approach.

    @property
    def db_name(self):
        """
        Read-only access to the database filename.

        ENCAPSULATION: Prevents runtime modification of the database path.
        @return: Database file name or ':memory:' for in-memory databases
        """
        return self._db_name

    @property
    def secret_key(self):
        """
        Read-only access to the Flask secret key.

        ENCAPSULATION: Prevents exposure or modification of the signing key.
        @return: Secret key string used for session signing
        """
        return self._secret_key

    @property
    def login_view(self):
        """
        Read-only access to the Flask-Login redirect endpoint.

        ENCAPSULATION: Prevents accidental changes to the login route name.
        @return: Login view endpoint name (e.g., 'login')
        """
        return self._login_view

    @property
    def openweather_api_key(self):
        """
        Read-only access to the OpenWeather API key.

        ENCAPSULATION: Protects the API key from unauthorized access.
        @return: OpenWeatherMap API key string (may be empty)
        """
        return self._openweather_api_key

    @property
    def upload_folder(self):
        """
        Read-only access to the document upload directory.

        ENCAPSULATION: Prevents changing the upload path at runtime.
        @return: Absolute path to the uploads directory
        """
        return self._upload_folder

    @property
    def allowed_extensions(self):
        """
        Read-only access to the set of allowed file extensions.

        ENCAPSULATION: Prevents bypassing file type validation.
        @return: Set of allowed lowercase extensions (e.g., {'pdf', 'docx'})
        """
        return self._allowed_extensions

    # ===================================================================
    # Utility Methods
    # ===================================================================

    def as_dict(self):
        """
        Return all configuration values as a dictionary.
        Useful for logging/debugging (with secret_key masked).

        @return: Dict of config keys and values
        """
        return {
            'db_name': self._db_name,
            'secret_key': '***masked***',
            'login_view': self._login_view,
            'openweather_api_key': '***masked***' if self._openweather_api_key else '',
        }

    def __repr__(self):
        """Developer-friendly representation."""
        return (f"Config(db_name='{self._db_name}', "
                f"secret_key='***', login_view='{self._login_view}')")


# Singleton default config for backward compatibility and simple usage
_default = Config()

# Module-level aliases so existing code doesn't break during transition
# These proxy through the default Config's @property accessors
DATABASE_NAME = _default.db_name
SECRET_KEY = _default.secret_key
LOGIN_VIEW = _default.login_view


def get_config():
    """Return the default Config instance (useful for simple scripts)."""
    return _default
