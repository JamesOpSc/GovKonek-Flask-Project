"""
GovKonek Repository Module

Database Layer - ABSTRACTION PRINCIPLE
Purpose: The Repository pattern abstracts all database operations.
Benefits: Database code is isolated, easy to change database without touching business logic.
All database queries are centralized in one place for easier maintenance and testing.

REFACTORED for testability:
    - Each repository accepts a `db_path` in its constructor (dependency injection).
    - Instance methods use `self._db_path` instead of a module-level global.
    - In tests, inject `':memory:'` to get an isolated database.
    - Backward-compatible static methods delegate to a default singleton instance.

OOP PRINCIPLES DEMONSTRATED:
    - INHERITANCE: All repositories extend BaseRepository (like Vehicle → Car/Truck)
    - ABSTRACTION: BaseRepository defines the interface; subclasses implement specifics
    - ENCAPSULATION: _db_path is private; DBContext manages connection lifecycle
    - EXCEPTION HANDLING: DatabaseError wraps sqlite3 errors with domain context
"""

import sqlite3
from abc import ABC
from config import DATABASE_NAME
from exceptions import (
    DatabaseError, ConnectionError, RecordNotFoundError, DuplicateRecordError
)


# ===========================================================================
# DBContext — Context Manager for Database Connections
# ===========================================================================

class DBContext:
    """
    Context manager for SQLite database connections.

    From the crash course (hardware_layer.py): uses `with` for automatic
    resource cleanup.  This implements:
      - EXCEPTION HANDLING: Automatically rolls back on error, closes on exit
      - RESOURCE MANAGEMENT: Guarantees connection.close() via __exit__
      - ABSTRACTION: Hides connection lifecycle from repository methods

    Usage:
        with DBContext('govkonek.db') as db:
            db.execute('SELECT * FROM users')
        # connection auto-closed here
    """

    def __init__(self, db_path):
        """
        @param db_path: Path to the SQLite database file.
        """
        self._db_path = db_path
        self._connection = None

    def __enter__(self):
        """Open the connection when entering the `with` block."""
        try:
            self._connection = sqlite3.connect(self._db_path)
            self._connection.row_factory = sqlite3.Row
            return self._connection
        except sqlite3.Error as e:
            raise ConnectionError(self._db_path, original_error=e)

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close the connection when leaving the `with` block.

        EXCEPTION HANDLING (from lecture):
          - If an exception occurred, roll back any uncommitted changes.
          - Always close the connection (like `finally`).
        """
        if self._connection:
            if exc_type is not None:
                # An exception occurred — rollback to prevent partial writes
                try:
                    self._connection.rollback()
                except sqlite3.Error:
                    pass  # connection may already be broken
            self._connection.close()
        # Return False so exceptions propagate (don't suppress them)
        return False


# ---------------------------------------------------------------------------
# Legacy: shared connection factory (kept for backward compatibility)
# ---------------------------------------------------------------------------

def _connect(db_path):
    """Create a connection with Row factory enabled. Legacy helper."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================================
# BaseRepository — Abstract Base for All Repositories
# ===========================================================================

class BaseRepository(ABC):
    """
    Abstract base class for all repository classes.

    INHERITANCE (from lecture): Just like Vehicle is the base class for
    Car, Truck, Motorcycle, this BaseRepository is the base for
    UserRepository, PostRepository, ProjectRepository, etc.

    Benefits:
      - DRY: __init__ and _get_db are defined ONCE, not 6 times
      - CONSISTENT: All repos use the same connection pattern
      - TESTABLE: db_path injection works identically for all repos
      - EXTENSIBLE: Add new repository by subclassing, not copy-pasting

    Subclasses only need to implement their domain-specific methods.
    """

    def __init__(self, db_path=None):
        """
        Initialize the repository with an injectable database path.

        @param db_path: Path to SQLite database file.
                        Defaults to config.DATABASE_NAME.
                        Use ':memory:' for isolated testing.
        """
        self._db_path = db_path or DATABASE_NAME

    # -- connection management -------------------------------------------

    def _get_db(self):
        """
        Create and return a new database connection.

        All subclasses inherit this method — no need to redefine it.
        This is INHERITANCE in action: shared behavior defined once.
        """
        return _connect(self._db_path)

    def _execute(self, query, params=(), fetch='all', commit=False):
        """
        Execute a query with automatic exception handling.

        EXCEPTION HANDLING (from lecture): Wraps sqlite3 errors in
        domain-specific DatabaseError, providing meaningful context.

        @param query: SQL query string
        @param params: Query parameters tuple
        @param fetch: 'all', 'one', or None (for INSERT/UPDATE/DELETE)
        @param commit: If True, commit after executing
        @return: Fetched rows, or cursor for non-fetch operations
        """
        conn = self._get_db()
        try:
            cursor = conn.execute(query, params)
            if commit:
                conn.commit()
            if fetch == 'all':
                return cursor.fetchall()
            elif fetch == 'one':
                return cursor.fetchone()
            return cursor
        except sqlite3.IntegrityError as e:
            raise DuplicateRecordError(
                entity='record', field='constraint', value=str(params)
            ) from e
        except sqlite3.Error as e:
            raise DatabaseError(
                f"Query failed: {query[:80]}...", original_error=e
            ) from e
        finally:
            conn.close()

    def _execute_write(self, query, params=()):
        """
        Execute a write query (INSERT/UPDATE/DELETE) and commit.
        Returns the cursor for accessing lastrowid.
        """
        return self._execute(query, params, fetch=None, commit=True)


# ===========================================================================
# UserRepository
# ===========================================================================

class UserRepository(BaseRepository):
    """
    Repository for user-related database operations.

    INHERITANCE: Extends BaseRepository — inherits __init__, _get_db,
    _execute, and _execute_write. Only defines user-specific queries.

    REFACTORED: Now instance-based. Pass `db_path` to the constructor.
    For backward compatibility, static methods still work using the default
    module-level singleton `_default_user_repo`.
    """

    # -- user CRUD --------------------------------------------------------

    def find_by_id(self, user_id):
        """Fetch a user by their ID."""
        return self._execute(
            'SELECT * FROM users WHERE id = ?', (user_id,), fetch='one'
        )

    def find_by_username(self, username):
        """Fetch a user by their username."""
        return self._execute(
            'SELECT * FROM users WHERE username = ?', (username,), fetch='one'
        )

    def create(self, username, hashed_password, role):
        """
        Insert a new user. Returns True on success, False on duplicate.

        EXCEPTION HANDLING: Catches DuplicateRecordError for duplicate usernames
        instead of letting raw sqlite3.IntegrityError propagate.
        """
        try:
            self._execute_write(
                'INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)',
                (username, hashed_password, role)
            )
            return True
        except DuplicateRecordError:
            return False

    def update_profile(self, user_id, email='', address='', phone_number='',
                       profile_picture=''):
        """Update a user's profile fields. Returns the updated user row."""
        self._execute_write(
            '''UPDATE users
               SET email = ?, address = ?, phone_number = ?, profile_picture = ?
               WHERE id = ?''',
            (email, address, phone_number, profile_picture, user_id)
        )
        return self.find_by_id(user_id)

    # -- backward-compatible static interface -----------------------------

    @staticmethod
    def get_db_connection():
        """Legacy: create a connection using the default database."""
        return _connect(DATABASE_NAME)


# ===========================================================================
# PostRepository
# ===========================================================================

class PostRepository(BaseRepository):
    """
    Repository for post, comment, and reaction database operations.

    INHERITANCE: Extends BaseRepository — inherits __init__, _get_db,
    _execute, and _execute_write.
    """

    # -- post CRUD --------------------------------------------------------

    def create_post(self, publisher_id, title, content, category='Announcement',
                     status='published', image_path=''):
        """Create a new post. Returns the created post as a dict."""
        cursor = self._execute_write(
            '''INSERT INTO posts (publisher_id, title, content, category, status, image_path)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (publisher_id, title, content, category, status, image_path)
        )
        post_id = cursor.lastrowid
        post = self._execute('''
            SELECT p.*, u.username as publisher_name
            FROM posts p JOIN users u ON p.publisher_id = u.id
            WHERE p.id = ?
        ''', (post_id,), fetch='one')
        return dict(post) if post else None

    def update_post(self, post_id, publisher_id, title, content):
        """Update a post. Only the owning publisher can update."""
        self._execute_write(
            'UPDATE posts SET title = ?, content = ? WHERE id = ? AND publisher_id = ?',
            (title, content, post_id, publisher_id)
        )
        post = self._execute('''
            SELECT p.*, u.username as publisher_name
            FROM posts p JOIN users u ON p.publisher_id = u.id
            WHERE p.id = ?
        ''', (post_id,), fetch='one')
        return dict(post) if post else None

    def delete_post(self, post_id, publisher_id):
        """Delete a post. Only the owning publisher can delete."""
        self._execute_write(
            'DELETE FROM posts WHERE id = ? AND publisher_id = ?',
            (post_id, publisher_id)
        )
        return True

    def get_all_posts(self, search=None, category=None, sort='newest'):
        """
        Fetch published posts with optional search, category filter, and sorting.

        @param search: Text to search in title and content (case-insensitive).
        @param category: Filter by post category (e.g. 'Announcement', 'Emergency', 'Health', 'Project').
                         Pass None or empty string for all categories.
        @param sort: Sort order — 'newest' (default), 'oldest', 'title'.
        @return: List of sqlite3.Row objects.
        """
        query = '''
            SELECT p.*, u.username as publisher_name
            FROM posts p
            JOIN users u ON p.publisher_id = u.id
            WHERE p.status = 'published'
        '''
        params = []

        if search and search.strip():
            query += ' AND (p.title LIKE ? OR p.content LIKE ?)'
            like_val = f'%{search.strip()}%'
            params.extend([like_val, like_val])

        if category and category.strip():
            query += ' AND p.category = ?'
            params.append(category.strip())

        # Sorting
        sort_map = {
            'newest': 'p.created_at DESC',
            'oldest': 'p.created_at ASC',
            'title': 'p.title ASC',
        }
        order_clause = sort_map.get(sort, 'p.created_at DESC')
        query += f' ORDER BY {order_clause}'

        return self._execute(query, tuple(params), fetch='all')

    def get_post_by_id(self, post_id):
        """Fetch a single post by ID."""
        return self._execute('''
            SELECT p.*, u.username as publisher_name
            FROM posts p
            JOIN users u ON p.publisher_id = u.id
            WHERE p.id = ?
        ''', (post_id,), fetch='one')

    # -- comments ---------------------------------------------------------

    def get_comments_for_post(self, post_id):
        """Fetch all comments for a post with usernames."""
        return self._execute('''
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.post_id = ?
            ORDER BY c.created_at ASC
        ''', (post_id,), fetch='all')

    def add_comment(self, post_id, user_id, content):
        """Add a comment. Returns the new comment as a Row."""
        cursor = self._execute_write(
            'INSERT INTO comments (post_id, user_id, content) VALUES (?, ?, ?)',
            (post_id, user_id, content)
        )
        comment_id = cursor.lastrowid
        return self._execute('''
            SELECT c.*, u.username
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        ''', (comment_id,), fetch='one')

    # -- reactions --------------------------------------------------------

    def get_reactions_for_post(self, post_id):
        """Fetch aggregated emoji counts for a post."""
        return self._execute('''
            SELECT emoji, COUNT(*) as count
            FROM reactions
            WHERE post_id = ?
            GROUP BY emoji
            ORDER BY count DESC
        ''', (post_id,), fetch='all')

    def get_user_reaction(self, post_id, user_id):
        """Get the emoji a specific user reacted with, or None."""
        reaction = self._execute(
            'SELECT emoji FROM reactions WHERE post_id = ? AND user_id = ?',
            (post_id, user_id), fetch='one'
        )
        return reaction['emoji'] if reaction else None

    def toggle_reaction(self, post_id, user_id, emoji):
        """
        Toggle a reaction:
          - same emoji  → remove   (returns 'removed')
          - different   → update   (returns 'changed')
          - none        → add      (returns 'added')
        """
        existing = self._execute(
            'SELECT id, emoji FROM reactions WHERE post_id = ? AND user_id = ?',
            (post_id, user_id), fetch='one'
        )

        if existing:
            if existing['emoji'] == emoji:
                self._execute_write(
                    'DELETE FROM reactions WHERE id = ?', (existing['id'],)
                )
                return 'removed', emoji
            else:
                self._execute_write(
                    'UPDATE reactions SET emoji = ? WHERE id = ?',
                    (emoji, existing['id'])
                )
                return 'changed', emoji
        else:
            self._execute_write(
                'INSERT INTO reactions (post_id, user_id, emoji) VALUES (?, ?, ?)',
                (post_id, user_id, emoji)
            )
            return 'added', emoji

    # -- backward-compatible static interface -----------------------------

    @staticmethod
    def get_db_connection():
        """Legacy: create a connection using the default database."""
        return _connect(DATABASE_NAME)


# ===========================================================================
# ProjectRepository
# ===========================================================================

class ProjectRepository(BaseRepository):
    """
    Repository for barangay project operations.

    INHERITANCE: Extends BaseRepository — inherits __init__, _get_db,
    _execute, and _execute_write.
    """

    def get_all(self):
        return [dict(p) for p in self._execute(
            'SELECT * FROM projects ORDER BY created_at DESC', fetch='all'
        )]

    def get_by_status(self, status):
        return [dict(p) for p in self._execute(
            'SELECT * FROM projects WHERE status = ? ORDER BY created_at DESC',
            (status,), fetch='all'
        )]

    def get_by_id(self, project_id):
        project = self._execute(
            'SELECT * FROM projects WHERE id = ?', (project_id,), fetch='one'
        )
        return dict(project) if project else None

    def create(self, title, description, status='ongoing', budget=0,
               location='', image_url='', start_date='', end_date='', publisher_id=None):
        """Create a new project. Returns the created project as a dict."""
        cursor = self._execute_write(
            '''INSERT INTO projects
               (title, description, status, budget, location, image_url, start_date, end_date, publisher_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (title, description, status, budget, location, image_url, start_date, end_date, publisher_id)
        )
        project = self._execute(
            'SELECT * FROM projects WHERE id = ?', (cursor.lastrowid,), fetch='one'
        )
        return dict(project) if project else None

    def update(self, project_id, publisher_id, title, description, status,
               budget, location, image_url, start_date, end_date):
        """Update a project. Only the owning publisher can update. Returns updated project or None."""
        self._execute_write(
            '''UPDATE projects
               SET title = ?, description = ?, status = ?, budget = ?,
                   location = ?, image_url = ?, start_date = ?, end_date = ?
               WHERE id = ? AND publisher_id = ?''',
            (title, description, status, budget, location, image_url,
             start_date, end_date, project_id, publisher_id)
        )
        project = self._execute(
            'SELECT * FROM projects WHERE id = ?', (project_id,), fetch='one'
        )
        return dict(project) if project else None

    def delete(self, project_id, publisher_id):
        """Delete a project. Only the owning publisher can delete."""
        self._execute_write(
            'DELETE FROM projects WHERE id = ? AND publisher_id = ?',
            (project_id, publisher_id)
        )
        return True


# ===========================================================================
# ServiceRepository
# ===========================================================================

class ServiceRepository(BaseRepository):
    """
    Repository for e-services operations.

    INHERITANCE: Extends BaseRepository.
    """

    def get_all(self):
        return [dict(s) for s in self._execute(
            'SELECT * FROM services WHERE is_active = 1 ORDER BY category, name',
            fetch='all'
        )]

    def get_by_category(self, category):
        return [dict(s) for s in self._execute(
            'SELECT * FROM services WHERE category = ? AND is_active = 1 ORDER BY name',
            (category,), fetch='all'
        )]

    def get_categories(self):
        return [c['category'] for c in self._execute(
            'SELECT DISTINCT category FROM services WHERE is_active = 1 ORDER BY category',
            fetch='all'
        )]


# ===========================================================================
# DocumentRepository
# ===========================================================================

class DocumentRepository(BaseRepository):
    """
    Repository for transparency document operations.

    INHERITANCE: Extends BaseRepository.
    """

    def get_all(self):
        return [dict(d) for d in self._execute(
            'SELECT * FROM documents ORDER BY published_date DESC', fetch='all'
        )]

    def get_by_category(self, category):
        return [dict(d) for d in self._execute(
            'SELECT * FROM documents WHERE category = ? ORDER BY published_date DESC',
            (category,), fetch='all'
        )]

    def get_categories(self):
        return [c['category'] for c in self._execute(
            'SELECT DISTINCT category FROM documents ORDER BY category', fetch='all'
        )]

    # -- document CRUD (publisher-only mutations) ------------------------

    def create(self, title, description, category, file_url, file_size,
               published_date, publisher_id):
        """Create a new transparency document. Returns the created document as a dict."""
        cursor = self._execute_write(
            '''INSERT INTO documents
               (title, description, category, file_url, file_size, published_date)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (title, description, category, file_url, file_size, published_date)
        )
        doc = self._execute(
            'SELECT * FROM documents WHERE id = ?', (cursor.lastrowid,), fetch='one'
        )
        return dict(doc) if doc else None

    def get_by_id(self, document_id):
        """Fetch a single document by ID."""
        doc = self._execute(
            'SELECT * FROM documents WHERE id = ?', (document_id,), fetch='one'
        )
        return dict(doc) if doc else None

    def delete(self, document_id, publisher_id):
        """
        Delete a transparency document.

        @param document_id: ID of the document to delete
        @param publisher_id: Publisher's user ID (for authorization — kept for
                             future per-publisher ownership tracking)
        """
        self._execute_write(
            'DELETE FROM documents WHERE id = ?', (document_id,)
        )
        return True


# ===========================================================================
# VoiceRepository — Citizens' Voice forum
# ===========================================================================

class VoiceRepository(BaseRepository):
    """
    Repository for Citizens' Voice forum operations.

    INHERITANCE: Extends BaseRepository.
    """

    # -- voice posts CRUD ------------------------------------------------

    def get_all(self, category=None, status=None):
        """Fetch all voice posts with author names, newest first. Optional filters."""
        query = '''
            SELECT vp.*, u.username as author_name, u.role as author_role,
                   (SELECT COUNT(*) FROM voice_comments vc WHERE vc.voice_post_id = vp.id) as comment_count
            FROM voice_posts vp
            JOIN users u ON vp.user_id = u.id
            WHERE 1=1
        '''
        params = []
        if category:
            query += ' AND vp.category = ?'
            params.append(category)
        if status:
            query += ' AND vp.status = ?'
            params.append(status)
        query += ' ORDER BY vp.created_at DESC'
        return [dict(p) for p in self._execute(query, tuple(params), fetch='all')]

    def get_by_id(self, voice_post_id):
        """Fetch a single voice post with author info."""
        post = self._execute('''
            SELECT vp.*, u.username as author_name, u.role as author_role,
                   (SELECT COUNT(*) FROM voice_comments vc WHERE vc.voice_post_id = vp.id) as comment_count
            FROM voice_posts vp
            JOIN users u ON vp.user_id = u.id
            WHERE vp.id = ?
        ''', (voice_post_id,), fetch='one')
        return dict(post) if post else None

    def create(self, user_id, title, content, category='General'):
        """Create a new voice post. Returns the created post as a dict."""
        cursor = self._execute_write(
            'INSERT INTO voice_posts (user_id, title, content, category) VALUES (?, ?, ?, ?)',
            (user_id, title, content, category)
        )
        post = self._execute('''
            SELECT vp.*, u.username as author_name, u.role as author_role, 0 as comment_count
            FROM voice_posts vp
            JOIN users u ON vp.user_id = u.id
            WHERE vp.id = ?
        ''', (cursor.lastrowid,), fetch='one')
        return dict(post) if post else None

    def update_status(self, voice_post_id, status):
        """Update the status of a voice post (open/resolved/closed)."""
        self._execute_write(
            'UPDATE voice_posts SET status = ? WHERE id = ?',
            (status, voice_post_id)
        )
        return True

    def delete(self, voice_post_id, user_id):
        """Delete a voice post. Only the author can delete."""
        self._execute_write(
            'DELETE FROM voice_posts WHERE id = ? AND user_id = ?',
            (voice_post_id, user_id)
        )
        return True

    def get_categories(self):
        """Get distinct categories used in voice posts."""
        return [c['category'] for c in self._execute(
            'SELECT DISTINCT category FROM voice_posts ORDER BY category', fetch='all'
        )]

    # -- voice comments --------------------------------------------------

    def get_comments(self, voice_post_id):
        """Fetch all comments for a voice post with author info."""
        return [dict(c) for c in self._execute('''
            SELECT vc.*, u.username as author_name, u.role as author_role
            FROM voice_comments vc
            JOIN users u ON vc.user_id = u.id
            WHERE vc.voice_post_id = ?
            ORDER BY vc.created_at ASC
        ''', (voice_post_id,), fetch='all')]

    def add_comment(self, voice_post_id, user_id, content, is_official=False):
        """Add a comment to a voice post. Returns the new comment as a dict."""
        cursor = self._execute_write(
            'INSERT INTO voice_comments (voice_post_id, user_id, content, is_official) VALUES (?, ?, ?, ?)',
            (voice_post_id, user_id, content, 1 if is_official else 0)
        )
        comment = self._execute('''
            SELECT vc.*, u.username as author_name, u.role as author_role
            FROM voice_comments vc
            JOIN users u ON vc.user_id = u.id
            WHERE vc.id = ?
        ''', (cursor.lastrowid,), fetch='one')
        return dict(comment) if comment else None

    # -- voice votes -----------------------------------------------------

    def get_user_vote(self, voice_post_id, user_id):
        """Get the vote type a user cast on a voice post, or None."""
        vote = self._execute(
            'SELECT vote_type FROM voice_votes WHERE voice_post_id = ? AND user_id = ?',
            (voice_post_id, user_id), fetch='one'
        )
        return vote['vote_type'] if vote else None

    def toggle_vote(self, voice_post_id, user_id, vote_type):
        """
        Toggle a vote on a voice post:
          - same vote_type → remove (returns 'removed')
          - different     → update (returns 'changed')
          - none          → add    (returns 'added')
        Returns (action, net_change) where net_change is the delta to apply to vote_count.
        """
        existing = self._execute(
            'SELECT id, vote_type FROM voice_votes WHERE voice_post_id = ? AND user_id = ?',
            (voice_post_id, user_id), fetch='one'
        )

        if existing:
            if existing['vote_type'] == vote_type:
                # Remove vote
                self._execute_write(
                    'DELETE FROM voice_votes WHERE id = ?', (existing['id'],)
                )
                delta = -1 if vote_type == 'up' else 1
                self._execute_write(
                    'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                    (delta, voice_post_id)
                )
                return 'removed', delta
            else:
                # Change vote
                self._execute_write(
                    'UPDATE voice_votes SET vote_type = ? WHERE id = ?',
                    (vote_type, existing['id'])
                )
                delta = 2 if vote_type == 'up' else -2
                self._execute_write(
                    'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                    (delta, voice_post_id)
                )
                return 'changed', delta
        else:
            # Add new vote
            self._execute_write(
                'INSERT INTO voice_votes (voice_post_id, user_id, vote_type) VALUES (?, ?, ?)',
                (voice_post_id, user_id, vote_type)
            )
            delta = 1 if vote_type == 'up' else -1
            self._execute_write(
                'UPDATE voice_posts SET vote_count = vote_count + ? WHERE id = ?',
                (delta, voice_post_id)
            )
            return 'added', delta
