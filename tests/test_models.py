"""
Unit tests for the GovKonek models module.

Follows the crash course unit_testing_in_python pattern:
  - unittest.TestCase with setUp/tearDown
  - Test one thing per test
  - Meaningful test method names

Tests the OOP pillars:
  - ENCAPSULATION: Private attributes are not directly writable
  - INHERITANCE: CitizenUser and PublisherUser are instances of User
  - POLYMORPHISM: get_permissions() and can_publish() differ by subclass
  - ABSTRACTION: User cannot be directly instantiated
"""

import unittest
import sys
import os

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import User, CitizenUser, PublisherUser, create_user_from_db


class TestUserAbstract(unittest.TestCase):
    """Tests for the abstract User base class (ABSTRACTION)."""

    def test_cannot_instantiate_abstract_user(self):
        """
        ABSTRACTION: User is an ABC - direct instantiation should raise TypeError.
        From the lecture: 'You cannot instantiate abstract classes directly.'
        """
        with self.assertRaises(TypeError):
            User(id=1, username='test', role='citizen')


class TestCitizenUser(unittest.TestCase):
    """
    Tests for CitizenUser (INHERITANCE + POLYMORPHISM).

    From the lecture: 'A method can process objects differently depending on
    the class type.'
    """

    def setUp(self):
        """Create a fresh CitizenUser before each test."""
        self.user = CitizenUser(id=1, username='juan', role='citizen')

    def tearDown(self):
        """Clean up after each test."""
        del self.user

    # -- INHERITANCE ------------------------------------------------------

    def test_is_instance_of_user(self):
        """
        INHERITANCE: CitizenUser IS-A User.
        From the lecture: 'Inherits all properties and behavior from User class.'
        """
        self.assertIsInstance(self.user, User)

    def test_is_instance_of_citizen_user(self):
        """Verify the concrete type is CitizenUser."""
        self.assertIsInstance(self.user, CitizenUser)

    def test_is_not_publisher(self):
        """CitizenUser should NOT be a PublisherUser."""
        self.assertNotIsInstance(self.user, PublisherUser)

    # -- ENCAPSULATION ---------------------------------------------------

    def test_id_is_read_only(self):
        """
        ENCAPSULATION: The id property is read-only.
        Attempting to set it should raise AttributeError.
        """
        self.assertEqual(self.user.id, 1)
        with self.assertRaises(AttributeError):
            self.user.id = 999

    def test_username_is_read_only(self):
        """ENCAPSULATION: username cannot be modified after creation."""
        self.assertEqual(self.user.username, 'juan')
        with self.assertRaises(AttributeError):
            self.user.username = 'hacker'

    def test_role_is_read_only(self):
        """ENCAPSULATION: role cannot be modified after creation."""
        self.assertEqual(self.user.role, 'citizen')
        with self.assertRaises(AttributeError):
            self.user.role = 'publisher'

    # -- POLYMORPHISM ----------------------------------------------------

    def test_get_permissions_citizen(self):
        """
        POLYMORPHISM: CitizenUser returns citizen-specific permissions.
        Same method name as PublisherUser, different behavior.
        """
        permissions = self.user.get_permissions()
        self.assertIn('view_dashboard', permissions)
        self.assertIn('file_complaint', permissions)
        self.assertNotIn('publish_updates', permissions)

    def test_cannot_publish(self):
        """
        POLYMORPHISM: CitizenUser.can_publish() returns False.
        Publisher's version returns True - same method, different behavior.
        """
        self.assertFalse(self.user.can_publish())

    # -- Flask-Login compatibility ----------------------------------------

    def test_is_authenticated(self):
        """UserMixin provides is_authenticated. Should be True by default."""
        self.assertTrue(self.user.is_authenticated)

    def test_is_active(self):
        """UserMixin provides is_active. Should be True by default."""
        self.assertTrue(self.user.is_active)

    def test_get_id(self):
        """Flask-Login's get_id() should return the user ID as a string."""
        self.assertEqual(self.user.get_id(), '1')


class TestPublisherUser(unittest.TestCase):
    """
    Tests for PublisherUser (INHERITANCE + POLYMORPHISM).

    Demonstrates how a subclass overrides inherited methods differently.
    """

    def setUp(self):
        self.user = PublisherUser(id=2, username='captain', role='publisher')

    def tearDown(self):
        del self.user

    # -- INHERITANCE ------------------------------------------------------

    def test_is_instance_of_user(self):
        """INHERITANCE: PublisherUser IS-A User."""
        self.assertIsInstance(self.user, User)

    def test_is_not_citizen(self):
        """PublisherUser should NOT be a CitizenUser."""
        self.assertNotIsInstance(self.user, CitizenUser)

    # -- ENCAPSULATION ---------------------------------------------------

    def test_id_is_read_only(self):
        """ENCAPSULATION: id cannot be modified after creation."""
        self.assertEqual(self.user.id, 2)
        with self.assertRaises(AttributeError):
            self.user.id = 999

    def test_username_is_read_only(self):
        """ENCAPSULATION: username cannot be modified after creation."""
        self.assertEqual(self.user.username, 'captain')
        with self.assertRaises(AttributeError):
            self.user.username = 'hacker'

    def test_role_is_read_only(self):
        """ENCAPSULATION: role cannot be modified after creation."""
        self.assertEqual(self.user.role, 'publisher')
        with self.assertRaises(AttributeError):
            self.user.role = 'citizen'

    # -- POLYMORPHISM ----------------------------------------------------

    def test_get_permissions_publisher(self):
        """
        POLYMORPHISM: PublisherUser returns publisher-specific permissions.
        Has MORE permissions than CitizenUser.
        """
        permissions = self.user.get_permissions()
        self.assertIn('view_dashboard', permissions)
        self.assertIn('file_complaint', permissions)
        self.assertIn('publish_updates', permissions)
        self.assertIn('view_analytics', permissions)

    def test_can_publish(self):
        """
        POLYMORPHISM: PublisherUser.can_publish() returns True.
        Opposite of CitizenUser - same method, different behavior.
        """
        self.assertTrue(self.user.can_publish())


class TestPolymorphism(unittest.TestCase):
    """
    Tests that demonstrate POLYMORPHISM in action.

    From the lecture: 'Polymorphism allows us to perform the same action
    in many different ways.'
    """

    def setUp(self):
        self.citizen = CitizenUser(1, 'juan', 'citizen')
        self.publisher = PublisherUser(2, 'captain', 'publisher')

    def tearDown(self):
        del self.citizen
        del self.publisher

    def test_same_method_different_results(self):
        """
        POLYMORPHISM: Both objects have can_publish() but return
        different values based on their class.
        """
        users = [self.citizen, self.publisher]
        results = [u.can_publish() for u in users]
        self.assertEqual(results, [False, True])

    def test_polymorphic_permission_check(self):
        """
        POLYMORPHISM: Same get_permissions() call returns different
        lists depending on the actual object type.
        """
        self.assertTrue(len(self.publisher.get_permissions()) >
                        len(self.citizen.get_permissions()))


class TestFactoryFunction(unittest.TestCase):
    """
    Tests for create_user_from_db factory function.

    Demonstrates the Factory Pattern for POLYMORPHISM:
      - Input: database row dict
      - Output: correct User subclass
    """

    def test_creates_citizen_for_citizen_role(self):
        """Factory creates CitizenUser when role is 'citizen'."""
        row = {'id': 1, 'username': 'juan', 'role': 'citizen'}
        user = create_user_from_db(row)
        self.assertIsInstance(user, CitizenUser)

    def test_creates_publisher_for_publisher_role(self):
        """Factory creates PublisherUser when role is 'publisher'."""
        row = {'id': 2, 'username': 'captain', 'role': 'publisher'}
        user = create_user_from_db(row)
        self.assertIsInstance(user, PublisherUser)

    def test_defaults_to_citizen_for_unknown_role(self):
        """Factory defaults to CitizenUser for unrecognized roles."""
        row = {'id': 3, 'username': 'unknown', 'role': 'moderator'}
        user = create_user_from_db(row)
        self.assertIsInstance(user, CitizenUser)


if __name__ == '__main__':
    unittest.main(verbosity=2)
