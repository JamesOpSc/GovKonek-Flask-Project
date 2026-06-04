"""
GovKonek Custom Exceptions Module

Demonstrates OOP EXCEPTION HANDLING principle from the lecture:
"Exception handling is essential for creating robust, user-friendly applications."

Custom exceptions provide:
- Meaningful, domain-specific error messages
- Clean separation between business-logic errors and system errors
- Easier debugging and error tracking
- Consistent error handling across all layers

Design follows the Exception Handling lecture's best practices:
1. Use specific exception types (not generic Exception)
2. Provide meaningful error messages
3. Allow the program to recover gracefully
"""


class GovKonekError(Exception):
    """
    Base exception for all GovKonek application errors.

    INHERITANCE: All custom exceptions extend this base class,
    following the same principle as User → CitizenUser / PublisherUser.
    This allows catching all GovKonek errors with a single `except GovKonekError`.
    """
    def __init__(self, message="An error occurred in the GovKonek application"):
        self.message = message
        super().__init__(self.message)


# ===========================================================================
# Database Layer Exceptions
# ===========================================================================

class DatabaseError(GovKonekError):
    """
    Raised when a database operation fails.

    ABSTRACTION: Hides low-level SQLite errors behind a domain-specific
    exception that makes sense in the application context.
    """
    def __init__(self, message="A database error occurred", original_error=None):
        self.original_error = original_error
        detail = f"{message}"
        if original_error:
            detail += f" | Cause: {str(original_error)}"
        super().__init__(detail)


class ConnectionError(DatabaseError):
    """Raised when the database connection cannot be established."""
    def __init__(self, db_path, original_error=None):
        self.db_path = db_path
        super().__init__(
            f"Failed to connect to database at '{db_path}'",
            original_error
        )


class RecordNotFoundError(DatabaseError):
    """Raised when a requested database record does not exist."""
    def __init__(self, entity, identifier):
        self.entity = entity
        self.identifier = identifier
        super().__init__(f"{entity} with identifier '{identifier}' was not found")


class DuplicateRecordError(DatabaseError):
    """Raised when attempting to insert a record that violates a UNIQUE constraint."""
    def __init__(self, entity, field, value):
        self.entity = entity
        self.field = field
        self.value = value
        super().__init__(f"{entity} with {field}='{value}' already exists")


# ===========================================================================
# Authentication & Authorization Exceptions
# ===========================================================================

class AuthError(GovKonekError):
    """Base exception for authentication and authorization errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when login credentials are invalid."""
    def __init__(self, message="Invalid username or password"):
        super().__init__(message)


class RegistrationError(AuthError):
    """Raised when user registration fails."""
    pass


class PermissionDeniedError(AuthError):
    """
    Raised when a user attempts an action they are not authorized for.

    ENCAPSULATION: This exception encapsulates the authorization check failure,
    preventing unauthorized action details from leaking.
    """
    def __init__(self, action, role):
        self.action = action
        self.role = role
        super().__init__(f"User with role '{role}' is not authorized to {action}")


# ===========================================================================
# Validation Exceptions
# ===========================================================================

class ValidationError(GovKonekError):
    """
    Base exception for input validation errors.

    From the Exception Handling lecture: "Validation: Enforces preconditions
    and business logic constraints."
    """
    pass


class RequiredFieldError(ValidationError):
    """Raised when a required field is missing or empty."""
    def __init__(self, field_name):
        self.field_name = field_name
        super().__init__(f"'{field_name}' is required and cannot be empty")


class InvalidValueError(ValidationError):
    """Raised when a field value is not in the allowed set."""
    def __init__(self, field_name, value, allowed_values):
        self.field_name = field_name
        self.value = value
        self.allowed_values = allowed_values
        allowed = ', '.join(str(v) for v in allowed_values)
        super().__init__(
            f"'{value}' is not a valid {field_name}. Allowed values: {allowed}"
        )


class InvalidEmojiError(ValidationError):
    """Raised when an unsupported emoji is used for a reaction."""
    def __init__(self, emoji, allowed):
        self.emoji = emoji
        super().__init__(f"Emoji '{emoji}' is not allowed. Use: {', '.join(sorted(allowed))}")


# ===========================================================================
# Service Layer Exceptions
# ===========================================================================

class ServiceError(GovKonekError):
    """Base exception for service-layer business logic errors."""
    pass


class PostError(ServiceError):
    """Raised when a post operation fails."""
    pass


class ProjectError(ServiceError):
    """Raised when a project operation fails."""
    pass


class VoiceError(ServiceError):
    """Raised when a Citizens' Voice operation fails."""
    pass
