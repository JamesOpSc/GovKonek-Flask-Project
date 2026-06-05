"""
Unit tests for BaseService, AuthService, PostService, and VoiceService.

Tests OOP principles:
  - INHERITANCE: All services extend BaseService
  - ENCAPSULATION: Repositories are private (_user_repo, _post_repo, _repo)
  - EXCEPTION HANDLING: Validation helpers raise domain-specific exceptions
  - POLYMORPHISM: _check_publisher delegates to user.can_publish()
"""

import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from service import (
    BaseService, AuthService, PostService, VoiceService
)
from repository import UserRepository, PostRepository, VoiceRepository
from models import CitizenUser, PublisherUser
from exceptions import (
    RequiredFieldError, InvalidValueError, PermissionDeniedError
)


# ===========================================================================
# BaseService Tests
# ===========================================================================

class TestBaseService(unittest.TestCase):
    """Tests for BaseService validation helpers."""

    def setUp(self):
        class TestSvc(BaseService):
            pass
        self.svc = TestSvc()

    # -- _require --------------------------------------------------------

    def test_require_valid_value_passes(self):
        """_require should not raise for a valid value."""
        self.svc._require('Hello', 'Title')

    def test_require_none_raises(self):
        """EXCEPTION HANDLING: _require(None) raises RequiredFieldError."""
        with self.assertRaises(RequiredFieldError):
            self.svc._require(None, 'Username')

    def test_require_empty_string_raises(self):
        """EXCEPTION HANDLING: _require('') raises RequiredFieldError."""
        with self.assertRaises(RequiredFieldError):
            self.svc._require('', 'Password')

    def test_require_whitespace_only_raises(self):
        """EXCEPTION HANDLING: _require('  ') raises RequiredFieldError."""
        with self.assertRaises(RequiredFieldError):
            self.svc._require('   ', 'Name')

    # -- _validate_choice ------------------------------------------------

    def test_validate_choice_valid(self):
        """_validate_choice should return the value if it's in allowed set."""
        result = self.svc._validate_choice('a', 'letter', ['a', 'b', 'c'])
        self.assertEqual(result, 'a')

    def test_validate_choice_invalid_defaults_to_first(self):
        """_validate_choice should default to first allowed value."""
        result = self.svc._validate_choice('z', 'letter', ['a', 'b'])
        self.assertEqual(result, 'a')

    # -- _check_publisher (POLYMORPHISM) ---------------------------------

    def test_check_publisher_allows_publisher(self):
        """
        POLYMORPHISM: _check_publisher uses user.can_publish().
        PublisherUser.can_publish() → True → no error.
        """
        publisher = PublisherUser(1, 'admin', 'publisher')
        self.svc._check_publisher(publisher)

    def test_check_publisher_denies_citizen(self):
        """
        POLYMORPHISM: CitizenUser.can_publish() → False → raises.
        Same method, different behavior based on object type.
        """
        citizen = CitizenUser(2, 'juan', 'citizen')
        with self.assertRaises(PermissionDeniedError):
            self.svc._check_publisher(citizen)

    # -- _sanitize -------------------------------------------------------

    def test_sanitize_strips_whitespace(self):
        """_sanitize should strip leading/trailing whitespace."""
        self.assertEqual(self.svc._sanitize('  hello  '), 'hello')

    def test_sanitize_none_returns_empty(self):
        """_sanitize should return empty string for None."""
        self.assertEqual(self.svc._sanitize(None), '')


# ===========================================================================
# AuthService Tests
# ===========================================================================

class TestAuthService(unittest.TestCase):
    """Tests for AuthService (INHERITANCE from BaseService)."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = UserRepository(db_path=self.db_path)
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        self.svc = AuthService(user_repo=self.repo)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_is_instance_of_base_service(self):
        """INHERITANCE: AuthService IS-A BaseService."""
        self.assertIsInstance(self.svc, BaseService)

    def test_register_user_success(self):
        """Register a new user should succeed."""
        success, msg = self.svc.register_user('juan', 'pass123', 'citizen')
        self.assertTrue(success)
        self.assertIn('successful', msg.lower())

    def test_register_empty_username_fails(self):
        """Register with empty username should fail with validation error."""
        success, msg = self.svc.register_user('', 'pass', 'citizen')
        self.assertFalse(success)
        self.assertIn('Username', msg)

    def test_register_duplicate_username_fails(self):
        """Register with existing username should fail."""
        self.svc.register_user('juan', 'pass1', 'citizen')
        success, msg = self.svc.register_user('juan', 'pass2', 'citizen')
        self.assertFalse(success)
        self.assertIn('already exists', msg.lower())

    def test_authenticate_valid_user(self):
        """Authenticate with correct credentials should succeed."""
        self.svc.register_user('maria', 'mysecret', 'citizen')
        success, user = self.svc.authenticate_user('maria', 'mysecret')
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user.username, 'maria')

    def test_authenticate_invalid_password(self):
        """Authenticate with wrong password should fail."""
        self.svc.register_user('maria', 'mysecret', 'citizen')
        success, user = self.svc.authenticate_user('maria', 'wrongpass')
        self.assertFalse(success)
        self.assertIsNone(user)

    def test_authenticate_nonexistent_user(self):
        """Authenticate nonexistent user should fail."""
        success, user = self.svc.authenticate_user('ghost', 'whatever')
        self.assertFalse(success)


# ===========================================================================
# PostService Tests
# ===========================================================================

class TestPostService(unittest.TestCase):
    """Tests for PostService (INHERITANCE from BaseService)."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        self.repo = PostRepository(db_path=self.db_path)
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL
            )
        ''')
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                publisher_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'published',
                category TEXT DEFAULT 'Announcement',
                image_path TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (publisher_id) REFERENCES users(id)
            )
        ''')
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.repo._execute_write('''
            CREATE TABLE IF NOT EXISTS reactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                emoji TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(post_id, user_id)
            )
        ''')
        user_repo = UserRepository(db_path=self.db_path)
        from werkzeug.security import generate_password_hash
        user_repo.create('captain', generate_password_hash('pw'), 'publisher')
        user_repo.create('juan', generate_password_hash('pw'), 'citizen')
        self.publisher = PublisherUser(1, 'captain', 'publisher')
        self.citizen = CitizenUser(2, 'juan', 'citizen')
        self.svc = PostService(post_repo=self.repo)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def test_is_instance_of_base_service(self):
        """INHERITANCE: PostService IS-A BaseService."""
        self.assertIsInstance(self.svc, BaseService)

    def test_create_post_as_publisher(self):
        """Publisher should be able to create a post."""
        post, error = self.svc.create_post(self.publisher, 'Title', 'Content')
        self.assertIsNone(error)
        self.assertIsNotNone(post)
        self.assertEqual(post['title'], 'Title')

    def test_create_post_as_citizen_fails(self):
        """Citizen should NOT be able to create a post (POLYMORPHISM)."""
        post, error = self.svc.create_post(self.citizen, 'Title', 'Content')
        self.assertIsNotNone(error)
        self.assertIsNone(post)

    def test_create_post_empty_title_fails(self):
        """Empty title should fail validation."""
        post, error = self.svc.create_post(self.publisher, '', 'Content')
        self.assertIsNotNone(error)

    def test_create_post_empty_content_fails(self):
        """Empty content should fail validation."""
        post, error = self.svc.create_post(self.publisher, 'Title', '')
        self.assertIsNotNone(error)

    def test_toggle_reaction_invalid_emoji(self):
        """Invalid emoji should return an error."""
        self.svc.create_post(self.publisher, 'T', 'C')
        result, error = self.svc.toggle_reaction(1, 2, '🔥')
        self.assertIsNotNone(error)
        self.assertIn('Invalid emoji', error)


if __name__ == '__main__':
    unittest.main(verbosity=2)
