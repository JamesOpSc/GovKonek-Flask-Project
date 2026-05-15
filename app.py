"""
GovKonek Flask Application - User Management System
This application implements all 4 OOP pillars:
    1. ENCAPSULATION - Private attributes with controlled property access
    2. ABSTRACTION - Repository and Service layers hide implementation details
    3. INHERITANCE - CitizenUser and PublisherUser extend the base User class
    4. POLYMORPHISM - User subclasses override methods for role-based behavior

Architecture:
    - Repository Layer: Handles all database operations (UserRepository)
    - Domain Models: User classes with business logic (User, CitizenUser, PublisherUser)
    - Service Layer: Orchestrates authentication logic (AuthService)
    - Route Layer: Flask routes that use the service layer
"""

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from abc import ABC, abstractmethod

# FLASK APPLICATION SETUP
app = Flask(__name__)

# The secret key is required by Flask to keep user sessions secure.
# For a real production app, this should be a random string hidden in a .env file.
app.secret_key = 'govkonek_super_secret_key'

# Set up the Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
# If someone tries to access a protected page without logging in, send them here
login_manager.login_view = 'login'

# DATABASE LAYER (ABSTRACTION PRINCIPLE)
# Purpose: The Repository pattern abstracts all database operations.
# Benefits: Database code is isolated, easy to change database without touching business logic.
# All database queries are centralized in one place for easier maintenance and testing.

class UserRepository:
    """
    Repository pattern: Centralizes all database operations for user data.
    This class handles all SQL queries, keeping database logic separate from business logic.
    This is the ABSTRACTION principle in action - we hide database complexity behind simple methods.
    """
    
    @staticmethod
    def get_db_connection():
        """
        Create and return a new database connection.
        @return: SQLite connection object with Row factory for easy column access
        """
        conn = sqlite3.connect('govkonek.db')
        # Row factory allows us to access columns by name (e.g., user['username'])
        # instead of by index (e.g., user[0])
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def find_by_id(user_id):
        """
        Fetch a user from the database by their ID.
        Used when Flask-Login loads a user session.
        
        @param user_id: The unique identifier of the user
        @return: Row object containing user data or None if not found
        """
        conn = UserRepository.get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        conn.close()
        return user_data
    
    @staticmethod
    def find_by_username(username):
        """
        Fetch a user from the database by their username.
        Used during login and registration to check if user exists.
        
        @param username: The username to search for
        @return: Row object containing user data or None if not found
        """
        conn = UserRepository.get_db_connection()
        user_data = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        return user_data
    
    @staticmethod
    def create(username, hashed_password, role):
        """
        Insert a new user into the database.
        Handles IntegrityError if username already exists due to UNIQUE constraint.
        
        @param username: The new user's username (must be unique)
        @param hashed_password: The bcrypt hashed password (never store plain passwords!)
        @param role: The user's role ('citizen' or 'publisher')
        @return: True if insertion succeeded, False if username already exists
        """
        conn = UserRepository.get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                        (username, hashed_password, role))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # This triggers if the username already exists (due to UNIQUE constraint in database)
            return False
        finally:
            conn.close()

# DOMAIN MODELS (ENCAPSULATION, INHERITANCE, POLYMORPHISM)
# Purpose: Define User classes with business logic and role-based behavior.
# These classes implement all OOP principles to create extensible, maintainable code.

class User(UserMixin, ABC):
    """
    Abstract base User class - represents a generic user in the system.
    
    Implements ENCAPSULATION:
        - Private attributes (_id, _username, _role) prevent direct modification
        - Public properties provide controlled read-only access to private data
        - Developers must use properties, not direct attribute access
    
    Implements ABSTRACTION:
        - Abstract methods (get_permissions, can_publish) define the interface
        - Subclasses must implement these methods with role-specific logic
    
    Inherits from:
        - UserMixin: Provides Flask-Login required methods (is_authenticated, is_active, etc.)
        - ABC (Abstract Base Class): Prevents direct instantiation of User class
    """
    
    def __init__(self, id, username, role):
        """
        Initialize a new User with basic information.
        
        @param id: Unique user identifier from database
        @param username: User's login name
        @param role: User's role in the system ('citizen' or 'publisher')
        """
        # Private attributes - use underscore prefix to indicate they're internal
        self._id = id
        self._username = username
        self._role = role
    
    # ENCAPSULATION: Properties provide controlled access to private attributes
    
    @property
    def id(self):
        """
        Read-only property for user ID.
        ENCAPSULATION: Prevents modification of user ID after creation.
        @return: The user's unique identifier
        """
        return self._id
    
    @property
    def username(self):
        """
        Read-only property for username.
        ENCAPSULATION: Prevents modification of username after creation.
        @return: The user's login name
        """
        return self._username
    
    @property
    def role(self):
        """
        Read-only property for user role.
        ENCAPSULATION: Prevents modification of role after creation.
        @return: The user's role ('citizen' or 'publisher')
        """
        return self._role
    
    # ABSTRACTION: Abstract methods define what subclasses must implement
    
    @abstractmethod
    def get_permissions(self):
        """
        POLYMORPHISM: Abstract method that returns role-specific permissions.
        Each subclass (CitizenUser, PublisherUser) implements this differently.
        This is POLYMORPHISM - same method name, different behavior based on user type.
        
        @return: List of permission strings that this user type has
        """
        pass
    
    @abstractmethod
    def can_publish(self):
        """
        POLYMORPHISM: Abstract method that checks if user can publish content.
        Each subclass (CitizenUser, PublisherUser) implements this differently.
        This is POLYMORPHISM - same method name, different behavior based on user type.
        
        @return: Boolean indicating if user can publish
        """
        pass


class CitizenUser(User):
    """
    Concrete implementation of User for citizen role.
    
    Demonstrates INHERITANCE:
        - Inherits all properties and behavior from User class
        - Reuses __init__ and property methods without rewriting them
        - Only needs to implement the abstract methods
    
    Demonstrates POLYMORPHISM:
        - Overrides get_permissions() with citizen-specific permissions
        - Overrides can_publish() to return False (citizens cannot publish)
        - Same method names, different behavior than PublisherUser
    """
    
    def get_permissions(self):
        """
        Citizens have limited permissions - they can view and file complaints.
        POLYMORPHISM: Same method name as PublisherUser, but returns different permissions.
        
        @return: List of permissions available to citizen users
        """
        return ['view_dashboard', 'view_complaints', 'file_complaint']
    
    def can_publish(self):
        """
        Citizens cannot publish updates to the system.
        POLYMORPHISM: Same method name as PublisherUser, but returns False.
        
        @return: False - citizens cannot publish
        """
        return False


class PublisherUser(User):
    """
    Concrete implementation of User for publisher role.
    
    Demonstrates INHERITANCE:
        - Inherits all properties and behavior from User class
        - Reuses __init__ and property methods without rewriting them
        - Only needs to implement the abstract methods
    
    Demonstrates POLYMORPHISM:
        - Overrides get_permissions() with publisher-specific permissions
        - Overrides can_publish() to return True (publishers can publish)
        - Same method names, different behavior than CitizenUser
    """
    
    def get_permissions(self):
        """
        Publishers have full permissions - they can view, file complaints, and publish updates.
        POLYMORPHISM: Same method name as CitizenUser, but returns different permissions.
        
        @return: List of permissions available to publisher users
        """
        return ['view_dashboard', 'view_complaints', 'file_complaint', 'publish_updates', 'view_analytics']
    
    def can_publish(self):
        """
        Publishers can publish updates to the system.
        POLYMORPHISM: Same method name as CitizenUser, but returns True.
        
        @return: True - publishers can publish
        """
        return True


def create_user_from_db(user_data):
    """
    Factory function: Creates the correct User subclass based on role.
    
    This function implements POLYMORPHISM through the Factory Pattern:
        - Input: Raw database row with user data
        - Output: Correct User subclass (CitizenUser or PublisherUser)
        - Callers don't need to know which subclass to instantiate
    
    Benefits:
        - Centralizes object creation logic
        - Easy to add new user types by adding an elif clause
        - Routes and services don't need to know about subclasses
    
    @param user_data: SQLite Row object containing user database record
    @return: CitizenUser or PublisherUser instance based on role in database
    """
    if user_data['role'] == 'publisher':
        return PublisherUser(user_data['id'], user_data['username'], user_data['role'])
    else:
        # Default to citizen for any other role
        return CitizenUser(user_data['id'], user_data['username'], user_data['role'])

# SERVICE LAYER (ABSTRACTION PRINCIPLE)
# Purpose: Service layer orchestrates business logic without being tied to Flask.
# Benefits: Easy to test, easy to reuse in different contexts (CLI, API, etc.)
# Keeps routes thin and focused on HTTP handling.

class AuthService:
    """
    Service class: Encapsulates all authentication and authorization logic.
    
    This class demonstrates ABSTRACTION:
        - Routes don't need to know HOW authentication works, just call the methods
        - Database details are hidden (delegated to UserRepository)
        - Password hashing details are hidden
        - Business rules are centralized and easy to modify
    
    Design pattern: Service Layer pattern
        - Separates business logic from HTTP/Flask concerns
        - Easy to test independently
        - Easy to reuse in different contexts
    """
    
    @staticmethod
    def register_user(username, password, role):
        """
        Register a new user with validation and error handling.
        ABSTRACTION: Routes don't care HOW registration works, just the result.
        
        Validation steps:
        1. Check that all fields are provided
        2. Check that username doesn't already exist
        3. Hash the password using bcrypt (never store plain passwords!)
        4. Insert into database
        
        @param username: Desired username (must be unique)
        @param password: Plain-text password (will be hashed)
        @param role: User's role ('citizen' or 'publisher')
        @return: Tuple of (success: bool, message: str)
                 - (True, "message") if registration succeeded
                 - (False, "error message") if registration failed
        """
        # Validation: Check for empty fields
        if not username or not password or not role:
            return False, "All fields are required"
        
        # Validation: Check if username already exists
        if UserRepository.find_by_username(username):
            return False, "Username already exists. Try another one."
        
        # Security: Hash the password using bcrypt (slow on purpose to resist brute-force attacks)
        hashed_password = generate_password_hash(password)
        
        # Attempt to create the user in database
        if UserRepository.create(username, hashed_password, role):
            return True, "Registration successful! Please log in."
        
        # If we get here, something went wrong in the database
        return False, "Registration failed"
    
    @staticmethod
    def authenticate_user(username, password):
        """
        Authenticate a user by username and password.
        ABSTRACTION: Routes don't care HOW authentication works.
        
        Steps:
        1. Look up user by username
        2. If user exists, verify password using bcrypt comparison
        3. If password matches, create and return User object
        4. If anything fails, return None
        
        @param username: Username to authenticate
        @param password: Plain-text password to verify (will be compared with hashed version)
        @return: Tuple of (success: bool, user: User or None)
                 - (True, User object) if authentication succeeded
                 - (False, None) if authentication failed
        """
        # Look up user in database
        user_data = UserRepository.find_by_username(username)
        
        # Check if user exists AND password is correct
        # check_password_hash safely compares plain password with bcrypt hash
        if user_data and check_password_hash(user_data['password_hash'], password):
            # Create the correct User subclass based on role
            user = create_user_from_db(user_data)
            return True, user
        
        # Either user doesn't exist or password is wrong (we don't say which for security)
        return False, None

# FLASK-LOGIN INTEGRATION
# Flask-Login requires a user_loader callback to reconstruct User objects from session.

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

# ROUTES / HTTP ENDPOINTS
# Routes are kept thin and focus on HTTP concerns (requests, responses, redirects).
# All business logic is delegated to the Service layer.

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registration page and form handler.
    
    GET: Display the registration form template
    POST: Process form submission and create new user account
    
    WORKFLOW:
    1. User submits registration form with username, password, role
    2. AuthService validates and creates user in database
    3. If successful, redirect to login page
    4. If unsuccessful, display error message and redisplay form
    """
    if request.method == 'POST':
        # Extract form data from user submission
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        
        # Delegate registration logic to AuthService (keeps route code simple)
        success, message = AuthService.register_user(username, password, role)
        
        if success:
            # Registration succeeded - show success message and redirect to login
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            # Registration failed - show error message and redisplay form
            flash(message, 'error')
    
    # Display the registration form template (GET request or after POST failure)
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page and form handler.
    
    GET: Display the login form template
    POST: Process form submission and authenticate user
    
    WORKFLOW:
    1. User submits login form with username and password
    2. AuthService authenticates user against database
    3. If successful, Flask-Login creates user session and redirects to dashboard
    4. If unsuccessful, display error message and redisplay form
    """
    if request.method == 'POST':
        # Extract form data from user submission
        username = request.form['username']
        password = request.form['password']
        
        # Delegate authentication logic to AuthService (keeps route code simple)
        success, user = AuthService.authenticate_user(username, password)
        
        if success:
            # Authentication succeeded - create session and redirect to dashboard
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            # Authentication failed - show error message and redisplay form
            flash('Invalid username or password.', 'error')
    
    # Display the login form template (GET request or after POST failure)
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """
    Protected dashboard page - only accessible to logged-in users.
    The @login_required decorator automatically redirects unauthenticated users to login page.
    
    This route demonstrates POLYMORPHISM in action:
    - current_user could be CitizenUser or PublisherUser
    - Both have get_permissions() and can_publish() methods
    - We call the same methods on both types, but get different results
    - No if-statements needed to check user type!
    
    WORKFLOW:
    1. User requests dashboard
    2. @login_required checks if user is logged in (redirects if not)
    3. We call polymorphic methods on current_user
    4. Different permissions returned based on actual user type
    5. Pass permissions to template for role-based UI rendering
    """
    # Call polymorphic methods - behavior depends on user type (CitizenUser or PublisherUser)
    # This is the power of POLYMORPHISM - same code, different behavior!
    permissions = current_user.get_permissions()
    can_publish = current_user.can_publish()
    
    # Pass user info and permissions to template for rendering
    # Template can use these to show/hide features based on role
    return render_template('dashboard.html', 
                          name=current_user.username,
                          role=current_user.role,
                          permissions=permissions,
                          can_publish=can_publish)

@app.route('/logout')
@login_required
def logout():
    """
    Logout handler - clears user session and redirects to login page.
    The @login_required decorator ensures only authenticated users can logout.
    
    WORKFLOW:
    1. User clicks logout link
    2. @login_required checks that user is logged in
    3. logout_user() clears the session
    4. Redirect to login page
    """
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def home():
    """
    Home page - redirects to login page.
    No homepage is defined, so we direct all traffic to login.
    """
    return redirect(url_for('login'))

# APPLICATION ENTRY POINT

if __name__ == '__main__':
    # Start the Flask development server
    # debug=True enables auto-reload on code changes and better error pages
    app.run(debug=True)