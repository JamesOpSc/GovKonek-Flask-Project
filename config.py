"""
GovKonek Flask Configuration Module

Contains all configuration settings for the Flask application.
This separates configuration from application logic for better maintainability.
"""

# Database configuration
DATABASE_NAME = 'govkonek.db'

# Flask secret key for session security
# For production, this should be loaded from environment variables
SECRET_KEY = 'govkonek_super_secret_key'

# Login configuration
LOGIN_VIEW = 'login'
