"""
GovKonek Flask Application - User Management System

This application implements all 4 OOP pillars:
    1. ENCAPSULATION - Private attributes with controlled property access
    2. ABSTRACTION - Repository and Service layers hide implementation details
    3. INHERITANCE - CitizenUser and PublisherUser extend the base User class
    4. POLYMORPHISM - User subclasses override methods for role-based behavior

Architecture:
    - config.py: Configuration settings (injectable Config class)
    - models.py: Domain models (User, CitizenUser, PublisherUser)
    - repository.py: Database layer (injectable UserRepository, PostRepository)
    - service.py: Business logic (injectable AuthService, PostService)
    - routes.py: Flask routes (access services via current_app.extensions)
    - app.py: Flask application setup with dependency injection container

REFACTORED for testability:
    - All dependencies are wired in create_app() and stored on app.extensions.
    - In tests, pass mock repositories/services via create_app(test_config=...).
    - Each layer can be tested in isolation with injected mocks.
"""

from flask import Flask
from flask_login import LoginManager
from config import Config, SECRET_KEY, LOGIN_VIEW
from repository import UserRepository, PostRepository, ProjectRepository, ServiceRepository, DocumentRepository, VoiceRepository, BarangayRepository
from service import AuthService, PostService, VoiceService, ProjectService, DocumentService, BarangayService
from models import create_user_from_db
from routes import create_routes


# ===========================================================================
# Dependency Injection Container
# ===========================================================================

def _build_services(app, config):
    """
    Wire up all dependencies and attach them to app.extensions.

    This is the central dependency injection container.  Every service and
    repository is created here and stored on the app so routes can access
    them via `current_app.extensions[...]`.

    In tests, you can bypass this by passing pre-built mock instances
    directly into app.extensions before calling create_routes().

    @param app: Flask application instance
    @param config: Config instance with db_name, secret_key, etc.
    """
    # -- repositories (injectable db_path) --------------------------------
    user_repo = UserRepository(db_path=config.db_name)
    post_repo = PostRepository(db_path=config.db_name)
    project_repo = ProjectRepository(db_path=config.db_name)
    service_repo = ServiceRepository(db_path=config.db_name)
    document_repo = DocumentRepository(db_path=config.db_name)
    voice_repo = VoiceRepository(db_path=config.db_name)
    barangay_repo = BarangayRepository(db_path=config.db_name)

    # -- services (injectable repositories) -------------------------------
    auth_service = AuthService(user_repo=user_repo)
    post_service = PostService(post_repo=post_repo)
    voice_service = VoiceService(voice_repo=voice_repo)
    project_service = ProjectService(project_repo=project_repo)
    document_service = DocumentService(document_repo=document_repo, config=config)
    barangay_service = BarangayService(barangay_repo=barangay_repo)

    # -- attach to app ----------------------------------------------------
    app.extensions['config'] = config
    app.extensions['user_repo'] = user_repo
    app.extensions['post_repo'] = post_repo
    app.extensions['project_repo'] = project_repo
    app.extensions['service_repo'] = service_repo
    app.extensions['document_repo'] = document_repo
    app.extensions['voice_repo'] = voice_repo
    app.extensions['auth_service'] = auth_service
    app.extensions['post_service'] = post_service
    app.extensions['voice_service'] = voice_service
    app.extensions['project_service'] = project_service
    app.extensions['document_service'] = document_service
    app.extensions['barangay_repo'] = barangay_repo
    app.extensions['barangay_service'] = barangay_service


# ===========================================================================
# Application Factory
# ===========================================================================

def create_app(config=None):
    """
    Application factory with optional config injection for testing.

    Usage:
        # Production
        app = create_app()

        # Testing with in-memory DB
        app = create_app(Config(db_name=':memory:', secret_key='test'))

    @param config: Config instance (defaults to Config() with production values)
    @return: Configured Flask application instance
    """
    app = Flask(__name__)
    cfg = config or Config()

    # Flask configuration
    app.secret_key = cfg.secret_key

    # Wire dependencies
    _build_services(app, cfg)

    # Flask-Login
    setup_login_manager(app)

    # Register routes
    create_routes(app)

    return app


# ===========================================================================
# Flask-Login Setup
# ===========================================================================

def setup_login_manager(app):
    """
    Configure Flask-Login with a user_loader that uses the injected UserRepository.

    The user_loader accesses the repository via app.extensions so it works
    with whatever repository was wired in (real or mock).
    """
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = LOGIN_VIEW

    @login_manager.user_loader
    def load_user(user_id):
        """Rebuild User object from session using the injected UserRepository."""
        user_repo = app.extensions.get('user_repo', UserRepository())
        user_data = user_repo.find_by_id(user_id)
        if user_data:
            return create_user_from_db(user_data)
        return None


# ===========================================================================
# Entry Point
# ===========================================================================

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)