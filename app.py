"""
GovKonek Flask Application - User Management System

This application implements all 4 OOP pillars:
    1. ENCAPSULATION - Private attributes with controlled property access
    2. ABSTRACTION - Repository and Service layers hide implementation details
    3. INHERITANCE - CitizenUser and PublisherUser extend the base User class
    4. POLYMORPHISM - User subclasses override methods for role-based behavior

Architecture:
    - config.py: Configuration settings
    - models.py: Domain models (User, CitizenUser, PublisherUser)
    - repository.py: Database layer (UserRepository)
    - service.py: Business logic (AuthService)
    - routes.py: Flask routes
    - app.py: Flask application setup (this file)

This modular structure makes the code more:
    - Testable: Each layer can be tested independently
    - Maintainable: Changes to one layer don't affect others
    - Reusable: Services can be used in different contexts (CLI, API, etc.)
    - Scalable: Easy to add new features without modifying existing code
"""

from flask import Flask
from flask_login import LoginManager
from config import SECRET_KEY, LOGIN_VIEW, DATABASE_NAME
from repository import UserRepository
from models import create_user_from_db
from routes import create_routes


# FLASK APPLICATION SETUP
def create_app():
    """
    Application factory function.
    
    Creating the app in a factory function provides several benefits:
    1. Multiple app instances can be created (useful for testing)
    2. Configuration can be passed as parameters
    3. App setup is clean and organized
    
    @return: Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Configure the Flask application
    app.secret_key = SECRET_KEY
    
    # Set up Flask-Login for session management
    setup_login_manager(app)
    
    # Register all routes
    create_routes(app)
    
    return app


def setup_login_manager(app):
    """
    Configure Flask-Login for the application.
    
    Flask-Login requires a user_loader callback to reconstruct User objects from session.
    This function centralizes all login configuration.
    
    @param app: Flask application instance
    """
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = LOGIN_VIEW
    
    @login_manager.user_loader
    def load_user(user_id):
        """
        Flask-Login callback: Loads a user from the database when restoring a session.
        
        How it works:
        1. When a user logs in, Flask-Login stores their user ID in the session
        2. On subsequent requests, Flask-Login needs to rebuild the User object
        3. Flask-Login calls this function with the stored user ID
        4. We return the User object so Flask-Login can set current_user
        
        @param user_id: The user ID stored in the session
        @return: User object if found, None if user was deleted from database
        """
        # Get raw user data from database
        user_data = UserRepository.find_by_id(user_id)
        if user_data:
            # Create the correct User subclass based on role
            return create_user_from_db(user_data)
        return None


# APPLICATION ENTRY POINT
if __name__ == '__main__':
    # Create the Flask application
    app = create_app()
    
    # Start the Flask development server
    # debug=True enables auto-reload on code changes and better error pages
    app.run(debug=True)