"""
GovKonek Service Module

Service Layer - ABSTRACTION PRINCIPLE
Purpose: Service layer orchestrates business logic without being tied to Flask.
Benefits: Easy to test, easy to reuse in different contexts (CLI, API, etc.)
Keeps routes thin and focused on HTTP handling.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from repository import UserRepository
from models import create_user_from_db


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
