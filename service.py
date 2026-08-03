"""
GovKonek Service Module

Service Layer - ABSTRACTION PRINCIPLE
Purpose: Service layer orchestrates business logic without being tied to Flask.
Benefits: Easy to test, easy to reuse in different contexts (CLI, API, etc.)
Keeps routes thin and focused on HTTP handling.

OOP PRINCIPLES DEMONSTRATED:
    - INHERITANCE: All services extend BaseService (like Vehicle → Car/Truck)
    - ABSTRACTION: BaseService provides shared validation helpers
    - ENCAPSULATION: Repositories are private (_repo), injected via constructor
    - EXCEPTION HANDLING: ValidationError raised for invalid inputs

REFACTORED for testability:
    - Services accept repository instances via constructor (dependency injection).
    - In tests, inject mock repositories to isolate business logic from the database.
"""

from abc import ABC
from werkzeug.security import generate_password_hash, check_password_hash
from repository import (
    UserRepository, PostRepository, ProjectRepository,
    DocumentRepository, VoiceRepository, BarangayRepository
)
from models import create_user_from_db
from exceptions import (
    RequiredFieldError,
    PermissionDeniedError
)


# ===========================================================================
# BaseService — Abstract Base for All Services
# ===========================================================================

class BaseService(ABC):
    """
    Abstract base class for all service classes.

    INHERITANCE (from lecture): Just like Vehicle is the base for Car/Truck,
    BaseService is the base for AuthService, PostService, ProjectService, etc.

    Provides common validation helpers so subclasses don't duplicate:
      - Required field checks
      - Allowed-value validation
      - Publisher-only authorization checks

    Benefits:
      - DRY: Validation logic defined ONCE
      - CONSISTENT: All services use the same validation patterns
      - TESTABLE: Each helper is isolated and easy to unit-test
      - EXTENSIBLE: New service types just extend BaseService
    """

    # ------------------------------------------------------------------
    # Validation Helpers (shared by all subclasses)
    # ------------------------------------------------------------------

    @staticmethod
    def _require(value, field_name):
        """
        Validate that a required field is non-empty.

        EXCEPTION HANDLING: Raises RequiredFieldError with a clear message
        instead of letting the caller check manually.

        @param value: The value to check (str or None)
        @param field_name: Human-readable field name for the error message
        @raises RequiredFieldError: if value is None or empty after stripping
        """
        if not value or not str(value).strip():
            raise RequiredFieldError(field_name)

    @staticmethod
    def _validate_choice(value, field_name, allowed):
        """
        Validate that a value is in a set of allowed choices.

        @param value: The value to validate
        @param field_name: Human-readable field name
        @param allowed: Iterable of allowed values
        @raises InvalidValueError: if value is not in allowed set
        @return: The value if valid (or the first allowed value as default)
        """
        if value not in allowed:
            # Default to first allowed value instead of raising
            return list(allowed)[0] if allowed else value
        return value

    @staticmethod
    def _check_publisher(user):
        """
        POLYMORPHISM: Check if a user can publish (delegates to user.can_publish()).

        Raises PermissionDeniedError if the user lacks publisher rights.

        @param user: User object with can_publish() method
        @raises PermissionDeniedError: if user is not a publisher
        """
        if not user.can_publish():
            raise PermissionDeniedError('perform this action', user.role)

    @staticmethod
    def _sanitize(value):
        """Strip whitespace from a string value. Returns empty string for None."""
        return str(value).strip() if value else ''
# AuthService
# ===========================================================================

class AuthService(BaseService):
    """
    Authentication and authorization business logic.

    INHERITANCE: Extends BaseService — inherits validation helpers.

    For testing, inject a mock or in-memory UserRepository.
    """

    def __init__(self, user_repo=None):
        """
        @param user_repo: UserRepository instance (injected, not lazy-imported).
        """
        self._user_repo = user_repo or UserRepository()

    # -- public API -------------------------------------------------------

    def register_user(self, username, password, role, barangay=''):
        """
        Register a new user account.

        Validates required fields, checks for duplicate usernames,
        hashes the password with werkzeug, and persists the user.

        @param username: Desired login name (must be unique)
        @param password: Plain-text password (hashed before storage)
        @param role: User role — 'citizen' or 'publisher'
        @param barangay: User's barangay (e.g. 'Payatas', 'Bagong Silangan')
        @return: (success: bool, message: str)
        """
        try:
            # Validate all required fields are non-empty
            self._require(username, 'Username')
            self._require(password, 'Password')
            self._require(role, 'Role')
        except RequiredFieldError as e:
            return False, str(e)

        # Check if username is already taken
        if self._user_repo.find_by_username(username):
            return False, "Username already exists. Try another one."

        # Hash the password for secure storage (never store plain text!)
        hashed_password = generate_password_hash(password)
        if self._user_repo.create(username, hashed_password, role, barangay):
            return True, "Registration successful! Please log in."
        return False, "Registration failed"

    def authenticate_user(self, username, password):
        """
        Authenticate a user by username and password.

        Looks up the user in the database, then uses werkzeug's
        check_password_hash to compare the provided password against
        the stored hash.

        @param username: Login name
        @param password: Plain-text password to verify
        @return: (success: bool, user: User or None)
        """
        user_data = self._user_repo.find_by_username(username)
        if user_data and check_password_hash(user_data['password_hash'], password):
            # Convert raw DB row to a User domain object via factory
            user = create_user_from_db(user_data)
            return True, user
        return False, None


# ===========================================================================
# PostService
# ===========================================================================

class PostService(BaseService):
    """
    Post, comment, and reaction business logic.

    INHERITANCE: Extends BaseService — inherits _require, _validate_choice,
    _check_publisher, and _sanitize helpers.
    """

    ALLOWED_EMOJI = {'👍', '❤️', '😄', '😢', '😡', '🎉'}
    VALID_CATEGORIES = ['Announcement', 'Emergency', 'Health', 'Project']

    def __init__(self, post_repo=None):
        """
        @param post_repo: PostRepository instance (injected).
        """
        self._post_repo = post_repo or PostRepository()

    # -- feed / detail ----------------------------------------------------

    def get_feed(self, search=None, category=None, sort=None):
        """
        Get published posts for the main feed.

        Supports optional filtering by search query and category,
        and sorting by newest, oldest, or title.

        @param search: Text to search in title and content
        @param category: Filter by post category (Announcement, Emergency, Health, Project)
        @param sort: Sort order — 'newest', 'oldest', 'title'
        @return: List of post dicts
        """
        posts = self._post_repo.get_all_posts(search=search, category=category, sort=sort)
        return [dict(p) for p in posts]

    def get_post_detail(self, post_id, user_id=None):
        """
        Get a single post with its comments, reaction counts, and user's reaction.

        This aggregates data from three related tables:
          - posts (the announcement itself)
          - comments (user discussion)
          - reactions (emoji counts + current user's reaction)

        @param post_id: Post's primary key
        @param user_id: Current user's ID (to check their reaction)
        @return: Dict with 'post', 'comments', 'reaction_counts', 'user_reaction', or None
        """
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
        """
        Add a comment to an announcement post.

        @param post_id: Post's primary key
        @param user_id: Comment author's user ID
        @param content: Comment text (required, non-empty)
        @return: (comment_dict, error) — error is None on success
        """
        try:
            self._require(content, 'Comment')
        except RequiredFieldError as e:
            return None, str(e)
        comment = self._post_repo.add_comment(post_id, user_id, self._sanitize(content))
        return dict(comment), None

    # -- reactions --------------------------------------------------------

    def toggle_reaction(self, post_id, user_id, emoji):
        """
        Toggle an emoji reaction on a post.

        Each user can have exactly ONE reaction per post:
          - Clicking the same emoji again → removes it
          - Clicking a different emoji    → changes to the new emoji
          - No existing reaction          → adds the new emoji

        @param post_id: Post's primary key
        @param user_id: Reacting user's ID
        @param emoji: Emoji character (must be in ALLOWED_EMOJI set)
        @return: (result_dict, error) — result includes action, counts, and user's reaction
        """
        if emoji not in self.ALLOWED_EMOJI:
            return None, f"Invalid emoji. Use: {', '.join(sorted(self.ALLOWED_EMOJI))}"
        action, _ = self._post_repo.toggle_reaction(post_id, user_id, emoji)

        # Re-fetch fresh counts after mutation
        reaction_counts = [dict(r) for r in self._post_repo.get_reactions_for_post(post_id)]
        user_reaction = self._post_repo.get_user_reaction(post_id, user_id)
        return {
            'action': action,          # 'added', 'removed', or 'changed'
            'reaction_counts': reaction_counts,
            'user_reaction': user_reaction,
        }, None

    # -- publisher-only post management -----------------------------------

    def create_post(self, user, title, content, category='Announcement', image_path=''):
        """
        Create a new post. ONLY publisher (barangay captain) can publish.
        Returns (post_dict, error).
        """
        try:
            self._check_publisher(user)
            self._require(title, 'Title')
            self._require(content, 'Content')
        except (PermissionDeniedError, RequiredFieldError) as e:
            return None, str(e)

        category = self._validate_choice(category, 'category', self.VALID_CATEGORIES)
        post = self._post_repo.create_post(
            user.id, self._sanitize(title), self._sanitize(content),
            category, image_path=image_path
        )
        return (post, None) if post else (None, "Failed to create post.")

    def update_post(self, user, post_id, title, content):
        """Update a post. ONLY the publisher who created it can edit."""
        try:
            self._check_publisher(user)
            self._require(title, 'Title')
            self._require(content, 'Content')
        except (PermissionDeniedError, RequiredFieldError) as e:
            return None, str(e)

        post = self._post_repo.update_post(post_id, user.id, self._sanitize(title), self._sanitize(content))
        return (post, None) if post else (None, "Post not found or you are not authorized to edit it.")

    def delete_post(self, user, post_id):
        """Delete a post. ONLY the publisher who created it can delete."""
        try:
            self._check_publisher(user)
        except PermissionDeniedError as e:
            return False, str(e)
        self._post_repo.delete_post(post_id, user.id)
        return True, None


# ===========================================================================
# VoiceService — Citizens' Voice forum business logic
# ===========================================================================

class VoiceService(BaseService):
    """
    Business logic for the Citizens' Voice forum.

    INHERITANCE: Extends BaseService.
    Any authenticated user can post topics, comment, and vote.
    Publisher (barangay captain) comments are flagged as official responses.
    """

    CATEGORIES = ['General', 'Grievance', 'Suggestion', 'Question', 'Announcement']
    VALID_STATUSES = {'open', 'resolved', 'closed'}

    def __init__(self, voice_repo=None):
        """
        @param voice_repo: VoiceRepository instance (injected).
        """
        self._repo = voice_repo or VoiceRepository()

    # -- voice posts -----------------------------------------------------

    def get_posts(self, category=None, status=None, search=None, sort=None):
        """
        Get all Citizens' Voice posts with optional filters.

        @param category: Filter by category (Grievance, Suggestion, etc.)
        @param status: Filter by status (open, resolved, closed)
        @param search: Search in title AND author username
        @param sort: Sort order — 'newest', 'oldest', 'most_voted', 'most_commented'
        @return: List of voice post dicts
        """
        return self._repo.get_all(category=category, status=status,
                                  search=search, sort=sort)

    def get_post_detail(self, voice_post_id, user_id=None):
        """
        Get a single voice post with its comments and the current user's vote.

        @param voice_post_id: Voice post's primary key
        @param user_id: Current user's ID (to check their vote)
        @return: Dict with 'post', 'comments', 'user_vote', or None if not found
        """
        post = self._repo.get_by_id(voice_post_id)
        if not post:
            return None
        return {
            'post': post,
            'comments': self._repo.get_comments(voice_post_id),
            'user_vote': self._repo.get_user_vote(voice_post_id, user_id) if user_id else None,
        }

    def create_post(self, user_id, title, content, category='General'):
        """
        Create a new Citizens' Voice post. Any authenticated user can post.

        @param user_id: Author's user ID
        @param title: Post title (required)
        @param content: Post body (required)
        @param category: Category (defaults to 'General')
        @return: (post_dict, error)
        """
        try:
            self._require(title, 'Title')
            self._require(content, 'Content')
        except RequiredFieldError as e:
            return None, str(e)
        category = self._validate_choice(category, 'category', self.CATEGORIES)
        post = self._repo.create(user_id, self._sanitize(title), self._sanitize(content), category)
        return (post, None) if post else (None, "Failed to create post.")

    def update_status(self, voice_post_id, status):
        """
        Update a voice post's status.

        Typically called by a publisher to mark a grievance as 'resolved'
        or 'closed' after addressing it.

        @param voice_post_id: Voice post's primary key
        @param status: New status — 'open', 'resolved', or 'closed'
        @return: (success: bool, error)
        """
        if status not in self.VALID_STATUSES:
            return False, f"Invalid status. Must be one of: {', '.join(self.VALID_STATUSES)}"
        self._repo.update_status(voice_post_id, status)
        return True, None

    def delete_post(self, voice_post_id, user_id):
        """
        Delete a voice post. Only the original author can delete.

        @param voice_post_id: Voice post's primary key
        @param user_id: Author's user ID (for authorization)
        @return: (success: bool, error)
        """
        self._repo.delete(voice_post_id, user_id)
        return True, None

    # -- comments --------------------------------------------------------

    def add_comment(self, voice_post_id, user_id, content, role):
        """
        Add a comment to a voice post.

        If the commenter is a publisher (barangay captain), the comment
        is automatically flagged as an official response for distinct UI styling.

        @param voice_post_id: Voice post's primary key
        @param user_id: Comment author's user ID
        @param content: Comment text
        @param role: Author's role ('citizen' or 'publisher')
        @return: (comment_dict, error)
        """
        try:
            self._require(content, 'Comment')
        except RequiredFieldError as e:
            return None, str(e)
        is_official = (role == 'publisher')
        comment = self._repo.add_comment(voice_post_id, user_id, self._sanitize(content), is_official)
        return (comment, None) if comment else (None, "Failed to add comment.")

    # -- votes -----------------------------------------------------------

    def toggle_vote(self, voice_post_id, user_id, vote_type):
        """
        Toggle an up/down vote on a voice post.

        Each user gets ONE vote per post:
          - Same vote type again → removes vote
          - Different vote type    → changes vote
          - No existing vote       → adds vote

        @param voice_post_id: Voice post's primary key
        @param user_id: Voting user's ID
        @param vote_type: 'up' or 'down'
        @return: (result_dict, error) — result includes action, net_change, user_vote
        """
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

class ProjectService(BaseService):
    """
    Business logic for Barangay Projects.

    INHERITANCE: Extends BaseService.
    Only publisher (barangay captain) can create, update, or delete projects.
    """

    VALID_STATUSES = ['ongoing', 'completed', 'planned']

    def __init__(self, project_repo=None):
        """
        @param project_repo: ProjectRepository instance (injected).
        """
        self._repo = project_repo or ProjectRepository()

    # -- read ------------------------------------------------------------

    def get_all(self):
        """
        Get all barangay projects, newest first.

        @return: List of project dicts
        """
        return self._repo.get_all()

    def get_by_id(self, project_id):
        """
        Get a single project by its ID.

        @param project_id: Project's primary key
        @return: Project dict or None if not found
        """
        return self._repo.get_by_id(project_id)

    # -- publisher-only mutations ----------------------------------------

    def create_project(self, user, title, description, status='ongoing',
                       budget=0, location='', image_url='',
                       start_date='', end_date='',
                       latitude=None, longitude=None):
        """
        Create a new barangay project. ONLY publisher can create.

        Validates required fields, checks publisher authorization,
        validates the date range (end >= start), and persists.

        @param user: Current user (must be publisher)
        @param title: Project name (required)
        @param description: Detailed description (required)
        @param status: 'ongoing', 'completed', or 'planned'
        @param budget: Budget amount in PHP
        @param location: Physical location of the project
        @param image_url: Relative URL of project image
        @param start_date: Start date (YYYY-MM-DD)
        @param end_date: Expected completion date (YYYY-MM-DD)
        @param latitude: GPS latitude for map marker
        @param longitude: GPS longitude for map marker
        @return: (project_dict, error)
        """
        try:
            self._check_publisher(user)
            self._require(title, 'Title')
            self._require(description, 'Description')
        except (PermissionDeniedError, RequiredFieldError) as e:
            return None, str(e)

        status = self._validate_choice(status, 'status', self.VALID_STATUSES)

        # Validate date range
        if start_date and end_date and end_date < start_date:
            return None, "End date cannot be before start date."

        project = self._repo.create(
            title=self._sanitize(title),
            description=self._sanitize(description),
            status=status, budget=budget,
            location=self._sanitize(location),
            image_url=self._sanitize(image_url),
            start_date=start_date, end_date=end_date,
            publisher_id=user.id,
            latitude=latitude, longitude=longitude
        )
        return (project, None) if project else (None, "Failed to create project.")

    def update_project(self, user, project_id, title, description, status,
                       budget, location, image_url, start_date, end_date,
                       latitude=None, longitude=None):
        """
        Update an existing project. ONLY the publisher who created it can edit.

        @param user: Current user (must be publisher)
        @param project_id: Project's primary key
        @param title: Updated title (required)
        @param description: Updated description (required)
        @param status: Updated status
        @param budget: Updated budget
        @param location: Updated location
        @param image_url: Updated image URL
        @param start_date: Updated start date
        @param end_date: Updated end date
        @param latitude: Updated GPS latitude
        @param longitude: Updated GPS longitude
        @return: (project_dict, error)
        """
        try:
            self._check_publisher(user)
            self._require(title, 'Title')
            self._require(description, 'Description')
        except (PermissionDeniedError, RequiredFieldError) as e:
            return None, str(e)

        status = self._validate_choice(status, 'status', self.VALID_STATUSES)

        if start_date and end_date and end_date < start_date:
            return None, "End date cannot be before start date."

        project = self._repo.update(
            project_id=project_id, publisher_id=user.id,
            title=self._sanitize(title),
            description=self._sanitize(description),
            status=status, budget=budget,
            location=self._sanitize(location),
            image_url=self._sanitize(image_url),
            start_date=start_date, end_date=end_date,
            latitude=latitude, longitude=longitude
        )
        return (project, None) if project else (None, "Project not found or you are not authorized to edit it.")

    def delete_project(self, user, project_id):
        """
        Delete a project. ONLY the publisher who created it can delete.

        @param user: Current user (must be publisher)
        @param project_id: Project's primary key
        @return: (success: bool, error)
        """
        try:
            self._check_publisher(user)
        except PermissionDeniedError as e:
            return False, str(e)
        self._repo.delete(project_id, user.id)
        return True, None


# ===========================================================================
# DocumentService — Transparency Documents business logic
# ===========================================================================

class DocumentService(BaseService):
    """
    Business logic for Transparency Documents.

    INHERITANCE: Extends BaseService.

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
        @param document_repo: DocumentRepository instance (injected)
        @param config: Config instance (for upload_folder and allowed_extensions)
        """
        self._repo = document_repo or DocumentRepository()
        self._config = config

    # -- read (all users) ------------------------------------------------

    def get_all(self):
        """
        Get all transparency documents, newest first.

        Accessible to all authenticated users (both citizens and publishers).

        @return: List of document dicts
        """
        return self._repo.get_all()

    def get_by_category(self, category):
        """
        Get documents filtered by category.

        @param category: Category name (e.g., 'Budget Report', 'Audit Report')
        @return: List of document dicts in the given category
        """
        return self._repo.get_by_category(category)

    def get_categories(self):
        """
        Get distinct document categories.

        @return: List of category strings
        """
        return self._repo.get_categories()

    def get_by_id(self, document_id):
        """
        Get a single document by its ID.

        @param document_id: Document's primary key
        @return: Document dict or None if not found
        """
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

        Uses a timestamp prefix (YYYYMMDD_HHMMSS) to avoid filename collisions
        when multiple users upload files with the same name.

        @param file: Flask FileStorage object (already validated)
        @param filename: Original filename from the user
        @return: Relative URL path to the saved file (e.g., '/static/uploads/20260604_abc_report.pdf')
        """
        import os
        from datetime import datetime

        upload_folder = self._config.upload_folder if self._config else 'static/uploads'

        # Ensure the upload directory exists (create if not)
        os.makedirs(upload_folder, exist_ok=True)

        # Generate unique filename: timestamp_originalname
        # Example: 20260604_143052_Q1_Budget_Report.pdf
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{timestamp}_{filename}"

        filepath = os.path.join(upload_folder, safe_name)
        file.save(filepath)

        # Return the relative URL for storage in the database and serving
        return f'/static/uploads/{safe_name}'

    # -- publisher-only mutations ----------------------------------------

    def create_document(self, user, title, description, category, file, published_date=''):
        """
        Upload a new transparency document. ONLY publisher can upload.

        Full workflow:
          1. Check publisher authorization via user.can_publish()
          2. Validate required fields (title)
          3. Validate the uploaded file (extension check)
          4. Calculate and format file size for display
          5. Save the file to disk with a unique name
          6. Create the database record with file metadata

        @param user: Current user (must be publisher)
        @param title: Document title
        @param description: Document description
        @param category: Document category (Budget Report, Audit Report, etc.)
        @param file: Flask FileStorage object (the uploaded file)
        @param published_date: Publication date string (YYYY-MM-DD), defaults to today
        @return: (document_dict, error)
        """
        # Authorization: only barangay captains can upload documents
        if not user.can_publish():
            return None, "Only the Barangay Captain can upload documents."

        # Validation: title is required
        if not title or not title.strip():
            return None, "Title is required."

        # Default invalid categories to 'General'
        if category not in self.VALID_CATEGORIES:
            category = 'General'

        # Validate file exists and has an allowed extension
        filename, error = self._validate_file(file)
        if error:
            return None, error

        # Calculate file size for display in the UI
        import os
        file.seek(0, os.SEEK_END)  # Move to end to get total size
        file_size_bytes = file.tell()
        file.seek(0)  # Reset to beginning so .save() works correctly

        # Format file size for human-readable display
        # Uses binary thresholds: < 1024 B, < 1024 KB, >= 1024 KB → MB
        if file_size_bytes < 1024:
            file_size = f"{file_size_bytes} B"
        elif file_size_bytes < 1024 * 1024:
            file_size = f"{file_size_bytes / 1024:.1f} KB"
        else:
            file_size = f"{file_size_bytes / (1024 * 1024):.1f} MB"

        # Save file to disk (returns relative URL like /static/uploads/20260604_report.pdf)
        file_url = self._save_file(file, filename)

        # Use today's date if the publisher didn't specify one
        if not published_date:
            from datetime import date
            published_date = date.today().isoformat()

        # Persist document metadata to the database
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

        Performs two cleanup steps:
          1. Removes the file from disk (if it exists)
          2. Removes the database record

        This two-step approach prevents orphaned files on disk.

        @param user: Current user (must be publisher)
        @param document_id: ID of the document to delete
        @return: (success: bool, error)
        """
        import os

        # Authorization check
        if not user.can_publish():
            return False, "Only the Barangay Captain can delete documents."

        # Look up the document to get its file path
        doc = self._repo.get_by_id(document_id)
        if not doc:
            return False, "Document not found."

        # Step 1: Delete the physical file from disk
        file_url = doc.get('file_url', '')
        if file_url and file_url != '#':
            # Convert relative URL (e.g., /static/uploads/report.pdf)
            # to an absolute filesystem path.
            # __file__ is service.py → dirname(__file__) is the project root
            project_root = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(project_root, file_url.lstrip('/'))
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except OSError:
                # File already deleted or permission issue — non-critical,
                # proceed with database cleanup anyway
                pass

        # Step 2: Delete the database record
        self._repo.delete(document_id, user.id)
        return True, None


# ===========================================================================
# BarangayService — Barangay landing-page business logic
# ===========================================================================

class BarangayService(BaseService):
    """
    Business logic for managing barangay landing-page configuration.

    INHERITANCE: Extends BaseService.

    Publishers can create and edit their barangay's public landing page.
    All users can view any barangay's landing page.
    """

    def __init__(self, barangay_repo=None):
        """
        @param barangay_repo: BarangayRepository instance (injected).
        """
        self._repo = barangay_repo or BarangayRepository()

    # -- read (all users) ------------------------------------------------

    def get_all(self):
        """
        Get all barangays.

        @return: List of barangay dicts
        """
        return self._repo.get_all()

    def get_by_id(self, barangay_id):
        """
        Get a single barangay by its ID.

        @param barangay_id: Barangay's primary key
        @return: Barangay dict or None if not found
        """
        return self._repo.get_by_id(barangay_id)

    def get_by_publisher(self, publisher_id):
        """
        Get the barangay managed by a specific publisher.

        @param publisher_id: Publisher's user ID
        @return: Barangay dict or None
        """
        return self._repo.get_by_publisher(publisher_id)

    def get_first(self):
        """
        Get the default/first barangay (fallback for generic landing page).

        @return: Barangay dict or None
        """
        return self._repo.get_first()

    # -- publisher-only mutations ----------------------------------------

    def create_barangay(self, user, name, description='', address='',
                        phone='', email='', facebook='',
                        office_hours_weekday='8:00 AM – 5:00 PM',
                        office_hours_saturday='8:00 AM – 12:00 PM',
                        motto='', latitude=14.71309, longitude=121.10063):
        """
        Create a new barangay landing page. ONLY publisher can create.

        Each publisher can manage exactly ONE barangay. If they already
        have one, they must edit it instead of creating a new one.

        @param user: Current user (must be publisher)
        @param name: Barangay name (required)
        @param description: Brief description of the barangay
        @param address: Full physical address (required)
        @param phone: Contact phone number
        @param email: Official email address
        @param facebook: Facebook page URL or handle
        @param office_hours_weekday: Weekday office hours display string
        @param office_hours_saturday: Saturday office hours display string
        @param motto: Barangay motto/tagline
        @param latitude: GPS latitude for map pin (default: Payatas, QC)
        @param longitude: GPS longitude for map pin (default: Payatas, QC)
        @return: (barangay_dict, error)
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can create a barangay page."
        if not name or not name.strip():
            return None, "Barangay name is required."
        if not address or not address.strip():
            return None, "Barangay address is required."

        # Check if publisher already manages a barangay
        existing = self._repo.get_by_publisher(user.id)
        if existing:
            return None, "You already manage a barangay. Edit it instead."

        barangay = self._repo.create(
            name=name.strip(),
            description=description.strip() if description else '',
            address=address.strip() if address else '',
            phone=phone.strip() if phone else '',
            email=email.strip() if email else '',
            facebook=facebook.strip() if facebook else '',
            office_hours_weekday=office_hours_weekday,
            office_hours_saturday=office_hours_saturday,
            motto=motto.strip() if motto else '',
            latitude=latitude,
            longitude=longitude,
            publisher_id=user.id
        )
        return (barangay, None) if barangay else (None, "Failed to create barangay page.")

    def update_barangay(self, user, barangay_id, **fields):
        """
        Update a barangay's landing-page info. ONLY the owning publisher.

        Only the fields provided in **fields are updated — others are left
        unchanged (partial update / PATCH semantics).

        @param user: Current user (must be publisher who owns the barangay)
        @param barangay_id: Barangay's primary key
        @param fields: Keyword args for fields to update (name, description, etc.)
        @return: (barangay_dict, error)
        """
        if not user.can_publish():
            return None, "Only the Barangay Captain can edit the barangay page."

        barangay = self._repo.get_by_id(barangay_id)
        if not barangay:
            return None, "Barangay not found."
        if barangay.get('publisher_id') != user.id:
            return None, "You are not authorized to edit this barangay."

        updated = self._repo.update(barangay_id, user.id, **fields)
        return (updated, None) if updated else (None, "Failed to update barangay page.")

    def delete_barangay(self, user, barangay_id):
        """
        Delete a barangay page. ONLY the owning publisher can delete.

        Verifies both that the user is a publisher AND that they own
        the specific barangay being deleted.

        @param user: Current user (must be the owning publisher)
        @param barangay_id: Barangay's primary key
        @return: (success: bool, error)
        """
        if not user.can_publish():
            return False, "Only the Barangay Captain can delete the barangay page."

        barangay = self._repo.get_by_id(barangay_id)
        if not barangay:
            return False, "Barangay not found."
        if barangay.get('publisher_id') != user.id:
            return False, "You are not authorized to delete this barangay."

        self._repo.delete(barangay_id, user.id)
        return True, None
