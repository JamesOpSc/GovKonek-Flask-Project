"""
GovKonek Domain Models Module

Defines the User classes demonstrating OOP principles:
- ENCAPSULATION: Private attributes with controlled property access
- INHERITANCE: CitizenUser and PublisherUser extend the base User class
- POLYMORPHISM: User subclasses override methods for role-based behavior
- ABSTRACTION: Abstract methods define the interface
"""

from flask_login import UserMixin
from abc import ABC, abstractmethod


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
