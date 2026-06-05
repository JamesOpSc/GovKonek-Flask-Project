"""
GovKonek Service Module

Service Layer - ABSTRACTION PRINCIPLE
Purpose: Service layer orchestrates business logic without being tied to Flask.
Benefits: Easy to test, easy to reuse in different contexts (CLI, API, etc.)
Keeps routes thin and focused on HTTP handling.

REFACTORED for testability:
    - Services accept repository instances via constructor (dependency injection).
    - In tests, inject mock repositories to isolate business logic from the database.
    - Static methods kept as backward-compatible wrappers around a default instance.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from repository import UserRepository, PostRepository
from models import create_user_from_db


# ===========================================================================
# AuthService
# ===========================================================================

class AuthService:
    """
    Authentication and authorization business logic.

    REFACTORED: Now instance-based. Pass a UserRepository to the constructor.
    For testing, inject a mock or an in-memory repository.
    """

    def __init__(self, user_repo=None):
        """
        @param user_repo: UserRepository instance.
                          Defaults to a new UserRepository() if not provided.
        """
        self._user_repo = user_repo or UserRepository()

    # -- public API -------------------------------------------------------

    def register_user(self, username, password, role):
        """Register a new user. Returns (success: bool, message: str)."""
        if not username or not password or not role:
            return False, "All fields are required"

        if self._user_repo.find_by_username(username):
            return False, "Username already exists. Try another one."

        hashed_password = generate_password_hash(password)
        if self._user_repo.create(username, hashed_password, role):
            return True, "Registration successful! Please log in."
        return False, "Registration failed"

    def authenticate_user(self, username, password):
        """Authenticate a user. Returns (success: bool, user: User or None)."""
        user_data = self._user_repo.find_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = create_user_from_db(user_data)
            return True, user
        return False, None

    # AuthService: no static wrappers needed — routes use injected instances.
    # If external code needs a default instance, create one:
    #     from repository import UserRepository
    #     auth = AuthService(UserRepository())


# ===========================================================================
# PostService
# ===========================================================================

class PostService:
    """
    Post, comment, and reaction business logic.

    REFACTORED: Now instance-based. Pass a PostRepository to the constructor.
    For testing, inject a mock repository.
    """

    ALLOWED_EMOJI = {'👍', '❤️', '😄', '😢', '😡', '🎉'}

    def __init__(self, post_repo=None):
        """
        @param post_repo: PostRepository instance.
                          Defaults to a new PostRepository() if not provided.
        """
        self._post_repo = post_repo or PostRepository()

    # -- feed / detail ----------------------------------------------------

    def get_feed(self, search=None, category=None, sort=None):
        """Get published posts with optional search, category filter, and sorting."""
        posts = self._post_repo.get_all_posts(search=search, category=category, sort=sort)
        return [dict(p) for p in posts]

    def get_post_detail(self, post_id, user_id=None):
        """Get a single post with comments, reaction counts, and user's reaction."""
        post = self._post_repo.get_post_by_id(post_id)
        if not post:
            return None

        return {
            'post': dict(post),
            'comments': [dict(c) for c in self._post_repo.get_comments_for_post(post_id)],
            'reaction_counts': [dict(r) for r in self._post_repo.get_reactions_for_post(post_id)],
            'user_reaction': self._post_repo.get_user_reaction(post_id, user_id) if user_id else None,
        }

    # -- comments ---------------------------------------------------------

    def add_comment(self, post_id, user_id, content):
        """Add a comment. Returns (comment_dict, error)."""
        if not content or not content.strip():
            return None, "Comment cannot be empty."
        comment = self._post_repo.add_comment(post_id, user_id, content.strip())
        return dict(comment), None

    # -- reactions --------------------------------------------------------

    def toggle_reaction(self, post_id, user_id, emoji):
        """Toggle a reaction. Returns (result_dict, error)."""
        if emoji not in self.ALLOWED_EMOJI:
            return None, "Invalid emoji."

        action, _ = self._post_repo.toggle_reaction(post_id, user_id, emoji)
        reaction_counts = [dict(r) for r in self._post_repo.get_reactions_for_post(post_id)]
        user_reaction = self._post_repo.get_user_reaction(post_id, user_id)

        return {
            'action': action,
            'reaction_counts': reaction_counts,
            'user_reaction': user_reaction,
        }, None

    # -- publisher-only post management -----------------------------------

    def create_post(self, user, title, content, category='Announcement', image_path=''):
        """
        Create a new post. ONLY publisher (barangay captain) can publish.
        Supports optional image attachment.

        Returns (post_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can publish announcements."
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."

        # Validate category
        valid_categories = ['Announcement', 'Emergency', 'Health', 'Project']
        if category not in valid_categories:
            category = 'Announcement'

        post = self._post_repo.create_post(
            user.id, title.strip(), content.strip(), category,
            image_path=image_path
        )
        return (post, None) if post else (None, "Failed to create post.")

    def update_post(self, user, post_id, title, content):
        """
        Update a post. ONLY the publisher who created it can edit.
        Returns (post_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can edit announcements."
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."

        post = self._post_repo.update_post(post_id, user.id, title.strip(), content.strip())
        return (post, None) if post else (None, "Post not found or you are not authorized to edit it.")

    def delete_post(self, user, post_id):
        """
        Delete a post. ONLY the publisher who created it can delete.
        Returns (success: bool, error).
        """
        if not user.can_publish():
            return False, "Only the Barangay Captain can delete announcements."
        self._post_repo.delete_post(post_id, user.id)
        return True, None

    # PostService: no static wrappers needed — routes use injected instances.


# ===========================================================================
# VoiceService — Citizens' Voice forum business logic
# ===========================================================================

class VoiceService:
    """
    Business logic for the Citizens' Voice forum.

    Any authenticated user can post topics, comment, and vote.
    Publisher (barangay captain) comments are flagged as official responses.
    """

    CATEGORIES = ['General', 'Grievance', 'Suggestion', 'Question', 'Announcement']
    VALID_STATUSES = {'open', 'resolved', 'closed'}

    def __init__(self, voice_repo=None):
        """
        @param voice_repo: VoiceRepository instance.
        """
        from repository import VoiceRepository
        self._repo = voice_repo or VoiceRepository()

    # -- voice posts -----------------------------------------------------

    def get_posts(self, category=None, status=None, search=None, sort=None):
        """Get all voice posts, optionally filtered by category, status, title/author search, and sorted."""
        return self._repo.get_all(category=category, status=status,
                                  search=search, sort=sort)

    def get_post_detail(self, voice_post_id, user_id=None):
        """Get a voice post with comments and user's vote."""
        post = self._repo.get_by_id(voice_post_id)
        if not post:
            return None
        return {
            'post': post,
            'comments': self._repo.get_comments(voice_post_id),
            'user_vote': self._repo.get_user_vote(voice_post_id, user_id) if user_id else None,
        }

    def create_post(self, user_id, title, content, category='General'):
        """Create a new voice post. Returns (post_dict, error)."""
        if not title or not title.strip():
            return None, "Title is required."
        if not content or not content.strip():
            return None, "Content is required."
        if category not in self.CATEGORIES:
            category = 'General'
        post = self._repo.create(user_id, title.strip(), content.strip(), category)
        return (post, None) if post else (None, "Failed to create post.")

    def update_status(self, voice_post_id, status):
        """Update a voice post's status. Returns (success, error)."""
        if status not in self.VALID_STATUSES:
            return False, f"Invalid status. Must be one of: {', '.join(self.VALID_STATUSES)}"
        self._repo.update_status(voice_post_id, status)
        return True, None

    def delete_post(self, voice_post_id, user_id):
        """Delete a voice post. Only the original author can delete. Returns (success, error)."""
        self._repo.delete(voice_post_id, user_id)
        return True, None

    # -- comments --------------------------------------------------------

    def add_comment(self, voice_post_id, user_id, content, role):
        """Add a comment. Publisher comments are marked official. Returns (comment_dict, error)."""
        if not content or not content.strip():
            return None, "Comment cannot be empty."
        is_official = (role == 'publisher')
        comment = self._repo.add_comment(voice_post_id, user_id, content.strip(), is_official)
        return (comment, None) if comment else (None, "Failed to add comment.")

    # -- votes -----------------------------------------------------------

    def toggle_vote(self, voice_post_id, user_id, vote_type):
        """Toggle up/down vote. Returns (result_dict, error)."""
        if vote_type not in ('up', 'down'):
            return None, "Vote must be 'up' or 'down'."
        action, delta = self._repo.toggle_vote(voice_post_id, user_id, vote_type)
        user_vote = self._repo.get_user_vote(voice_post_id, user_id)
        return {
            'action': action,
            'net_change': delta,
            'user_vote': user_vote,
        }, None

    def get_categories(self):
        """Return the list of valid categories."""
        return self.CATEGORIES


# ===========================================================================
# ProjectService — Barangay Projects business logic
# ===========================================================================

class ProjectService:
    """
    Business logic for Barangay Projects.

    Only publisher (barangay captain) can create, update, or delete projects.
    All users can view projects.
    """

    VALID_STATUSES = ['ongoing', 'completed', 'planned']

    def __init__(self, project_repo=None):
        """
        @param project_repo: ProjectRepository instance.
        """
        from repository import ProjectRepository
        self._repo = project_repo or ProjectRepository()

    # -- read ------------------------------------------------------------

    def get_all(self):
        """Get all projects, newest first."""
        return self._repo.get_all()

    def get_by_id(self, project_id):
        """Get a single project by ID."""
        return self._repo.get_by_id(project_id)

    # -- publisher-only mutations ----------------------------------------

    def create_project(self, user, title, description, status='ongoing',
                       budget=0, location='', image_url='',
                       start_date='', end_date=''):
        """
        Create a new project. ONLY publisher (barangay captain) can create.
        Returns (project_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can create projects."
        if not title or not title.strip():
            return None, "Title is required."
        if not description or not description.strip():
            return None, "Description is required."
        if status not in self.VALID_STATUSES:
            status = 'ongoing'

        project = self._repo.create(
            title=title.strip(),
            description=description.strip(),
            status=status,
            budget=budget,
            location=location.strip(),
            image_url=image_url.strip(),
            start_date=start_date,
            end_date=end_date,
            publisher_id=user.id
        )
        return (project, None) if project else (None, "Failed to create project.")

    def update_project(self, user, project_id, title, description, status,
                       budget, location, image_url, start_date, end_date):
        """
        Update a project. ONLY the publisher who created it can edit.
        Returns (project_dict, error).
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can edit projects."
        if not title or not title.strip():
            return None, "Title is required."
        if not description or not description.strip():
            return None, "Description is required."
        if status not in self.VALID_STATUSES:
            status = 'ongoing'

        project = self._repo.update(
            project_id=project_id,
            publisher_id=user.id,
            title=title.strip(),
            description=description.strip(),
            status=status,
            budget=budget,
            location=location.strip(),
            image_url=image_url.strip(),
            start_date=start_date,
            end_date=end_date
        )
        return (project, None) if project else (None, "Project not found or you are not authorized to edit it.")

    def delete_project(self, user, project_id):
        """
        Delete a project. ONLY the publisher who created it can delete.
        Returns (success: bool, error).
        """
        if not user.can_publish():
            return False, "Only the Barangay Captain can delete projects."
        self._repo.delete(project_id, user.id)
        return True, None


# ===========================================================================
# DocumentService — Transparency Documents business logic
# ===========================================================================

class DocumentService:
    """
    Business logic for Transparency Documents.

    Only publisher (barangay captain) can upload, update, or delete documents.
    All users can view and download documents.

    File Handling (from the crash course):
      - Validates file extensions against config.allowed_extensions
      - Saves files to config.upload_folder with unique names
      - Returns the file path for storage in the database
    """

    VALID_CATEGORIES = [
        'Budget Report', 'Audit Report', 'Ordinance', 'Resolution',
        'Procurement', 'Disaster Preparedness', 'General'
    ]

    def __init__(self, document_repo=None, config=None):
        """
        @param document_repo: DocumentRepository instance
        @param config: Config instance (for upload_folder and allowed_extensions)
        """
        from repository import DocumentRepository
        self._repo = document_repo or DocumentRepository()
        self._config = config

    # -- read (all users) ------------------------------------------------

    def get_all(self):
        """Get all documents, newest first."""
        return self._repo.get_all()

    def get_by_category(self, category):
        """Get documents filtered by category."""
        return self._repo.get_by_category(category)

    def get_categories(self):
        """Get distinct document categories."""
        return self._repo.get_categories()

    def get_by_id(self, document_id):
        """Get a single document by ID."""
        return self._repo.get_by_id(document_id)

    # -- file validation -------------------------------------------------

    def _validate_file(self, file):
        """
        Validate an uploaded file.

        EXCEPTION HANDLING (from lecture):
          - Checks if a file was actually provided
          - Validates the file extension against the allowed set
          - Returns a user-friendly error message

        @param file: Flask FileStorage object from request.files
        @return: (filename, error) — error is None if valid
        """
        if not file or file.filename == '':
            return None, "No file was selected."

        filename = file.filename
        if '.' not in filename:
            return None, "File must have an extension."

        ext = filename.rsplit('.', 1)[1].lower()
        allowed = self._config.allowed_extensions if self._config else {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'txt', 'csv'}

        if ext not in allowed:
            return None, f"File type '.{ext}' is not allowed. Allowed: {', '.join(sorted(allowed))}"

        return filename, None

    def _save_file(self, file, filename):
        """
        Save an uploaded file with a unique name to prevent overwrites.

        Uses a timestamp prefix to avoid filename collisions.

        @param file: Flask FileStorage object
        @param filename: Original filename
        @return: Relative URL path to the saved file (e.g., '/static/uploads/20260604_abc_report.pdf')
        """
        import os
        from datetime import datetime

        upload_folder = self._config.upload_folder if self._config else 'static/uploads'

        # Ensure upload directory exists
        os.makedirs(upload_folder, exist_ok=True)

        # Generate unique filename: timestamp_originalname
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{timestamp}_{filename}"

        filepath = os.path.join(upload_folder, safe_name)
        file.save(filepath)

        # Return the relative URL for storage in the database
        return f'/static/uploads/{safe_name}'

    # -- publisher-only mutations ----------------------------------------

    def create_document(self, user, title, description, category, file, published_date=''):
        """
        Upload a new transparency document. ONLY publisher can upload.

        POLYMORPHISM: Uses user.can_publish() — same method name as
        PostService.create_post() and ProjectService.create_project().

        @param user: Current user (must be publisher)
        @param title: Document title
        @param description: Document description
        @param category: Document category
        @param file: Flask FileStorage object (the uploaded file)
        @param published_date: Publication date string (YYYY-MM-DD)
        @return: (document_dict, error)
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can upload documents."

        if not title or not title.strip():
            return None, "Title is required."

        if category not in self.VALID_CATEGORIES:
            category = 'General'

        # Validate and save file
        filename, error = self._validate_file(file)
        if error:
            return None, error

        # Get file size
        import os
        file.seek(0, os.SEEK_END)
        file_size_bytes = file.tell()
        file.seek(0)  # Reset for saving

        # Format file size for display
        if file_size_bytes < 1024:
            file_size = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            file_size = f"{file_size_bytes / 1024:.1f} KB"
        else:
            file_size = f"{file_size_bytes / (1024 * 1024):.1f} MB"

        # Save file to disk
        file_url = self._save_file(file, filename)

        # Use today's date if none provided
        if not published_date:
            from datetime import date
            published_date = date.today().isoformat()

        # Create database record
        doc = self._repo.create(
            title=title.strip(),
            description=description.strip(),
            category=category,
            file_url=file_url,
            file_size=file_size,
            published_date=published_date,
            publisher_id=user.id
        )
        return (doc, None) if doc else (None, "Failed to save document.")

    def delete_document(self, user, document_id):
        """
        Delete a transparency document. ONLY publisher can delete.

        Also removes the file from disk to free up storage.

        @param user: Current user (must be publisher)
        @param document_id: ID of the document to delete
        @return: (success: bool, error)
        """
        import os

        if not user.can_publish():
            return False, "Only the Barangay Captain can delete documents."

        # Get the document to find its file path
        doc = self._repo.get_by_id(document_id)
        if not doc:
            return False, "Document not found."

        # Delete the file from disk
        file_url = doc.get('file_url', '')
        if file_url and file_url != '#':
            # Convert relative URL (e.g., /static/uploads/report.pdf)
            # to absolute filesystem path
            # __file__ is service.py → dirname is the project root
            project_root = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(project_root, file_url.lstrip('/'))
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                pass  # File already gone or permission issue — not critical

        # Delete from database
        self._repo.delete(document_id, user.id)
        return True, None
