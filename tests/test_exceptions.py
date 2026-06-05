"""
Unit tests for the GovKonek exceptions module.

Tests OOP principles:
  - INHERITANCE: All custom exceptions extend GovKonekError
  - EXCEPTION HANDLING: Meaningful error messages with context
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exceptions import (
    GovKonekError, DatabaseError, ConnectionError, RecordNotFoundError,
    DuplicateRecordError, AuthError, InvalidCredentialsError,
    RegistrationError, PermissionDeniedError, ValidationError,
    RequiredFieldError, InvalidValueError, InvalidEmojiError,
    ServiceError, PostError, ProjectError, VoiceError
)


class TestExceptionInheritance(unittest.TestCase):
    """
    INHERITANCE: All custom exceptions should be in the GovKonekError
    hierarchy, just like CitizenUser/PublisherUser extend User.
    """

    def test_database_error_is_govkonek_error(self):
        """DatabaseError IS-A GovKonekError."""
        self.assertIsInstance(DatabaseError(), GovKonekError)

    def test_connection_error_is_database_error(self):
        """ConnectionError IS-A DatabaseError IS-A GovKonekError."""
        self.assertIsInstance(ConnectionError(':memory:'), DatabaseError)
        self.assertIsInstance(ConnectionError(':memory:'), GovKonekError)

    def test_duplicate_record_error_is_database_error(self):
        """DuplicateRecordError IS-A DatabaseError."""
        self.assertIsInstance(
            DuplicateRecordError('User', 'username', 'juan'), DatabaseError
        )

    def test_auth_error_is_govkonek_error(self):
        """AuthError IS-A GovKonekError."""
        self.assertIsInstance(AuthError(), GovKonekError)

    def test_invalid_credentials_is_auth_error(self):
        """InvalidCredentialsError IS-A AuthError."""
        self.assertIsInstance(InvalidCredentialsError(), AuthError)

    def test_permission_denied_is_auth_error(self):
        """PermissionDeniedError IS-A AuthError."""
        self.assertIsInstance(
            PermissionDeniedError('publish', 'citizen'), AuthError
        )

    def test_validation_error_is_govkonek_error(self):
        """ValidationError IS-A GovKonekError."""
        self.assertIsInstance(ValidationError(), GovKonekError)

    def test_service_error_is_govkonek_error(self):
        """ServiceError IS-A GovKonekError."""
        self.assertIsInstance(ServiceError(), GovKonekError)


class TestExceptionMessages(unittest.TestCase):
    """Tests that exceptions produce meaningful messages."""

    def test_record_not_found_message(self):
        """RecordNotFoundError should include entity and identifier."""
        ex = RecordNotFoundError('User', 42)
        self.assertIn('User', str(ex))
        self.assertIn('42', str(ex))

    def test_duplicate_record_message(self):
        """DuplicateRecordError should include field and value."""
        ex = DuplicateRecordError('User', 'username', 'juan')
        self.assertIn('User', str(ex))
        self.assertIn('username', str(ex))
        self.assertIn('juan', str(ex))

    def test_permission_denied_message(self):
        """PermissionDeniedError should include action and role."""
        ex = PermissionDeniedError('delete posts', 'citizen')
        self.assertIn('delete posts', str(ex))
        self.assertIn('citizen', str(ex))

    def test_required_field_message(self):
        """RequiredFieldError should include the field name."""
        ex = RequiredFieldError('title')
        self.assertIn('title', str(ex))
        self.assertIn('required', str(ex).lower())

    def test_invalid_value_message(self):
        """InvalidValueError should include value and allowed values."""
        ex = InvalidValueError('status', 'deleted', ['open', 'closed'])
        self.assertIn('deleted', str(ex))
        self.assertIn('open', str(ex))
        self.assertIn('closed', str(ex))

    def test_invalid_emoji_message(self):
        """InvalidEmojiError should include the invalid emoji and allowed set."""
        ex = InvalidEmojiError('🔥', {'👍', '❤️'})
        self.assertIn('🔥', str(ex))

    def test_connection_error_includes_path(self):
        """ConnectionError should include the database path."""
        ex = ConnectionError('/path/to/db.sqlite')
        self.assertIn('/path/to/db.sqlite', str(ex))

    def test_connection_error_wraps_original(self):
        """ConnectionError should include the original error message."""
        original = ValueError("disk full")
        ex = ConnectionError(':memory:', original_error=original)
        self.assertIn('disk full', str(ex))


class TestExceptionCatching(unittest.TestCase):
    """
    Tests that exceptions can be caught at appropriate levels of the hierarchy.

    From the Exception Handling lecture:
      'Use specific exception types (not generic Exception).'
    """

    def test_catch_all_govkonek_errors(self):
        """All app exceptions can be caught with GovKonekError."""
        errors = [
            DatabaseError(),
            AuthError(),
            ValidationError(),
            ServiceError(),
        ]
        for err in errors:
            try:
                raise err
            except GovKonekError:
                pass  # Expected — all are GovKonekErrors

    def test_catch_specific_database_errors(self):
        """DatabaseError catches database-specific errors but not auth."""
        # DatabaseError should catch ConnectionError
        try:
            raise ConnectionError(':memory:')
        except DatabaseError:
            pass  # Expected

        # DatabaseError should NOT catch AuthError
        try:
            raise AuthError()
        except DatabaseError:
            self.fail("DatabaseError should not catch AuthError")
        except GovKonekError:
            pass  # Correct — AuthError is GovKonekError but not DatabaseError


if __name__ == '__main__':
    unittest.main(verbosity=2)
