"""
GovKonek File Upload Helper Module

OOP PRINCIPLES DEMONSTRATED:
    - ABSTRACTION: Hides file-system details (path creation, naming, saving)
      behind a simple interface — routes don't need to know about os.makedirs,
      timestamp generation, or extension validation.
    - ENCAPSULATION: The upload directory and allowed extensions are
      configurable via constructor injection.
    - EXCEPTION HANDLING: Validation errors are raised as domain-specific
      exceptions with clear messages.

From the crash course (event-driven_and_db_prog):
    Separates concerns — file upload logic belongs in a dedicated module,
    not scattered across route handlers.
"""

import os
from datetime import datetime


class FileUploadHelper:
    """
    Centralized file upload handler.

    Encapsulates all file-system operations so routes stay thin and focused
    on HTTP concerns.  Duplicated file-save logic across 3+ route handlers
    is now a single, testable class.

    Usage:
        helper = FileUploadHelper(upload_dir='static/uploads')
        url_path = helper.save(uploaded_file, prefix='post')
    """

    # Default allowed image extensions
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
    # Default allowed document extensions
    ALLOWED_DOC_EXTENSIONS = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'csv'}

    def __init__(self, upload_dir=None, allowed_extensions=None):
        """
        Initialize the upload helper.

        @param upload_dir: Absolute or relative path to the upload directory.
                           Defaults to 'static/uploads' relative to project root.
        @param allowed_extensions: Set of lowercase file extensions to allow.
                                   Defaults to ALLOWED_IMAGE_EXTENSIONS.
        """
        if upload_dir is None:
            # Default: static/uploads/ relative to this file's parent (project root)
            project_root = os.path.dirname(os.path.abspath(__file__))
            upload_dir = os.path.join(project_root, 'static', 'uploads')

        self._upload_dir = upload_dir
        self._allowed_extensions = allowed_extensions or self.ALLOWED_IMAGE_EXTENSIONS

    # -- public API -------------------------------------------------------

    def save(self, file, prefix='file', allowed_extensions=None):
        """
        Save an uploaded file with a unique name.

        ABSTRACTION: Callers don't need to know about os.makedirs,
        timestamp generation, extension validation, or path joining.

        @param file: Flask FileStorage object (has .filename and .save())
        @param prefix: Prefix for the generated filename (e.g., 'post', 'profile')
        @param allowed_extensions: Override the default allowed extensions
        @return: Relative URL path (e.g., '/static/uploads/post_20260101_abc.jpg')
        @raises ValueError: If file is empty or has an invalid extension
        """
        # Validate
        if not file or not file.filename:
            raise ValueError("No file was selected.")

        # Extract extension
        if '.' not in file.filename:
            raise ValueError("File must have an extension.")

        ext = file.filename.rsplit('.', 1)[-1].lower()
        allowed = allowed_extensions or self._allowed_extensions

        if ext not in allowed:
            raise ValueError(
                f"File type '.{ext}' is not allowed. "
                f"Allowed: {', '.join(sorted(allowed))}"
            )

        # Ensure directory exists
        os.makedirs(self._upload_dir, exist_ok=True)

        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{prefix}_{timestamp}.{ext}"
        filepath = os.path.join(self._upload_dir, safe_name)

        # Save
        file.save(filepath)

        # Return relative URL path
        return f'/static/uploads/{safe_name}'

    def delete(self, url_path):
        """
        Delete a file from disk by its URL path.

        ABSTRACTION: Uses self._upload_dir rather than hardcoding the
        project root, so it works correctly with injected temp directories
        in tests.

        @param url_path: Relative URL path (e.g., '/static/uploads/file.pdf')
        @return: True if deleted, False if file didn't exist
        """
        if not url_path or url_path == '#':
            return False

        # Extract just the filename from the URL path
        filename = os.path.basename(url_path)
        file_path = os.path.join(self._upload_dir, filename)

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except OSError:
            pass
        return False

    # -- properties -------------------------------------------------------

    @property
    def upload_dir(self):
        """Read-only access to the upload directory path."""
        return self._upload_dir


# Module-level singleton for convenience
_default_helper = FileUploadHelper()


def get_upload_helper():
    """Return the default FileUploadHelper instance."""
    return _default_helper
