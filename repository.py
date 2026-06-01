"""
GovKonek Repository Module

Database Layer - ABSTRACTION PRINCIPLE
Purpose: The Repository pattern abstracts all database operations.
Benefits: Database code is isolated, easy to change database without touching business logic.
All database queries are centralized in one place for easier maintenance and testing.
"""

import sqlite3
from config import DATABASE_NAME


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
        conn = sqlite3.connect(DATABASE_NAME)
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
